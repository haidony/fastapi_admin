import json

from fastapi import Query

from app.common.enums import QueueEnum
from app.core.validator import DateTimeStr


class PaginationQueryParam:
    """分页查询参数基类"""

    def __init__(
        self,
        page_no: int = Query(default=1, description="当前页码", ge=1),
        page_size: int = Query(default=10, description="每页数量", ge=1, le=100),
        order_by: str | None = Query(
            default=None,
            description="排序字段,格式:[{'field1': 'asc'}, {'field2': 'desc'}]",
        ),
    ) -> None:
        """
        初始化分页查询参数。

        参数:
        - page_no (int | None): 当前页码，默认 None。
        - page_size (int | None): 每页数量，默认 None，最大 100。
        - order_by (str | None): 排序字段，格式 'field,asc;field2,desc'。

        返回:
        - None
        """
        self.page_no = page_no
        self.page_size = page_size
        # 将字符串格式的order_by转换为服务层需要的List[Dict[str, str]]格式
        if order_by:
            try:
                self.order_by = json.loads(order_by)
            except ValueError:
                # 如果解析失败，使用默认排序
                self.order_by = [{"id": "desc"}]
        else:
            self.order_by = [{"id": "desc"}]


class BaseQueryParam:
    """基础查询字段 Mixin（created_time + updated_time）"""

    def __init__(
        self,
        created_time: list[DateTimeStr] | None = Query(
            None,
            description="创建时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
        updated_time: list[DateTimeStr] | None = Query(
            None,
            description="更新时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
    ) -> None:
        super().__init__()
        # 时间范围查询
        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))


class UserByQueryParam:
    """审计字段 Mixin（created_id + updated_id）"""

    def __init__(
        self,
        created_id: int | None = Query(None, description="创建人"),
        updated_id: int | None = Query(None, description="更新人"),
    ) -> None:
        super().__init__()
        if created_id:
            self.created_id = (QueueEnum.eq.value, created_id)
        if updated_id:
            self.updated_id = (QueueEnum.eq.value, updated_id)


class TenantByQueryParam:
    """租户字段 Mixin（tenant_id）"""

    def __init__(
        self,
        tenant_id: int | None = Query(None, description="租户ID"),
    ) -> None:
        super().__init__()
        if tenant_id:
            self.tenant_id = (QueueEnum.eq.value, tenant_id)
