// Shield fixture: minimal Node entry for acme-widget
'use strict';

const pkg = require('./package.json');

module.exports = {
  version: pkg.version,
  name: pkg.name,
};
