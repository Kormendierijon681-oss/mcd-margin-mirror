"""毛利估算：把订单金额按使用者提供的成本结构拆开。

核心洞察（也是这个项目的传播点）：
    用券省下的钱，减的是营收，不减成本。
    所以「你省得越多，这一单的毛利率掉得越狠」。
"""

from __future__ import annotations

from typing import Iterable, List

from .cost_model import CostParams, EstimateResult, OrderItem


def estimate(items: Iterable[OrderItem], params: CostParams) -> EstimateResult:
    items = list(items)
    if not items:
        raise ValueError("订单为空")

    list_total = sum(i.list_amount for i in items)
    revenue = sum(i.paid_amount for i in items)

    if revenue <= 0:
        raise ValueError(f"实付金额必须大于 0，收到 {revenue}")

    # 固定类成本按「原价营收」计：顾客用券不会让门店少花一分钱
    food_cost = list_total * params.food_cost_ratio
    labor_cost = list_total * params.labor_ratio
    occupancy_cost = list_total * params.occupancy_ratio
    other_cost = list_total * params.other_ratio
    # 变动类成本按「券后实付」计：特许权费跟着实付走
    royalty_cost = revenue * params.royalty_ratio

    total_cost = food_cost + labor_cost + occupancy_cost + royalty_cost + other_cost
    gross_profit = revenue - total_cost

    return EstimateResult(
        revenue=revenue,
        food_cost=food_cost,
        labor_cost=labor_cost,
        occupancy_cost=occupancy_cost,
        royalty_cost=royalty_cost,
        other_cost=other_cost,
        gross_profit=gross_profit,
        gross_margin=gross_profit / revenue,
        list_total=list_total,
        discount_total=list_total - revenue,
        breakdown={
            "食品/包装": food_cost,
            "人工": labor_cost,
            "房租物业": occupancy_cost,
            "特许权费": royalty_cost,
            "其他": other_cost,
        },
    )


def compare_scenarios(
    items: Iterable[OrderItem],
    params: CostParams,
    discounts: List[float],
) -> List[dict]:
    """同一份订单在不同折扣力度下的毛利对比。

    discounts: 折扣率列表，例如 [0.0, 0.5, 0.7] 表示原价 / 五折 / 三折。
    """
    base = list(items)
    out: List[dict] = []
    for rate in discounts:
        discounted = [
            OrderItem(
                name=i.name,
                unit_price=i.unit_price,
                quantity=i.quantity,
                paid_price=round(i.list_amount * (1.0 - rate), 2),
            )
            for i in base
        ]
        r = estimate(discounted, params)
        out.append(
            {
                "discount_rate": rate,
                "revenue": r.revenue,
                "gross_profit": r.gross_profit,
                "gross_margin": r.gross_margin,
            }
        )
    return out


def break_even_discount(items: Iterable[OrderItem], params: CostParams) -> float:
    """毛利率归零时的让利率。超过这个值，这一单在门店层面不赚钱。

    推导（L=原价合计，r=让利率，F=固定成本率合计，R=特许权费率）：
        实付 = L(1-r)
        成本 = L·F + L(1-r)·R
        毛利 = 0  =>  (1-r)(1-R) = F  =>  r = 1 - F/(1-R)
    """
    f = params.fixed_total_ratio()
    royalty = params.royalty_ratio
    if royalty >= 1.0:
        raise ValueError("royalty_ratio 必须 < 1")
    if f <= 0:
        return 1.0
    rate = 1.0 - f / (1.0 - royalty)
    if rate < 0.0:
        return 0.0  # 成本结构本身已无利润空间
    return round(rate, 6)
