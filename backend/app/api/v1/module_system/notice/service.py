from app.core.base_schema import AuthSchema, BatchSetAvailable
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.excel_util import ExcelUtil

from .crud import NoticeCRUD
from .model import NoticeModel, NoticeReadModel
from .schema import (
    NoticeCreateSchema,
    NoticeOutSchema,
    NoticeQueryParam,
    NoticeUpdateSchema,
    PanelDataOut,
    PanelMessageItem,
)


class NoticeService:
    """
    公告管理模块服务层
    """

    @classmethod
    async def get_notice_detail_service(cls, auth: AuthSchema, id: int) -> NoticeOutSchema:
        """
        获取公告详情。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - id (int): 公告ID。

        返回:
        - Dict: 公告详情字典。
        """
        notice_obj = await NoticeCRUD(auth).get(id=id)
        if not notice_obj:
            raise CustomException(msg="公告不存在")
        return NoticeOutSchema.model_validate(notice_obj)

    @classmethod
    async def get_notice_list_service(
        cls,
        auth: AuthSchema,
        search: NoticeQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> list[NoticeOutSchema]:
        """
        获取公告列表。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - search (NoticeQueryParam | None): 查询参数模型。
        - order_by (list[dict] | None): 排序参数列表。

        返回:
        - list[dict]: 公告详情字典列表。
        """
        notice_obj_list = await NoticeCRUD(auth).list(
            search=search.__dict__ if search else {}, order_by=order_by
        )
        return [
            NoticeOutSchema.model_validate(notice_obj)
            for notice_obj in notice_obj_list
        ]

    @classmethod
    async def get_notice_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: NoticeQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> dict:
        """
        分页查询公告（数据库 OFFSET/LIMIT）。

        参数:
        - auth (AuthSchema): 认证信息模型
        - page_no (int): 页码（从 1 开始）
        - page_size (int): 每页条数
        - search (NoticeQueryParam | None): 查询条件
        - order_by (list[dict] | None): 排序字段列表

        返回:
        - dict: 分页结果（结构由 `CRUD.page` 返回约定）
        """
        offset = (page_no - 1) * page_size
        return await NoticeCRUD(auth).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search.__dict__ if search else {},
            out_schema=NoticeOutSchema,
        )

    @classmethod
    async def get_notice_available_page_service(cls, auth: AuthSchema) -> dict:
        """
        已启用公告分页（与历史行为一致：固定第 1 页、每页 10 条）。

        参数:
        - auth (AuthSchema): 认证信息模型

        返回:
        - dict: 分页结果（结构由 `CRUD.page` 返回约定）
        """
        return await NoticeCRUD(auth).page(
            offset=0,
            limit=10,
            order_by=[{"id": "asc"}],
            search={"status": 0},
            out_schema=NoticeOutSchema,
        )

    @classmethod
    async def create_notice_service(cls, auth: AuthSchema, data: NoticeCreateSchema) -> NoticeOutSchema:
        """
        创建公告。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - data (NoticeCreateSchema): 创建公告负载模型。

        返回:
        - dict: 创建的公告详情字典。

        异常:
        - CustomException: 创建失败，该公告通知已存在。
        """
        notice = await NoticeCRUD(auth).get(notice_title=data.notice_title)
        if notice:
            raise CustomException(msg="创建失败，该公告通知已存在")
        notice_obj = await NoticeCRUD(auth).create(data=data)
        return NoticeOutSchema.model_validate(notice_obj)

    @classmethod
    async def update_notice_service(
        cls, auth: AuthSchema, id: int, data: NoticeUpdateSchema
    ) -> NoticeOutSchema:
        """
        更新公告。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - id (int): 公告ID。
        - data (NoticeUpdateSchema): 更新公告负载模型。

        返回:
        - dict: 更新的公告详情字典。

        异常:
        - CustomException: 更新失败，该公告通知不存在或公告通知标题重复。
        """
        notice = await NoticeCRUD(auth).get(id=id)
        if not notice:
            raise CustomException(msg="更新失败，该公告通知不存在")
        exist_notice = await NoticeCRUD(auth).get(notice_title=data.notice_title)
        if exist_notice and exist_notice.id != id:
            raise CustomException(msg="更新失败，公告通知标题重复")
        notice_obj = await NoticeCRUD(auth).update(id=id, data=data)
        return NoticeOutSchema.model_validate(notice_obj)

    @classmethod
    async def delete_notice_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """
        删除公告。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - ids (list[int]): 删除的ID列表。

        异常:
        - CustomException: 删除失败，删除对象不能为空或该公告通知不存在。

        返回:
        - None
        """
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        notices = await NoticeCRUD(auth).list(search={"id": ("in", ids)})
        notice_map = {n.id: n for n in notices}
        for nid in ids:
            if nid not in notice_map:
                raise CustomException(msg="删除失败，该公告通知不存在")
        await NoticeCRUD(auth).delete(ids=ids)

    @classmethod
    async def set_notice_available_service(cls, auth: AuthSchema, data: BatchSetAvailable) -> None:
        """
        批量设置公告状态。

        参数:
        - auth (AuthSchema): 认证信息模型。
        - data (BatchSetAvailable): 批量设置可用负载模型。

        异常:
        - CustomException: 批量设置失败，该公告通知不存在。

        返回:
        - None
        """
        await NoticeCRUD(auth).set(ids=data.ids, status=data.status)

    @classmethod
    async def export_notice_service(cls, notice_list: list[dict]) -> bytes:
        """
        导出公告列表。

        参数:
        - notice_list (list[dict]): 公告详情字典列表。

        返回:
        - bytes: Excel 文件的字节流。
        """
        mapping_dict = {
            "id": "编号",
            "notice_title": "公告标题",
            "notice_type": "公告类型（1通知 2公告）",
            "notice_content": "公告内容",
            "status": "状态",
            "description": "备注",
            "created_time": "创建时间",
            "updated_time": "更新时间",
            "created_id": "创建者ID",
            "updated_id": "更新者ID",
        }

        # 复制数据并转换状态
        data = notice_list.copy()
        for item in data:
            # 处理状态
            item["status"] = "启用" if item.get("status") == 0 else "停用"
            # 处理公告类型
            item["notice_type"] = "通知" if item.get("notice_type") == "1" else "公告"

        return ExcelUtil.export_list2excel(list_data=data, mapping_dict=mapping_dict)

    @classmethod
    async def get_latest_notices_service(cls, auth: AuthSchema, limit: int = 5) -> list[NoticeOutSchema]:
        """获取最新 N 条已启用公告"""
        from sqlalchemy import desc, select

        from .model import NoticeModel
        from .schema import NoticeOutSchema

        stmt = (
            select(NoticeModel)
            .where(NoticeModel.status == 0)
            .order_by(desc(NoticeModel.created_time))
            .limit(limit)
        )
        result = await auth.db.execute(stmt)
        notices = result.scalars().all()
        return [NoticeOutSchema.model_validate(n) for n in notices]

    # ============ 已读追踪 ============

    @classmethod
    async def mark_read_service(cls, auth: AuthSchema, notice_id: int) -> None:
        """标记通知为已读（幂等：已读的不重复写入）"""
        from datetime import datetime

        from sqlalchemy import select

        # 检查公告是否存在
        notice = await NoticeCRUD(auth).get(id=notice_id)
        if not notice:
            raise CustomException(msg="该公告不存在")

        # 检查是否已读
        exist_stmt = select(NoticeReadModel).where(
            NoticeReadModel.user_id == auth.user.id,
            NoticeReadModel.notice_id == notice_id,
        )
        result = await auth.db.execute(exist_stmt)
        if result.scalar_one_or_none():
            return  # 已读，幂等返回

        read_record = NoticeReadModel(
            user_id=auth.user.id,
            notice_id=notice_id,
            read_time=datetime.now(),
        )
        auth.db.add(read_record)
        await auth.db.flush()

    @classmethod
    async def mark_all_read_service(cls, auth: AuthSchema) -> int:
        """全部标记已读：将当前租户所有 status=0 且未读的公告批量标记为已读，返回操作数量"""
        from datetime import datetime

        from sqlalchemy import select

        # 查询所有已启用但未读的公告
        read_ids_stmt = select(NoticeReadModel.notice_id).where(
            NoticeReadModel.user_id == auth.user.id
        )
        read_ids_result = await auth.db.execute(read_ids_stmt)
        read_ids = {row[0] for row in read_ids_result.fetchall()}

        notices_stmt = select(NoticeModel.id).where(NoticeModel.status == 0)
        notices_result = await auth.db.execute(notices_stmt)
        all_ids = {row[0] for row in notices_result.fetchall()}

        unread_ids = all_ids - read_ids
        if not unread_ids:
            return 0

        now = datetime.now()
        from sqlalchemy import insert

        if unread_ids:
            await auth.db.execute(
                insert(NoticeReadModel),
                [{"user_id": auth.user.id, "notice_id": nid, "read_time": now} for nid in unread_ids],
            )
        await auth.db.flush()
        return len(unread_ids)

    @classmethod
    async def get_unread_count_service(cls, auth: AuthSchema) -> int:
        """获取当前用户未读通知数量"""
        from sqlalchemy import func, select

        # 所有已启用公告总数
        total_stmt = select(func.count()).select_from(NoticeModel).where(
            NoticeModel.status == 0
        )
        total_result = await auth.db.execute(total_stmt)
        total_count = total_result.scalar() or 0

        # 已读数量
        read_stmt = select(func.count()).select_from(NoticeReadModel).where(
            NoticeReadModel.user_id == auth.user.id
        )
        read_result = await auth.db.execute(read_stmt)
        read_count = read_result.scalar() or 0

        return max(0, total_count - read_count)

    @classmethod
    async def get_panel_data_service(cls, auth: AuthSchema) -> PanelDataOut:
        """聚合通知面板数据：通知 + 消息 + 待办"""
        from sqlalchemy import desc, select

        # 1. 通知：最新 5 条已启用公告
        notices = await cls.get_latest_notices_service(auth, limit=5)

        # 2. 消息：最近的操作日志（作为系统消息）
        messages = []
        try:
            from app.api.v1.module_system.log.model import OperationLogModel

            stmt = select(OperationLogModel).order_by(desc(OperationLogModel.created_time)).limit(5)
            result = await auth.db.execute(stmt)
            logs = result.scalars().all()
            for log_entry in logs:
                messages.append(PanelMessageItem(
                    id=log_entry.id,
                    title=log_entry.request_path or "系统操作",
                    content=f"{log_entry.request_method} {log_entry.request_path}",
                    time=log_entry.created_time.strftime("%Y-%m-%d %H:%M")
                    if log_entry.created_time
                    else "",
                    type="system",
                ))
        except Exception as e:
            logger.warning(f"获取面板消息数据失败（操作日志表可能不存在），已跳过: {e}")

        # 3. 待办：暂无数据源，返回空列表
        pendings: list[dict] = []

        return PanelDataOut(
            notices=notices,
            messages=messages,
            pendings=pendings,
        )
