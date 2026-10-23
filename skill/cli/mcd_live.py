#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用餐 · 麦当劳 MCP 实时版引擎（每次运行都真实调用 MCP）

用法：
  set MCD_MCP_TOKEN=xxx
  python mcd_live.py "6人 150元 2人不吃辣"
  python mcd_live.py "1人 30元 减脂" --city 上海市 --keyword 人民广场
  python mcd_live.py "3人 100元" --store 1450713

真实调用链（每次运行）：
  query-nearby-stores → query-meals → list-nutrition-foods → available-coupons
  → 本地配餐 → calculate-price（真实验价）
全程 traceId 打印在小票底部，可核验。
"""
import argparse, json, os, re, sys, urllib.request

ENDPOINT = os.environ.get("MCD_MCP_ENDPOINT", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
_rid = [0]

# ---------- JSON-RPC ----------
def rpc(method, params=None, timeout=40):
    if not TOKEN:
        raise SystemExit("缺少环境变量 MCD_MCP_TOKEN（mcp.mcd.cn 申请）")
    _rid[0] += 1
    body = {"jsonrpc": "2.0", "id": _rid[0], "method": method}
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream",
                 "Authorization": "Bearer " + TOKEN}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    if raw.lstrip().startswith(("event:", "data:")):
        ch = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = ch[-1] if ch else "{}"
    return json.loads(raw)

_CALLS = []

def tool(name, args=None, timeout=40):
    d = rpc("tools/call", {"name": name, "arguments": args or {}}, timeout=timeout)
    sc = (d.get("result") or {}).get("structuredContent") or {}
    _CALLS.append({"tool": name, "success": sc.get("success"),
                   "traceId": sc.get("traceId"), "arguments": args or {}})
    if not sc.get("success"):
        raise RuntimeError(f"{name} 调用失败：{sc.get('message')}")
    return sc.get("data")

# ---------- 需求解析 ----------
RESTRICT_RULES = [
    ("不吃辣", r"(不吃辣|不要辣|忌辣|不辣的?)", ["麦辣", "香辣", "辣"]),
    ("不吃猪肉", r"(不吃猪|忌猪|清真)", ["猪", "培根", "火腿", "香肠", "叉烧"]),
    ("不吃牛", r"(不吃牛)", ["牛", "安格斯", "巨无霸"]),
    ("不吃鸡", r"(不吃鸡)", ["鸡", "麦乐鸡", "鸡翅"]),
    ("素食", r"(素食|吃素|全素)", ["猪", "牛", "鸡", "鱼", "肉", "蛋", "培根", "火腿", "香肠", "鳕", "虾", "安格斯", "巨无霸"]),
    ("不喝冰", r"(不(喝|要)冰|去冰|常温)", ["冰"]),
    ("不喝咖啡因", r"(不(喝)?咖啡因|不喝咖啡|无咖啡因)", ["咖啡", "美式", "拿铁", "卡布奇诺", "浓缩", "红茶", "可乐", "麦咖啡"]),
    ("不吃奶", r"(不吃奶|乳糖不耐)", ["奶", "芝士", "吉士", "冰淇淋", "新地", "麦旋风", "拿铁", "卡布奇诺"]),
]

def parse(text):
    n = 1
    m = re.search(r"(\d+)\s*(?:人|位|个)", text)
    if m: n = int(m.group(1))
    b = None
    m = re.search(r"(?:预算|共|大概|差不多)?\s*(\d+(?:\.\d+)?)\s*(?:元|块|rmb)?", text)
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)", text)
    if m2: b = float(m2.group(1))
    elif m and float(m.group(1)) > 5: b = float(m.group(1))
    if b is None: b = round(30.0 * n, 2)
    excl = []
    for label, pat, _ in RESTRICT_RULES:
        mm = re.search(pat, text)
        if mm:
            cnt = 0
            c = re.search(r"(\d+)\s*人\s*(?:" + pat + ")", text)
            if c: cnt = int(c.group(1))
            excl.append((label, cnt or n))
    kcal_mode = None
    if re.search(r"(减脂|低卡|低热量|健身|控卡|瘦)", text): kcal_mode = "low"
    elif re.search(r"(管饱|吃饱|增肌|大胃|饿了|顶饿)", text): kcal_mode = "high"
    return n, b, excl, kcal_mode

# ---------- 菜单 ----------
STAPLE_CATS = ("麦满分系列", "厚松饼堡系列", "炒双蛋堡系列", "早安营养卷", "粥王系列", "超值早餐", "人气热卖")
DRINK_CATS = ("饮品", "麦咖啡™", "一早现磨")
SNACK_CATS = ("小食甜品/其他",)

def classify(meal):
    name, cats = meal["name"], meal.get("cats") or []
    is_combo = ("套餐" in name) or ("组合" in name) or ("三件套" in name) or ("二件套" in name)
    if is_combo: return "combo"
    if any(c in DRINK_CATS for c in cats): return "drink"
    if any(c in SNACK_CATS for c in cats): return "snack"
    if any(c in STAPLE_CATS for c in cats): return "staple"
    return "other"

def blocked(name, excludes):
    for label, words in excludes:
        for w in words:
            if w in name: return label
    return None

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("requirement", help='例："6人 150元 2人不吃辣"')
    ap.add_argument("--city", default="上海市")
    ap.add_argument("--keyword", default="人民广场")
    ap.add_argument("--store", default=None, help="直接指定 storeCode，跳过门店搜索")
    args = ap.parse_args()

    n, budget, excl_raw, kcal_mode = parse(args.requirement)
    out = []
    p = out.append

    # 1. 门店
    if args.store:
        store_code, store_name = args.store, "(指定门店)"
    else:
        stores = tool("query-nearby-stores",
                      {"beType": 1, "searchType": 2, "city": args.city, "keyword": args.keyword})
        if not stores: raise SystemExit("未找到门店")
        store_code, store_name = stores[0]["storeCode"], stores[0]["storeName"]

    # 2. 实时菜单
    md = tool("query-meals", {"storeCode": store_code, "orderType": 1, "beType": 1})
    meals, cats = md["meals"], md["categories"]
    cat_of = {}
    for c in cats:
        for mm in c["meals"]:
            cat_of.setdefault(mm["code"], []).append(c["name"].replace("\n", ""))
    menu = []
    for code, v in meals.items():
        menu.append({"code": code, "name": v["name"],
                     "price": float(v["currentPrice"]),
                     "orig": float(v.get("originalPrice") or v["currentPrice"]),
                     "cats": cat_of.get(code, [])})

    # 3. 实时营养
    nutr_raw = tool("list-nutrition-foods")
    nutr = {}
    for line in nutr_raw.split("\n")[2:]:
        ps = [x.strip() for x in line.split(",")]
        if len(ps) < 9: continue
        try: nutr[ps[0]] = float(ps[3])
        except ValueError: pass

    # 4. 实时优惠券
    try:
        coupons = tool("available-coupons") or []
    except Exception:
        coupons = []

    # 5. 忌口过滤
    excludes = [(label, words) for label, _, words in RESTRICT_RULES
                if any(label == l for l, _ in excl_raw)]
    ok = []
    for m in menu:
        kind = classify(m)
        if kind == "other": continue
        hit = blocked(m["name"], excludes)
        m2 = dict(m, kind=kind, cal=nutr.get(m["name"]), blocked_by=hit)
        ok.append(m2)
    usable = [m for m in ok if not m["blocked_by"]]
    n_blocked = len(ok) - len(usable)

    # 6. 配餐：单品组合（主食 + 饮品 [+ 小食]），价格与营养均可逐项核验
    per = budget / n
    def kcal_ok(m):
        if m["cal"] is None: return True
        if kcal_mode == "low": return m["cal"] <= 420
        if kcal_mode == "high": return m["cal"] >= 200
        return True

    def best(pool, limit):
        c = [m for m in pool if m["price"] <= limit and kcal_ok(m)]
        if not c: return None
        c.sort(key=lambda x: (-x["price"], (x["cal"] or 0)))
        return c[0]

    staples = [m for m in usable if m["kind"] == "staple"]
    DESSERT_WORDS = ("阿芙佳朵", "麦旋风", "新地", "冰淇淋", "圆筒", "圣代", "派", "麦乐酷")
    drinks = [m for m in usable if m["kind"] == "drink"
              and not any(w in m["name"] for w in DESSERT_WORDS)]
    snacks = [m for m in usable if m["kind"] == "snack"
              or (m["kind"] == "drink" and any(w in m["name"] for w in DESSERT_WORDS))]

    picks = []
    # 优先「主食 + 饮品」在人均预算内最大化利用；饮品按大众偏好排序，避免浓缩咖啡等小众款
    POPULAR = ("可乐", "雪碧", "红茶", "牛奶", "豆浆", "柠柠", "橙橙", "苹果",
               "柠檬", "怡泉", "纯悦", "燕麦奶", "鲜萃")
    pair = None
    drink_order = sorted(drinks, key=lambda m: (0 if any(w in m["name"] for w in POPULAR) else 1,
                                               -m["price"]))
    for dr in drink_order:
        if not kcal_ok(dr): continue
        cand = [st for st in staples if st["price"] + dr["price"] <= per and kcal_ok(st)]
        if cand:
            pair = (max(cand, key=lambda x: x["price"]), dr)
            break
    if pair:
        main, dr = pair[0], pair[1]
    else:
        main = best(staples, per)
        dr = None
    if not main:
        p("·  点不成 · 预算不足")
        p("─────────────────────────────")
        p(f"人数 {n} 人 · 预算 {budget:.1f} 元 · 人均 {per:.1f} 元")
        cand = [m for m in usable if m["kind"] in ("staple", "snack")]
        if cand:
            ch = min(cand, key=lambda x: x["price"])
            need = ch["price"] * n
            p(f"当前时段最低主食：{ch['name']} {ch['price']:.1f} 元 ×{n} = {need:.1f} 元")
            p(f"还差 {need - budget:.1f} 元；或人数减到 {int(budget // ch['price'])} 人")
        else:
            p("当前时段无符合忌口的餐品可点，建议放宽忌口或换时段。")
        print("\n".join(out)); return

    picks.append({"meal": main, "qty": n})
    total = main["price"] * n
    left = budget - total
    if dr:
        picks.append({"meal": dr, "qty": n})
        total += dr["price"] * n
        left = budget - total

    # 结余买小食（份数受结余约束，不超预算）
    ups = []
    for s in sorted(snacks, key=lambda x: -x["price"]):
        if s["price"] <= 0 or left < s["price"]: continue
        q = int(min(n, left // s["price"]))
        if q >= 1:
            picks.append({"meal": s, "qty": q})
            total += s["price"] * q
            left = budget - total
            ups.append(f"{s['name']} ×{q}（{s['price']*q:.1f} 元）")

    # 8. 真实验价
    calc = None
    try:
        calc = tool("calculate-price", {"storeCode": store_code, "orderType": 1, "beType": 1,
                    "items": [{"productCode": x["meal"]["code"], "quantity": x["qty"]} for x in picks]})
    except Exception as e:
        calc = {"_error": str(e)}

    # 9. 小票
    kcal_total = sum((x["meal"]["cal"] or 0) * x["qty"] for x in picks)
    kcal_known = all(x["meal"]["cal"] is not None for x in picks)
    n_known = sum(x["qty"] for x in picks if x["meal"]["cal"] is not None)
    n_total = sum(x["qty"] for x in picks)
    w = 46
    p("█ 麦当劳 · 用餐（MCP 实时模式）")
    p(f"门店：{store_name}")
    seg = [f"{n}人", f"预算 {budget:.0f} 元",
           ("、".join(f"{c}人{lb}" for lb, c in excl_raw) if excl_raw else "无忌口")]
    if kcal_mode:
        seg.append("低卡向" if kcal_mode == "low" else "管饱向")
    p("需求：" + " · ".join(seg))
    p("─" * w)
    for x in picks:
        m = x["meal"]
        p(f"{m['name']}  ×{x['qty']}")
        p(f"  {m['price']:.1f} × {x['qty']} = {m['price']*x['qty']:.1f}" +
          (f"   {m['cal']*x['qty']:.0f} kcal" if m["cal"] is not None else ""))
    p("─" * w)
    p(f"合计 {total:.1f} 元 · 人均 {total/n:.1f} 元 · 结余 {left:.1f} 元")
    if kcal_known:
        p(f"能量 {kcal_total:.0f} kcal · 人均 {kcal_total/n:.0f} kcal")
    elif n_known:
        p(f"能量 {kcal_total:.0f} kcal（{n_known}/{n_total} 份已收录营养数据 · 数据源：list-nutrition-foods）")
    else:
        p("能量：本单餐品暂未收录于官方营养库（list-nutrition-foods）")

    if calc and "_error" not in calc:
        real = calc.get("originalPrice")
        pay = calc.get("price")
        disc = calc.get("discount")
        if real is not None:
            p(f"▸ 官方计价核验：原价 {real/100:.2f} 元" +
              (f" · 优惠 {float(disc)/100:.2f} 元 · 应付 {float(pay)/100:.2f} 元" if pay is not None else "") +
              ("  ✓ 与本地合计一致" if abs(real/100 - total) < 0.01 else "  ⚠ 与本地合计有差异"))
        tw = calc.get("takeWayList") or []
        if tw:
            p(f"▸ 取餐方式：{' / '.join(t['title'] for t in tw)}")
    p("─" * w)
    if ups:
        p("结余升级：" + "；".join(ups))
    if n_blocked:
        p(f"忌口过滤：{n_blocked} 个餐品因忌口被排除")
    if coupons:
        names = []
        for c in coupons[:3]:
            nm = c.get("couponName")
            if nm and nm not in names: names.append(nm)
        if names:
            p("可领券：" + " / ".join(names))
    p("─" * w)
    p("真实 MCP 调用链（可核验）：")
    for c in _CALLS:
        p(f"  {c['tool']:<22} {'OK' if c['success'] else 'FAIL'}  {c['traceId']}")
    print("\n".join(out))

if __name__ == "__main__":
    main()
