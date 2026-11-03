const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const context = vm.createContext({});
vm.runInContext(fs.readFileSync('web/silhouettes.js', 'utf8'), context);
function call(name, plane) {
  context.plane = plane;
  return vm.runInContext(`${name}(plane)`, context);
}

// Expected names and engine layouts, including ICAO codes whose marketed
// names differ substantially from the code. Each silhouette family appears.
const classifications = [
  ['B737', 'BOEING 737 FAMILY', 'Boeing 737-700'],
  ['B738', 'BOEING 737 FAMILY', 'Boeing 737-800'],
  ['B38M', 'BOEING 737 FAMILY', 'Boeing 737 MAX 8'],
  ['B3XM', 'BOEING 737 FAMILY', 'Boeing 737 MAX 10'],
  ['CL30', 'CHALLENGER 300/350 FAMILY', 'Bombardier Challenger 300'],
  ['CL35', 'CHALLENGER 300/350 FAMILY', 'Bombardier Challenger 350/3500'],
  ['CL60', 'REAR-ENGINE BUSINESS JET', 'Bombardier Challenger 600 series'],
  ['C25A', 'REAR-ENGINE BUSINESS JET', 'Cessna Citation CJ2'],
  ['C56X', 'REAR-ENGINE BUSINESS JET', 'Cessna Citation Excel/XLS'],
  ['GLF6', 'REAR-ENGINE BUSINESS JET', 'Gulfstream G650/G650ER'],
  ['CRJ7', 'REAR-ENGINE REGIONAL JET', 'Bombardier CRJ700'],
  ['CRJX', 'REAR-ENGINE REGIONAL JET', 'Bombardier CRJ1000'],
  ['E145', 'REAR-ENGINE REGIONAL JET', 'Embraer ERJ 145'],
  ['DC10', 'TRI-JET', 'McDonnell Douglas DC-10'],
  ['MD11', 'TRI-JET', 'McDonnell Douglas MD-11'],
  ['B722', 'REAR-ENGINE TRI-JET', 'Boeing 727-200'],
  ['FA50', 'REAR-ENGINE TRI-JET', 'Dassault Falcon 50'],
  ['F900', 'REAR-ENGINE TRI-JET', 'Dassault Falcon 900'],
  ['FA7X', 'REAR-ENGINE TRI-JET', 'Dassault Falcon 7X'],
  ['FA8X', 'REAR-ENGINE TRI-JET', 'Dassault Falcon 8X'],
  ['A320', 'TWIN-ENGINE JET', 'Airbus A320'],
  ['A20N', 'TWIN-ENGINE JET', 'Airbus A320neo'],
  ['A359', 'TWIN-ENGINE JET', 'Airbus A350-900'],
  ['BCS3', 'TWIN-ENGINE JET', 'Airbus A220-300'],
  ['B77L', 'TWIN-ENGINE JET', 'Boeing 777-200LR/F'],
  ['B789', 'TWIN-ENGINE JET', 'Boeing 787-9'],
  ['E75L', 'TWIN-ENGINE JET', 'Embraer E175'],
  ['E290', 'TWIN-ENGINE JET', 'Embraer E190-E2'],
  ['B744', 'FOUR-ENGINE JET', 'Boeing 747-400'],
  ['B74S', 'FOUR-ENGINE JET', 'Boeing 747SP'],
  ['A388', 'FOUR-ENGINE JET', 'Airbus A380-800'],
  ['AT72', 'TWIN TURBOPROP', 'ATR 72-100/200'],
  ['AT76', 'TWIN TURBOPROP', 'ATR 72-600'],
  ['DH8D', 'TWIN TURBOPROP', 'De Havilland Canada Dash 8-400'],
  ['B350', 'TWIN TURBOPROP', 'Beechcraft King Air 350'],
  ['C30J', 'FOUR-ENGINE TURBOPROP', 'Lockheed Martin C-130J Super Hercules'],
  ['P3', 'FOUR-ENGINE TURBOPROP', 'Lockheed P-3 Orion'],
  ['A400', 'FOUR-ENGINE TURBOPROP', 'Airbus A400M Atlas'],
  ['C172', 'LIGHT PROPELLER AIRCRAFT', 'Cessna 172 Skyhawk'],
  ['PC12', 'LIGHT PROPELLER AIRCRAFT', 'Pilatus PC-12'],
  ['P28R', 'LIGHT PROPELLER AIRCRAFT', 'Piper PA-28 Arrow'],
  ['B06', 'HELICOPTER', 'Bell 206 JetRanger/LongRanger'],
  ['EC35', 'HELICOPTER', 'Airbus H135/Eurocopter EC135'],
  ['H160', 'HELICOPTER', 'Airbus H160'],
  ['S92', 'HELICOPTER', 'Sikorsky S-92'],
  ['UNMAPPED', 'AIRCRAFT', '']
];
for (const [type, family, name] of classifications) {
  assert.equal(call('aircraftProfile', {type}).name, family, `${type} engine/layout family`);
  assert.equal(call('aircraftModelName', {type}), name, `${type} model name`);
}
assert.equal(call('aircraftModelName', {type: ' b738 '}), 'Boeing 737-800');

