# 封面图 prompt 模板

尺寸固定 **900×383**（公众号头条封面 2.35:1）。

## 关键坑

**不要在封面里生成文字。** 生图模型画中文基本必出乱码，英文短词也常拼错。
正确做法：生成纯图形封面，标题文字在公众号后台叠加，或用 SVG/图片工具后加。

## prompt 结构

```
[主体] + [风格] + [配色] + [构图] + [负面约束]
```

示例：

> Flat vector illustration, a developer's desk seen from above: laptop, terminal
> window, coffee cup, scattered sticky notes. Minimal flat design, geometric shapes,
> no gradients. Palette: soft blue #3b82f6 and warm gray, off-white background.
> Wide 2.35:1 composition, subject centered with breathing room on the left third.
> No text, no letters, no words, no watermark, no photorealism, no 3D render.

## 可调的风格方向

| 方向 | 关键词 |
| --- | --- |
| 扁平插画（默认） | flat vector illustration, minimal, geometric, solid colors |
| 等距 2.5D | isometric illustration, clean lines, soft shadow |
| 极简抽象 | abstract geometric composition, bold shapes, limited palette |
| 线稿 | line art, thin stroke, monoline, white background |

## 落盘

存为 `images/cover.png`，确保 900×383。如果模型出的是别的比例，裁剪而不是拉伸。

## 备选方案

生图质量不稳定时，直接用 SVG 画一个几何封面（项目名 + 大色块 + 简单图形），
转 PNG 后再上传。纯几何封面的点击率未必比 AI 图差。
