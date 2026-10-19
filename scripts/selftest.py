"""自测断言：改完逻辑必跑。零依赖。

    python scripts/selftest.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.cost_model import CostParams, CostParamsError, OrderItem  # noqa: E402
from src.estimator import (  # noqa: E402
    break_even_discount,
    compare_scenarios,
    estimate,
)

# 虚构成本参数，仅用于数学正确性验证，不代表任何真实经营数据
PARAMS = CostParams(
    food_cost_ratio=0.30,
    labor_ratio=0.20,
    occupancy_ratio=0.10,
    royalty_ratio=0.05,
    other_ratio=0.05,
    source="自测虚构参数",
)

FAILS: list[str] = []


def check(name: str, cond: bool) -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}")
        FAILS.append(name)


def main() -> int:
    print("mcd-margin-mirror selftest")

    print("\n[1] 参数校验")
    try:
        CostParams.from_dict({"food_cost_ratio": 0.3})
        check("缺字段应报错", False)
    except CostParamsError:
        check("缺字段应报错", True)
    try:
        CostParams.from_dict(
            {"food_cost_ratio": 1.5, "labor_ratio": 0, "occupancy_ratio": 0, "royalty_ratio": 0}
        )
        check("比率越界应报错", False)
    except CostParamsError:
        check("比率越界应报错", True)
    try:
        CostParams(
            food_cost_ratio=0.9,
            labor_ratio=0.2,
            occupancy_ratio=0.1,
            royalty_ratio=0.05,
        )
        check("成本率合计>1 应报错", False)
    except CostParamsError:
        check("成本率合计>1 应报错", True)
    check("未知字段应报错", _unknown_field_raises())

    print("\n[2] 计算正确性")
    items = [OrderItem(name="A", unit_price=100.0, quantity=1)]
    r = estimate(items, PARAMS)
    check("营收=100", abs(r.revenue - 100.0) < 1e-9)
    check("成本率合计=0.70", abs(PARAMS.total_cost_ratio() - 0.70) < 1e-9)
    check("毛利=30", abs(r.gross_profit - 30.0) < 1e-9)
    check("毛利率=30%", abs(r.gross_margin - 0.30) < 1e-9)

    print("\n[3] 券后逻辑：省的是营收，不省固定成本")
    discounted = [OrderItem(name="A", unit_price=100.0, quantity=1, paid_price=50.0)]
    r2 = estimate(discounted, PARAMS)
    # 固定成本 65（按原价 100 计）+ 特许权费 2.5（按实付 50 计）= 67.5
    check("半价后毛利=-17.5", abs(r2.gross_profit - (-17.5)) < 1e-9)
    check("半价后毛利率=-35%", abs(r2.gross_margin - (-0.35)) < 1e-9)

    print("\n[4] 盈亏平衡让利率")
    be = break_even_discount(items, PARAMS)
    check(f"平衡点={be:.4f} (期望 0.3158)", abs(be - 0.315789) < 1e-4)
    at_be = estimate(
        [OrderItem(name="A", unit_price=100.0, quantity=1, paid_price=round(100 * (1 - be), 4))],
        PARAMS,
    )
    check("平衡点处毛利≈0", abs(at_be.gross_profit) < 0.01)

    print("\n[5] 多档位对比单调性")
    scen = compare_scenarios(items, PARAMS, [0.0, 0.1, 0.2, 0.3])
    margins = [s["gross_margin"] for s in scen]
    check("毛利率随折扣递减", all(margins[i] > margins[i + 1] for i in range(len(margins) - 1)))

    print("\n[6] 数量与多品项")
    multi = [
        OrderItem(name="A", unit_price=30.0, quantity=2),
        OrderItem(name="B", unit_price=20.0, quantity=1),
    ]
    r3 = estimate(multi, PARAMS)
    check("原价合计=80", abs(r3.list_total - 80.0) < 1e-9)
    check("毛利=24", abs(r3.gross_profit - 24.0) < 1e-9)

    print()
    if FAILS:
        print(f"{len(FAILS)} failed: {FAILS}")
        return 1
    print("all passed")
    return 0


def _unknown_field_raises() -> bool:
    try:
        CostParams.from_dict(
            {
                "food_cost_ratio": 0.3,
                "labor_ratio": 0.2,
                "occupancy_ratio": 0.1,
                "royalty_ratio": 0.05,
                "bogus": 1,
            }
        )
        return False
    except CostParamsError:
        return True


if __name__ == "__main__":
    raise SystemExit(main())
