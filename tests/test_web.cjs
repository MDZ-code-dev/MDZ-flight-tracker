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
  const pathFor=type=>vm.runInContext(`aircraftProfile({type:${JSON.stringify(type)}}).path`,context);
  for(const type of ['B731','B732','B733','B734','B735','B736','B737','B738','B739','B37M','B38M','B39M','B3XM']){
    context.plane={...base,type,description:'Bombardier Challenger 350',category:'A7'};
    vm.runInContext('renderNearest(plane,1)',context);
    assert.equal(elements.aircraftSilhouette.attributes.d,pathFor('B738'));
    assert.notEqual(elements.aircraftSilhouette.attributes.d,pathFor('CL35'));
    assert.ok(elements.typeLine.textContent.includes('Boeing 737'));
    assert.ok(!elements.typeLine.textContent.includes('Bombardier'));
    assert.equal(elements.description.textContent,type);
  }
  context.plane={...base,type:'CL35',description:'Boeing 737-800'};
  vm.runInContext('renderNearest(plane,1)',context);
  assert.equal(elements.aircraftSilhouette.attributes.d,pathFor('CL35'));
  assert.ok(elements.typeLine.textContent.includes('Challenger 350'));
  assert.ok(!elements.typeLine.textContent.includes('Boeing'));
  context.plane={...base,type:'UNMAPPED',callsign:'ROU1857',description:'---'};
  vm.runInContext('renderNearest(plane,1)',context);
  assert.equal(elements.aircraftSilhouette.attributes.d,pathFor('UNMAPPED'));
  assert.ok(!elements.typeLine.textContent.includes('Boeing'));
  vm.runInContext('renderNearest(null,0)', context);
  assert.equal(elements.aircraftSilhouette.attributes.d, '');
  assert.equal(elements.aircraftSilhouette.attributes.transform, undefined);
  // Out-of-order replies must never replace a newer aircraft with an older one.
  context.renderList=()=>{}; context.drawRadar=()=>{};
  const pending=[];
  context.mdzFetch=()=>new Promise(resolve=>pending.push(resolve));
  vm.runInContext('state.config={lat:43.65,lon:-79.38};',context);
  const oldRequest=vm.runInContext('refresh()',context),newRequest=vm.runInContext('refresh()',context);
  const newer={...base,type:'B738',hex:'new737',callsign:'BOEING'};
  const older={...base,type:'CL35',hex:'old350',callsign:'CHALLENGER'};
  pending[1]({json:async()=>({ok:true,nearest:newer,planes:[newer],total:1})});
  await newRequest;
  pending[0]({json:async()=>({ok:true,nearest:older,planes:[older],total:1})});
  await oldRequest;
  assert.equal(elements.callsign.textContent,'BOEING');
  assert.equal(elements.hex.textContent,'NEW737');
  assert.equal(elements.aircraftVisualType.textContent,'B738');
  assert.equal(elements.aircraftSilhouette.attributes.d,pathFor('B738'));
  context.mdzFetch=async()=>{throw new Error('Feed unavailable');};
  await vm.runInContext('refresh()',context);
  assert.equal(elements.aircraftVisualTitle.textContent,'LAST KNOWN AIRCRAFT');
  assert.ok(elements.aircraftVisual.classes.has('is-stale'));
  context.mdzFetch=async()=>({json:async()=>({ok:true,nearest:newer,planes:[newer],total:1})});
  await vm.runInContext('refresh()',context);
  assert.equal(elements.aircraftVisualTitle.textContent,'TRACKED AIRCRAFT');
  assert.ok(!elements.aircraftVisual.classes.has('is-stale'));
  // A location change also invalidates a reply from the previous location,
  // even when clearing coordinates prevents a new aircraft request.
  let oldLocationResponse;
  context.mdzFetch=path=>path==='/api/config' ? Promise.resolve({json:async()=>({ok:true,config:{lat:null,lon:null}})}) :
    new Promise(resolve=>{oldLocationResponse=resolve;});
  const oldLocation=vm.runInContext('refresh()',context);
  context.closeSettings=()=>{}; context.resetTimer=()=>{};
  await vm.runInContext('saveSettings()',context);
  oldLocationResponse({json:async()=>({ok:true,nearest:older,planes:[older],total:1,config:{lat:1,lon:1}})});
  await oldLocation;
  assert.equal(elements.aircraftSilhouette.attributes.d,'');
  assert.equal(vm.runInContext('state.config.lat',context),null);
  vm.runInContext('state.config={lat:43.65,lon:-79.38}',context);
  let settingsOpened=false;context.openSettings=()=>{settingsOpened=true;};
  context.mdzFetch=async()=>({json:async()=>({ok:false,needs_location:true,config:{lat:null,lon:null}})});
  await vm.runInContext('refresh()',context);
  assert.ok(settingsOpened);
  assert.equal(elements.aircraftSilhouette.attributes.d,'');
  assert.equal(vm.runInContext('state.config.lat',context),null);
  console.log('PASS: routing, distinct aircraft/model names, heading, identity consistency, stale replies and location changes');
})().catch(error => {console.error(error); process.exitCode = 1;});
