# workbuddy.md — WorkBuddy 开发对话上下文

> 本文件记录本项目使用 WorkBuddy 开发的完整过程，用于核验 WorkBuddy 专项奖励条件。

## 1. 需求提出

**用户**：我想要一个参赛 Skill。方向选 A「麦麦毛利镜」——输入一份麦当劳订单，算出这单门店大概赚多少。

**背景约束（用户明确）**：
- 大陆手机号注册、GitHub 公开仓库 → 身份暴露需控制
- 不能编造任何品牌的真实经营数据
- 时间紧：2026-10-25 23:59 报名截止

## 2. 方案设计（WorkBuddy 产出）

**核心洞察**：顾客用券省下的钱减的是营收，不减成本。所以让利越大，门店毛利掉得越陡。

**分层原则**：取数交给 MCP，算术交给代码，表达交给 Agent。涉及金额的算术一律不让大模型口算。

**数据诚实原则**：不内置任何真实成本率。所有参数必须由使用者提供，缺字段直接报错，绝不用"行业经验值"凑数。

## 3. 开发过程中的关键修正（真实迭代记录）

### 3.1 相对导入错误

```
ImportError: attempted relative import with no known parent package
```
修正：补 `src/__init__.py`，脚本改为 `from src.xxx import ...`，`sys.path` 指向项目根而非 `src`。

### 3.2 元数据字段被校验拦截

```
CostParamsError: 未知参数字段：['_warning']
```
修正：`from_dict` 过滤下划线开头的键，视为注释元数据。

### 3.3 建模错误（最重要的一处）

**初版模型**：所有成本按营收（券后实付）比例摊分。

**问题**：这会让毛利率恒定不变——打五折后毛利率仍是 30%。这明显违背现实。

**原因**：食品成本、人工、房租是固定发生的，不因顾客用券而减少；只有特许权费按实付抽成。

**修正**：
```
固定类成本（食品/人工/房租/其他）按【原价合计】计
变动类成本（特许权费）按【券后实付】计
```
盈亏平衡公式相应改为：`r = 1 − F/(1−R)`（F=固定成本率合计，R=特许权费率）。

修正后：原价购买毛利 30%，打五折毛利 −17.5%（毛利率 −35%），符合现实直觉。

## 4. 验证

```
python3 scripts/selftest.py
→ 16 项断言全部通过（参数校验 4 / 计算正确性 4 / 券后逻辑 2 / 盈亏平衡 2 / 单调性 1 / 多品项 2）

python3 scripts/demo.py
→ 原价 ¥47.00 → 券后 ¥21.90 → 估算毛利 ¥-11.16 → 毛利率 -50.9%
→ 盈亏平衡让利率 28.4%
→ docs/demo.html 生成成功
```

注：demo 数据为 `sample_data/` 中的虚构占位符，已显著标注。

## 5. 交付物

- `src/cost_model.py` — 成本参数模型与校验（缺字段/越界/合计>1 全部拒绝）
- `src/estimator.py` — 毛利估算、多档位对比、盈亏平衡计算
- `src/report.py` — 文本与 HTML 报告，内置免责声明
- `scripts/selftest.py` — 16 项自测断言
- `scripts/demo.py` — 离线可复现演示（无需 Token）
- `skills/mcd-margin-mirror/SKILL.md` — Skill 定义，含"什么时候不要用"
- `README.md` / `MCP_INTEGRATION.md` / `mcp-config.example.json` / `CONTEST_DECLARATION.md`

---

*以上为使用 WorkBuddy 完成本项目开发的真实过程记录。*

## 6. 提交前的官方规格逐项校对（2026-10-23，WorkBuddy 主导）

报名之前我用 WorkBuddy 做了三件事：**不靠猜，逐条比对官方仓库**。

### 6.1 拉官方仓库逐条核对 MCP 工具清单

克隆 `M-China/mcd-mcp-server`（官方 MCP Server 仓库），工具清单在其 README 的 HTML 表格里，我写脚本解析后与本项目的工具表逐项比对：

