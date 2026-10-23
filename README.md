# 用餐 · 把饭点安排明白

> 麦当劳程序员节创意开发大赛 · 用餐赛道参赛作品 · 基于 WorkBuddy 打造的麦门点单 Skill
> **麦当劳 MCP 已接入并跑通真实调用**：每次出小票真打 5 个接口（门店 → 实时菜单 → 官方营养 → 可领券 → 官方计价核验），调用证据与 traceId 全部存档，见 [evidence/](./evidence) 与 [demo/live_run.md](./demo/live_run.md)。

一句话点单引擎，三大功能，输出**总价不超预算、忌口零违反、每笔花费有依据**的小票式方案。

## 项目介绍

| 模式 | 一句话示例 | 输出 |
| --- | --- | --- |
| 🍔 A 套餐推荐（含热量） | 「30 元推荐个不辣的套餐」/「减脂期 35 块吃什么」 | 吃饱/吃好/豪华三档套餐小票，每档标注合计千卡 |
| 💰 B 麦门省钱 | 「想吃鸡腿堡加薯条，预算 35，帮我省着点」 | 原价 vs 省后对比小票 + 逐条省钱依据 |
| 🎉 C 聚餐一键点 | 「6 个人预算 150 元，2 人不吃辣，帮我点」 | 全员忌口适配的九步算法小票 |

**亮点**：
- **真调了麦当劳 MCP**：35 个工具已探明，实际调用 `query-nearby-stores` / `query-meals` / `list-nutrition-foods` / `available-coupons` / `calculate-price`，小票底部打印每次调用的 traceId
- **官方计价核验**：小票合计与 `calculate-price` 逐分比对（多个场景 `149.00 = 149.00`、`58.50 = 58.50` 全对齐）；实测还抓到官方隐藏促销——本地算 150.00，官方返回「优惠 22.50 · 应付 127.50」
- 忌口全覆盖：素食 / 不吃辣 / 不吃猪肉 / 不喝冰饮 / 不喝咖啡因 / 过敏
- **热量用官方数据**：`list-nutrition-foods` 160 条（千卡/蛋白/脂肪/碳水/钠/钙），未收录的如实标"未收录"，不估算
- 预算硬约束：一分不超，结余不硬花
- 双引擎：`cli/mcd_live.py`（实时 MCP）/ `cli/yongcan_cli.py`（离线兜底），算法完全一致，只换数据源

## 安装方法

1. 克隆本仓库，将 `skill/` 目录复制到 WorkBuddy 技能目录：`~/.workbuddy/skills/用餐/`
2. （可选，推荐）接入麦当劳 MCP：
   - 到 mcp.mcd.cn 手机号登录 → 右上角「控制台」→「激活」申请免费 MCP Token
   - WorkBuddy 左侧【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置MCP】，
     粘贴 `mcp-config.example.json` 内容并把 `${MCD_MCP_TOKEN}` 换成实际 Token → 保存
   - 回到【自定义连接器】把 mcd-mcp【启用】
3. 对 WorkBuddy Agent 说话即用（见下）

## 使用示例

实时模式（已接入 MCP，真实输出见 [demo/live_run.md](./demo/live_run.md)）：

```
> 6 个人预算 150 元，2 人不吃辣，帮我点
  大脆鸡扒麦满分 ×6   11.0 × 6 = 66.0   2166 kcal
  【美汁源】"黄金橙橙" ×6   13.0 × 6 = 78.0   990 kcal
  灰焰圆筒 ×1   5.0 × 1 = 5.0
  ────────────────────────
  合计 149.0 元 · 人均 24.8 · 结余 1.0
  ▸ 官方计价核验：原价 149.00 元 ✓ 与本地合计一致
  ▸ 真实 MCP 调用链：query-nearby-stores / query-meals / list-nutrition-foods / available-coupons / calculate-price
    （每步 traceId 见小票底部，可在麦当劳侧核验）

> 1 人 25 元 减脂
  大脆鸡扒麦满分 ×1 + 黄金橙橙 ×1 → 24.0 元 · 526 kcal

> 3 人 60 元 1 人素食
  粥王系列精选 ×3 + 多汁柠柠 ×3 → 58.5 元（54 个餐品因忌口自动排除）
```

离线兜底模式（无 Token 也能跑，见 [demo/sample_run.md](./demo/sample_run.md)）：

```
> 6 个人预算 150 元，2 人不吃辣，帮我点
  香辣鸡腿堡 ×4 / 新奥尔良烤鸡腿堡 ×2 / 冰可乐(中) ×6 / 中薯条 ×1
  合计 148.0 · 人均 24.7 · 结余 2.0 · 762 千卡
```

现场演示：直接双击打开 `skill/assets/开饭.html`——单文件离线可用，像素风界面，支持一句话点单、预设场景、随机点单、小票复制。

## 目标用户

- **团建组织者**：几个人口味各异、预算卡死，一张小票摆平所有忌口
- **精打细算的麦门弟子**：想吃好又想省，要的是"省了多少、为什么省"的明白账
- **带娃家长**：过敏与忌口信息必须被严格执行，不接受"AI 忘了"
- **AI Skill 开发者**：一份"算法合同 + 收口自检 + 使用日志"的可靠 Skill 工程范本

## 仓库结构

