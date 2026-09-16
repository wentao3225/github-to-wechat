#!/usr/bin/env node
/**
 * Center-crop and resize a PNG to an exact size.
 *
 * Why this exists: image models rarely return the ratio you ask for. Generating
 * at whatever size the model prefers and cropping afterwards is far more
 * reliable than requesting an exact size in the prompt (or the `size` param).
 * WeChat's cover banner is 2.35:1 (900x383).
 *
 * Usage:
 *   node fitcover.js <file.png> [WxH]
 *
 * Default target is 900x383. Cropping is center-anchored (fit: cover), and the
 * file is overwritten in place — the original aspect is not preserved.
 *
 * Needs `sharp`; auto-installs into <SKILL_DIR>/node_modules on first use via
 * scripts/sharp-loader.js — the same code path svg2png.js uses, so the two can
 * not drift apart. Set NO_AUTO_INSTALL=1 to disable.
 */
const fs = require('fs');
const path = require('path');
const { loadSharp } = require('./sharp-loader');

const args = process.argv.slice(2);
if (!args.length) {
  console.error('usage: node fitcover.js <file.png> [WxH=900x383]');
  process.exit(1);
}

const file = args[0];
if (!fs.existsSync(file)) {
  console.error('file not found: ' + file);
  process.exit(1);
}

const spec = args[1] || '900x383';
const m = spec.match(/^(\d+)\s*x\s*(\d+)$/i);
if (!m) {
  console.error('bad size: ' + spec + ' (expected WxH, e.g. 900x383)');
  process.exit(1);
}
const width = parseInt(m[1], 10);
const height = parseInt(m[2], 10);

let sharp;
try {
  sharp = loadSharp();
} catch (e) {
  console.error('ERROR: ' + e.message);
  process.exit(1);
}

const tmp = file + '.fit.tmp.png';
sharp(file)
  .resize(width, height, { fit: 'cover', position: 'center' })
  .png({ compressionLevel: 9 })
  .toFile(tmp)
  .then(function (info) {
    fs.renameSync(tmp, file);
    console.log('OK   ' + path.basename(file) + ' -> ' + info.width + 'x' + info.height);
  })
  .catch(function (e) {
    try { fs.unlinkSync(tmp); } catch (_) {}
    console.error('FAIL ' + e.message);
    process.exit(1);
  });
