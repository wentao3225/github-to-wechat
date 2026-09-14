---
name: github-to-wechat
description: |
  把一个 GitHub 仓库地址变成一篇可以直接发到微信公众号的文章：抓仓库信息、定选题角度、
  生成配图（封面用生图模型、正文示意图用 SVG 转 PNG）、写初稿、可选地去 AI 味，
  最后产出可一键复制的 HTML 和图片文件夹。
  触发词：这个仓库写一篇文章、发公众号、github 转公众号、写篇推文、成稿、出稿。
agent_created: true
---

# GitHub 仓库 → 公众号文章

输入一个 GitHub 仓库地址，输出一篇可发布的微信公众号文章：HTML 稿 + 配图文件夹。

安装、配置、触发方式见 `README.md`，本文档只描述执行流程。

## 依赖

`paths.py`、`md2wechat.py` 与 `gen_cover.py` 只用 Python 标准库，无需安装。
`svg2png.js` 需要 `sharp`，已设计为首次运行时自动安装到 `<SKILL_DIR>/node_modules`，
装完继续本次转换，无需人工介入，也不用设置 `NODE_PATH`。
脚本报「找不到模块」时才需要排查依赖：加 `--no-install` 可跳过自动安装，
或按 `README.md` 手动执行一次 `npm install`。正常的字号告警不是依赖问题。

## 配置

下面所有 `<XXX>` 都是占位符，按此顺序取值，**前者优先**：

1. 用户在会话里明确指定的路径
2. `<SKILL_DIR>/.env` 里的同名变量（`.env` 不进 git，模板见 `.env.example`）
3. 下表的默认值

| 占位符 | .env 变量 | 默认值 | 什么时候才需要配 |
| --- | --- | --- | --- |
| `<SKILL_DIR>` | — | 本文件所在目录 | 不用配 |
| `<ARTICLES_DIR>` | `WECHAT_ARTICLES_DIR` | `~/articles` | 想固定输出目录时 |
| `<PYTHON_BIN>` | `PYTHON_BIN` | 当前解释器 | 运行时不在 PATH 时 |
| `<NODE_BIN>` | `NODE_BIN` | `node` | 运行时不在 PATH 时 |
| `<NODE_MODULES>` | `NODE_MODULES` | `<SKILL_DIR>/node_modules` | `sharp` 装在别处时 |
| `<HUMANIZER_SKILL>` | `HUMANIZER_SKILL` | 空（跳过第 5 步） | 需要去 AI 味时 |

默认值面向开箱即用。只在默认值不合用时才需要写 `.env`。

**路径类的值不要手工推导。** `scripts/paths.py` 会按同样的顺序（命令行参数 →
环境变量 → `<SKILL_DIR>/.env` → 默认值）解析并打印绝对路径。用它，不要自己拼。

> 运行时路径不要写死版本号。版本管理器升级后目录名会变（例如 node 的
> `22.22.2-2` → `22.22.2-3`），写死的路径会静默失效。只有默认值不可用时才配。

## 输出目录：只能问脚本，不要自己拼

**不要用「当前工作区」「当前目录」推导任何路径，也不要手工拼 `<ARTICLES_DIR>`。**
「当前工作区」对 skill 没有意义 —— skill 会被任意 agent 从任意 cwd 调起，
从家目录启动时同样的文章会落进 `~/articles`，而不是 `.env` 里配的目录，
而所有脚本仍然报成功。

开工第一件事，跑路径解析脚本（它按绝对路径读 `<SKILL_DIR>/.env`，与 cwd 无关）：

```bash
"<PYTHON_BIN>" "<SKILL_DIR>/scripts/paths.py" show      # 所有路径 + 各自来源
ISSUE="$("<PYTHON_BIN>" "<SKILL_DIR>/scripts/paths.py" issue <repo-name>)"
cd "$ISSUE"
```

`issue` 打印 `<ARTICLES_DIR>/YYYY-MM-DD-<repo-name>/` 的绝对路径并建好目录。
本期所有产出都落在这里，`$ISSUE` 就是它的绝对路径。

优先级脚本已经处理好了，**不要为此弹选择题打断流程**：

