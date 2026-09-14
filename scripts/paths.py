#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve runtime paths for github-to-wechat.

Where articles go
-----------------
<cwd>/articles — the `articles/` folder of whatever workspace the caller is
standing in. One rule, no configuration, nothing to keep in sync: open the
right workspace, get the right output.

This used to be configurable (.env / environment variable / CLI flag). That
version had a real failure mode: the setting was documented as a priority
chain, but no script ever read it, so a configured directory was silently
ignored and articles landed somewhere else while every script reported
success. A single hard rule is harder to get wrong than four levels of
precedence. So the knob is gone.

This script still exists because the caller must not hand-build paths: it
prints absolute paths and creates the issue folder, date and repo slug
included. It also resolves the runtime binaries, which *are* configurable via
<SKILL_DIR>/.env — but only when python/node are not on PATH.

Usage:
    python paths.py show                       # every path, with where it came from
    python paths.py articles                   # just the articles dir
    python paths.py issue CmdDo                # <cwd>/articles/2026-09-14-CmdDo (creates it)
    python paths.py issue owner/CmdDo --json    # machine-readable
    python paths.py issue CmdDo --date 2026-09-20
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


def articles_dir():
    """<cwd>/articles. Where you stand decides — by design, not by accident."""
    return os.path.join(os.getcwd(), "articles")


def resolve(var, dotenv, default):
    """Return (value, source). .env is the only override for runtime binaries."""
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


def collect():
    dotenv = load_dotenv(ENV_PATH)
    python_bin, python_src = resolve("PYTHON_BIN", dotenv, sys.executable)
    node_bin, node_src = resolve(
        "NODE_BIN", dotenv, shutil.which("node") or "node")
    node_modules, nm_src = resolve(
        "NODE_MODULES", dotenv, os.path.join(SKILL_DIR, "node_modules"))
    humanizer, hum_src = resolve("HUMANIZER_SKILL", dotenv, "")
    return {
        "skill_dir": SKILL_DIR,
        "cwd": as_posix(os.getcwd()),
        "env_path": ENV_PATH,
        "env_exists": os.path.exists(ENV_PATH),
        "articles_dir": as_posix(articles_dir()),
        "articles_dir_source": "cwd",
        "python_bin": python_bin if python_bin == "python3" else as_posix(python_bin),
        "python_bin_source": python_src,
        "node_bin": node_bin if os.path.sep not in node_bin else as_posix(node_bin),
        "node_bin_source": node_src,
        "node_modules": as_posix(node_modules),
        "node_modules_source": nm_src,
        "humanizer_skill": as_posix(humanizer) if humanizer else "",
        "humanizer_skill_source": hum_src,
    }


def cmd_show(args):
    info = collect()
    rows = [
        ("SKILL_DIR", info["skill_dir"], "-"),
        ("CWD", info["cwd"], "-"),
        ("ARTICLES_DIR", info["articles_dir"], "<cwd>/articles"),
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
        print("")
        print("NOTE ARTICLES_DIR 固定为「当前工作区/articles」，不可配置。")
        print("     产物落在 CWD 下 —— 开工前确认上方的 CWD 就是你要写入的工作区。")
    return 0


def cmd_articles(args):
    print(collect()["articles_dir"])
    return 0


def cmd_issue(args):
    info = collect()
    date = args.date or datetime.date.today().isoformat()
    slug = slugify_repo(args.repo)
    issue = as_posix(os.path.join(info["articles_dir"], "%s-%s" % (date, slug)))

    created = False
    if not args.no_create:
        os.makedirs(issue, exist_ok=True)
        created = True

    if args.json:
        print(json.dumps({
            "cwd": info["cwd"],
            "articles_dir": info["articles_dir"],
            "issue_dir": issue,
            "created": created,
            "topics_file": info["articles_dir"] + "/topics.md",
        }, ensure_ascii=False, indent=2))
    else:
        print(issue)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="Resolve github-to-wechat runtime paths "
                    "(articles land in <cwd>/articles — not configurable).")

    sub = ap.add_subparsers(dest="command")

    sp = sub.add_parser("show", help="print every resolved path and its source")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("articles", help="print the articles dir")
    sp.set_defaults(func=cmd_articles)

    sp = sub.add_parser("issue", help="print (and create) this issue's folder")
    sp.add_argument("repo", help="repo name, or owner/repo")
    sp.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    sp.add_argument("--no-create", action="store_true", help="print only, do not mkdir")
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
