"""离线演示：不需要 MCP Token 也能跑通完整流程。

    python scripts/demo.py
    open docs/demo.html

数据全部来自 sample_data/ 的虚构样例。
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.cost_model import CostParams, OrderItem  # noqa: E402
from src.estimator import (  # noqa: E402
    break_even_discount,
    compare_scenarios,
    estimate,
)
from src.report import render_html, render_text  # noqa: E402


def load(name: str) -> dict:
    with open(os.path.join(ROOT, "sample_data", name), encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    menu = load("menu_sample.json")
    params = CostParams.from_dict(load("params_sample.json"))

    items = [OrderItem(name=i["name"], unit_price=i["unit_price"], quantity=i.get("quantity", 1)) for i in menu["items"]]
    list_total = sum(i.list_amount for i in items)
    paid_total = menu["coupon_paid_total"]

    paid_items = [
        OrderItem(
            name=i.name,
            unit_price=i.unit_price,
            quantity=i.quantity,
            paid_price=round(i.list_amount * paid_total / list_total, 2),
        )
        for i in items
    ]
    # 修正分摊尾差，保证合计与券后实付一致
    diff = round(paid_total - sum(i.paid_amount for i in paid_items), 2)
    if diff:
        paid_items[-1].paid_price = round(paid_items[-1].paid_price + diff, 2)

    r = estimate(paid_items, params)

    print(render_text(r, params))
    print()
    print("不同折扣力度下的门店毛利：")
    for s in compare_scenarios(items, params, [0.0, 0.2, 0.4, 0.5, 0.6]):
        print(
            f"  让利 {s['discount_rate']:>4.0%}  实付 ¥{s['revenue']:>7.2f}  "
            f"毛利 ¥{s['gross_profit']:>8.2f}  毛利率 {s['gross_margin']:>7.1%}"
        )
    print(f"\n盈亏平衡让利率：{break_even_discount(items, params):.1%}（超过此值，该单在门店层面不赚钱）")

    out = os.path.join(ROOT, "docs", "demo.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_html(r, params))
    print(f"\nHTML 已生成：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
