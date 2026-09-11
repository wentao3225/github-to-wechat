#!/usr/bin/env node
/**
 * SVG -> PNG converter for WeChat articles.
 * WeChat does NOT accept SVG uploads, every SVG must become a PNG first.
 *
 * Usage:
 *   node svg2png.js <file.svg|dir> [width] [density]
 *
 * Defaults: width=1080, density=288
 * 1080 not 750: WeChat recompresses uploads, so starting larger keeps text crisp.
 * density=288 = 4x oversampling of a 680-wide viewBox, smooths text edges.
 *
 * Requires `sharp`, resolved via the script's own location:
 *   cd <SKILL_DIR> && npm install sharp
 * No NODE_PATH needed — Node resolves modules relative to this script,
 * so <SKILL_DIR>/node_modules/sharp is found automatically.
 */
const fs = require('fs');
const path = require('path');

// Locate sharp. Two ways, and no NODE_PATH needed on the command line:
//   1. <SKILL_DIR>/node_modules  — default, from `npm install sharp`
//   2. NODE_MODULES in .env      — when sharp lives somewhere else
const envNodeModules = (() => {
  try {
    const text = fs.readFileSync(path.join(__dirname, '..', '.env'), 'utf8');
    const m = text.match(/^\s*NODE_MODULES\s*=\s*(.+?)\s*$/m);
    return m ? m[1].replace(/^["']|["']$/g, '') : null;
  } catch (e) {
    return null;
  }
})();
if (envNodeModules) module.paths.push(envNodeModules);

const sharp = require('sharp');

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error('usage: node svg2png.js <file.svg|dir> [width=1080] [density=288]');
  process.exit(1);
}

const input = path.resolve(args[0]);
const width = parseInt(args[1] || '1080', 10);
const density = parseInt(args[2] || '288', 10);

const MIN_FONT_SIZE = 14;

function checkFontSizes(file) {
  const svg = fs.readFileSync(file, 'utf8');
  const sizes = [...svg.matchAll(/font-size="([\d.]+)"/g)].map((m) => parseFloat(m[1]));
  const tooSmall = [...new Set(sizes.filter((s) => s < MIN_FONT_SIZE))].sort((a, b) => a - b);
  if (tooSmall.length) {
    console.log(
      `WARN ${path.basename(file)}: font-size ${tooSmall.join(', ')}px < ${MIN_FONT_SIZE}px. ` +
      `at viewBox 680 this renders ~${Math.round(tooSmall[0] * 1080 / 680)}px on a 1080-wide PNG, unreadable on a phone. body text should be 20px+.`
    );
    return false;
  }
  return true;
}

async function convert(file) {
  const out = file.replace(/\.svg$/i, '.png');
  checkFontSizes(file);
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
  for (const f of files) {
    if (await convert(f)) ok++;
  }
  console.log(`\n${ok}/${files.length} converted at width=${width}px`);
  process.exit(ok === files.length ? 0 : 1);
})();
