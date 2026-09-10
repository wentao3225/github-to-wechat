# github-to-wechat

把一个 GitHub 仓库地址变成一篇可以直接发到微信公众号的文章。

抓仓库真实数据 → 定选题角度（人工确认）→ 生成配图 → 写初稿 → 去 AI 味 → 产出可一键复制的 HTML 和图片文件夹。

给 WorkBuddy / Claude Code 这类 AI 编码工具用的 skill（`SKILL.md` 里有完整的六步流程规范）。

---

## 快速开始

### 1. 安装

放到**用户级**技能目录：

```bash
git clone https://github.com/wentao3225/github-to-wechat.git \
  ~/.workbuddy/skills/github-to-wechat
```

> **必须放用户级，不能放项目级。** 项目级 `.workbuddy/skills/` 下的 skill 不会被 Skill 工具自动发现，`/github-to-wechat` 会报 not found（已实测）。

### 2. 装依赖

两个脚本需要外部库，缺一个都跑不了：

```bash
# Python：markdown + beautifulsoup4（md2wechat.py 用）
python -m venv ~/.workbuddy/binaries/python/envs/default
~/.workbuddy/binaries/python/envs/default/Scripts/pip install markdown beautifulsoup4

# Node：sharp（svg2png.js 用）
cd ~/.workbuddy/binaries/node/workspace && npm install sharp
```

### 3. 配置生图后端（可选）

封面默认用内置生图模型。想走 Agnes（当前免费）就配一下：

```bash
cp .env.example .env
# 编辑 .env，把 IMAGE_API_KEY 的 sk-xxxx 换成真 key
```

key 从 https://platform.agnes-ai.cn 控制台 → API Key 管理 获取。

> `.env` 含密钥，已被 `.gitignore` 忽略，不会提交。

### 4. 用

```
/github-to-wechat https://github.com/owner/repo   # 斜杠命令带链接
/github-to-wechat                                  # 不带参数，会追问
```

或者直接丢个链接说「写篇公众号」，自然语言也能触发。

---

## 换机器后必改的路径

`SKILL.md` 里硬编码了本机绝对路径，克隆到新环境后**必须全局替换**，否则脚本找不到运行时：

| 位置 | 内容 | 改成 |
| --- | --- | --- |
| `SKILL.md:18` / `:91` | skill 安装路径 | 你实际的 skill 目录 |
| `SKILL.md:32` | 文章产物目录 | 你想存文章的地方 |
| `SKILL.md:73` | humanizer 的 SKILL.md | 你本地 humanizer 的路径，没有就删掉第 5 步 |
| `SKILL.md:83-88` | python / node 可执行文件路径 | 你实际的运行时路径 |
| `references/image-backends.md:42,58` | 同上 | 同上 |
| `scripts/svg2png.js:14` | NODE_PATH 注释 | 你的 node_modules 位置 |

Windows 上可以用这条命令批量查哪些地方还留着旧路径：

```bash
grep -rn "25626" --include="*.md" --include="*.py" --include="*.js" .
```

---

## 目录结构

```
github-to-wechat/
├── SKILL.md                    六步流程主文件（skill 的入口）
├── README.md                   本文件
├── .env.example                生图后端配置模板
├── .gitignore
├── references/
│   ├── style-guide.md          人设、结构模板、禁用词、去 AI 味高频必查项
│   ├── cover-prompt.md         封面 prompt 模板
│   └── image-backends.md       生图后端（Agnes / 内置）配置与模型清单
└── scripts/
    ├── gen_cover.py            文生图，OpenAI 兼容 /v1/images/generations
    ├── svg2png.js              SVG → PNG，字号 <14px 会报警告
    └── md2wechat.py            Markdown → 全 inline style 的微信 HTML
```

## 产出物

```
<产物目录>/2026-09-10-<repo-name>/
├── draft.md       初稿（去 AI 味之前）
├── final.md       定稿（存档用）
├── final.html     发布用，浏览器打开 → 全选 → 粘贴进公众号编辑器
└── images/
    ├── cover.png  封面 900×383
    └── *.png      正文图 1080px 宽
```

---

## 三条硬规矩

这三条是踩过坑才定下来的，改流程时注意别破坏：

1. **SVG 必须转 PNG。** 公众号正文图片只收 jpg / png / gif，SVG 传不上去。
2. **先去 AI 味，再套 HTML。** 反过来 humanizer 会把 inline style 当正文一起改，样式会坏。顺序固定：Markdown 纯文本 → humanizer → HTML。
3. **选题必须人工确认。** AI 自己挑的选题往往没有信息增量，这一步留给人的判断。

## 已知约束

- **图片要手动上传。** 个人订阅号没有素材管理接口权限（需微信认证），只能从 `images/` 文件夹手动传。
- **SVG 字号别低于 16px。** viewBox 宽 680 时正文 20px 起、标题 22-26px。字号太小转出来手机上必糊，`svg2png.js` 会警告但不阻断。
- **封面不要生成文字。** 生图模型画中文基本必出乱码，标题在后台叠加。
- **`<text>` 的 y 是基线不是中心。** 要垂直居中得自己算：`y = 块y + 块高/2 + 字号×0.35`。librsvg 对 `dominant-baseline` 支持不稳。
