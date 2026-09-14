# github-to-wechat

把一个 GitHub 仓库地址变成一篇可以直接发到微信公众号的文章。

六步流程：抓仓库真实数据 → 定选题角度（人工确认）→ 生成配图 → 写初稿 →
可选地去 AI 味 → 产出可一键复制的 HTML 和图片文件夹。

以 skill 形式提供，完整流程规范见 [`SKILL.md`](SKILL.md)。

## 特点

- **Python 侧零依赖** —— `md2wechat.py` 只用标准库，不需要 `pip install`
- **无需配置即可运行** —— 所有配置项都有默认值，按需覆盖
- **不写死绝对路径** —— 路径通过占位符 + 会话/环境解析，换机器不用改代码

## 环境要求

- Python 3.8+
- Node.js 20.9+（仅用于 SVG → PNG，版本下限由 `sharp` 决定）

## 安装

```bash
git clone https://github.com/wentao3225/github-to-wechat.git ~/.claude/skills/github-to-wechat
```

一行搞定，没有后续步骤。把路径末段换成你的 skill 目录即可
（`~/.claude/skills/`、`~/.workbuddy/skills/` 等，以你的工具文档为准）。

> **装在用户级，不要装项目级** —— 部分工具的斜杠命令只从用户级加载，
> 装项目级会导致命令找不到。

### 依赖怎么解决

`sharp` 是唯一的第三方依赖，用于 SVG → PNG 转换。它的跨平台二进制无法随仓库分发，
所以设计为**首次运行 `svg2png.js` 时自动安装**：装进 `<SKILL_DIR>/node_modules`，
装完继续执行本次转换，全程不需要手动操作。

想提前装好（比如离线环境）：

```bash
cd ~/.claude/skills/github-to-wechat && npm install
```

想关掉自动安装：给 `svg2png.js` 加 `--no-install`，或设环境变量 `NO_AUTO_INSTALL=1`。

## 配置（全部可选）

不配置也能直接跑，默认值面向开箱即用。需要调整时：

```bash
cp .env.example .env
```

| 变量 | 默认值 | 什么时候需要配 |
| --- | --- | --- |
| `IMAGE_API_KEY` | 空（用宿主工具生图） | 想走外部生图 API 时 |
| `IMAGE_MODEL` | `agnes-image-2.5-flash` | 想换图片模型时 |
| `PYTHON_BIN` | `python3` | Python 不在 PATH 时 |
| `NODE_BIN` | `node` | Node 不在 PATH 时 |
| `NODE_MODULES` | `<SKILL_DIR>/node_modules` | `sharp` 装在别处时 |
| `WECHAT_ARTICLES_DIR` | 当前工作区下的 `articles/` | 想固定输出目录时 |
| `HUMANIZER_SKILL` | 空（跳过去 AI 味步骤） | 需要去 AI 味时 |

`.env` 已被 `.gitignore` 忽略，不会提交。

## 用法

```
/github-to-wechat https://github.com/owner/repo   # 斜杠命令带链接
/github-to-wechat                                  # 不带参数，会追问
```

自然语言也可以：「给这个仓库写篇公众号文章」。

## 依赖说明

| 脚本 | 依赖 |
| --- | --- |
| `md2wechat.py` | 无（纯标准库） |
| `svg2png.js` | `sharp`（缺失时自动安装） |
| `gen_cover.py` | 无（纯标准库，可选组件） |

`svg2png.js` 按这个顺序找 `sharp`：`<SKILL_DIR>/node_modules` → `.env` 中的
`NODE_MODULES`。两处都没有就自动执行 `npm install`，装到 `<SKILL_DIR>/node_modules`。
命令行不需要设置 `NODE_PATH`。

## 文章输出到哪

三级优先，前者覆盖后者：

1. 会话里指定的路径
2. `.env` 中的 `WECHAT_ARTICLES_DIR`
3. 当前工作区下的 `articles/`

默认值是「当前工作区」而非固定目录，这样在任何工作区调用都能正常工作。

## 目录结构

