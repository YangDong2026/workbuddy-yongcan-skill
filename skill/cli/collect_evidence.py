#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦当劳 MCP 真实调用证据采集器
运行：MCD_MCP_TOKEN=xxx python scripts/collect_evidence.py
输出：用餐-mcp-skill/evidence/*.json（原始 JSON-RPC 返回，含 traceId，不含 Token）
"""
import json, os, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcd_call import rpc, call_tool

ROOT = r"C:/Users/MyPC/WorkBuddy/2026-10-21-20-22-57"
OUT = os.path.join(ROOT, "用餐-mcp-skill", "evidence")
os.makedirs(OUT, exist_ok=True)

STORE = "1450713"  # 麦当劳上海黄浦华旭国际大厦餐厅

CALLS = [
    ("01_initialize", "rpc", "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                            "clientInfo": {"name": "yongcan-skill", "version": "1.0"}}),
    ("02_tools_list", "rpc", "tools/list", {}),
    ("03_now_time_info", "tool", "now-time-info", {}),
    ("04_available_coupons", "tool", "available-coupons", {}),
    ("05_campaign_calendar", "tool", "campaign-calendar", {}),
    ("06_nearby_stores", "tool", "query-nearby-stores",
     {"beType": 1, "searchType": 2, "city": "上海市", "keyword": "人民广场"}),
    ("07_query_meals", "tool", "query-meals",
     {"storeCode": STORE, "orderType": 1, "beType": 1}),
    ("08_nutrition_foods", "tool", "list-nutrition-foods", {}),
]

summary = []
for i, (fname, kind, name, args) in enumerate(CALLS, 1):
    try:
        d = rpc(name, args, rid=100 + i) if kind == "rpc" else call_tool(name, args, rid=100 + i)
        sc = (d.get("result") or {}).get("structuredContent") or {}
        ok = sc.get("success") if sc else (("result" in d) and not (d.get("result") or {}).get("isError"))
        trace = sc.get("traceId", "-")
        record = {
            "seq": i, "captured_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "method": "initialize" if kind == "rpc" else "tools/call",
            "tool": name if kind == "tool" else "-",
            "arguments": args, "success": bool(ok), "traceId": trace,
            "raw_response": d,
        }
        with open(os.path.join(OUT, fname + ".json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        summary.append((fname, "OK" if ok else "FAIL", trace))
        print(f"[{i}] {fname:<22} {'OK' if ok else 'FAIL'}  traceId={trace}")
    except Exception as e:
        summary.append((fname, "ERROR " + str(e)[:60], "-"))
        print(f"[{i}] {fname:<22} ERROR {e}")

with open(os.path.join(OUT, "00_index.json"), "w", encoding="utf-8") as f:
    json.dump({"captured_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "endpoint": "https://mcp.mcd.cn",
               "server": "mcd-mcp v1.0.0",
               "store": "麦当劳上海黄浦华旭国际大厦餐厅 (storeCode=1450713)",
               "calls": [{"seq": i + 1, "file": s[0], "status": s[1], "traceId": s[2]}
                         for i, s in enumerate(summary)]}, f, ensure_ascii=False, indent=1)
print("\n证据已存:", OUT)
