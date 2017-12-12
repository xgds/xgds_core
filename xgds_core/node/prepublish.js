var pkg = require('../package.json');
var path = require('path');
var copydir = require('copy-dir');

var base = path.join(__dirname, '..');
var modules = path.join(base, 'node_modules');
var dist = path.join(base, 'dist');

Object.keys(pkg.dependencies).forEach(function (dep) {
    copydir.sync(path.join(modules, dep), path.join(dist, dep));
});
