from app.core.base_schema import AuthSchema, BatchSetAvailable
from app.core.exceptions import CustomException
from app.utils.excel_util import ExcelUtil

from .crud import PositionCRUD
from .schema import (
    PositionCreateSchema,
    PositionOutSchema,
    PositionQueryParam,
    PositionUpdateSchema,
)


class PositionService:
    """岗位模块服务层"""

    @classmethod
    async def get_position_detail_service(cls, auth: AuthSchema, id: int) -> PositionOutSchema:
        """
        获取岗位详情

        参数:
        - auth (AuthSchema): 认证信息模型
        - id (int): 岗位ID

        返回:
        - Dict: 岗位详情对象
        """
        position = await PositionCRUD(auth).get(id=id)
        if not position:
            raise CustomException(msg="岗位不存在")
        return PositionOutSchema.model_validate(position)

    @classmethod
    async def get_position_list_service(
        cls,
        auth: AuthSchema,
        search: PositionQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> list[PositionOutSchema]:
        """
        获取岗位列表

        参数:
        - auth (AuthSchema): 认证信息模型
        - search (PositionQueryParam | None): 查询参数对象
        - order_by (list[dict] | None): 排序参数列表

        返回:
        - list[PositionOutSchema]: 岗位列表
        """
        position_list = await PositionCRUD(auth).list(
            search=search.__dict__ if search else {}, order_by=order_by
        )
        return [
            PositionOutSchema.model_validate(position) for position in position_list
        ]

    @classmethod
    async def get_position_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: PositionQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """
        分页查询岗位（数据库 OFFSET/LIMIT）。

        参数:
        - auth (AuthSchema): 认证信息模型
        - page_no (int): 页码（从 1 开始）
        - page_size (int): 每页条数
        - search (PositionQueryParam | None): 查询条件
        - order_by (list[dict[str, str]] | None): 排序字段列表

        返回:
        - dict: 分页结果（结构由 `CRUD.page` 返回约定）
        """
        offset = (page_no - 1) * page_size
        return await PositionCRUD(auth).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search.__dict__ if search else {},
            out_schema=PositionOutSchema,
        )

    @classmethod
    async def create_position_service(cls, auth: AuthSchema, data: PositionCreateSchema) -> PositionOutSchema:
        """
        创建岗位

        参数:
        - auth (AuthSchema): 认证信息模型
        - data (PositionCreateSchema): 岗位创建模型

        返回:
        - dict: 创建的岗位详情字典
        """
        position = await PositionCRUD(auth).get(name=data.name)
        if position:
            raise CustomException(msg="创建失败，该岗位已存在")
        new_position = await PositionCRUD(auth).create(data=data)
        return PositionOutSchema.model_validate(new_position)

    @classmethod
    async def update_position_service(
        cls, auth: AuthSchema, id: int, data: PositionUpdateSchema
    ) -> PositionOutSchema:
        """
        更新岗位

        参数:
        - auth (AuthSchema): 认证信息模型
        - id (int): 岗位ID
        - data (PositionUpdateSchema): 岗位更新模型

        返回:
        - dict: 更新的岗位对象
        """
        position = await PositionCRUD(auth).get(id=id)
        if not position:
            raise CustomException(msg="更新失败，该岗位不存在")
        exist_position = await PositionCRUD(auth).get(name=data.name)
        if exist_position and exist_position.id != id:
            raise CustomException(msg="更新失败，岗位名称重复")
        updated_position = await PositionCRUD(auth).update(id=id, data=data)
        return PositionOutSchema.model_validate(updated_position)

    @classmethod
    async def delete_position_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """
        删除岗位

        参数:
        - auth (AuthSchema): 认证信息模型
        - ids (list[int]): 岗位ID列表

        返回:
        - None
        """
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        # 批量校验岗位存在性
        positions = await PositionCRUD(auth).list(search={"id": ("in", ids)})
        position_map = {p.id: p for p in positions}
        for pid in ids:
            if pid not in position_map:
                raise CustomException(msg="删除失败，该岗位不存在")
        await PositionCRUD(auth).delete(ids=ids)

    @classmethod
    async def set_position_available_service(
        cls, auth: AuthSchema, data: BatchSetAvailable
    ) -> None:
        """
        设置岗位状态

        参数:
        - auth (AuthSchema): 认证信息模型
        - data (BatchSetAvailable): 批量设置状态模型

        返回:
        - None
        """
        positions = await PositionCRUD(auth).list(search={"id": ("in", data.ids)})
        position_map = {p.id: p for p in positions}
        for pid in data.ids:
            if pid not in position_map:
                raise CustomException(msg=f"岗位ID {pid} 不存在")
        await PositionCRUD(auth).set(ids=data.ids, status=data.status)

    @classmethod
    async def export_position_list_service(cls, position_list: list[dict]) -> bytes:
        """
        导出岗位列表

        参数:
        - position_list (list[dict]): 岗位列表对象

        返回:
        - bytes: 导出的Excel文件字节流
        """
        mapping_dict = {
            "id": "编号",
            "name": "岗位名称",
            "order": "显示顺序",
            "status": "状态",
            "description": "备注",
            "created_time": "创建时间",
            "updated_time": "更新时间",
            "created_id": "创建者ID",
            "updated_id": "更新者ID",
        }

        # 复制数据并转换状态
        data = position_list.copy()
        for item in data:
            item["status"] = "启用" if item.get("status") == 0 else "停用"
            item["creator"] = (
                item.get("created_by", {}).get("name", "未知")
                if isinstance(item.get("created_by"), dict)
                else "未知"
            )

        return ExcelUtil.export_list2excel(list_data=data, mapping_dict=mapping_dict)
