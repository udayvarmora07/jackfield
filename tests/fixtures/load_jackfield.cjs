const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

module.exports = function loadJackfield(context, entry) {
  context.URLSearchParams ??= URLSearchParams;
  context.history ??= {
    state: null,
    replaceState(_state, _title, href) { context.location.hash = href; },
  };
  for (const file of ['state.js', 'router.js', 'palette.js', 'app.js']) {
    const source = path.join(path.dirname(entry), file);
    vm.runInContext(fs.readFileSync(source, 'utf8'), context, { filename: source });
  }
};
