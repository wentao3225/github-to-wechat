---
name: github-to-wechat
description: |
  把一个 GitHub 仓库地址变成一篇可以直接发到微信公众号的文章：抓仓库信息、定选题角度、
  生成配图（封面用生图模型、正文示意图用 SVG 转 PNG）、写初稿、用 humanizer 去 AI 味，
  最后产出可一键复制的 HTML 和图片文件夹。
  触发词：这个仓库写一篇文章、发公众号、github 转公众号、写篇推文、成稿、出稿。
agent_created: true
---

# GitHub 仓库 → 公众号文章

## 调用方式

用户级 skill，装在这里：

```
C:\Users\25626\.workbuddy\skills\github-to-wechat
```

三种触发方式都行：

1. `/github-to-wechat https://github.com/owner/repo` —— 斜杠命令带 URL，最直接
2. `/github-to-wechat` 不带参数，我追问仓库地址
3. 直接丢链接说「写篇公众号」，自然语言也能触发

**为什么必须放用户级**：项目级 `.workbuddy/skills/` 下的 skill 不会被 Skill 工具自动发现，
`/github-to-wechat` 会报 not found（2026-09-10 实测）。要命令可用就只能放用户级。

## 产物目录

固定：`D:\桌面\Files\improve\GithubOfShare\articles`

跟 skill 存放位置无关，是这里写死的。本期目录为 `articles/YYYY-MM-DD-<repo-name>/`。
要临时输出到别处，在会话里直接说路径。

## 三条硬规矩（违反就白干）

1. **SVG 必须转 PNG。** 公众号正文图片只收 jpg / png / gif，SVG 传不上去。任何画完的 SVG 都要走 `svg2png.js`，没有例外。
2. **先去 AI 味，再套 HTML。** 顺序反过来，humanizer 会把 inline style 当正文一起改，样式会被改坏。流程固定为：Markdown 纯文本 → humanizer → HTML。
3. **选题必须人工确认。** 定角度后先给用户看，他点头再往下写。AI 自己挑的选题没有信息增量。

## 流程

### 1. 抓仓库信息
拿到 URL 后先取真实数据，禁止凭印象写：
- `gh repo view <owner/repo> --json name,description,stargazerCount,language,updatedAt,license,url`
- README 要点（用 WebFetch 抓 raw README，长的话只看前 200 行）
- 记下：star 数、语言、最近提交时间、许可证、一句话定位

抓不到就直说，不要编 star 数和数据。

### 2. 定选题角度
给用户 **3 个候选角度**让他选，每个角度一句话说清"读者看完能得到什么"。角度优先选：
- 解决一个具体的、国内开发者真会遇到的痛点
- 和某个主流方案的对比
- 一个反常识的用法或坑

避开「又一个 XX 工具」这种没有增量的角度。

### 3. 生成配图
- **封面**：生图模型，尺寸 900×383（2.35:1）。prompt 参考 `references/cover-prompt.md`。后端选择见 `references/image-backends.md`（默认内置生图，已配置 IMAGE_API_KEY 时走 `scripts/gen_cover.py`）。
- **正文示意图**：手写 SVG（架构图 / 流程图 / 对比表），存到 `images/`，再用 `svg2png.js` 转 PNG。
- **字号规范（血泪教训）**：SVG viewBox 宽 680 时，正文文字必须 20px 起、标题 22-26px、图注 18px、等宽路径 15px。低于 16px 转出来在手机上就是糊的。转 PNG 用 1080 宽 + density 288（脚本默认值），公众号会再压缩到 750 显示，等于超采样。
- 每篇 3～5 张图。SVG 里所有 `rect`/`text` 必须显式写 `fill`，不能依赖 CSS class。
- **文字垂直居中**：`<text>` 的 y 是基线不是中心。要放进高 h 的块里，y = 块y + h/2 + 4（20px 字号时 +7，15px 时 +5）。librsvg 对 `dominant-baseline` 支持不稳，直接算基线最可靠。

### 4. 写初稿
按 `references/style-guide.md` 的文风和结构模板写 Markdown，存为 `draft.md`。
引用 README 的功能描述时**必须改写成自己的话**，原样照抄等于洗稿。

### 5. 去 AI 味
读取 `C:\Users\25626\.agents\skills\humanizer\SKILL.md`，按它的 §1–§19 规则改写 `draft.md`，产出 `final.md`。
（这个 skill 装在 `~/.agents/` 而不是 WorkBuddy 的技能目录，跨生态不会被自动发现，所以直接按路径读文件。）

高频必查项：不是X而是Y / 一行式收尾段落 / 破折号滥用 / 三连排比 / `**标签：**` 加粗 / emoji 开头 / "赋能""助力""革命性"。

保留 `final.md` 和 `draft.md` 两份，方便对比 humanizer 改了什么。

### 6. 出稿
```bash
# SVG -> PNG（必须；默认 1080 宽 / density 288）
NODE_PATH="C:/Users/25626/.workbuddy/binaries/node/workspace/node_modules" \
  "C:/Users/25626/.workbuddy/binaries/node/versions/22.22.2-2/node.exe" \
  "<skill>/scripts/svg2png.js" "images"

# Markdown -> 微信 HTML
"C:/Users/25626/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  "<skill>/scripts/md2wechat.py" "final.md" --theme "#3b82f6" --title "<标题>"
```
`<skill>` = `C:\Users\25626\.workbuddy\skills\github-to-wechat`

产出：`final.md`（存档）、`final.html`（浏览器打开 → 全选 → 粘贴到公众号编辑器）、`images/*.png`（手动上传）。

最后把标题、摘要（≤54 字）、用到的仓库写进 `<产物目录>/topics.md` 记账，避免重复选题。

## 目录约定

```
<产物目录>/2026-09-10-awesome-xx/
├── draft.md        初稿（去味前）
├── final.md        定稿（去味后，存档用）
├── final.html      发布用，双击打开复制
└── images/
    ├── cover.png   封面 900x383
    ├── diagram.svg 源
    └── diagram.png 正文图 1080px
```
