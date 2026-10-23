# MCP_INTEGRATION.md · 麦当劳 MCP 集成说明

> 官方要求：说明实际使用的麦当劳 MCP Server、Tool、调用流程和业务价值。
> **当前状态：已接入并跑通真实调用。** 本文所有调用记录均附 `traceId`，可在麦当劳侧核验，无一条虚构。

## 一、使用的 MCP Server（官方配置）

| 项目 | 说明 |
| --- | --- |
| Server | 麦当劳中国官方 MCP `mcd-mcp` v1.0.0（`initialize` 实测返回 `serverInfo.name = mcd-mcp`） |
| 协议类型 | `streamablehttp`（JSON-RPC 2.0 over HTTP POST） |
| 服务端点 | `https://mcp.mcd.cn` |
| 鉴权 | `Authorization: Bearer <MCD_MCP_TOKEN>` |
| Token 获取 | mcp.mcd.cn 手机号登录 → 右上角「控制台」→「激活」→ 复制 Token（免费） |
| 配置文件 | `mcp-config.example.json`（脱敏示例，真实 Token 走环境变量 `MCD_MCP_TOKEN`，不入库） |

WorkBuddy 连接器配置（官方步骤）：

1. 打开 WorkBuddy，左侧边栏【专家·技能·连接器】→ 选中【连接器】页签
2. 右上角【自定义连接器】→【配置MCP】
3. 填入 `mcp-config.example.json` 的 JSON（把 `${MCD_MCP_TOKEN}` 换成实际 Token），【保存】
4. 回到【自定义连接器】，将 mcd-mcp【启用】

## 二、MCP 开放的 35 个 Tool（`tools/list` 实测清单）

按业务域归类，本技能实际调用标 **★**：

| 域 | Tool |
| --- | --- |
| 点餐主链 | **★query-nearby-stores**（查门店）、**★query-meals**（实时菜单）、query-meal-detail（套餐组成/特调）、**★calculate-price**（真价含优惠）、create-order（下单）、query-order、order-list、cancel-order |
| 营养 | **★list-nutrition-foods**（160 条餐品营养数据：千焦/千卡/蛋白/脂肪/碳水/钠/钙） |
| 优惠券 | **★available-coupons**（可领券）、auto-bind-coupons（一键领券）、query-my-coupons（卡包券）、query-store-coupons（门店可用券） |
| 活动日历 | **★campaign-calendar**（麦麦日历：当月活动时间线）、**★now-time-info**（服务器时间） |
| 外送 / 团餐 | delivery-query-addresses、delivery-create-address、delivery-query-stores、query-meal-assistance（助餐服务）、query-promotions（满减满折）、delivery-query-stores |
| 积分商城 | mall-points-products、mall-product-detail、mall-create-order、mall-order-list、mall-order-detail、query-my-account、query-lottery-info、draw-lottery、query-my-prizes |
| 主题派对 | query-party-city、query-party-store、query-party-store-date、query-party-store-session、party-order-create |
| 满意度 | query-survey-coupon |

> 说明：技能只用到点餐主链 + 营养 + 券 + 日历这 8 个核心工具，其余为 MCP 已开放但本技能未使用的能力，如实列出以免夸大。

## 三、真实调用流程（每次出小票都走这 5 步）

```
query-nearby-stores   按「城市+关键词」定位门店 → storeCode
        ↓
query-meals           拉该门店当前时段实时菜单（餐品名/现价/原价/分类/可售状态）
        ↓
list-nutrition-foods  拉官方营养库（160 条），按餐品名关联千卡与蛋白
        ↓
available-coupons     拉用户可领券（当前实测：11.9元麦辣鸡腿堡 / 19.9元王牌炸鸡任选2 / 免费脆薯饼）
        ↓
[本地配餐]            预算内配「主食+饮品+小食」，忌口硬过滤，热量目标适配
        ↓
calculate-price       把点单提交官方真价核验（含促销优惠），结果与本地合计逐分比对
        ↓
出小票                 底部打印 5 个 traceId + 官方计价核验结果
```

落地实现：`cli/mcd_live.py`（零依赖 Python，`python cli/mcd_live.py "6人 150元 2人不吃辣"`）。
每次运行都真实打这 5 个接口，不是预生成数据。

## 四、调用证据（`evidence/` 目录，原始 JSON-RPC 返回）

