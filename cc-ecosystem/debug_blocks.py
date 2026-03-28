#!/usr/bin/env python3
"""Debug block format by testing blocks one by one."""

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

def notion_req(method: str, endpoint: str, payload: dict | None = None) -> dict:
    url = f"{NOTION_API}/{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"object": "error", "status": e.code, "message": body}

# Create a fresh page
payload = {
    "parent": {"page_id": "330fd892-6478-81d5-8cce-def9a1c772ae"},
    "properties": {"title": {"title": [{"type": "text", "text": {"content": "Debug Test 3"}}]}},
    "children": []
}
result = notion_req("POST", "pages", payload)
print("Page creation:", result.get("object"), result.get("id", result.get("message", "")))
page_id = result.get("id")
time.sleep(1.2)

# Test block types individually
tests = [
    ("heading_1", {"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "Test"}}]}}),
    ("paragraph", {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}}]}}),
    ("bulleted", {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "Item"}}]}}),
    ("numbered", {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": "Item"}}]}}),
    ("quote", {"type": "quote", "quote": {"rich_text": [{"type": "text", "text": {"content": "Quote"}}]}}),
    ("divider", {"type": "divider", "divider": {}}),
    ("code", {"type": "code", "code": {"rich_text": [{"type": "text", "text": {"content": "hi"}}], "language": "javascript"}}),
]

for name, block in tests:
    r = notion_req("PATCH", f"pages/{page_id}/blocks/children", {"children": [block]})
    status = r.get("object", "unknown")
    print(f"  {name}: {status}")
    time.sleep(1.1)

# Test table
print("\nTesting table...")
table_block = {
    "type": "table",
    "table": {"has_column_header": True, "has_row_header": False},
    "children": [
        {"type": "table_row", "table_row": {"cells": [
            [{"type": "text", "text": {"content": "Col A"}}],
            [{"type": "text", "text": {"content": "Col B"}}]
        ]}},
        {"type": "table_row", "table_row": {"cells": [
            [{"type": "text", "text": {"content": "Val 1"}}],
            [{"type": "text", "text": {"content": "Val 2"}}]
        ]}}
    ]
}
r = notion_req("PATCH", f"pages/{page_id}/blocks/children", {"children": [table_block]})
print(f"  table: {r.get('object')} - {str(r.get('message', 'OK'))[:200]}")
if r.get("object") == "error":
    print(json.dumps(r, indent=2)[:500])
