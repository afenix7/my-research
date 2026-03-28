#!/usr/bin/env python3
"""Convert Markdown files to Notion blocks and create Notion pages using notion-client SDK."""

import asyncio
import json
import re
import sys
import os
from notion_client import AsyncClient
from typing import Any

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "330fd892-6478-81d5-8cce-def9a1c772ae")

CODE_LANGUAGES = {
    "bash", "cpp", "csharp", "css", "diff", "docker", "go", "graphql",
    "html", "java", "javascript", "json", "kotlin", "lua", "markdown",
    "nginx", "php", "plain text", "python", "ruby", "rust", "scala",
    "shell", "sql", "swift", "typescript", "yaml", "text",
    "sh", "zsh", "js", "ts", "yml", "c", "rb", "rs", "md", "txt",
}

FILES = [
    ("README.md", "📋 总览与对比分析"),
    ("gsd-codemap.md", "⚙️ GSD CodeMap"),
    ("gstack-codemap.md", "🌐 gstack CodeMap"),
    ("superpowers-codemap.md", "💪 Superpowers CodeMap"),
    ("ralph-codemap.md", "🔄 Ralph CodeMap"),
    ("opencli-codemap.md", "🖥️ opencli CodeMap"),
]

BASE_DIR = "/root/my-research/cc-ecosystem"


def rich_text(text: str) -> list:
    chunks = []
    for i in range(0, len(text), 2000):
        chunks.append({"type": "text", "text": {"content": text[i:i+2000]}})
    return chunks


def md_to_blocks(md: str) -> list[dict]:
    blocks = []
    lines = md.split("\n")
    i = 0
    in_code_block = False
    code_lang = ""
    code_content = []

    def flush_code():
        nonlocal code_content, code_lang
        if code_content:
            content = "\n".join(code_content)
            lang = code_lang.lower().strip()
            if lang not in CODE_LANGUAGES:
                lang = "plain text"
            for j in range(0, len(content), 2000):
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": rich_text(content[j:j+2000]),
                        "language": lang,
                    }
                })
            code_content = []
            code_lang = ""

    while i < len(lines):
        line = lines[i]

        # Code block start/end
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                code_content = []
            else:
                flush_code()
                in_code_block = False
            i += 1
            continue

        if in_code_block:
            code_content.append(line)
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^(-{3,}|_{3,}|\*{3,})$', line.strip()):
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # Headings
        hm = re.match(r'^(#{1,6})\s+(.*)', line)
        if hm:
            level = len(hm.group(1))
            text = hm.group(2).strip()
            heading_type = f"heading_{min(level, 3)}"
            blocks.append({
                "type": heading_type,
                heading_type: {"rich_text": rich_text(text)}
            })
            i += 1
            continue

        # Table
        if re.match(r'^\|', line):
            table_lines = []
            while i < len(lines) and re.match(r'^\|', lines[i]):
                table_lines.append(lines[i])
                i += 1

            if len(table_lines) >= 2:
                header_cells = [c.strip() for c in table_lines[0].strip().strip('|').split('|')]
                data_lines = table_lines[2:] if len(table_lines) > 2 else []

                if header_cells:
                    num_cols = len(header_cells)
                    table_children = [
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [[{"type": "text", "text": {"content": h[:2000]}}] for h in header_cells]
                            }
                        }
                    ]
                    for dl in data_lines:
                        cells = [c.strip() for c in dl.strip().strip('|').split('|')]
                        # Normalize: pad short rows, truncate long rows
                        if len(cells) < num_cols:
                            cells = cells + [""] * (num_cols - len(cells))
                        elif len(cells) > num_cols:
                            cells = cells[:num_cols]
                        table_children.append({
                            "type": "table_row",
                            "table_row": {
                                "cells": [[{"type": "text", "text": {"content": c[:2000]}}] for c in cells]
                            }
                        })

                    # NOTE: children goes INSIDE the 'table' object for Notion table blocks
                    blocks.append({
                        "type": "table",
                        "table": {
                            "table_width": len(header_cells),
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": table_children,
                        }
                    })
            continue

        # Blockquote
        if line.startswith(">"):
            content = line[1:].strip()
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                content += " " + lines[i][1:].strip()
                i += 1
            blocks.append({
                "type": "quote",
                "quote": {"rich_text": rich_text(content)}
            })
            continue

        # Bullet list
        if re.match(r'^[-*+]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^[-*+]\s+', lines[i]):
                m = re.match(r'^[-*+]\s+(.*)', lines[i])
                items.append(m.group(1))
                i += 1
            for item in items:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rich_text(item)}
                })
            continue

        # Numbered list
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                m = re.match(r'^\d+\.\s+(.*)', lines[i])
                items.append(m.group(1))
                i += 1
            for item in items:
                blocks.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": rich_text(item)}
                })
            continue

        # Empty line
        if line.strip() == "":
            i += 1
            continue

        # Paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() != "" \
                and not lines[i].startswith("#") \
                and not lines[i].startswith("```") \
                and not re.match(r'^[-*+]\s', lines[i]) \
                and not re.match(r'^\d+\.\s', lines[i]) \
                and not re.match(r'^>', lines[i]) \
                and not re.match(r'^\|', lines[i]) \
                and not re.match(r'^(-{3,}|_{3,}|\*{3,})$', lines[i].strip()):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            text = " ".join(para_lines).strip()
            if text:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {"rich_text": rich_text(text)}
                })

    return blocks


async def main():
    client = AsyncClient(auth=NOTION_TOKEN)

    for filename, title in FILES:
        filepath = f"{BASE_DIR}/{filename}"
        print(f"\nProcessing: {filename} -> {title}")
        with open(filepath, "r", encoding="utf-8") as f:
            md = f.read()

        blocks = md_to_blocks(md)
        print(f"  Converted to {len(blocks)} blocks")

        try:
            # Create empty page first
            page = await client.pages.create(
                parent={"page_id": PARENT_PAGE_ID},
                properties={
                    "title": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    }
                },
                children=[]
            )
            page_id = page["id"]
            print(f"  Created page: {page_id}")
            await asyncio.sleep(1.2)

            # Append blocks in batches of 100
            for batch_start in range(0, len(blocks), 100):
                batch = blocks[batch_start:batch_start + 100]
                result = await client.blocks.children.append(page_id, children=batch)
                print(f"  Appended {len(batch)} blocks (batch {batch_start // 100 + 1})")
                await asyncio.sleep(1.2)

            notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            print(f"  DONE: {notion_url}")

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    print("\n\nAll done!")


if __name__ == "__main__":
    asyncio.run(main())
