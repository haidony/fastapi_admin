import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import async_db_session
from app.core.dependencies import _authenticate
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.router_class import OperationLogRoute

from .schema import ChatQuerySchema
from .service import ChatService

WS_AI = APIRouter(
    route_class=OperationLogRoute,
    prefix="/ai/chat",
    tags=["智能助手WebSocket"],
)


async def _send_error_and_close(websocket: WebSocket, message: str) -> None:
    """发送错误消息并关闭连接"""
    try:
        await websocket.send_text(f"错误: {message}")
    except RuntimeError:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass


@WS_AI.websocket("/ws", name="WebSocket聊天")
async def websocket_chat_controller(websocket: WebSocket) -> None:
    """
    WebSocket 聊天接口。

    支持两种消息格式：
    1. 纯文本：直接发送消息内容
    2. JSON 格式：{"message": "消息内容", "session_id": "会话ID", "files": [...]}

    ws://127.0.0.1:8001/api/v1/ai/chat/ws?token=xxx
    """
    await websocket.accept()
    token = websocket.query_params.get("token")

    if not token:
        await _send_error_and_close(websocket, "未提供认证token，请重新登录")
        return

    try:
        # 认证：db 会话需在整个连接生命周期内保持打开（auth.db 供 ChatService 使用）
        redis = websocket.app.state.redis
        async with async_db_session() as db:
            auth = await _authenticate(token, db, redis)

            user = auth.user
            logger.info("WebSocket连接已建立: {} - 用户: {}", websocket.client, user.username if user else "未认证")

            # 消息循环
            while True:
                try:
                    data = await websocket.receive_text()
                    try:
                        message_data = json.loads(data)
                        query = ChatQuerySchema(**message_data)
                        logger.info("收到聊天查询: {} - 会话ID: {}", query, query.session_id)

                        chat_result = ChatService.chat_query(query=query, auth=auth)
                        async for chunk in chat_result:
                            if chunk:
                                try:
                                    await websocket.send_text(chunk)
                                except RuntimeError:
                                    logger.warning("WebSocket连接已关闭，停止发送消息")
                                    return
                    except json.JSONDecodeError:
                        logger.warning("收到非JSON消息: {}", data)
                        await websocket.send_text("消息格式错误，请发送JSON格式的消息")
                    except Exception as e:
                        logger.error("处理消息时出错: {}", e)
                        await websocket.send_text(f"处理消息时出错: {e}")

                except WebSocketDisconnect:
                    logger.info("WebSocket连接已断开: {}", websocket.client)
                    return

    except CustomException as e:
        # 认证失败等业务异常
        logger.warning("WebSocket认证失败: {}", e.msg)
        await _send_error_and_close(websocket, e.msg)
    except Exception as e:
        # 未知异常
        logger.exception("WebSocket未知异常: {}", e)
        await _send_error_and_close(websocket, "服务器内部错误")