```
├── README.md                 ← 本文件（项目介绍/安装/使用示例/目标用户）
├── CONTEST_DECLARATION.md    ← 参赛声明（官方原文，一字未改）
├── MCP_INTEGRATION.md        ← 麦当劳 MCP Server/35个Tool/调用流程/业务价值
├── mcp-config.example.json   ← 脱敏 MCP 配置示例（仅环境变量占位符）
├── workbuddy.md              ← WorkBuddy 开发过程 + MCP 使用记录
├── cli/
│   ├── mcd_live.py           ← ★ 实时 MCP 引擎（每次运行真打 5 个接口 + 官方计价核验）
│   ├── mcd_call.py           ← MCP 调用器（streamable HTTP，零依赖）
│   ├── collect_evidence.py   ← 调用证据采集（批量落原始 JSON-RPC 返回）
│   └── yongcan_cli.py        ← 离线点单引擎（无 Token 兜底，三模式可跑、可验账）
├── evidence/                 ← ★ 真实调用证据：9 份原始 JSON-RPC 返回 + 汇总索引
│   ├── 00_index.json
│   ├── 01_initialize.json          02_tools_list.json（35 工具）
│   ├── 03_now_time_info.json       04_available_coupons.json
│   ├── 05_campaign_calendar.json   06_nearby_stores.json
│   ├── 07_query_meals.json（96 餐品实时价）
│   ├── 08_nutrition_foods.json（160 条营养）
│   └── 09_calculate_price.json（官方计价核验）
├── demo/
│   ├── live_run.md           ← ★ 实时模式 4 个场景真实输出（含 traceId）
│   └── sample_run.md         ← 离线模式 5 个场景真实输出
└── skill/                    ← 技能本体
    ├── SKILL.md              ← 技能定义：模式路由 + MCP 接入层 + 三大模式
    ├── references/
    │   ├── algorithm.md      ← 算法合同：固定菜单、九步算法、四条铁律、自检
    │   └── mcp-usage-log.md  ← 麦当劳 MCP 调用日志（真实记录，含 traceId）
    └── assets/
        └── 开饭.html         ← 离线演示网页（单文件、可现场运行）
```

## 命令行直跑（零依赖，Python 3.8+）

**实时模式**（需 MCP Token，走真实接口）：

```bash
export MCD_MCP_TOKEN=<mcp.mcd.cn 申请的 Token>      # Windows: set MCD_MCP_TOKEN=...
python cli/mcd_live.py "6人 150元 2人不吃辣"                    # 模式C 聚餐一键点
python cli/mcd_live.py "1人 25元 减脂"                         # 模式A 减脂低卡
python cli/mcd_live.py "3人 60元 1人素食" --city 上海市 --keyword 人民广场
python cli/collect_evidence.py                                 # 重采 evidence/ 全部原始返回
```

**离线模式**（无 Token 也能跑，用于验账）：

```bash
python cli/yongcan_cli.py "6人 150元 2人不吃辣"                 # 模式C 聚餐一键点
python cli/yongcan_cli.py "8人 200元 2人素食 1人过敏 1人不喝冰"   # 复杂忌口
python cli/yongcan_cli.py --mode a "35元 减脂 不辣"              # 模式A 套餐推荐（含千卡）
python cli/yongcan_cli.py --mode b "想吃鸡腿堡和薯条 预算35"      # 模式B 麦门省钱
```

真实终端输出：[demo/live_run.md](./demo/live_run.md)（实时 4 场景）· [demo/sample_run.md](./demo/sample_run.md)（离线 5 场景）。

## 提交对照（官方五文件要求 · 逐条对齐）

| 官方要求 | 是否必须 | 本仓库 |
| --- | --- | --- |
| README.md（项目介绍/安装/使用示例/目标用户） | 必须 | ✅ 本文件 |
| CONTEST_DECLARATION.md（官方原文，文件名及内容均不可改） | 必须 | ✅ 直接取自官方仓库原文 |
| MCP_INTEGRATION.md（Server/Tool/流程/业务价值） | 必须 | ✅ |
| 源代码 | 必须 | ✅ `skill/` 全套 + `cli/` 双引擎 + 离线演示网页 |
| workbuddy.md（WorkBuddy 对话上下文） | 选填（拿 3000 积分必须） | ✅ |
| mcp-config.example.json（脱敏配置） | 非官方清单，便于复用 | ✅ 加分项 |

> 诚实声明：麦当劳 MCP **已接入并跑通真实调用**（证据见 `evidence/`，每次调用带 traceId）。本仓库不含任何真实 Token，配置仅环境变量占位符。离线兜底模式明确标注，不虚构价格与调用记录；两条路径的配餐算法完全一致。

## 报名步骤（两步都要做）

1. **作品站**：提交作品，填写本仓库地址。
2. **麦当劳大赛仓库发报名 Issue**（格式校验严格，标题与正文之间不要换行，项目地址不要用 Markdown 链接格式）：

```
【参赛申请】
项目名称：用餐 · 把饭点安排明白
项目地址：https://github.com/<你的用户名>/<仓库名>
项目简介：一句话点单的麦门用餐引擎——套餐推荐含热量标注、麦门省钱对比、聚餐一键点全员忌口零违反，接入麦当劳 MCP 时用实时菜单与活动。
```

⏰ 截止：**2026-10-25 23:59**（北京时间）；榜单于 2026-10-26 00:00 按 GitHub Star 数定榜（Star 为 0 不进榜）。

**报名硬条件**：仓库为 Public 公开仓库；仓库创建时间在 2025-12-25 ~ 2026-10-25 之间；上述文件齐全且文件名不可改动。

**奖励速览**：Star > 0 进排行榜（前 100 名）；前三名分别获巨无霸 50/30/20 次免费兑换券；前 100 名提交 workbuddy.md 得 3,000 WorkBuddy 积分，前三名另得 10,240 积分。
