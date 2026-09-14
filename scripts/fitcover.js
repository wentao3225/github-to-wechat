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
 * Needs `sharp`; auto-installs into <SKILL_DIR>/node_modules on first use,
 * same as svg2png.js. Set NO_AUTO_INSTALL=1 to disable.
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_DIR = path.join(__dirname, '..');

function envValue(key) {
  try {
    const text = fs.readFileSync(path.join(SKILL_DIR, '.env'), 'utf8');
    const m = text.match(new RegExp('^\\s*' + key + '\\s*=\\s*(.+?)\\s*$', 'm'));
    return m ? m[1].replace(/^["']|["']$/g, '') : null;
  } catch (e) {
    return null;
  }
}

function loadSharp() {
  const extra = envValue('NODE_MODULES');
  if (extra) module.paths.push(extra);
  try {
    return require('sharp');
  } catch (e) {
    // not installed yet, fall through
  }
  if (process.env.NO_AUTO_INSTALL === '1') {
    throw new Error('sharp not installed, and auto-install is disabled (NO_AUTO_INSTALL=1)');
  }
  console.log('sharp not found, installing into ' + path.join(SKILL_DIR, 'node_modules') + ' (one time) ...');
  const npmCli = path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');
  const npmArgs = ['install', '--no-audit', '--no-fund', '--prefer-offline'];
  const opts = { cwd: SKILL_DIR, stdio: 'inherit', timeout: 600000 };
  const r = fs.existsSync(npmCli)
    ? spawnSync(process.execPath, [npmCli].concat(npmArgs), opts)
    : spawnSync('npm', npmArgs, Object.assign({}, opts, { shell: true }));
  if (r.error) throw new Error('npm could not be started (' + r.error.message + ')');
  if (r.status !== 0) throw new Error('npm install exited with code ' + r.status);
  return require('sharp');
}

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
