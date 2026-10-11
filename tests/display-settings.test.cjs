const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('assets/js/app.js', 'utf8').replace(/\ninit\(\);\s*$/, '');
const controls = Object.fromEntries(['[data-text-size]', '[data-motion]'].map(key => [key, { value: '', addEventListener(_, fn) { this.change = fn; } }]));
const status = { hidden: true, textContent: '' };
const dataset = {};
let blocked = false;
const records = new Map();
const context = vm.createContext({
  window: { location: { protocol: 'https:' }, localStorage: {
    getItem(key) { return records.get(key) ?? null; },
    setItem(key, value) { if (blocked) throw new Error('Quota exceeded'); records.set(key, value); },
  } },
  document: { documentElement: { dataset }, querySelector: key => key === '#display-save-status' ? status : controls[key] ?? null },
});
vm.runInContext(code, context);
vm.runInContext('initDisplaySettings()', context);
assert.equal(dataset.textSize, 'standard');
controls['[data-text-size]'].value = 'large';
controls['[data-text-size]'].change();
assert.equal(dataset.textSize, 'large');
assert.equal(JSON.parse(records.get('disfigurement-index-display-v1')).textSize, 'large');
blocked = true;
controls['[data-motion]'].value = 'reduce';
controls['[data-motion]'].change();
assert.equal(dataset.motion, 'reduce');
assert.match(status.textContent, /page only/);
assert.throws(() => vm.runInContext("writeLocalArray('records', [{ id: 'synthetic' }])", context), error => {
  assert.equal(error.code, 'STORAGE_UNAVAILABLE');
  context.caught = error;
  assert.equal(vm.runInContext('isBackendUnavailable(caught)', context), false);
  return true;
});
assert.equal(records.has('records'), false);
console.log('Display preferences and failed-save boundary passed.');