1. 用户本次指定了目录 → 传 `--articles-dir <路径>`
2. `.env` 配了 `WECHAT_ARTICLES_DIR` → 脚本自己会读，不必询问
3. 都没配 → 落到 `~/articles`，开工前一句话告知输出位置即可

想换输出位置就改 `.env` 的 `WECHAT_ARTICLES_DIR`，不要改这段流程。

## 五条硬性规则

1. **SVG 必须转 PNG。** 公众号正文图片只接受 jpg / png / gif，SVG 无法上传。
   任何生成的 SVG 都要经过 `svg2png.js`，没有例外。
2. **先去 AI 味，再套 HTML。** 顺序颠倒时，改写工具会把 inline style 当正文一起改，
   样式会被破坏。固定顺序：Markdown 纯文本 → 去 AI 味 → HTML。
3. **选题必须人工确认。** 给出候选角度后等用户确认再动笔。自动挑选的选题缺少信息增量。
4. **正文图必须被引用。** 生成了图却没写进稿子，文章就成了纯文字。
   引用要在**写稿时按语义放好**，这是正路。第 6 步 `md2wechat.py` 会兜底：
   发现没被引用的图，按间距补进 `final.md` 并报 `FIX`。
   看到 `FIX` 说明写稿时漏了 —— 回去把图挪到真正对应的段落后面，别留着默认位置。
5. **路径只来自 `paths.py`。** 不要用 cwd 推导 `<ARTICLES_DIR>`，不要手工拼本期目录。
   第 0 步跑 `paths.py issue <repo-name>`，用它打印出来的绝对路径。

## 流程

### 0. 解析输出目录

见上面「输出目录」。先跑 `paths.py issue <repo-name>` 拿到 `$ISSUE` 并 `cd` 进去，
后续每一步都在这个目录里执行。目录不需要手工 `mkdir`，脚本会建。

### 1. 抓仓库信息

拿到 URL 后先取真实数据，禁止凭印象编造：

- `gh repo view <owner/repo> --json name,description,stargazerCount,language,updatedAt,license,url`
- `gh` 不可用时走 GitHub API（`api.github.com/repos/<owner>/<repo>`）+ 抓取 raw README
- 记下：star 数、语言、最近提交时间、许可证、一句话定位

抓不到就如实说明，不要编造 star 数和数据。

### 2. 定选题角度

给用户 **3 个候选角度**，每个角度一句话说清「读者看完能得到什么」。优先选择：

- 解决一个具体的、国内开发者真会遇到的痛点
- 与某个主流方案的对比
- 一个反常识的用法或坑

避开「又一个 XX 工具」这类没有信息增量的角度。

### 3. 生成配图

- **封面**：`gen_cover.py` 生图，目标 900×383（2.35:1）。prompt 参考
  `references/cover-prompt.md`，后端选择见 `references/image-backends.md`。

  ```bash
  "<PYTHON_BIN>" "<SKILL_DIR>/scripts/gen_cover.py" \
    --prompt "<封面 prompt>" --out "images/cover.png" --no-proxy
  ```

  生图模型很少按你要的比例出图，所以脚本默认会**居中裁剪**到 900×383
  （`--fit`，默认 `900x383`，不要关掉）。裁剪会切掉上下边缘，
  写 prompt 时让主体集中在水平中线附近，别把重要元素放在最上/最下。

- **正文示意图**：手写 SVG（架构图 / 流程图 / 对比表），存入 `images/`，再用 `svg2png.js` 转 PNG。
  骨架直接抄 `references/svg-template.md` —— 那份模板的字号和间距已经调好，
  从空白开始画是上一次踩坑的原因。

- **字号是最容易翻车的一项**：viewBox 宽 680 时，正文 20px、卡片标题 22px、大标题 26px、
  图注 18px。**任何文字都不要低于 16px。** 宁可少写几个字、把画布画矮一点，
  也不要为了塞内容而缩字号 —— 低于 16px 在手机上不可读。
  转 PNG 用 1080 宽 + density 288（脚本默认值），公众号压缩到 750 显示，等于超采样。
  `svg2png.js` 会对 <16px 的字号发出警告，**看到警告就回去改，不要忽略继续出稿**。

