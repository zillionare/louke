'use strict';

const assert = require('assert');
const pkg = require('../package.json');

assert.strictEqual(typeof pkg.version, 'string', 'version must be a string');
assert.match(pkg.version, /^\d+\.\d+\.\d+$/, 'version must be SemVer');
console.log('ok');
