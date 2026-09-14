#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown -> WeChat-ready HTML, with every style inlined.

WeChat's editor strips <style> blocks and class attributes, so styles must sit
on the elements themselves. This converter writes them inline during rendering
rather than post-processing the HTML tree.

Standard library only — no pip install required.

Usage:
    python3 md2wechat.py input.md [-o output.html] [--theme "#3b82f6"] [--title "..."]
"""
import argparse
import html
import os
import re
import sys

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
    "h3": "font-size:16px;font-weight:bold;color:#2b2b2b;margin:26px 0 12px;line-height:1.4;",
    "h4": "font-size:15px;font-weight:bold;color:#3f3f3f;margin:22px 0 10px;line-height:1.4;",
    "p": "margin:16px 0;font-size:15px;line-height:1.75;color:#3f3f3f;",
    # paragraphs inside a blockquote read slightly smaller
    "p_in_quote": "margin:6px 0;font-size:14px;line-height:1.7;color:#6b6b6b;",
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

FENCE_RE = re.compile(r"^(```|~~~)\s*([^\s`]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
ITEM_RE = re.compile(r"^(\s*)([-+*]|\d+[.)])\s+(.*)$")
IMG_REF_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")


def esc(text):
    """Escape text content (quotes left alone, they are harmless in text nodes)."""
    return html.escape(text, quote=False)


def esc_attr(text):
    return html.escape(text, quote=True)


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_table_sep(line):
    if "|" not in line:
        return False
    cells = split_row(line)
    return bool(cells) and all(re.match(r"^:?-{2,}:?$", c) for c in cells)


class Renderer:
    def __init__(self, theme=DEFAULT_THEME):
        self.theme = theme

    # ---------------------------------------------------------------- inline

    def inline(self, text):
        """Render inline markup. Block-level callers pass raw markdown text."""
        stash = []

        def keep(snippet):
            stash.append(snippet)
            return "\x00%d\x00" % (len(stash) - 1)

        # Code spans first: their content must not be touched by later rules.
        text = re.sub(
            r"`([^`\n]+)`",
            lambda m: keep('<code style="%s">%s</code>' % (STYLES["code_inline"], esc(m.group(1)))),
            text,
        )

        # Images before links (the syntax differs only by the leading "!").
        text = re.sub(
            r"!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)",
            lambda m: keep(self._img(m.group(1), m.group(2))),
            text,
        )

        text = re.sub(
            r"\[([^\]]+)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)",
            lambda m: keep('<a href="%s" style="%s">%s</a>' % (
                esc_attr(m.group(2)), STYLES["a"], self.inline(m.group(1)))),
            text,
        )

        # Escape what is left, then apply emphasis to the escaped text.
        text = esc(text)
        text = re.sub(r"\*\*(.+?)\*\*", r'<strong style="%s">\1</strong>' % STYLES["strong"], text)
        text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r'<em style="%s">\1</em>' % STYLES["em"], text)
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

        # Single newline inside a paragraph becomes <br> (markdown "nl2br" behaviour).
        text = text.replace("\n", "<br>")

        for i, snippet in enumerate(stash):
            text = text.replace("\x00%d\x00" % i, snippet)
        return text

    def _img(self, alt, src):
        if not src.startswith(("http://", "https://", "data:")):
            src = "images/" + os.path.basename(src)
        return '<img src="%s" alt="%s" style="%s" data-ratio="">' % (
            esc_attr(src), esc_attr(alt), STYLES["img"])

    # ---------------------------------------------------------------- blocks

    def render(self, lines):
        out = []
        i, n = 0, len(lines)
        while i < n:
            s = lines[i].strip()

            if not s:
                i += 1
                continue

            m = FENCE_RE.match(s)
            if m:
                fence, buf = m.group(1), []
                i += 1
                while i < n and lines[i].strip() != fence:
                    buf.append(lines[i])
                    i += 1
                i += 1  # closing fence (or EOF)
                out.append('<pre style="%s"><code>%s</code></pre>' % (
                    STYLES["pre"], esc("\n".join(buf))))
                continue

            if HR_RE.match(s):
                out.append('<hr style="%s">' % STYLES["hr"])
                i += 1
                continue

            m = HEADING_RE.match(s)
            if m:
                level = len(m.group(1))
                if level <= 4:
                    tag = "h%d" % level
                    style = STYLES[tag]
                    if level == 2:
                        style += "border-left:4px solid %s;" % self.theme
                    out.append('<%s style="%s">%s</%s>' % (tag, style, self.inline(m.group(2)), tag))
                else:
                    out.append('<h4 style="%s">%s</h4>' % (STYLES["h4"], self.inline(m.group(2))))
                i += 1
                continue

            if i + 1 < n and "|" in s and is_table_sep(lines[i + 1]):
                head = split_row(lines[i])
                i += 2
                rows = []
                while i < n and "|" in lines[i] and lines[i].strip():
                    rows.append(split_row(lines[i]))
                    i += 1
                out.append(self._table(head, rows))
                continue

            if s.startswith(">"):
                buf = []
                while i < n and lines[i].strip().startswith(">"):
                    buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                    i += 1
                inner = self.render(buf).replace(
                    '<p style="%s">' % STYLES["p"], '<p style="%s">' % STYLES["p_in_quote"])
                out.append('<blockquote style="%s">%s</blockquote>' % (STYLES["blockquote"], inner))
                continue

            if ITEM_RE.match(lines[i]):
                entries = []
                while i < n:
                    mm = ITEM_RE.match(lines[i])
                    if mm:
                        indent = len(mm.group(1).replace("\t", "    "))
                        kind = "ol" if mm.group(2)[0].isdigit() else "ul"
                        entries.append((indent, kind, mm.group(3)))
                        i += 1
                    elif lines[i].strip() and entries and self._indent_of(lines[i]) > entries[-1][0]:
                        indent, kind, text = entries[-1]
                        entries[-1] = (indent, kind, text + " " + lines[i].strip())
                        i += 1
                    else:
                        break
                out.append(self._list(entries))
                continue

            # paragraph: consume until a blank line or the start of another block
            buf = []
            while i < n:
                cur = lines[i].strip()
                if not cur or FENCE_RE.match(cur) or HEADING_RE.match(cur) \
                        or HR_RE.match(cur) or cur.startswith(">") or ITEM_RE.match(lines[i]):
                    break
                buf.append(cur)
                i += 1
            out.append('<p style="%s">%s</p>' % (STYLES["p"], self.inline("\n".join(buf))))

        return "\n".join(out)

    @staticmethod
    def _indent_of(line):
        return len(line) - len(line.lstrip())

    def _list(self, entries):
        """Build nested <ul>/<ol> from (indent, kind, text) tuples."""
        out, stack = [], []  # stack entries: (indent, tag)
        for indent, kind, text in entries:
            tag = "ol" if kind == "ol" else "ul"
            while stack and indent < stack[-1][0]:
                out.append("</li></%s>" % stack.pop()[1])
            if not stack or indent > stack[-1][0]:
                # nested list stays inside the open <li>, so it indents correctly
                out.append('<%s style="%s">' % (tag, STYLES[tag]))
                stack.append((indent, tag))
                out.append('<li style="%s">%s' % (STYLES["li"], self.inline(text)))
            else:
                out.append("</li>")
                out.append('<li style="%s">%s' % (STYLES["li"], self.inline(text)))
        while stack:
            out.append("</li></%s>" % stack.pop()[1])
        return "".join(out)

    def _table(self, head, rows):
        parts = ['<table style="%s">' % STYLES["table"]]
        parts.append("<tr>" + "".join(
            '<th style="%s">%s</th>' % (STYLES["th"], self.inline(c)) for c in head) + "</tr>")
        for row in rows:
            parts.append("<tr>" + "".join(
                '<td style="%s">%s</td>' % (STYLES["td"], self.inline(c)) for c in row) + "</tr>")
        parts.append("</table>")
        return "".join(parts)


def strip_front_matter(text):
    """Drop a leading YAML front matter block, if present."""
    if text.startswith("---"):
        m = re.match(r"^---\n.*?\n---\n", text, re.S)
        if m:
            return text[m.end():]
    return text


def check_unused_images(md_path, text):
    """Body images sitting in images/ that the markdown never references.

    Generating a diagram but forgetting to write it into the article is an easy
    miss, and the reader just sees a wall of text. cover.png is excluded: covers
    are uploaded to WeChat separately and never inlined.
    """
    img_dir = os.path.join(os.path.dirname(os.path.abspath(md_path)), "images")
    if not os.path.isdir(img_dir):
        return []
    referenced = set(os.path.basename(m.group(1)) for m in IMG_REF_RE.finditer(text))
    unused = []
    for name in sorted(os.listdir(img_dir)):
        if not name.lower().endswith(".png") or name == "cover.png":
            continue
        if name not in referenced:
            unused.append(name)
    return unused


def check_missing_images(md_path, text):
    """Images the markdown references but that are not on disk."""
    base = os.path.dirname(os.path.abspath(md_path))
    missing = []
    for m in IMG_REF_RE.finditer(text):
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            continue
        if not os.path.exists(os.path.join(base, src)) \
                and not os.path.exists(os.path.join(base, "images", os.path.basename(src))):
            missing.append(src)
    return missing


def main():
    ap = argparse.ArgumentParser(description="Markdown -> WeChat HTML (inlined styles)")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--theme", default=DEFAULT_THEME)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = strip_front_matter(f.read())

    body = Renderer(args.theme).render(text.split("\n"))
    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    out_html = HTML_TPL.format(title=esc(title), section_style=STYLES["section"], body=body)

    out_path = args.output or os.path.splitext(args.input)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)

    print("OK -> %s  (%d chars)" % (out_path, len(out_html)))

    # Guards against the "generated diagrams nobody sees" failure mode.
    unused = check_unused_images(args.input, text)
    missing = check_missing_images(args.input, text)
    if unused:
        print("")
        print("WARN 以下正文图没有被引用，读者看不到它们：")
        for name in unused:
            print("       images/%s   -> 在稿子里加 ![说明](images/%s)" % (name, name))
        print("     用不上的图直接删掉，不要留在 images/ 里。")
    if missing:
        print("")
        print("WARN 以下图片被引用但文件不存在：")
        for src in missing:
            print("       %s" % src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
