#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦当劳 MCP 调用器（streamable HTTP，零依赖）
用法：
  set MCD_MCP_TOKEN=xxx
  python mcd_call.py tools/list
  python mcd_call.py tools/call query-meals '{"storeCode":"...","orderType":1,"beType":1}'
Token 只从环境变量读取，绝不写入仓库。
"""
import json, os, sys, urllib.request

ENDPOINT = os.environ.get("MCD_MCP_ENDPOINT", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")


def rpc(method, params=None, rid=1, timeout=40):
    body = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + TOKEN,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # 兼容 SSE 帧
    if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):
        chunks = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = chunks[-1] if chunks else "{}"
    return json.loads(raw)


def call_tool(name, args=None, rid=10):
    return rpc("tools/call", {"name": name, "arguments": args or {}}, rid=rid)


def main():
    if not TOKEN:
        sys.exit("缺少环境变量 MCD_MCP_TOKEN")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tools/list"
    if cmd == "tools/list":
        d = rpc("tools/list", {})
        tools = d.get("result", {}).get("tools", [])
        for t in tools:
            print(t["name"])
        print("--- 共 %d 个工具 ---" % len(tools))
        return
    if cmd == "tools/call":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        d = call_tool(name, args)
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return
    sys.exit("未知命令: " + cmd)


if __name__ == "__main__":
    main()