采集于 2026-10-23，门店：麦当劳上海黄浦华旭国际大厦餐厅（`storeCode=1450713`）。

| 序号 | 文件 | Tool / Method | 结果 | traceId |
| --- | --- | --- | --- | --- |
| 1 | `01_initialize.json` | `initialize` | OK（mcd-mcp v1.0.0） | —（协议握手） |
| 2 | `02_tools_list.json` | `tools/list` | OK（35 个工具） | — |
| 3 | `03_now_time_info.json` | now-time-info | OK | `d23ae324ccb883eec8a07bf1b8264e3f` |
| 4 | `04_available_coupons.json` | available-coupons | OK（3 类券） | `ed54b1c880c8e3b482131c500adf76b3` |
| 5 | `05_campaign_calendar.json` | campaign-calendar | OK（12 天活动时间线） | `407f9bee9efb7a6b94303ce2276ebf43` |
| 6 | `06_nearby_stores.json` | query-nearby-stores | OK（5 家门店） | `eff742135d66707d4699f1d3fcdb552c` |
| 7 | `07_query_meals.json` | query-meals | OK（96 个餐品实时价） | `a12ca83674c637f1411964030b687289` |
| 8 | `08_nutrition_foods.json` | list-nutrition-foods | OK（160 条营养） | `c70ce420bd2851e63fbc20036d845ea2` |
| 9 | `09_calculate_price.json` | calculate-price | OK（2×双层猪柳蛋麦满分 + 2×冰牛奶 = 80.00 元，与菜单价逐分一致） | `e5c03a95b693fa1292c28a87eef84cfd` |
| — | `00_index.json` | 汇总索引 | — | — |

每次实时出小票另产生 5 个新 traceId，详见 `demo/live_run.md`（4 个场景 × 5 次调用）。

## 五、实测发现（真实数据里长出来的结论，不是设计假设）

1. **`calculate-price` 会返回真实促销优惠**：某次 6 人单本地合计 150.00 元，官方返回「原价 150.00 · 优惠 22.50 · 应付 127.50」——说明部分餐品有隐藏促销，本地估算只能算到"原价"，**真优惠只有官方接口知道**。这是接入 MCP 最硬的价值。
2. **菜单是分时段的**：09:43 拉取仅返回 96 个早餐类餐品（麦满分/厚松饼堡/粥王/麦咖啡等），午晚市品类不同。技能每次运行都重新拉，不缓存隔夜菜单。
3. **套餐价与单品价不可混算**：套餐 `currentPrice 17.9 / originalPrice 29.9`，`calculate-price` 若不带 `roundList` 会按原价计。故技能只用**单品组合**出单，保证本地合计与官方计价逐分对齐。
4. **营养库收录率约 22%**（96 个菜单餐品中 21 个能按名匹配）：营养库以单品为主，套餐/组合类多未收录。技能如实标注「N/M 份已收录」，不估算、不编造。
5. **活动日历只给 `activityCode`**（如 `m228`/`185p`），无活动名称文案。技能只报"今日有 N 场活动"，不编活动名。

## 六、业务价值（对应官方 MCP 三大能力）

| 官方 MCP 能力 | 本技能用法 | 价值 |
| --- | --- | --- |
| 智能点餐（点餐与下单） | 模式 A/C 用 `query-meals` 取实时菜单，`calculate-price` 做真价核验 | 小票金额与门店一致，且能捕获官方促销（实测省 22.50 元） |
| 优惠券周周领 | `available-coupons` 把小票可领券直接印在单据上 | 从"结构性省钱"升级为"结构 + 可用券"双重提示 |
| 麦麦日历（活动信息） | `campaign-calendar` 拉当月活动时间线 | 推荐不只算钱，还知道今天有几场活动 |
| 营养搭配 | `list-nutrition-foods` 160 条官方营养数据 | "按热量配餐"用的是官方数据，不是估算值 |

## 七、降级与诚实声明

- **有 Token**：走上述 5 步真实链路，小票底部打印 traceId。
- **无 Token**：`cli/yongcan_cli.py` 用合同内离线菜单兜底，小票标注「离线菜单模式」，不伪造价格与调用记录。
- 两条路径的配餐算法（预算硬约束、忌口零违反、结余不硬花）完全一致，差别只在数据来源。
- 本仓库不含任何真实 Token；`mcp-config.example.json` 仅环境变量占位符。
