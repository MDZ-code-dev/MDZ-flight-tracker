const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('web/app.js', 'utf8');
const bridge = fs.readFileSync('web/native.js', 'utf8');
const elements = {};
const context = {
  document: {getElementById(id) {return elements[id] ??= {textContent: ''};}},
  window: {}, setTimeout, clearTimeout,
  fetch: async (path, options) => ({json: async () => ({path, options})})
};
vm.createContext(context);
vm.runInContext(bridge, context);
vm.runInContext(source.slice(0, source.indexOf("$('modeBtn').addEventListener")), context);
(async () => {
  const desktop = await vm.runInContext("mdzFetch('/api/config')", context);
  assert.equal((await desktop.json()).path, '/api/config');
  context.window.MDZAndroid = {request(id, path, method, body) {
    assert.equal(path, '/api/config'); assert.equal(method, 'POST');
    assert.equal(JSON.parse(body).lat, 43);
    context.window.MDZNativeResult(id, {ok: true, config: {lat: 43}});
  }};
  const native = await vm.runInContext("mdzFetch('/api/config',{method:'POST',body:'{\"lat\":43}'})", context);
  assert.equal((await native.json()).config.lat, 43);
  const base = {callsign:'TEST',hex:'abc123',distance_nm:1,bearing:90,bearing_direction:'E',track:null};
  for (const [fields, expected] of [
    [{type:'B747',description:'---'}, 'B747'],
    [{type:'B738',description:'BOEING 737-800'}, 'B738'],
    [{type:'---',description:'BOEING 747'}, 'BOEING 747'],
    [{type:'',description:null}, 'UNKNOWN']
  ]) {
    context.plane = {...base, ...fields};
    vm.runInContext('renderNearest(plane,1)', context);
    assert.equal(elements.description.textContent, expected);
  }
  vm.runInContext('renderNearest(null,0)', context);
  assert.equal(elements.description.textContent, '---');
  console.log('PASS: desktop HTTP routing, Android bridge save/callback, nearest aircraft rendering');
})().catch(error => {console.error(error); process.exitCode = 1;});
