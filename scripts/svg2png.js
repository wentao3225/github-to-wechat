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
 * manual command instead.
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_DIR = path.join(__dirname, '..');

const rawArgs = process.argv.slice(2);
const noInstall = rawArgs.includes('--no-install') || process.env.NO_AUTO_INSTALL === '1';
const args = rawArgs.filter((a) => !a.startsWith('--'));

// sharp lookup, two locations. Node already searches <SKILL_DIR>/node_modules
// because this script lives in <SKILL_DIR>/scripts, so the auto-install target
// needs no path juggling. A .env NODE_MODULES entry adds a second location for
// setups that keep node_modules outside the skill directory.
const envNodeModules = (() => {
  try {
    const text = fs.readFileSync(path.join(SKILL_DIR, '.env'), 'utf8');
    const m = text.match(/^\s*NODE_MODULES\s*=\s*(.+?)\s*$/m);
    return m ? m[1].replace(/^["']|["']$/g, '') : null;
  } catch (e) {
    return null;
  }
})();
if (envNodeModules) module.paths.push(envNodeModules);

function loadSharp() {
  try {
    return require('sharp');
  } catch (e) {
    return null;
  }
}

// npm is the `npm` shim next to node, which on Windows is a .cmd file that
// cannot be spawned without a shell. Prefer the JS entry point shipped inside
// the node installation: it runs under the current node binary, so no shell and
// no PATH lookup are involved. Fall back to PATH npm for nvm/volta style setups.
function resolveNpm() {
  const cli = path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');
  return fs.existsSync(cli) ? cli : null;
}

// Returns an error string on failure, null on success.
// --prefer-offline: reuse the npm cache when it already has the packages, so a
// second machine or a re-clone does not hit the network at all.
function installSharp() {
  const npmCli = resolveNpm();
  const argv = ['install', '--no-audit', '--no-fund', '--prefer-offline'];
  console.log(`sharp not found, installing into ${path.join(SKILL_DIR, 'node_modules')} (one time) ...`);
  const opts = { cwd: SKILL_DIR, stdio: 'inherit', timeout: 300000 };
  const r = npmCli
    ? spawnSync(process.execPath, [npmCli, ...argv], opts)
    : spawnSync('npm', argv, { ...opts, shell: true });
  if (r.error) return `npm could not be started (${r.error.message})`;
  if (r.status !== 0) return `npm install exited with code ${r.status}`;
  return null;
}

let sharp = loadSharp();
if (!sharp) {
  if (noInstall) {
    console.error('sharp is not installed and auto-install is disabled (--no-install).');
  } else {
    const err = installSharp();
    if (err) {
      console.error(`Auto-install failed: ${err}`);
    } else {
      sharp = loadSharp();
    }
  }
  if (!sharp) {
    console.error(
      `\nsharp could not be loaded. Install it manually:\n` +
      `  cd ${SKILL_DIR}\n` +
      `  npm install\n`
    );
    process.exit(1);
  }
}

if (args.length < 1) {
  console.error('usage: node svg2png.js <file.svg|dir> [width=1080] [density=288] [--no-install]');
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
