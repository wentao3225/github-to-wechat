#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown -> WeChat-ready HTML with fully inlined styles.

WeChat's editor strips <style> blocks and <class> attributes, so every style
must be inlined on the element itself. This script does that conversion.

Usage:
    python md2wechat.py input.md [-o output.html] [--theme #3b82f6] [--title "..."]
"""
import argparse
import os
import re
import sys

import markdown
from bs4 import BeautifulSoup

DEFAULT_THEME = "#3b82f6"

# Styles that survive WeChat's editor. No <style> blocks, no classes.
STYLES = {
    "section": (
        "font-size:15px;color:#3f3f3f;line-height:1.75;letter-spacing:0.5px;"
        "word-break:break-word;font-family:-apple-system,BlinkMacSystemFont,"
        "'PingFang SC','Helvetica Neue',Arial,sans-serif;"
    ),
    "h1": (
        "font-size:20px;font-weight:bold;color:#1a1a1a;margin:32px 0 16px;"
        "line-height:1.4;text-align:center;"
    ),
    "h2": (
        "font-size:18px;font-weight:bold;color:#1a1a1a;margin:32px 0 16px;"
        "line-height:1.4;padding-left:12px;"
    ),
    "h3": (
        "font-size:16px;font-weight:bold;color:#2b2b2b;margin:26px 0 12px;line-height:1.4;"
    ),
    "h4": "font-size:15px;font-weight:bold;color:#3f3f3f;margin:22px 0 10px;line-height:1.4;",
    "p": "margin:16px 0;font-size:15px;line-height:1.75;color:#3f3f3f;",
    "blockquote": (
        "margin:18px 0;padding:12px 16px;background:#f7f8fa;border-left:4px solid #dcdfe6;"
        "color:#6b6b6b;font-size:14px;line-height:1.7;border-radius:2px;"
    ),
    "pre": (
        "margin:18px 0;padding:16px;background:#282c34;color:#abb2bf;border-radius:6px;"
        "font-size:13px;line-height:1.65;overflow-x:auto;white-space:pre-wrap;"
        "word-break:break-all;font-family:Menlo,Consolas,'Courier New',monospace;"
    ),
    "code_inline": (
        "background:#f2f4f7;color:#c7254e;padding:2px 6px;border-radius:3px;"
        "font-size:13px;font-family:Menlo,Consolas,'Courier New',monospace;"
    ),
    "ul": "margin:16px 0;padding-left:22px;list-style-type:disc;",
    "ol": "margin:16px 0;padding-left:22px;list-style-type:decimal;",
    "li": "margin:8px 0;font-size:15px;line-height:1.75;color:#3f3f3f;",
    "img": "max-width:100%;height:auto;display:block;margin:20px auto;border-radius:6px;",
    "a": "color:#576b95;text-decoration:none;",
    "strong": "font-weight:bold;",
    "em": "font-style:italic;",
    "hr": "border:none;border-top:1px solid #e8e8e8;margin:28px 0;",
    "table": "width:100%;border-collapse:collapse;margin:18px 0;font-size:14px;",
    "th": "border:1px solid #e8e8e8;padding:8px 10px;background:#f7f8fa;font-weight:bold;text-align:left;",
    "td": "border:1px solid #e8e8e8;padding:8px 10px;",
}

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;padding:20px;background:#f5f5f5;">
<div style="max-width:677px;margin:0 auto;background:#ffffff;padding:24px 20px;border-radius:4px;">
<section style="{section_style}">
{body}
</section>
</div>
</body>
</html>
"""


def md_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "tables", "fenced_code", "sane_lists", "nl2br"],
        extension_configs={},
    )


def stylize(html: str, theme: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        tag["style"] = STYLES[tag.name] + (f"border-left:4px solid {theme};" if tag.name == "h2" else "")

    for tag in soup.find_all("p"):
        tag["style"] = STYLES["p"]

    for tag in soup.find_all("blockquote"):
        tag["style"] = STYLES["blockquote"]
        for p in tag.find_all("p"):
            p["style"] = "margin:6px 0;font-size:14px;line-height:1.7;color:#6b6b6b;"

    for tag in soup.find_all("pre"):
        tag["style"] = STYLES["pre"]

    for tag in soup.find_all("code"):
        # a <code> inside <pre> is a code block; standalone code is inline
        if tag.find_parent("pre") is None:
            tag["style"] = STYLES["code_inline"]

    for tag in soup.find_all(["ul", "ol"]):
        tag["style"] = STYLES[tag.name]
    for tag in soup.find_all("li"):
        tag["style"] = STYLES["li"]

    for tag in soup.find_all("img"):
        tag["style"] = STYLES["img"]
        tag["data-ratio"] = ""
        if not tag.get("src", "").startswith(("http://", "https://", "data:")):
            tag["src"] = "images/" + os.path.basename(tag.get("src", ""))

    for tag in soup.find_all("a"):
        tag["style"] = STYLES["a"]

    for tag in soup.find_all("strong"):
        tag["style"] = STYLES["strong"]
    for tag in soup.find_all("em"):
        tag["style"] = STYLES["em"]

    for tag in soup.find_all("hr"):
        tag["style"] = STYLES["hr"]

    for tag in soup.find_all("table"):
        tag["style"] = STYLES["table"]
    for tag in soup.find_all("th"):
        tag["style"] = STYLES["th"]
    for tag in soup.find_all("td"):
        tag["style"] = STYLES["td"]

    return str(soup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--theme", default=DEFAULT_THEME)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    # strip optional YAML front matter
    if text.startswith("---"):
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if m:
            text = text[m.end():]

    body = stylize(md_to_html(text), args.theme)

    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    out_html = HTML_TPL.format(title=title, section_style=STYLES["section"], body=body)

    out_path = args.output or os.path.splitext(args.input)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)

    print(f"OK -> {out_path}  ({len(out_html)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
