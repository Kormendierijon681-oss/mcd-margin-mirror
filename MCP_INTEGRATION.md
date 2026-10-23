# MCP 集成说明

本文件说明项目使用的麦当劳 MCP Server / Tool、调用流程、成本口径与业务价值。

> 工具清单与字段语义已逐条比对官方 `M-China/mcd-mcp-server` 仓库的工具列表（截至 2026-10-23，Server 版本 1.0.8+）。真实调用记录见 `workbuddy.md`。

## 一、使用的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp`（麦当劳 MCP 官方服务） |
| Server 地址 | `https://mcp.mcd.cn` |
| Token 申请 | `open.mcd.cn/mcp` → 手机号登录 → 控制台 → 激活 → 领取（免费） |
| 配置方式 | 环境变量 `${MCD_MCP_TOKEN}`，见 `mcp-config.example.json` |
| 传输方式 | Streamable HTTP，请求头 `Authorization: Bearer <token>` |

## 二、使用的 Tool 与用途

| Tool | 官方说明 | 本项目用途 | 核心 |
|---|---|---|---|
| `query-meals` | 查询当前门店可售卖的餐品菜单（分类、餐品编码、标签等） | 取菜单结构与餐品编码，作为订单选品与成本口径的骨架 | ✅ |
| `query-meal-detail` | 查询餐品详情 | 取单品原价与规格，构成订单「原价合计 L」 | ✅ |
| `available-coupons` | 查询用户当前可领取的麦麦省优惠券列表 | 券池第 1 路：可领券 | ✅ |
| `query-my-coupons` | 查询用户账户下所有可用优惠券 | 券池第 2 路：已有券 | ✅ |
| `query-store-coupons` | 查询用户在当前门店下可使用的优惠券列表 | 券池第 3 路：门店专属券 | ✅ |
| `auto-bind-coupons` | 自动领取麦麦省所有当前可用优惠券 | 券池第 4 路：领券后新增（不调会漏掉这一部分优惠） | ✅ |
| `calculate-price` | 根据商品列表（可含优惠券）计算商品金额、配送费、优惠金额及应付总价 | 券后核价，得到门店实收 P | ✅ |
| `list-nutrition-foods` | 获取常见餐品营养成分（能量、蛋白质、脂肪、碳水、钠、钙等） | 可选扩展：先按热量/营养约束筛餐品，再算毛利 | 可选 |
| `create-order` | 创建订单并返回支付链接 | **本项目不调用**，只做分析不下单 | ❌ |

> 券必须四路查全（可领券 / 已有券 / 门店券 / 一键领券后新增）。少查一路会低估让利幅度，进而**高估**门店毛利——这是本项目最容易被忽略的偏差来源。

## 三、调用流程

```
1. query-meals + query-meal-detail
   └─> 菜单结构 + 单品原价 → 计算 原价合计 L

2. auto-bind-coupons
   ├─> available-coupons      （可领券）
   ├─> query-my-coupons      （已有券）
   ├─> query-store-coupons   （门店券）
   └─> auto-bind-coupons     （领券后新增，四路合并成券池）

3. calculate-price（带券）
   └─> 商品金额 / 优惠金额 / 应付总价 → 门店实收 P

4. 本地确定性计算（src/estimator.py，全程不经过大模型）
   固定类成本 = L × (food_ratio + labor_ratio + occupancy_ratio + other_ratio)
   变动类成本 = P × royalty_ratio
   毛利       = P − 固定类成本 − 变动类成本
   毛利率     = 毛利 / P
   盈亏平衡让利率 = 1 − F / (1 − R)
                 （F=固定成本率合计，R=特许权费率）
```

**为什么这样分**：顾客用券省下的钱，减的是**营收**，不减门店的成本。所以让利越大，这一单的毛利率掉得越狠。涉及金额的算术一律交给 `src/estimator.py`，不让大模型口算。

## 四、成本口径说明（读结果前必看）

本项目输出的是**门店期间成本分摊口径**下的单笔贡献，不是会计意义上的边际贡献：

- 人工、房租物业这类**期间固定成本**，本模型按「该单原价占门店期间原价合计的份额」分摊到单笔。门店单期汇总时总额守恒（不会多算也不会少算）。
- 但**单品层面**会失真：一份高价订单会按比例多摊人工和房租，看起来"更亏"。要看单品的真实边际贡献，应把 `labor_ratio` 与 `occupancy_ratio` 置 0，只保留食材、包装与特许权费。
- 成本率全部由使用者提供，项目**不内置任何"行业经验值"**；缺字段直接报错。

## 五、已知局限

1. `query-meals` 返回的是菜单结构与餐品编码，单品价格需再取 `query-meal-detail` 或由 `calculate-price` 的商品金额反推；两者口径不一致时以 `calculate-price` 为准。
2. 配送费计入实收会影响门店口径：麦麦送场景下配送费由顾客承担，需在建模时剔除，否则会虚增营收。
3. 门店券与麦麦省券的叠加规则由服务端决定，模型侧不做假设，实测以 `calculate-price` 返回为准。
4. 本项目不处理时段、天气、节假日对成本结构的影响。

## 六、业务价值

1. **对消费者**：把"我省了多少"翻译成"门店这单赚多少"，让优惠的代价变得具体。
2. **对餐饮从业者**：一个可直接复用的「让利率 ↔ 毛利率」教学模型，直观展示为什么折扣打过头会亏钱。
3. **对开发者**：示范 MCP 取数 + 确定性算法分层 —— 涉及金额的部分一律交给代码，不让模型口算。

## 七、安全与合规

- 真实 Token **从不入库**，配置仅使用环境变量占位符 `${MCD_MCP_TOKEN}`。
- 项目不调用 `create-order`，不涉及任何交易与支付行为。
- 所有成本参数由使用者自行提供，项目本身不持有、不传播任何品牌的经营数据。
- 输出显著标注为估算结果，并声明不构成经营建议。

## 八、连通性自检

拿到 Token 后，可用一条命令验证 MCP 是否连通（**Token 只在本地终端生效，不写进任何文件**）：

```bash
export MCD_MCP_TOKEN='你的token'
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://mcp.mcd.cn/ \
  -H "Authorization: Bearer ${MCD_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}'
```

实测记录（2026-10-23，未带 Token）：`https://mcp.mcd.cn/` 返回 **403**，带合法 Token 的 `initialize` 应返回 200 与 Server 信息。
注意端点是根路径 `https://mcp.mcd.cn/`；`/mcp`、`/sse` 等路径均返回 404。