```
github-to-wechat/
├── SKILL.md                    六步流程主文件（skill 入口）
├── README.md
├── .env.example                配置模板
├── .gitignore
├── package.json                声明 sharp 依赖，供自动安装使用
├── package-lock.json           锁定依赖版本
├── references/
│   ├── style-guide.md          文风、结构模板、禁用清单
│   ├── svg-template.md         SVG 示意图骨架（字号间距已调好）
│   ├── cover-prompt.md         封面 prompt 模板
│   └── image-backends.md       生图后端配置与接入清单
└── scripts/
    ├── md2wechat.py            Markdown → 微信 HTML（零依赖，含图片引用校验）
    ├── svg2png.js              SVG → PNG，字号过小时告警
    ├── fitcover.js             居中裁剪 PNG 到指定尺寸（封面用）
    └── gen_cover.py            文生图，OpenAI 兼容接口，出图后自动裁剪封面
```

## 产出物

```
<输出目录>/2026-09-10-<repo-name>/
├── draft.md       初稿（改写之前）
├── final.md       定稿（存档）
├── final.html     发布用，浏览器打开 → 全选 → 粘贴进公众号编辑器
└── images/
    ├── cover.png  封面 900×383
    └── *.png      正文图 1080px 宽
```

## 四条硬性规则

改动流程时注意不要破坏：

1. **SVG 必须转 PNG。** 公众号正文图片只接受 jpg / png / gif。
2. **先去 AI 味，再套 HTML。** 顺序颠倒会把 inline style 当正文改写，样式被破坏。
3. **选题必须人工确认。** 自动挑选的选题缺少信息增量。
4. **正文图必须被引用。** 生成 `images/` 里的图却没写进文章，读者只会看到纯文字。
   `md2wechat.py` 出稿时会列出未被引用的图。

## 已知约束

- **图片需要手动上传。** 个人订阅号没有素材管理接口权限（需微信认证），
  只能从 `images/` 目录手动上传。
- **SVG 字号不要低于 16px。** viewBox 宽 680 时正文至少 20px，标题 22–26px。
  从 `references/svg-template.md` 抄骨架最省事 —— 那份模板的间距已经调好。
  `svg2png.js` 会告警但不阻断，看到告警要回去改。
- **封面会被自动裁剪。** 生图模型很少按 2.35:1 出图，`gen_cover.py` 出图后
  居中裁剪到 900×383，上下边缘会被切掉，所以主体要摆在水平中线附近。
- **封面不要生成文字。** 生图模型渲染中文容易出现乱码，标题在后台叠加更可靠。
- **`<text>` 的 `y` 是基线不是中心。** 垂直居中需要手动计算：
  `y = 块y + 块高/2 + 字号×0.35`。librsvg 对 `dominant-baseline` 支持不稳定。
- **正文图必须写进稿子。** 生成了图却不引用，读者看到的还是纯文字。
  `md2wechat.py` 会在出稿时列出未被引用的图。
- **不要编造博主本人的经历。** 具体场景只能写成通用痛点，不能写成「上周我帮同事……」。
  详见 `references/style-guide.md` 的「经历红线」。

## 设计说明

**为什么路径用占位符？** skill 会被分发到不同机器，写死 `/home/xxx/...` 对别人没有意义，
也会泄露本机信息。因此 `SKILL.md` 中使用 `<SKILL_DIR>`、`<PYTHON_BIN>` 这类占位符，
运行时按「会话指定 → `.env` → 默认值」解析。

**为什么 Python 侧零依赖？** `md2wechat.py` 需要在生成标签时直接写入 inline style，
自行渲染 Markdown 即可完成，不需要额外的 Markdown 库和 HTML 解析库，
省掉一整步依赖安装。代价是需要自己维护渲染逻辑（约 250 行）。

**为什么 `sharp` 改成自动安装？** 它的跨平台二进制无法随仓库提交 —— 提交进去会让
仓库膨胀几十 MB，而且对异构平台（Linux / macOS）完全没用。让用户手动跑一条
`npm install` 又是明显的流失点，所以把安装藏进首次运行：检测到缺失就装，装完继续。
