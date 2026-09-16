# 生图后端配置

封面图有两种来源：宿主 AI 工具自带的生图能力，或外部生图 API。
`scripts/gen_cover.py` 走后者，适配任何 OpenAI 兼容的 `/v1/images/generations` 接口。

不配置外部 API 也能用，只要宿主工具具备生图能力。

## 配置方式

在 `<SKILL_DIR>/.env` 里填（`.env` 已被 `.gitignore` 忽略）：

```bash
cp .env.example .env
```

```ini
IMAGE_API_BASE=https://api.agnes-ai.cn
IMAGE_API_KEY=sk-xxxx
IMAGE_MODEL=agnes-image-2.5-flash
```

优先级：命令行参数 > 系统环境变量 > `.env`。

也可以临时用环境变量：`export IMAGE_API_KEY='sk-xxxx'`（Windows 持久化用 `setx`）。

配好后生成封面：

```bash
cd "<本期目录>"
"<PYTHON_BIN>" "<SKILL_DIR>/scripts/gen_cover.py" \
  --prompt "<封面 prompt，参考 cover-prompt.md>" \
  --out images/cover.png
```

## Agnes（示例供应商）

官方文档：[定价](https://www.agnes-ai.cn/zh-Hans/docs/pricing) · [概述](https://www.agnes-ai.cn/zh-Hans/docs/overview)

- **Base URL**：`https://api.agnes-ai.cn/v1` —— OpenAI 风格兼容，`Authorization: Bearer <key>`
- 脚本传 `--base-url https://api.agnes-ai.cn`（根地址），脚本会自动拼 `/v1`
- **图片模型 ID**：

  | 模型 ID | 说明 |
  | --- | --- |
  | `agnes-image-2.5-flash` | 版本最高，优先使用 |
  | `agnes-image-2.1-flash` | 旧一版 |
  | `agnes-image-2.0-flash` | 最旧 |

  版本号越高越新。**价格与免费额度以[官网定价页](https://www.agnes-ai.cn/zh-Hans/docs/pricing)
  为准，这里不抄数字** —— 写死的价目表比代码过时得快。

- **`size` 收什么，以平台为准。** Agnes 实测像素值可用（`--size 1536x1024`，
  这也是脚本的默认值）；有的平台只收档位名（`1K` / `2K` / `3K` / `4K`）。
  返回 400 就换一种重试，脚本在 400 的报错里也会给这个提示。

## 接入其他平台的核对清单

1. 平台是否提供 `/v1/images/generations`？是则直接可用。
2. 响应返回 `data[0].url` 还是 `data[0].b64_json`？脚本两种都处理。
3. `size` 参数收像素值（`1536x1024`）还是档位名（`2K`）？不同平台不一致，试错一次即可确定。
4. **严禁把 key 写进 skill 文件、文章或任何会被提交的文件。**

## 画质说明

- 用外部 API 时优先选支持的最大分辨率，本地再缩到封面的 900×383。
- 宿主工具内置生图若有质量档位，选高档（medium 通常偏糊），但要注意额度消耗，
  出图前先告知用户。
