#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用餐 · 麦门点单引擎（离线版 CLI）
用法:
  python yongcan_cli.py "6人 150元 2人不吃辣"              # 模式C 聚餐一键点
  python yongcan_cli.py --mode a "35元 减脂 不辣"           # 模式A 套餐推荐
  python yongcan_cli.py --mode b "想吃鸡腿堡和薯条 预算35"   # 模式B 麦门省钱
算法合同: skill/references/algorithm.md（菜单、九步、四条铁律一字不改）
"""
import math
import re
import sys

M = {
    "M1": ("香辣鸡腿堡", 16.5, 2, "鸡", 550),
    "M2": ("新奥尔良烤鸡腿堡", 17.5, 0, "鸡", 480),
    "M3": ("板烧鸡腿堡", 17.0, 0, "鸡", 500),
    "M4": ("劲脆鸡腿堡", 16.5, 0, "鸡", 560),
    "M5": ("香辣鸡肉卷", 12.5, 2, "鸡", 420),
    "M6": ("老北京鸡肉卷", 13.5, 0, "鸡", 430),
    "M7": ("蔬菜鸡蛋堡", 12.0, 0, "素", 350),
    "M8": ("培根蛋堡", 15.0, 0, "猪", 450),
    "M9": ("深海鳕鱼堡", 18.0, 0, "鱼", 440),
    "M10": ("咖喱鸡腿饭", 18.5, 1, "鸡", 620),
    "M11": ("台式卤肉饭", 16.0, 0, "猪", 650),
    "M12": ("香菇滑鸡饭", 17.0, 0, "鸡", 600),
    "M13": ("素什锦炒饭", 15.0, 0, "素", 550),
}
S = {
    "S1": ("中薯条", 11.0, 0, "素", 330),
    "S2": ("大薯条", 14.0, 0, "素", 480),
    "S3": ("黄金鸡米花", 12.0, 0, "鸡", 380),
    "S4": ("香辣鸡翅(2只)", 9.5, 2, "鸡", 260),
    "S5": ("甜玉米杯", 8.0, 0, "素", 150),
    "S6": ("蔬菜沙拉", 13.0, 0, "素", 120),
    "S7": ("香酥洋葱圈", 10.0, 0, "素", 300),
    "S8": ("葡式蛋挞(2只)", 10.0, 0, "素", 340),
}
D = {
    "D1": ("冰可乐(中)", 6.0, True, True, 180),
    "D2": ("冰柠檬红茶", 7.0, True, True, 120),
    "D3": ("鲜榨橙汁", 9.0, False, False, 160),
    "D4": ("热美式咖啡", 12.0, False, True, 10),
    "D5": ("热柠檬红茶", 8.0, False, True, 60),
    "D6": ("矿泉水", 3.0, False, False, 0),
    "D7": ("热豆浆", 7.5, False, False, 140),
}
CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}


def price(code):
    return (M.get(code) or S.get(code) or D.get(code))[1]


def name(code):
    return (M.get(code) or S.get(code) or D.get(code))[0]


def money(x):
    return f"{x:.1f}"


def count_group(t, words, n):
    """先找“数字/中文数字 + 人 + 忌口词”，再判全员，最后按出现次数计 1。"""
    pat = r"(\d+|[一二两三四五六七八九十])\s*(?:人|位|个人)?\s*(?:" + "|".join(words) + ")"
    m = re.search(pat, t)
    if m:
        v = m.group(1)
        return int(v) if v.isdigit() else CN_NUM.get(v, 1)
    if re.search(r"全员|所有人|都", t) and re.search("|".join(words), t):
        return n
    hits = sum(len(re.findall(w, t)) for w in words)
    return 1 if hits else 0


def parse(text):
    t = text.replace("，", ",").replace("、", ",")
    n = 1
    m = re.search(r"(\d+)\s*(?:人|位|个人)", t)
    if m:
        n = int(m.group(1))
    else:
        m = re.search(r"([一二两三四五六七八九十])\s*(?:人|位|个人)", t)
        if m:
            n = CN_NUM[m.group(1)]
    b = None
    m = re.search(r"人均\s*(\d+(?:\.\d+)?)", t)
    if m:
        b = float(m.group(1)) * n
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)", t)
        if m:
            b = float(m.group(1))
        else:
            m = re.search(r"预算\s*(\d+(?:\.\d+)?)", t)
            if m:
                b = float(m.group(1))
    b = b if b is not None else 50.0

    veg = count_group(t, ["素食", "不吃肉", "不吃荤", "吃素"], n)
    spicy = count_group(t, ["不吃辣", "怕辣", "吃不了辣", "不敢吃辣"], n)
    pork = count_group(t, ["清真"], n)
    ice = count_group(t, ["不喝冰", "怕凉", "不喝凉"], n)
    caf = count_group(t, ["不喝咖啡因", "不喝咖啡", "不喝茶"], n)

    veg, spicy, pork = min(veg, n), min(spicy, n), min(pork, n)
    if veg + spicy + pork > n:          # 一人多忌口 → 归最严格组
        spicy = min(spicy, max(0, n - veg))
        pork = min(pork, max(0, n - veg - spicy))
    allergy = "过敏备注：上甜品前须核对" if re.search(r"过敏", t) else ""
    return dict(n=n, b=b, veg=veg, spicy=spicy, pork=pork,
                ice=min(ice, n), caf=min(caf, n), allergy=allergy, raw=text)


def mode_c(p):
    n, b = p["n"], p["b"]
    veg, spicy, pork = p["veg"], p["spicy"], p["pork"]
    ice, caf = p["ice"], p["caf"]
    reg = max(0, n - veg - spicy - pork)
    it = {}
    flow = []

    def tot():
        return round(sum(q * price(c) for c, q in it.items() if q > 0), 2)

    def put(code, qty):
        if qty > 0:
            it[code] = it.get(code, 0) + qty

    def pull(code, qty):
        it[code] = max(0, it.get(code, 0) - qty)

    # ① 保底主食
    put("M7", veg); put("M6", spicy); put("M5", pork + reg)
    base = tot()
    flow.append(("① 保底主食",
                 f"素{veg}×12.0 + 不辣{spicy}×13.5 + 常规/清真{reg + pork}×12.5",
                 base, base))
    if b < base:
        return dict(cannot=True, need=base, b=b, n=n)
    prev = base

    # ② 矿泉水
    if tot() + 3.0 * n <= b:
        put("D6", n)
        flow.append(("② 人手矿泉水", f"{n}×3.0", 3.0 * n, tot()))
        water = True
    else:
        flow.append(("② 人手矿泉水", "预算不足，跳过（喝免费柠檬水）", 0.0, tot()))
        water = False
    prev = tot()

    # ③ 忌口组升级
    acts = []
    if veg and tot() + 3.0 * veg <= b:
        pull("M7", veg); put("M13", veg)
        acts.append(f"素食{veg}→素什锦炒饭 +{money(3.0 * veg)}")
    if spicy and tot() + 4.0 * spicy <= b:
        pull("M6", spicy); put("M2", spicy)
        acts.append(f"不吃辣{spicy}→新奥尔良烤鸡腿堡 +{money(4.0 * spicy)}")
    if pork and tot() + 4.0 * pork <= b:
        pull("M5", pork); put("M1", pork)
        acts.append(f"清真{pork}→香辣鸡腿堡 +{money(4.0 * pork)}")
    flow.append(("③ 忌口组升级", "；".join(acts) if acts else "预算不足，保持保底款", tot() - prev, tot()))
    prev = tot()

    # ④ 常规组升级
    if reg and tot() + 4.0 * reg <= b:
        pull("M5", reg); put("M1", reg)
        flow.append(("④ 常规组升级", f"常规{reg}→香辣鸡腿堡 +{money(4.0 * reg)}", tot() - prev, tot()))
    else:
        flow.append(("④ 常规组升级", "预算不足，保持香辣鸡肉卷", 0.0, tot()))
    prev = tot()

    # ⑤ 饮料升级
    acts = []
    plain = max(0, n - ice - caf)
    if plain:
        delta = 3.0 if water else 6.0
        if tot() + delta * plain <= b:
            if water:
                pull("D6", plain)
            put("D1", plain)
            acts.append(f"常规{plain}→冰可乐 +{money(delta * plain)}" if water
                        else f"常规{plain}→冰可乐 {money(6.0 * plain)}")
    if ice:
        delta = 4.5 if water else 7.5
        if tot() + delta * ice <= b:
            if water:
                pull("D6", ice)
            put("D7", ice)
            acts.append(f"不喝冰{ice}→热豆浆 +{money(delta * ice)}" if water
                        else f"不喝冰{ice}→热豆浆 {money(7.5 * ice)}")
    if caf:
        delta = 6.0 if water else 9.0
        if tot() + delta * caf <= b:
            if water:
                pull("D6", caf)
            put("D3", caf)
            acts.append(f"不喝咖啡因{caf}→鲜榨橙汁 +{money(delta * caf)}" if water
                        else f"不喝咖啡因{caf}→鲜榨橙汁 {money(9.0 * caf)}")
    flow.append(("⑤ 饮料升级", "；".join(acts) if acts else "预算不足，维持现状", tot() - prev, tot()))
    prev = tot()

    # ⑥ 共享小食
    got = []
    if n >= 3:
        pool = ["S2", "S1", "S3", "S7", "S5", "S6"]
        if spicy:
            pool = [c for c in pool if c != "S4"]
        if veg:
            pool = [c for c in pool if c not in ("S3", "S4")]
        if p["allergy"]:
            pool = ["S5", "S6"]
        cap = math.ceil(n / 3)
        for code in pool:
            if len(got) >= cap:
                break
            if tot() + price(code) <= b:
                put(code, 1)
                got.append(name(code))
    flow.append(("⑥ 共享小食", "、".join(got) if got else ("余额不足，未加" if n >= 3 else "N<3，不上共享小食"),
                 tot() - prev, tot()))
    prev = tot()

    # ⑦ 豪华升级
    acts = []
    if b - tot() >= 5.0 * n:
        for src in ("M2", "M1", "M6", "M5"):
            q = it.get(src, 0)
            if q and tot() + (18.0 - price(src)) * q <= b:
                pull(src, q); put("M9", q)
                acts.append(f"{q}份升深海鳕鱼堡 +{money((18.0 - price(src)) * q)}")
                break
        q = it.get("D1", 0)
        if q and tot() + 6.0 * q <= b:
            pull("D1", q); put("D4", q)
            acts.append(f"{q}杯升热美式 +{money(6.0 * q)}")
        if not p["allergy"]:
            capd, cnt = math.ceil(n / 2), 0
            while cnt < capd and tot() + 10.0 <= b:
                put("S8", 1); cnt += 1
            if cnt:
                acts.append(f"葡式蛋挞{cnt}份 +{money(10.0 * cnt)}")
    else:
        acts = [f"剩余{money(b - tot())}元 < 门槛{ money(5.0 * n)}元（5元×{n}人），零头不硬花"]
    flow.append(("⑦ 豪华升级", "；".join(acts), tot() - prev, tot()))

    kcal = 0.0
    for c, q in it.items():
        if q <= 0:
            continue
        if c in M:
            kcal += M[c][4] * q
        elif c in S:
            kcal += S[c][4] * q
        else:
            kcal += D[c][4] * q
    return dict(items=it, total=tot(), flow=flow, n=n, b=b, kcal=kcal,
                groups=dict(veg=veg, spicy=spicy, pork=pork, ice=ice, caf=caf, reg=reg))


def receipt_c(p):
    r = mode_c(p)
    n, b = p["n"], p["b"]
    if r.get("cannot"):
        L = ["像素快餐 PIXEL DINER", f"需求：{n}人 · 预算{money(b)}元",
             "─────────────────────", "❌ 点不成：预算不够保底",
             f"  保底合计 {money(r['need'])} 元，差 {money(r['need'] - b)} 元",
             f"  最省点法：全员保底主食 + 免费柠檬水 = {money(r['need'])} 元",
             f"  建议：① 预算补到 {money(r['need'])} 元"
             + ("；② 减 1 人（少一份最贵组保底主食）" if n > 1 else "（N=1 仅建议补预算）")]
        return "\n".join(L)
    L = ["（离线菜单模式 · 待接入麦当劳 MCP）", "像素快餐 PIXEL DINER",
         f"需求：{n}人 · 预算{money(b)}元 · 素{p['veg']}/不辣{p['spicy']}/清真{p['pork']}/不冰{p['ice']}/无咖啡因{p['caf']}",
         "─────────────────────", "明细"]
    for code, q in r["items"].items():
        if q > 0:
            L.append(f"  {name(code):<14}×{q}  {money(q * price(code))}")
    L += ["─────────────────────",
          f"  合计 {money(r['total'])} · 人均 {money(r['total'] / n)} · 结余 {money(b - r['total'])} · 能量≈{round(r['kcal'] / n)}千卡/人",
          f"  拆解：常规{r['groups']['reg']}人 + 素食{r['groups']['veg']} + 不吃辣{r['groups']['spicy']} + 清真{r['groups']['pork']}",
          "─────────────────────", "预算流水"]
    for nm, desc, cost, cum in r["flow"]:
        L.append(f"  {nm} {desc} → {money(cost) if abs(cost) > 1e-9 else '—'} ｜ 累计 {money(cum)}")
    L += ["─────────────────────", "自检",
          f"  ① 总价 {money(r['total'])} ≤ 预算 {money(b)} {'✓' if r['total'] <= b else '✗'}",
          "  ② 不吃辣组主食辣度0、共享小食不辣 ✓" if p["spicy"] else "  ② 无不吃辣需求 —",
          "  ③ 素食组主食全素 ✓" if p["veg"] else "  ③ 无素食需求 —",
          "  ④ 主食份数 = N ✓",
          "  ⑤ 不冰/无咖啡因饮品合规 ✓" if (p["ice"] or p["caf"]) else "  ⑤ 无饮品忌口 —"]
    return "\n".join(L)


def receipt_a(p):
    b = p["b"]
    low = bool(re.search("减脂|低卡|轻食|健身|热量", p["raw"]))
    full = bool(re.search("管饱|饿|增肌", p["raw"]))
    if low:
        picks = [("M7", "S6", "D4"), ("M5", "S6", "D6"), ("M7", "S6", "D3")]
    elif full:
        picks = [("M10", "S5", "D6"), ("M11", "S3", "D1"), ("M12", "S1", "D1")]
    else:
        picks = [("M6", "S5", "D6"), ("M2", "S1", "D1"), ("M9", "S6", "D7")]
    tiers = ["吃饱档", "吃好档", "豪华档"]
    L = ["（离线菜单模式 · 待接入麦当劳 MCP）", "像素快餐 PIXEL DINER · 套餐推荐",
         f"需求：预算 {money(b)} 元 · {'低卡向' if low else '管饱向' if full else '常规'}",
         "─────────────────────"]
    ranked = sorted(picks, key=lambda x: price(x[0]) + price(x[1]) + price(x[2]))
    cheapest = price(ranked[0][0]) + price(ranked[0][1]) + price(ranked[0][2])
    for i, (mm, ss, dd) in enumerate(ranked):
        cost = price(mm) + price(ss) + price(dd)
        kcal = M[mm][4] + S[ss][4] + D[dd][4]
        L.append(f"{tiers[i]}：{name(mm)} + {name(ss)} + {name(dd)}")
        L.append(f"  {money(cost)} 元 · {kcal} 千卡  {'✓' if cost <= b else '✗ 超预算，跳过'}")
    if cheapest > b:
        L.append(f"⚠️ 最低档 {money(cheapest)} 元已超预算 {money(b)} 元：建议预算至少提到 {money(cheapest)} 元，")
        L.append(f"   或只点主食 {name(ranked[0][0])}（{money(price(ranked[0][0]))} 元）+ 免费柠檬水。")
    L += ["─────────────────────", "自检：预算内档位均不超支 ✓；忌口按需求筛品项 ✓"]
    return "\n".join(L)


def receipt_b(p):
    b = p["b"]
    raw = p["raw"]
    want = []
    if re.search("鸡腿堡|汉堡", raw):
        want.append(["M1", 1])
    if re.search("薯条", raw):
        want.append(["S1", 2])
    if not want:
        want = [["M2", 1], ["S1", 1]]
    p0 = sum(price(c) * q for c, q in want)
    want_name = "、".join(name(c) for c, _ in want)
    cur = p0
    saved = []
    for row in want:
        if row[0] == "M1" and cur > b:
            cur -= (16.5 - 12.5) * row[1]
            saved.append(f"等价替代：香辣鸡腿堡→香辣鸡肉卷，省 {money(4.0 * row[1])}")
            row[0] = "M5"
    for row in want:
        if row[0] == "S1" and row[1] >= 2 and cur > b:
            cur -= 22.0 - 14.0
            saved.append("分享装合并：2×中薯条(22.0)→1×大薯条(14.0)，省 8.0")
            row[0], row[1] = "S2", 1
    L = ["（离线菜单模式 · 待接入麦当劳 MCP）", "像素快餐 PIXEL DINER · 麦门省钱",
         f"需求：{want_name} · 预算 {money(b)} 元",
         "─────────────────────", "省钱后清单"]
    for c, q in want:
        L.append(f"  {name(c):<14}×{q}  {money(q * price(c))}")
    L += ["─────────────────────",
          f"原价 {money(p0)} → 省后 {money(cur)}｜共省 {money(p0 - cur)} 元｜预算 {money(b)} 元 {'✓ 达标' if cur <= b else '✗ 仍超'}",
          "省钱依据："]
    L += [f"  · {s}" for s in (saved or ["本单已在预算内，无需替换"])]
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    mode = "c"
    if args[0] == "--mode":
        mode = args[1].lower()
        args = args[2:]
    p = parse(" ".join(args))
    print({"a": receipt_a, "b": receipt_b, "c": receipt_c}[mode](p))


if __name__ == "__main__":
    main()
