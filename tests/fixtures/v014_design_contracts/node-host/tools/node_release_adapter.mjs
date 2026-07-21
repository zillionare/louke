#!/usr/bin/env node
// Shield fixture: Node release adapter for v0.14-002 NFR-0300.
// Mirrors the contract defined in
// design-artifacts/validation/release-version-node-host.valid.candidate.json
// Commands:
//   inspect-source  -> print JSON {version: <package.json version>}
//   prepare --tag <tag> -> write package.json with prepared version
const fs = require('fs');
const path = require('path');

function readPkg() {
  const p = path.join(process.cwd(), 'package.json');
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function writePkg(pkg) {
  const p = path.join(process.cwd(), 'package.json');
  fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + '\n');
}

const [cmd, ...rest] = process.argv.slice(2);

if (cmd === 'inspect-source') {
  const pkg = readPkg();
  if (!pkg.version || !/^\d+\.\d+\.\d+$/.test(pkg.version)) {
    console.error(JSON.stringify({ok: false, error: 'invalid version'}));
    process.exit(1);
  }
  console.log(JSON.stringify({ok: true, version: pkg.version}));
} else if (cmd === 'prepare') {
  const tagIdx = rest.indexOf('--tag');
  if (tagIdx < 0 || tagIdx === rest.length - 1) {
    console.error(JSON.stringify({ok: false, error: 'missing --tag'}));
    process.exit(1);
  }
  const tag = rest[tagIdx + 1];
  const m = /^widget-v(\d+\.\d+\.\d+)$/.exec(tag);
  if (!m) {
    console.error(JSON.stringify({ok: false, error: 'invalid tag'}));
    process.exit(1);
  }
  const pkg = readPkg();
  pkg.version = m[1];
  writePkg(pkg);
  const crypto = require('crypto');
  const digest = crypto.createHash('sha256').update(JSON.stringify(pkg)).digest('hex');
  console.log(JSON.stringify({ok: true, version: m[1], digest}));
} else {
  console.error(JSON.stringify({ok: false, error: 'unknown command'}));
  process.exit(1);
}
