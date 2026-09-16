#!/usr/bin/env node
/**
 * SVG -> PNG converter for WeChat articles.
 * WeChat does NOT accept SVG uploads, every SVG must become a PNG first.
 *
 * Usage:
 *   node svg2png.js <file.svg|dir> [width] [density] [--no-install]
 *
 * Defaults: width=1080, density=288
 * 1080 not 750: WeChat recompresses uploads, so starting larger keeps text crisp.
 * density=288 = 4x oversampling of a 680-wide viewBox, smooths text edges.
 *
 * Dependency: `sharp`. If it is missing this script installs it once into
 * <SKILL_DIR>/node_modules and continues, so a fresh clone works with no manual
 * step. Pass --no-install (or set NO_AUTO_INSTALL=1) to skip that and print the
 * manual command instead. Lookup and install live in scripts/sharp-loader.js,
 * shared with fitcover.js so the two cannot drift apart.
 */
const fs = require('fs');
const path = require('path');
const { loadSharp } = require('./sharp-loader');

const rawArgs = process.argv.slice(2);
const noInstall = rawArgs.includes('--no-install') || process.env.NO_AUTO_INSTALL === '1';
const args = rawArgs.filter((a) => !a.startsWith('--'));

let sharp;
try {
  sharp = loadSharp({ allowInstall: !noInstall });
} catch (e) {
  console.error(e.message);
  process.exit(1);
}

if (args.length < 1) {
  console.error('usage: node svg2png.js <file.svg|dir> [width=1080] [density=288] [--no-install]');
  process.exit(1);
}

const input = path.resolve(args[0]);
const width = parseInt(args[1] || '1080', 10);
const density = parseInt(args[2] || '288', 10);

// Must match the red line documented in references/svg-template.md.
// At viewBox width 680, one SVG unit maps to ~1.59px on the 1080px PNG, and the
// phone then scales it back down — below 16px the text stops being readable.
const MIN_FONT_SIZE = 16;

// Both spellings count: the presentation attribute `font-size="14"` and the CSS
// declaration `font-size:14px` (an inline style= or a <style> block). Matching
// only the attribute form let CSS-styled text slip past the check unnoticed.
// Relative units (em / rem / %) are not resolved — write px in diagrams.
const FONT_SIZE_RE = /font-size\s*(?:=\s*["']?([\d.]+)|:\s*([\d.]+)\s*px)/g;

function checkFontSizes(file) {
  const svg = fs.readFileSync(file, 'utf8');
  const sizes = [...svg.matchAll(FONT_SIZE_RE)]
    .map((m) => parseFloat(m[1] !== undefined ? m[1] : m[2]))
    .filter((n) => !Number.isNaN(n));
  const tooSmall = [...new Set(sizes.filter((s) => s < MIN_FONT_SIZE))].sort((a, b) => a - b);
  if (tooSmall.length) {
    console.log(
      `WARN ${path.basename(file)}: 字号 ${tooSmall.join(', ')}px 低于 ${MIN_FONT_SIZE}px 下限，手机上读不清。` +
      ` 正文用 20px、图注 18px、标题 22-26px；内容装不下就删条目或拆成两张图，不要缩字号。` +
      ` 骨架见 references/svg-template.md。`
    );
    return false;
  }
  return true;
}

async function convert(file) {
  const out = file.replace(/\.svg$/i, '.png');
  try {
    const info = await sharp(file, { density })
      .resize({ width, withoutEnlargement: false })
      .png({ compressionLevel: 9 })
      .toFile(out);
    console.log(`OK   ${path.basename(file)} -> ${path.basename(out)}  (${info.width}x${info.height})`);
    return true;
  } catch (e) {
    console.error(`FAIL ${path.basename(file)}: ${e.message}`);
    return false;
  }
}

(async () => {
  const stat = fs.statSync(input);
  let files = [];
  if (stat.isDirectory()) {
    files = fs.readdirSync(input)
      .filter((f) => f.toLowerCase().endsWith('.svg'))
      .map((f) => path.join(input, f));
  } else {
    files = [input];
  }

  if (files.length === 0) {
    console.error('no .svg found');
    process.exit(1);
  }

  let ok = 0;
  let warned = 0;
  for (const f of files) {
    if (!checkFontSizes(f)) warned++;
    if (await convert(f)) ok++;
  }
  console.log(`\n${ok}/${files.length} converted at width=${width}px`);
  if (warned) {
    console.log(`WARN ${warned} 张图的字号低于 ${MIN_FONT_SIZE}px 下限，改完重新转换再出稿。`);
  }
  process.exit(ok === files.length ? 0 : 1);
})();
