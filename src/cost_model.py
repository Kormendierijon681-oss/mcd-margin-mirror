"""成本模型：参数全部外部传入，不内置任何真实经营数据。

设计原则（诚实优先）：
1. 本模块不假设、不硬编码任何品牌的真实成本结构。
2. 所有比率必须由使用者提供（来自其认可的公开口径或自有数据）。
3. 未提供即报错，绝不用"看起来合理"的默认值凑数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


class CostParamsError(ValueError):
    """成本参数缺失或不合法。"""


@dataclass
class CostParams:
    """门店层面的成本结构（占「原价营收」比，0–1）。

    关键建模原则（决定这个工具算得对不对）：
        固定类成本 —— 不因顾客用券而减少，按「原价合计」计：
            food_cost_ratio    食品/包装成本率
            labor_ratio        人工成本率
            occupancy_ratio    房租与物业成本率
            other_ratio        折旧、水电、损耗等其他成本率
        变动类成本 —— 随实付金额抽成，按「券后实付」计：
            royalty_ratio      特许权/品牌使用费率

    为什么必须区分：顾客用券省下的钱减的是营收，不减成本。
    若把所有成本都按实付比例摊，毛利率会恒定不变，那是错的。
    """

    food_cost_ratio: float
    labor_ratio: float
    occupancy_ratio: float
    royalty_ratio: float
    other_ratio: float = 0.0
    source: str = "未标注来源"
    note: str = ""

    REQUIRED = (
        "food_cost_ratio",
        "labor_ratio",
        "occupancy_ratio",
        "royalty_ratio",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED:
            value = getattr(self, name)
            if value is None:
                raise CostParamsError(f"缺少必填成本参数：{name}")
            if not 0.0 <= float(value) <= 1.0:
                raise CostParamsError(f"{name} 必须在 0–1 之间，收到 {value}")
        if not 0.0 <= float(self.other_ratio) <= 1.0:
            raise CostParamsError(f"other_ratio 必须在 0–1 之间，收到 {self.other_ratio}")
        total = self.total_cost_ratio()
        if total > 1.0:
            raise CostParamsError(
                f"成本率合计 {total:.4f} 超过 1.0，请检查参数（这会导致负毛利）"
            )

    def fixed_total_ratio(self) -> float:
        """不随折扣变化的成本率合计（按原价营收计）。"""
        return (
            self.food_cost_ratio
            + self.labor_ratio
            + self.occupancy_ratio
            + self.other_ratio
        )

    def total_cost_ratio(self) -> float:
        """全成本率合计，仅用于完整性校验（不代表实际摊分方式）。"""
        return self.fixed_total_ratio() + self.royalty_ratio

    def as_dict(self) -> Dict[str, float]:
        return {
            "food_cost_ratio": self.food_cost_ratio,
            "labor_ratio": self.labor_ratio,
            "occupancy_ratio": self.occupancy_ratio,
            "royalty_ratio": self.royalty_ratio,
            "other_ratio": self.other_ratio,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CostParams":
        # 下划线开头的键视为注释/元数据，不参与校验
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        unknown = set(data) - set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        if unknown:
            raise CostParamsError(f"未知参数字段：{sorted(unknown)}")
        missing = [k for k in cls.REQUIRED if k not in data]
        if missing:
            raise CostParamsError(
                f"缺少必填字段 {missing}。"
                "本工具不提供默认成本率，请使用者自行填写其认可的口径。"
            )
        return cls(**data)


@dataclass
class OrderItem:
    """单个订单项。价格来自 MCP 实时结果或离线样例数据。"""

    name: str
    unit_price: float  # 原价（元）
    quantity: int = 1
    paid_price: float | None = None  # 券后实付（元），None 表示按原价

    @property
    def list_amount(self) -> float:
        return self.unit_price * self.quantity

    @property
    def paid_amount(self) -> float:
        if self.paid_price is None:
            return self.list_amount
        return self.paid_price


@dataclass
class EstimateResult:
    revenue: float
    food_cost: float
    labor_cost: float
    occupancy_cost: float
    royalty_cost: float
    other_cost: float
    gross_profit: float
    gross_margin: float
    list_total: float
    discount_total: float
    breakdown: Dict[str, float] = field(default_factory=dict)