const pathFor = type => call('aircraftProfile', {type}).path;
for (const type of ['B731', 'B732', 'B733', 'B734', 'B735', 'B736', 'B737', 'B738', 'B739', 'B37M', 'B38M', 'B39M', 'B3XM']) {
  const plane = {type, description: 'Bombardier Challenger 350', category: 'A7'};
  assert.equal(call('aircraftProfile', plane).path, pathFor('B738'));
  assert.notEqual(call('aircraftProfile', plane).path, pathFor('CL35'));
  assert.match(call('aircraftModelName', plane), /^Boeing 737/);
}
assert.notEqual(pathFor('CRJ7'), pathFor('A320'), 'CRJs must not use underwing twinjet geometry');
assert.notEqual(pathFor('DC10'), pathFor('B722'), 'Trijet layouts have different engine positions');
assert.notEqual(pathFor('C130'), pathFor('AT76'), 'Four turboprops must differ from twin turboprops');
assert.equal(call('aircraftProfile', {type: 'CL35', description: 'Boeing 737-800'}).path, pathFor('CL35'));

// Neither callsigns nor registrations establish an airframe model. A real but
// unknown designator must also prevent a description from overriding it.
for (const plane of [
  {type: 'UNMAPPED', callsign: 'ROU1857', registration: 'C-TEST', description: 'Boeing 737-800'},
  {type: '', callsign: 'BOEING737', registration: 'B738', description: ''},
  {type: 'FA9X', callsign: 'FALCON900', description: 'Dassault Falcon 900'}
]) {
  assert.equal(call('aircraftModelName', plane), '');
  assert.equal(call('aircraftProfile', plane).name, 'AIRCRAFT');
}
assert.equal(call('aircraftModelName', null), '');
assert.equal(call('aircraftProfile', null).name, 'AIRCRAFT');
assert.equal(call('aircraftProfile', {type: '---', description: 'Boeing 737-800'}).name, 'BOEING 737 FAMILY');
assert.equal(call('aircraftModelName', {type: '', description: 'Boeing 737 MAX 8'}), 'Boeing 737 MAX 8');
assert.equal(call('aircraftProfile', {type: 'UNKNOWN', description: 'Bombardier Challenger 3500'}).name, 'CHALLENGER 300/350 FAMILY');

// Only an unambiguous disagreement warrants a warning. Family descriptions,
// aliases, generic engine/weight classifications and unknown types stay quiet.
const identityCases = [
  ['B738', 'Bombardier Challenger 350', true],
  ['CL35', 'Boeing 737-800', true],
  ['A320', 'Boeing 737', true],
  ['B737', 'Boeing 737-800', true],
  ['B38M', '737-800', true],
  ['B738', 'Boeing 737 MAX 8', true],
  ['B738', 'Boeing 737', false],
  ['B738', 'B737', false],
  ['B738', 'Boeing B737', false],
  ['B738', 'B737-700', true],
  ['B738', 'ICAO B737', true],
  ['B738', 'ICAO TYPE: B737', true],
  ['B738', 'BOEING B737-800', false],
  ['B38M', 'Boeing 737 MAX 8', false],
  ['CL35', 'Bombardier Challenger 350', false],
  ['CL35', 'Bombardier Challenger 3500', false],
  ['CL30', 'Bombardier Challenger 350', true],
  ['CL35', 'L2J', false],
  ['B738', '', false],
  ['UNKNOWN', 'Bombardier Challenger 350', false],
  ['UNMAPPED', 'Boeing 737', false],
  ['B738', 'B738', false],
  ['B738', 'CL35', true],
  ['B738', 'Boeing 737 / Challenger 350', false],
  ['A20N', 'Airbus A320', false],
  ['A320', 'AIRBUS A320-214', false],
  ['A321', 'Airbus A319', true],
  ['A35K', 'Airbus A350-1000', false],
  ['E175', 'EMBRAER E175', false],
  ['E75L', 'Embraer 175', false],
  ['E290', 'EMBRAER E190-E2', false],
  ['CRJ7', 'Bombardier CRJ700', false],
  ['CRJ7', 'Bombardier CRJ900', true],
  ['FA7X', 'Dassault Falcon 7X', false],
  ['MD11', 'McDonnell Douglas DC-10', true]
];
for (const [type, description, expected] of identityCases) {
  const plane = {type, description, callsign: 'TEST123', hex: 'abc123'};
  const before = {...plane};
  const warning = call('aircraftIdentityWarning', plane);
  assert.equal(Boolean(warning), expected, `${type} / ${description}`);
  if (expected) {
    assert.ok(warning.includes(type), 'Warning retains the reported type');
    assert.ok(warning.includes(description), 'Warning explains the source discrepancy');
  }
  assert.deepEqual(plane, before, 'Checking identity must preserve source metadata');
}
assert.equal(call('aircraftIdentityWarning', null), '');

// Every line and cubic Bezier stays within the convex hull of its control
// points. Keeping those points in the disk proves any heading remains visible.
const silhouettes = vm.runInContext('aircraftSilhouettes', context);
for (const [name, silhouette] of Object.entries(silhouettes)) {
  const unsupported = silhouette.path.replace(/[MLCZ]|-?\d+(?:\.\d+)?|[\s,]+/g, '');
  assert.equal(unsupported, '', `${name}: geometry checker needs an update for a new SVG command`);
  const coordinates = silhouette.path.match(/-?\d+(?:\.\d+)?/g).map(Number);
  assert.ok(coordinates.length >= 6 && coordinates.length % 2 === 0, `${name}: valid coordinate pairs`);
  for (let i = 0; i < coordinates.length; i += 2) {
    const radius = Math.hypot(coordinates[i] - 120, coordinates[i + 1] - 120);
    assert.ok(radius <= 108, `${name}: control point ${coordinates[i]},${coordinates[i + 1]} clips when rotated`);
  }
}
console.log(`PASS: ${classifications.length} aircraft classifications, distinct engine layouts, ${identityCases.length} identity checks and silhouette rotation bounds`);
