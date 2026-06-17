from app.core.base_schema import AuthSchema, BatchSetAvailable
from app.core.exceptions import CustomException
from app.utils.common_util import (
    get_child_id_map,
    get_child_recursion,
    get_parent_id_map,
    get_parent_recursion,
)

from .crud import DeptCRUD
from .schema import (
    DeptCreateSchema,
    DeptDetailOutSchema,
    DeptQueryParam,
    DeptTreeOutSchema,
    DeptUpdateSchema,
)


class DeptService:
    """
    部门管理模块服务层
    """

    @classmethod
    async def get_dept_detail_service(cls, auth: AuthSchema, id: int) -> DeptDetailOutSchema:
        """
        获取部门详情。

        参数:
        - auth (AuthSchema): 认证对象。
        - id (int): 部门 ID。

        返回:
        - DeptDetailOutSchema: 部门详情对象。
        """
        dept = await DeptCRUD(auth).get(id=id)
        if not dept:
            raise CustomException(msg="部门不存在")
        dept_out = DeptDetailOutSchema.model_validate(dept)
        if dept.parent_id:
            parent = await DeptCRUD(auth).get(id=dept.parent_id)
            if parent:
                dept_out.parent_name = parent.name
        return dept_out

    @classmethod
    async def get_dept_tree_service(
        cls,
        auth: AuthSchema,
        search: DeptQueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> list[dict]:
        """
        获取部门树形列表。

        参数:
        - auth (AuthSchema): 认证对象。
        - search (DeptQueryParam | None): 查询参数对象。
        - order_by (list[dict] | None): 排序参数。

        返回:
        - list[dict]: 部门树形列表对象。
        """
        # 使用树形结构查询，预加载children关系
        dept_list = await DeptCRUD(auth).get_tree_list(
            search=search.__dict__ if search else {}, order_by=order_by
        )
        # 转换为字典列表（使用树形 Schema），tree_list 已通过 selectin 预加载 children
        dept_dict_list = [DeptTreeOutSchema.model_validate(dept).model_dump() for dept in dept_list]
        # 仅保留根节点，子树已在 model_dump 中递归序列化
        return [d for d in dept_dict_list if d.get("parent_id") is None]

    @classmethod
    async def create_dept_service(cls, auth: AuthSchema, data: DeptCreateSchema) -> DeptDetailOutSchema:
        """
        创建部门。

        参数:
        - auth (AuthSchema): 认证对象。
        - data (DeptCreateSchema): 部门创建对象。

        返回:
        - DeptDetailOutSchema: 新创建的部门对象。

        异常:
        - CustomException: 当部门已存在时抛出。
        """
        dept = await DeptCRUD(auth).get(name=data.name)
        if dept:
            raise CustomException(msg="创建失败，该部门已存在")
        obj = await DeptCRUD(auth).get(code=data.code)
        if obj:
            raise CustomException(msg="创建失败，编码已存在")

        # 检查租户配额
        from app.api.v1.module_platform.tenant.service import TenantService
        await TenantService.check_quota_service(auth, auth.tenant_id, "dept")

        dept = await DeptCRUD(auth).create(data=data)
        return DeptDetailOutSchema.model_validate(dept)

    @classmethod
    async def update_dept_service(cls, auth: AuthSchema, id: int, data: DeptUpdateSchema) -> DeptDetailOutSchema:
        """
        更新部门。

        参数:
        - auth (AuthSchema): 认证对象。
        - id (int): 部门 ID。
        - data (DeptUpdateSchema): 部门更新对象。

        返回:
        - DeptDetailOutSchema: 更新后的部门对象。

        异常:
        - CustomException: 当部门不存在或名称重复时抛出。
        """
        dept = await DeptCRUD(auth).get(id=id)
        if not dept:
            raise CustomException(msg="更新失败，该部门不存在")
        exist_dept = await DeptCRUD(auth).get(name=data.name)
        if exist_dept and exist_dept.id != id:
            raise CustomException(msg="更新失败，部门名称重复")
        exist_code = await DeptCRUD(auth).get(code=data.code)
        if exist_code and exist_code.id != id:
            raise CustomException(msg="更新失败，部门编码已存在")

        dept = await DeptCRUD(auth).update(id=id, data=data)
        dept_out = DeptDetailOutSchema.model_validate(dept)
        if dept_out.parent_id:
            parent = await DeptCRUD(auth).get(id=dept_out.parent_id)
            if parent:
                dept_out.parent_name = parent.name
        return dept_out

    @classmethod
    async def delete_dept_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """
        删除部门。

        参数:
        - auth (AuthSchema): 认证对象。
        - ids (list[int]): 部门 ID 列表。

        返回:
        - None

        异常:
        - CustomException: 当删除对象为空时抛出。
        - CustomException: 当存在子部门时抛出。
        """
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")

        # 获取所有部门列表，用于构建树形关系
        all_depts = await DeptCRUD(auth).list()

        # 构建子部门ID映射
        child_id_map = get_child_id_map(model_list=all_depts)

        for id in ids:
            # 检查是否有子部门
            if id in child_id_map and child_id_map[id]:
                raise CustomException(msg="存在子部门，不允许删除父部门")

        # 执行批量删除操作
        await DeptCRUD(auth).delete(ids=ids)

    @classmethod
    async def batch_set_available_service(cls, auth: AuthSchema, data: BatchSetAvailable) -> None:
        """
        批量设置部门可用状态。

        参数:
        - auth (AuthSchema): 认证对象。
        - data (BatchSetAvailable): 批量设置可用状态对象。

        返回:
        - None
        """
        dept_list = await DeptCRUD(auth).list()
        total_ids = []

        if data.status == 0:
            id_map = get_parent_id_map(model_list=dept_list)
            for dept_id in data.ids:
                enable_ids = get_parent_recursion(id=dept_id, id_map=id_map)
                total_ids.extend(enable_ids)
        else:
            id_map = get_child_id_map(model_list=dept_list)
            for dept_id in data.ids:
                disable_ids = get_child_recursion(id=dept_id, id_map=id_map)
                total_ids.extend(disable_ids)

        await DeptCRUD(auth).set(ids=total_ids, status=data.status)
