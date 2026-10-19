# MCP 集成说明

本文件说明项目实际使用的麦当劳 MCP Server / Tool、调用流程与业务价值。

## 一、使用的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp`（麦当劳 MCP 官方服务） |
| Token 申请 | `open.mcd.cn/mcp` → 手机号登录 → 控制台 → 激活 → 领取（免费） |
| 配置方式 | 环境变量 `${MCD_MCP_TOKEN}`，见 `mcp-config.example.json` |

## 二、调用的 Tool 与用途

| Tool | 用途 | 是否核心 |
|---|---|---|
| `query-meals` | 拉取当前门店可售菜单与价格（**原价主数据源**，决定固定成本基数） | ✅ 核心 |
| `available-coupons` | 麦麦省可领券池 | ✅ 核心 |
| `query-my-coupons` | 我账户已有券 | ✅ 核心 |
| `query-store-coupons` | 门店专属券 | ✅ 核心 |
| `auto-bind-coupons` | 一键领取全部可用券（不调会漏券） | ✅ 核心 |
| `calculate-price` | 券后核价，得到真实实付金额（**变动成本基数**） | ✅ 核心 |
| `list-nutrition-foods` | 营养数据（可选扩展：按热量约束筛选后再算毛利） | 可选 |
| `create-order` | 下单（本项目**不调用**，只做分析不下单） | ❌ 不使用 |

> 说明：券必须从四路查全（可领券 / 已有券 / 门店券 / 一键领取后新增），少查一路会低估优惠力度，进而高估门店毛利。

## 三、调用流程

```
1. query-meals
   └─> 得到菜单与原价 → 计算 原价合计 L

2. auto-bind-coupons
   ├─> available-coupons
   ├─> query-my-coupons
   └─> query-store-coupons        （四路券池合并）

3. calculate-price
   └─> 得到券后实付 → 实付 P

4. 本地确定性计算（src/estimator.py，不经过大模型）
   固定成本 = L × (food + labor + occupancy + other)
   变动成本 = P × royalty
   毛利     = P − 固定成本 − 变动成本
   毛利率   = 毛利 / P
   盈亏平衡让利率 = 1 − 固定成本率合计 / (1 − royalty)
```

## 四、业务价值

1. **对消费者**：把"我省了多少"翻译成"门店这单赚多少"，让优惠的代价变得具体。
2. **对餐饮从业者**：一个可直接复用的「让利率 ↔ 毛利率」教学模型，直观展示为什么折扣打过头会亏钱。
3. **对开发者**：示范 MCP 取数 + 确定性算法分层 —— 涉及金额的部分一律交给代码，不让模型口算。

## 五、安全与合规

- 真实 Token **从不入库**，配置仅使用环境变量占位符。
- 项目不调用 `create-order`，不涉及任何交易与支付行为。
- 所有成本参数由使用者自行提供，项目本身不持有、不传播任何品牌的经营数据。
- 输出显著标注为估算结果，并声明不构成经营建议。
