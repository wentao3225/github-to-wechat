# 生图后端配置

封面默认用 WorkBuddy 内置生图。要用 Agnes 或别的 OpenAI 兼容平台，按下面配。

## Agnes（供应商，已核实 2026-09-10）

官方文档：定价 https://www.agnes-ai.cn/zh-Hans/docs/pricing · 概述 https://www.agnes-ai.cn/zh-Hans/docs/overview

- **Base URL**：`https://api.agnes-ai.cn/v1`（脚本里 `--base-url` 传根地址 `https://api.agnes-ai.cn`，脚本自动拼 `/v1`）
- **OpenAI 风格兼容**，认证 `Authorization: Bearer <key>`，脚本已按这个写
- **图片模型 ID**（定价页原文，三档都同价）：

  | 模型 ID | 刊例价（1K / 2K / 3K / 4K，每千张） | 现价 |
  | --- | --- | --- |
  | `agnes-image-2.5-flash` | ¥70 / ¥120 / ¥140 / ¥160 | **¥0** |
  | `agnes-image-2.1-flash` | 同上 | **¥0** |
  | `agnes-image-2.0-flash` | 同上 | **¥0** |

  **当前全部免费**（含输入参考图）。所以优先用 Agnes，省内置的生图额度。
  推荐 `agnes-image-2.5-flash`（版本号最高）。

- **✅ 已实测打通（2026-09-10，key 配好后首跑成功）**：
  - `POST /v1/images/generations` + `size: "1536x1024"`（像素值）**直接成功**，没踩视频那个档位名的坑
  - 出图质量好，prompt 还原度高，477KB / 1080×750 左右
  - 若哪天报 400，再怀疑档位名（`--size 2K`），脚本会打印提示

- 注意区分：`~/.workbuddy/skills/agnes-video` 那个 skill 只做**视频**，跟生图无关。

## 配置方法

**首选：改 skill 根目录下的 `.env`**（最省事，不用碰系统设置，不用重启 WorkBuddy）

首次使用从模板复制（模板已提交到 git，`.env` 本身被 .gitignore 忽略）：

```bash
cp .env.example .env      # Windows CMD: copy .env.example .env
# 然后编辑 .env，把 IMAGE_API_KEY 的 sk-xxxx 换成真 key
```

优先级：命令行参数 > 系统环境变量 > `.env`。

<skill> = `C:\Users\25626\.workbuddy\skills\github-to-wechat`

备选（想全局生效再用）：
```bash
# Git Bash 临时，关掉 shell 失效
export IMAGE_API_KEY='sk-xxxx'
export IMAGE_MODEL='agnes-image-2.5-flash'

# Windows 永久，需重启 WorkBuddy 才读得到
setx IMAGE_API_KEY "sk-xxxx"
setx IMAGE_MODEL "agnes-image-2.5-flash"
```

配好后生成封面：

```bash
"C:/Users/25626/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  "<skill>/scripts/gen_cover.py" \
  --prompt "<封面 prompt，参考 cover-prompt.md>" \
  --out images/cover.png --no-proxy
```

`--no-proxy` 是给本地代理（Clash 等）没开的情况用的，和 agnes-video 一样的坑。
若 400，追加 `--size 2K`。

## 接入新平台的核对清单

1. 平台是否有 `/v1/images/generations`（OpenAI images API 兼容）？有就直接用脚本。
2. 响应回 `data[0].url` 还是 `data[0].b64_json`？脚本两种都处理了。
3. `size` 参数格式：像素值（`1536x1024`）还是档位名（`2K`）？Agnes 是后者。
4. **严禁把 key 写进 skill 文件、文章或 topics.md。**

## 画质备注（踩过的坑）

- 内置 ImageGen 的 `quality` 默认 medium，出的图偏糊。要清晰封面用 `quality: "high"`（费额度，**出图前必须先告知用户消耗**）。
- 外部 API 优先挑支持的最大分辨率，本地再缩到封面 900×383。
