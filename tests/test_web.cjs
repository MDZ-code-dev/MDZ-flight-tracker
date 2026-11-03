const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('web/app.js', 'utf8');
const bridge = fs.readFileSync('web/native.js', 'utf8');
const silhouettes = fs.readFileSync('web/silhouettes.js', 'utf8');
const elements = {};
function element(id) {
  return elements[id] ??= {
    textContent: '', attributes: {}, classes: new Set(),
    setAttribute(name, value) {this.attributes[name] = value;},
    removeAttribute(name) {delete this.attributes[name];},
    classList: {toggle(name, force) {force ? elements[id].classes.add(name) : elements[id].classes.delete(name);}}
  };
}
const context = {
  document: {getElementById: element},
  window: {}, setTimeout, clearTimeout,
  fetch: async (path, options) => ({json: async () => ({path, options})})
};
vm.createContext(context);
vm.runInContext(bridge, context);
vm.runInContext(silhouettes, context);
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
  assert.equal(elements.aircraftSilhouette.attributes.d, '');
  assert.ok(elements.aircraftVisual.classes.has('is-empty'));
  context.plane = {...base, type:'B747', track:238};
  vm.runInContext('renderNearest(plane,1)', context);
  const jetPath = elements.aircraftSilhouette.attributes.d;
  assert.ok(jetPath.length > 20);
  assert.equal(elements.aircraftVisualType.textContent, 'B747');
  assert.equal(elements.aircraftSilhouette.attributes.transform, 'rotate(238 120 120)');
  assert.ok(!elements.aircraftVisual.classes.has('is-empty'));
  assert.equal(vm.runInContext("aircraftProfile({type:'B747'}).name",context),'FOUR-ENGINE JET');
  assert.equal(vm.runInContext("aircraftProfile({type:'AT76'}).name",context),'TWIN TURBOPROP');
  assert.equal(vm.runInContext("aircraftProfile({type:'C172'}).name",context),'LIGHT PROPELLER AIRCRAFT');
  assert.equal(vm.runInContext("aircraftProfile({type:'---',description:'BOEING 747-400'}).name",context),'FOUR-ENGINE JET');
  assert.equal(vm.runInContext("aircraftProfile({type:'UNMAPPED',description:'BOEING 747-400'}).name",context),'AIRCRAFT');
  context.plane = {...base, type:'B06', category:'A7'};
  vm.runInContext('renderNearest(plane,1)', context);
  assert.notEqual(elements.aircraftSilhouette.attributes.d, jetPath);
  assert.equal(elements.aircraftSilhouette.attributes.transform, 'rotate(0 120 120)');
  assert.ok(elements.aircraftVisualProfile.textContent.includes('HEADING UNKNOWN'));
  const helicopterPath = elements.aircraftSilhouette.attributes.d;
  context.plane = {...base, type:'UNMAPPED', description:'---', track:0};
  vm.runInContext('renderNearest(plane,1)', context);
  assert.notEqual(elements.aircraftSilhouette.attributes.d, helicopterPath);
  assert.ok(!elements.aircraftVisualProfile.textContent.includes('HEADING UNKNOWN'));
  assert.ok(elements.aircraftVisual.attributes['aria-label'].includes('heading 0 degrees'));
  vm.runInContext('renderNearest(null,0)', context);
  assert.equal(elements.aircraftSilhouette.attributes.d, '');
  assert.equal(elements.aircraftSilhouette.attributes.transform, undefined);
  console.log('PASS: HTTP/Android routing, aircraft rendering, silhouette changes, heading, unknown model and cleared contact');
})().catch(error => {console.error(error); process.exitCode = 1;});
