#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve runtime paths for github-to-wechat — the single source of truth.

Why this file exists
--------------------
The output directory used to be documented as "the articles/ folder under the
current workspace". For a human reading docs that is fine; for an agent it is
useless, because every caller resolves "current workspace" from its own cwd.
A run started from the home directory silently wrote to ~/articles instead of
the folder configured in .env — the article landed in the wrong place while
every script reported success.

Docs are advisory. Scripts are not. So every path decision goes through this
file, which reads <SKILL_DIR>/.env by absolute path and prints an absolute
result. No cwd, no guessing, nothing left to drift.

Resolution order, first hit wins:
    1. CLI flag           --articles-dir
    2. environment var    WECHAT_ARTICLES_DIR
    3. <SKILL_DIR>/.env   WECHAT_ARTICLES_DIR
    4. built-in default   ~/articles

The default is deliberately a fixed location rather than "wherever you happen
to be standing", so that two runs from two different cwds agree.

Usage:
    python paths.py show                       # every path, with where it came from
    python paths.py articles                   # just the articles dir
    python paths.py issue CmdDo                # <ARTICLES_DIR>/2026-09-14-CmdDo (creates it)
    python paths.py issue owner/CmdDo --json    # machine-readable
    python paths.py issue CmdDo --date 2026-09-20
    python paths.py issue CmdDo --articles-dir "D:/somewhere/articles"
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(SKILL_DIR, ".env")


def load_dotenv(path):
    """Minimal .env reader: KEY=VALUE per line, # comments and blanks ignored."""
    if not os.path.exists(path):
        return {}
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def default_articles_dir():
    """A fixed location, not cwd-relative — that is the whole point."""
    return os.path.join(os.path.expanduser("~"), "articles")


def resolve(var, cli_value, dotenv, default):
    """Return (value, source)."""
    if cli_value:
        return cli_value, "cli"
    if os.environ.get(var):
        return os.environ[var], "env"
    if dotenv.get(var):
        return dotenv[var], ".env"
    return default, "default"


def as_posix(path):
    """Normalise separators so the value works in bash, PowerShell and Python."""
    if not path:
        return path
    return os.path.abspath(os.path.expanduser(path)).replace("\\", "/")


def slugify_repo(repo):
    """owner/CmdDo -> CmdDo, tidy the leftovers for use in a folder name."""
    name = repo.strip().strip("/").split("/")[-1]
    name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", name)
    return name.strip("-") or "repo"


def collect(args):
    dotenv = load_dotenv(ENV_PATH)
    articles, articles_src = resolve(
        "WECHAT_ARTICLES_DIR",
        getattr(args, "articles_dir", None),
        dotenv,
        default_articles_dir(),
    )
    python_bin, python_src = resolve(
        "PYTHON_BIN", getattr(args, "python_bin", None), dotenv, sys.executable)
    node_bin, node_src = resolve(
        "NODE_BIN", getattr(args, "node_bin", None), dotenv, shutil.which("node") or "node")
    node_modules, nm_src = resolve(
        "NODE_MODULES", None, dotenv, os.path.join(SKILL_DIR, "node_modules"))
    humanizer, hum_src = resolve(
        "HUMANIZER_SKILL", None, dotenv, "")
    return {
        "skill_dir": SKILL_DIR,
        "env_path": ENV_PATH,
        "env_exists": os.path.exists(ENV_PATH),
        "articles_dir": as_posix(articles),
        "articles_dir_source": articles_src,
        "python_bin": as_posix(python_bin) if python_bin != "python3" else python_bin,
        "python_bin_source": python_src,
        "node_bin": as_posix(node_bin) if os.path.sep in node_bin else node_bin,
        "node_bin_source": node_src,
        "node_modules": as_posix(node_modules),
        "node_modules_source": nm_src,
        "humanizer_skill": as_posix(humanizer) if humanizer else "",
        "humanizer_skill_source": hum_src,
    }


def cmd_show(args):
    info = collect(args)
    rows = [
        ("SKILL_DIR", info["skill_dir"], "-"),
        ("ARTICLES_DIR", info["articles_dir"], info["articles_dir_source"]),
        ("PYTHON_BIN", info["python_bin"], info["python_bin_source"]),
        ("NODE_BIN", info["node_bin"], info["node_bin_source"]),
        ("NODE_MODULES", info["node_modules"], info["node_modules_source"]),
        ("HUMANIZER_SKILL", info["humanizer_skill"] or "(not set, step 5 skipped)",
         info["humanizer_skill_source"]),
    ]
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(".env: %s%s" % (info["env_path"],
                              "" if info["env_exists"] else "   <- NOT FOUND"))
        width = max(len(k) for k, _, _ in rows)
        for name, value, source in rows:
            print("%-*s = %s   [%s]" % (width, name, value, source))
        if info["articles_dir_source"] == "default":
            print("")
            print("NOTE ARTICLES_DIR 用的是默认值。想固定输出位置，"
                  "在 %s 里写一行：" % info["env_path"])
            print("     WECHAT_ARTICLES_DIR=<你想要的绝对路径>")
    return 0


def cmd_articles(args):
    info = collect(args)
    print(info["articles_dir"])
    return 0


def cmd_issue(args):
    info = collect(args)
    date = args.date or datetime.date.today().isoformat()
    slug = slugify_repo(args.repo)
    issue = os.path.join(info["articles_dir"], "%s-%s" % (date, slug)).replace("\\", "/")
    issue = as_posix(issue)

    created = False
    if not args.no_create:
        os.makedirs(issue, exist_ok=True)
        created = True

    if args.json:
        print(json.dumps({
            "articles_dir": info["articles_dir"],
            "articles_dir_source": info["articles_dir_source"],
            "issue_dir": issue,
            "created": created,
            "topics_file": info["articles_dir"] + "/topics.md",
        }, ensure_ascii=False, indent=2))
    else:
        print(issue)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="Resolve github-to-wechat runtime paths (absolute, cwd-independent).")
    # shared so they work before or after the subcommand
    for p in (ap,):
        p.add_argument("--articles-dir", default=None,
                       help="override WECHAT_ARTICLES_DIR")
        p.add_argument("--python-bin", default=None, help="override PYTHON_BIN")
        p.add_argument("--node-bin", default=None, help="override NODE_BIN")
        p.add_argument("--json", action="store_true", help="machine-readable output")

    sub = ap.add_subparsers(dest="command")

    sp = sub.add_parser("show", help="print every resolved path and its source")
    sp.add_argument("--articles-dir", default=None)
    sp.add_argument("--python-bin", default=None)
    sp.add_argument("--node-bin", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("articles", help="print the articles dir")
    sp.add_argument("--articles-dir", default=None)
    sp.add_argument("--python-bin", default=None)
    sp.add_argument("--node-bin", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_articles)

    sp = sub.add_parser("issue", help="print (and create) this issue's folder")
    sp.add_argument("repo", help="repo name, or owner/repo")
    sp.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    sp.add_argument("--no-create", action="store_true", help="print only, do not mkdir")
    sp.add_argument("--articles-dir", default=None)
    sp.add_argument("--python-bin", default=None)
    sp.add_argument("--node-bin", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_issue)

    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    if not getattr(args, "func", None):
        args = ap.parse_args(["show"] + sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
