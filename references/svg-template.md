# SVG 示意图模板

直接复制改内容。字号和间距已经按 1080px 输出调好，**不要改小**。

## 为什么需要模板

手机上看公众号，正文图显示宽度约 375px。SVG 画布宽 680，缩到手机上大约只剩
0.55 倍 —— 也就是说 SVG 里的 20px 字，到了手机上只有约 11px。

低于 16px 的字（手机上不到 9px）就接近一团模糊了。示意图宁可少画几项、
多分一张图，也不要缩字号去塞内容。

## 骨架：左右对比

最常见的类型，其他布局（流程图、架构图、时间线）从这个改。

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 300">
  <rect width="680" height="300" fill="#f8fafc"/>

  <!-- 大标题 26px，y 是基线，不是中心 -->
  <text x="340" y="44" text-anchor="middle" fill="#0f172a"
        font-size="26" font-weight="bold">标题文字</text>

  <!-- 左卡片：圆角矩形 -->
  <rect x="30" y="72" width="290" height="200" rx="12"
        fill="#ffffff" stroke="#cbd5e1"/>
  <text x="175" y="106" text-anchor="middle" fill="#475569"
        font-size="22" font-weight="bold">左侧标题</text>

  <!-- 条目：小圆点 + 文字，行距按 40 递增 -->
  <circle cx="62" cy="146" r="5" fill="#94a3b8"/>
  <text x="80" y="152" fill="#334155" font-size="20">第一条内容</text>

  <circle cx="62" cy="186" r="5" fill="#94a3b8"/>
  <text x="80" y="192" fill="#334155" font-size="20">第二条内容</text>

  <circle cx="62" cy="226" r="5" fill="#94a3b8"/>
  <text x="80" y="232" fill="#334155" font-size="20">第三条内容</text>

  <!-- 右卡片：用主题色描边表示“改进后” -->
  <rect x="360" y="72" width="290" height="200" rx="12"
        fill="#ffffff" stroke="#3b82f6" stroke-width="2"/>
  <text x="505" y="106" text-anchor="middle" fill="#1d4ed8"
        font-size="22" font-weight="bold">右侧标题</text>

  <circle cx="392" cy="146" r="5" fill="#3b82f6"/>
  <text x="410" y="152" fill="#334155" font-size="20">第一条内容</text>

  <circle cx="392" cy="186" r="5" fill="#3b82f6"/>
  <text x="410" y="192" fill="#334155" font-size="20">第二条内容</text>

  <circle cx="392" cy="226" r="5" fill="#3b82f6"/>
  <text x="410" y="232" fill="#334155" font-size="20">第三条内容</text>
</svg>
```

## 字号速查

| 用途 | 字号 | 备注 |
| --- | --- | --- |
| 大标题 | 26px | 一张图最多一个 |
| 卡片标题 / 小标题 | 22px | 加 `font-weight="bold"` |
| 正文条目 | 20px | 默认尺寸 |
| 图注 / 次要说明 | 18px | 用 `#64748b` 一类浅色 |
| 代码路径（等宽） | 18px | 加 `font-family="Menlo,Consolas,monospace"` |
| **红线** | **≥16px** | 低于这个值 `svg2png.js` 会告警 |

## 间距参考

- 画布宽固定 **680**，高按内容定（300 / 350 / 420 都常见）
- 外边距：左右 **30–40**，顶部到标题基线 **44**，标题到内容 **28–30**
- 卡片内边距：左右 **30**，顶部到卡片标题基线 **34**
- 条目行距：**40**（20px 字配 40 行距，视觉最舒服）
- 标题与首条内容的间距：**40**

## 配色

与公众号正文主题一致（主题色 `#3b82f6`）：

| 角色 | 色值 |
| --- | --- |
| 画布底色 | `#f8fafc` |
| 卡片底 / 描边 | `#ffffff` / `#e2e8f0`（强调时 `#3b82f6`） |
| 大标题 | `#0f172a` |
| 卡片标题 | `#475569`（强调时 `#1d4ed8`） |
| 正文 | `#334155` |
| 次要说明 | `#64748b` |

## 四个必查项

1. **所有文字 ≥16px。** 转换时 `svg2png.js` 会报出具体是哪一个字号、渲染后多少像素。
   `font-size="N"` 与 CSS `font-size:Npx` 两种写法都查；相对单位（em / rem / %）不查，写 px。
2. **`rect` / `text` 都要显式写 `fill`。** 不能依赖 CSS class —— librsvg 会把没写 fill 的元素渲染成黑色。
3. **`<text>` 的 `y` 是基线。** 垂直居中要塞进高 `h` 的块时用
   `y = 块y + h/2 + 字号×0.35`（20px 字号即 +7）。别用 `dominant-baseline`，
   librsvg 支持不稳定。
4. **不要用 emoji 承载语义。** 实测能渲染，但依赖系统字体，换台机器可能变成方块或彩色差异。
   用文字标签或几何图形代替。

## 内容太密时

按这个顺序处理，不要缩字号：

1. 删掉次要条目（一张图讲清一件事就够）
2. 拆成两张图
3. 把长的条目改写得更短