- 每篇 3–5 张正文图（封面另算）。SVG 里所有 `rect` / `text` 必须显式写 `fill`，
  不能依赖 CSS class。
- **文字垂直居中**：`<text>` 的 `y` 是基线而非中心。要塞进高 `h` 的块中时取
  `y = 块y + h/2 + 4`（20px 字号用 +7，15px 用 +5）。librsvg 对 `dominant-baseline`
  支持不稳定，直接计算基线更可靠。

### 4. 写初稿

按 `references/style-guide.md` 的文风与结构模板写 Markdown，存为 `draft.md`。

**把正文图写进稿子里。** 每张正文图都要在合适位置用 `![一句说明](images/xxx.png)` 引用，
说明写清这张图在讲什么。`images/` 里有几张正文 PNG，稿子里就该有几处引用。
图生成了却没写进去，读者看到的就是一篇纯文字文章，前面那些图等于白做。
封面不进正文，单独上传。

顺序上先写文字、再决定每张图放在哪一段后面。先画图再找位置塞，通常塞得很生硬。

引用 README 的功能描述时**必须改写成自己的话**，原样照抄等同于洗稿。

### 5. 去 AI 味（可选）

**仅在配了 `<HUMANIZER_SKILL>` 时执行**：读取该文件，按其规则改写 `draft.md`，产出 `final.md`。
**未配置则跳过**，直接 `cp draft.md final.md` 继续。

`HUMANIZER_SKILL` 需要填绝对路径 —— 这类去 AI 味的 skill 通常装在别的目录树，
不会被工具自动发现。

高频检查项：`不是X而是Y` 结构 / 一行式收尾段落 / 破折号滥用 / 三连排比 /
`**标签：**` 式加粗 / emoji 开头 / 「赋能」「助力」「革命性」。

保留 `draft.md` 和 `final.md` 两份，便于对比改写差异。

### 6. 出稿

在第 0 步拿到的 `$ISSUE` 里执行：

```bash
cd "$ISSUE"

# SVG -> PNG（必须；默认 1080 宽 / density 288）
"<NODE_BIN>" "<SKILL_DIR>/scripts/svg2png.js" "images"

# Markdown -> 微信 HTML
"<PYTHON_BIN>" "<SKILL_DIR>/scripts/md2wechat.py" "final.md" \
  --theme "#3b82f6" --title "<标题>"
```

`md2wechat.py` 会把没被引用的正文图按间距补进 `final.md` 并报 `FIX`，因此
交付物不会退化成纯文字。看到 `FIX` 就去按硬性规则 4 把图挪到语义正确的段落后面，
再跑一次 —— 补进去的位置带 `<!-- 自动补图，位置可调 -->`，渲染 HTML 时会自动去掉，
在稿子里留着就是提醒你还没调。

不需要设置 `NODE_PATH`：Node 按脚本自身位置解析模块，
只要 `sharp` 在 `<SKILL_DIR>/node_modules` 就能找到（或由 `<NODE_MODULES>` 指定）；
两处都没有时脚本会自动装一次再继续，不需要人工介入。

产出：

- `final.md` —— 存档
- `final.html` —— 浏览器打开 → 全选 → 粘贴进公众号编辑器
- `images/*.png` —— 手动上传到公众号

最后把标题、摘要（≤54 字）、仓库名**追加**到 `<ARTICLES_DIR>/topics.md`（`$ISSUE` 的上一级）。
台账是追加不是覆盖 —— 已有行要保留，否则会丢掉历史选题记录。文件不存在才新建表头。

## 目录约定

```
<ARTICLES_DIR>/2026-09-10-awesome-xx/
├── draft.md        初稿（改写前）
├── final.md        定稿（改写后，存档）
├── final.html      发布用，浏览器打开复制
└── images/
    ├── cover.png   封面 900×383
    ├── diagram.svg SVG 源文件（便于修改）
    └── diagram.png 正文图 1080px
```

`<ARTICLES_DIR>` 和本期目录的绝对路径都由 `scripts/paths.py` 给出，不要手工拼。
