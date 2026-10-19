"""输出报告：纯文本 + 简易 HTML，方便截图与传播。"""

from __future__ import annotations

from typing import List

from .cost_model import CostParams, EstimateResult


DISCLAIMER = (
    "⚠️ 本结果为基于使用者自填成本率的结构化估算，"
    "非任何品牌的官方经营数据，不构成经营建议。"
)


def money(x: float) -> str:
    return f"¥{x:,.2f}"


def render_text(result: EstimateResult, params: CostParams, title: str = "麦麦毛利镜") -> str:
    lines: List[str] = []
    lines.append(f"=== {title} ===")
    lines.append("")
    lines.append(f"原价合计：{money(result.list_total)}")
    lines.append(f"券后实付：{money(result.revenue)}")
    lines.append(f"优惠金额：{money(result.discount_total)}")
    lines.append("")
    lines.append("成本拆解（固定类按原价计，特许权费按实付计）：")
    for name, value in result.breakdown.items():
        ratio = value / result.revenue if result.revenue else 0.0
        lines.append(f"  {name:<8} {money(value):>12}  ({ratio:>6.1%})")
    lines.append("")
    lines.append(f"估算毛利：{money(result.gross_profit)}")
    lines.append(f"估算毛利率：{result.gross_margin:.1%}")
    lines.append("")
    lines.append(f"成本口径来源：{params.source}")
    if params.note:
        lines.append(f"备注：{params.note}")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def render_html(result: EstimateResult, params: CostParams, title: str = "麦麦毛利镜") -> str:
    rows = "".join(
        f"<tr><td>{name}</td><td class='num'>{money(v)}</td>"
        f"<td class='num'>{v / result.revenue:.1%}</td></tr>"
        for name, v in result.breakdown.items()
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", sans-serif; max-width: 640px;
         margin: 40px auto; color: #1a1a1a; background: #fff; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #ffc72c; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  td, th {{ padding: 8px 4px; border-bottom: 1px solid #eee; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .big {{ font-size: 28px; font-weight: 700; color: #d7232c; }}
  .note {{ font-size: 12px; color: #888; margin-top: 24px; }}
  .kv {{ display: flex; justify-content: space-between; padding: 4px 0; }}
</style></head>
<body>
<h1>{title}</h1>
<div class="kv"><span>原价合计</span><span>{money(result.list_total)}</span></div>
<div class="kv"><span>券后实付</span><span>{money(result.revenue)}</span></div>
<div class="kv"><span>优惠金额</span><span>{money(result.discount_total)}</span></div>
<table>
<tr><th>成本项</th><th class="num">金额</th><th class="num">占实付</th></tr>
{rows}
</table>
<div class="kv"><span>估算毛利</span><span class="big">{money(result.gross_profit)}</span></div>
<div class="kv"><span>估算毛利率</span><span class="big">{result.gross_margin:.1%}</span></div>
<p class="note">成本口径来源：{params.source}<br>{DISCLAIMER}</p>
</body></html>"""
