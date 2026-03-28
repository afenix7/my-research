#!/usr/bin/env python3
"""Debug block format - test with full error details."""

import json
import urllib.request
import time
import os

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def notion_req_debug(method: str, endpoint: str, payload: dict | None = None) -> dict:
    url = f"{NOTION_API}/{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            return {"object": "success", "data": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except:
            err = body
        return {"object": "error", "status": e.code, "error": err}

# Create a fresh page
result = notion_req_debug("POST", "pages", {
    "parent": {"page_id": "330fd892-6478-81d5-8cce-def9a1c772ae"},
    "properties": {"title": {"title": [{"type": "text", "text": {"content": "Debug Test 4"}}]}},
    "children": []
})
print("Page creation:", result.get("object"), result.get("data", {}).get("id", result.get("error")))
page_id = result.get("data", {}).get("id")
time.sleep(1.2)

if not page_id:
    print("No page ID, exiting")
    exit(1)

# Test single block
block = {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello world"}}]}}
r = notion_req_debug("PATCH", f"pages/{page_id}/blocks/children", {"children": [block]})
print(f"Single paragraph: {json.dumps(r, indent=2)[:1000]}")
