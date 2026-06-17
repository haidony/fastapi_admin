from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema
from app.core.validator import DateTimeStr, validate_required_code


class DeptCreateSchema(BaseModel):
    """部门创建模型"""

    name: str = Field(..., min_length=1, max_length=64, description="部门名称")
    order: int = Field(default=1, ge=0, description="显示顺序")
    code: str = Field(..., min_length=2, max_length=64, description="部门编码")
    leader: str | None = Field(default=None, max_length=32, description="部门负责人")
    phone: str | None = Field(default=None, max_length=20, description="联系电话")
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    parent_id: int | None = Field(default=None, ge=0, description="父部门ID")
    status: int = Field(default=0, ge=0, le=1, description="状态(0:正常 1:禁用)")
    description: str | None = Field(default=None, max_length=255, description="备注")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        """校验部门名称：不能为空"""
        if not value or not value.strip():
            raise ValueError("部门名称不能为空")
        return value.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str):
        """校验部门编码：字母开头，2-64 位，仅含字母/数字/下划线"""
        return validate_required_code(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: int):
        """校验状态：仅支持 0(正常)、1(禁用)"""
        if value not in {0, 1}:
            raise ValueError("状态仅支持 0(正常) 或 1(禁用)")
        return value


class DeptUpdateSchema(DeptCreateSchema):
    """部门更新模型"""


class DeptDetailOutSchema(DeptCreateSchema, BaseSchema):
    """部门详情响应模型（不含 children，用于详情和更新）"""

    model_config = ConfigDict(from_attributes=True)

    parent_name: str | None = Field(default=None, max_length=64, description="父部门名称")


class DeptTreeOutSchema(DeptDetailOutSchema):
    """部门树形响应模型（含 children，用于树形列表）"""

    children: list["DeptTreeOutSchema"] | None = Field(default=None, description="子部门列表")


# 兼容旧代码的别名（后续可逐步移除）
DeptOutSchema = DeptDetailOutSchema


class DeptQueryParam:
    """部门管理查询参数"""

    def __init__(
        self,
        name: str | None = Query(None, description="部门名称"),
        status: str | None = Query(None, description="部门状态(True正常 False停用)"),
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

        # 模糊查询字段
        self.name = (QueueEnum.like.value, name)

        # 精确查询字段
        self.status = (QueueEnum.eq.value, status)

        # 时间范围查询
        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