| 本项目文档里写的 | 官方是否存在 | 官方语义 | 结论 |
|---|---|---|---|
| `query-meals` | ✅ 存在 | 查询当前门店可售卖的餐品菜单（分类、餐品编码、标签等） | ⚠️ **不含价格**，原文我写错了 |
| `query-meal-detail` | ✅ 存在 | 查询餐品详情 | 本项目原先漏了，补进工具表 |
| `available-coupons` | ✅ 存在 | 麦麦省券列表查询 | 一致 |
| `query-my-coupons` | ✅ 存在 | 我的优惠券查询 | 一致 |
| `query-store-coupons` | ✅ 存在 | 查询用户当前门店下可用的优惠券列表 | 一致 |
| `auto-bind-coupons` | ✅ 存在 | 麦麦省一键领券 | 一致 |
| `calculate-price` | ✅ 存在 | 根据商品列表（可含优惠券）计算商品金额、配送费、优惠金额及应付总价 | 一致 |
| `list-nutrition-foods` | ✅ 存在 | 餐品营养信息列表 | 一致 |
| `create-order` | ✅ 存在 | 创建订单 | 本项目**不调用** |

**修正**：原价合计 L 改为由 `query-meal-detail` 取，券后实付 P 由 `calculate-price` 取；`query-meals` 只承担菜单结构与餐品编码。

### 6.2 实测 MCP 端点，纠正配置错误

原 `mcp-config.example.json` 写的是 `"url": "https://open.mcd.cn/mcp"`——那是**领 Token 的控制台页**，不是 MCP 服务地址。官方配置是 `https://mcp.mcd.cn`。

我用 curl 实测确认：

```
POST https://mcp.mcd.cn/          → 403（缺 Token，被拒）   ← 真端点
POST https://mcp.mcd.cn/mcp/      → 404
POST https://mcp.mcd.cn/sse       → 404
```

结论：端点是**根路径**，且 Token 为硬性要求（403）。配置已改为官方地址。

### 6.3 补 README 缺失的一节 + 补口径说明

官方 README 明确要求参赛项目 README 含「项目介绍、安装方法、使用示例、目标用户」，而项目此前**完全没写怎么接 MCP**（只写了成本参数怎么填）。已补「接入麦当劳 MCP」三步：申请 Token（open.mcd.cn，手机号，免费）→ 配置连接器（`url` + `Authorization: Bearer ${MCD_MCP_TOKEN}`）→ 在 Agent 里跑一次真实链路。

另外补了成本口径说明：人工与房租属**期间固定成本**，按原价占比分摊到单笔，门店单期汇总总额守恒，但**单品层面会失真**（高价单被多摊人工房租）；看单品边际贡献应把 labor/occupancy 置 0。这个坑不写清楚，后来者会重复踩。

### 6.4 自测与第三方安全审计

```
python3 scripts/selftest.py   → 16 项断言全部通过
python3 scripts/demo.py       → 原价 ¥47.00 → 券后 ¥21.90 → 估算毛利 ¥-11.16 → 毛利率 -50.9%
```

仓库提交后跑了三轮 diff 增量安全扫描（第三方扫描插件，Fast 模式），结论均为 **0 findings / 门禁通过**，并据此把误入版本库的扫描产物清出、补 `.gitignore`。

## 7. 发布与报名（2026-10-23 23:53）

用 WorkBuddy 一键完成：

1. 创建 public 仓库 `Kormendierijon681-oss/mcd-margin-mirror`（创建时间落在官方要求的时间窗内）
2. 自动把 README 里的用户名占位符替换为实际地址后 push
3. 校验 5 个必交文件均可公开访问
4. 按官方规定的 4 行格式，在官方活动仓库提交报名 Issue（标题与正文之间不加空行、字段名与内容同行、项目地址用裸链接不用 Markdown）
5. 官方机器人 `M-China-Official` 回复：「您的作品已成功参赛，您可以通过官方项目的排行榜.md 查看排名」

顺带核对了官方奖励规则：**进入排行榜**（即公开 Star 数进入前 100）才能拿到周边与 WorkBuddy 专项积分，未进榜则颗粒无收。当前官方榜单进榜线为 38 Star，故本项目同步在社区发布了配套文章并公开仓库地址，寻求真实用户的 Star 支持（官方禁止的是刷赞造假，正常推荐不违规）。
