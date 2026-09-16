#!/usr/bin/env node
/**
 * Shared `sharp` loader for svg2png.js and fitcover.js.
 *
 * sharp ships per-platform binaries that cannot live in the repository, so a
 * fresh clone has no sharp on disk. Both scripts therefore need the same three
 * steps: look in <SKILL_DIR>/node_modules, look where .env points, and if it is
 * still missing install it once. That logic used to be copy-pasted into both
 * files, where the install timeout had already drifted apart (300s vs 600s) —
 * one copy is one thing to keep correct.
 *
 * Lookup order, first hit wins:
 *   1. <SKILL_DIR>/node_modules — node resolves this by itself, the scripts
 *      live in <SKILL_DIR>/scripts
 *   2. NODE_MODULES from .env
 *   3. auto-install into <SKILL_DIR>/node_modules
 *
 * Step 3 is skipped when NO_AUTO_INSTALL=1, or when the caller passes
 * `{ allowInstall: false }`.
 */
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_DIR = path.join(__dirname, '..');
const INSTALL_TIMEOUT_MS = 600000;

function envValue(key) {
  try {
    const text = fs.readFileSync(path.join(SKILL_DIR, '.env'), 'utf8');
    const m = text.match(new RegExp('^\\s*' + key + '\\s*=\\s*(.+?)\\s*$', 'm'));
    return m ? m[1].replace(/^["']|["']$/g, '') : null;
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

// Returns an error string, or null on success.
// --prefer-offline: reuse the npm cache when it already has the packages, so a
// second machine or a re-clone does not hit the network at all.
function installSharp() {
  const target = path.join(SKILL_DIR, 'node_modules');
  console.log(`sharp not found, installing into ${target} (one time) ...`);
  const argv = ['install', '--no-audit', '--no-fund', '--prefer-offline'];
  const opts = { cwd: SKILL_DIR, stdio: 'inherit', timeout: INSTALL_TIMEOUT_MS };
  const npmCli = resolveNpm();
  const r = npmCli
    ? spawnSync(process.execPath, [npmCli, ...argv], opts)
    : spawnSync('npm', argv, Object.assign({}, opts, { shell: true }));
  if (r.error) return `npm could not be started (${r.error.message})`;
  if (r.status !== 0) return `npm install exited with code ${r.status}`;
  return null;
}

function withManualHint(reason) {
  return `${reason}\n手动安装：\n  cd ${SKILL_DIR}\n  npm install`;
}

/**
 * Load sharp, installing it once if needed.
 *
 * Throws with an actionable message when it cannot be loaded, so callers only
 * need to print `err.message` and exit non-zero.
 * Pass { allowInstall: false } to skip the install attempt.
 */
function loadSharp(options) {
  const allowInstall = !options || options.allowInstall !== false;

  const extra = envValue('NODE_MODULES');
  if (extra && !module.paths.includes(extra)) module.paths.push(extra);

  try {
    return require('sharp');
  } catch (e) {
    if (!allowInstall) {
      throw new Error(withManualHint(
        'sharp is not installed and auto-install is disabled (--no-install).'));
    }
    const err = installSharp();
    if (err) throw new Error(withManualHint(`Auto-install failed: ${err}`));
  }

  try {
    return require('sharp');
  } catch (e) {
    throw new Error(withManualHint(`sharp still cannot be loaded after install: ${e.message}`));
  }
}

module.exports = { loadSharp, SKILL_DIR, INSTALL_TIMEOUT_MS };
