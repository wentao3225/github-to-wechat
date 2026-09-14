# 封面图 prompt 模板

目标尺寸 **900×383**（公众号头条封面 2.35:1）。

## 注意事项

**不要在封面里生成文字。** 生图模型画中文基本必出乱码，英文短词也常拼错。
正确做法：生成纯图形封面，标题文字在公众号后台叠加，或用 SVG / 图片工具后加。

**构图要给裁剪留余地。** `gen_cover.py` 会把出图居中裁剪到 2.35:1，上下边缘会被切掉
（一张 16:9 的图大约上下各切 12%）。主体放在**水平中线附近**，不要贴着上边缘或下边缘
摆重要元素，prompt 里写 `main subject vertically centered` 有帮助。

## prompt 结构

```
[主体] + [风格] + [配色] + [构图] + [负面约束]
```

示例：

> Flat vector illustration, a developer's desk seen from above: laptop, terminal
> window, coffee cup, scattered sticky notes. Minimal flat design, geometric shapes,
> no gradients. Palette: soft blue #3b82f6 and warm gray, off-white background.
> Wide composition, main subject vertically centered with breathing room on both sides.
> No text, no letters, no words, no watermark, no photorealism, no 3D render.

## 可调的风格方向

| 方向 | 关键词 |
| --- | --- |
| 扁平插画（默认） | flat vector illustration, minimal, geometric, solid colors |
| 等距 2.5D | isometric illustration, clean lines, soft shadow |
| 极简抽象 | abstract geometric composition, bold shapes, limited palette |
| 线稿 | line art, thin stroke, monoline, white background |

## 落盘

`gen_cover.py` 默认会自动居中裁剪到 900×383，不需要手工处理：

```bash
"<PYTHON_BIN>" "<SKILL_DIR>/scripts/gen_cover.py" \
  --prompt "<上面的 prompt>" --out "images/cover.png" --no-proxy
```

裁剪用的是居中裁切（不是拉伸），所以比例一定对，代价是上下边缘有损失 ——
这正是上面要求主体居中构图的原因。确需保留完整画面时加 `--fit ''`，
但那样封面比例不对，上传公众号时还得手动裁一次。

## 备选方案

生图质量不稳定时，直接用 SVG 画一个几何封面（项目名 + 大色块 + 简单图形），
转 PNG 后再上传。纯几何封面的点击率未必比 AI 图差。
