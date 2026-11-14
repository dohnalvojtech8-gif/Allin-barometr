const assert=require('node:assert/strict');global.window={};require('../server/web/reference.js');const calc=window.BarometrWeight,ref=window.BarometrReference;
assert.equal(calc({gross:42,tare:7,full:77,capacity:50,density:1,unitWeight:0,unit:'l'}).qty,25);
assert.equal(calc({gross:7,tare:7,full:77,capacity:50,density:1,unitWeight:0,unit:'l'}).qty,0);
assert.equal(calc({gross:77,tare:7,full:77,capacity:50,density:1,unitWeight:0,unit:'l'}).qty,50);
assert.throws(()=>calc({gross:78,tare:7,full:77,capacity:50,density:1,unitWeight:0,unit:'l'}));
assert.throws(()=>calc({gross:6,tare:7,full:77,capacity:50,density:1,unitWeight:0,unit:'l'}));
assert.throws(()=>calc({gross:8,tare:7,full:6,capacity:50,density:1,unitWeight:0,unit:'l'}));
assert.equal(calc({gross:25.5,tare:10,full:0,capacity:30,density:1,unitWeight:0,unit:'l'}).qty,15.5);
for(const b of ref.beers){assert.ok(ref.sources[b.source]?.url.startsWith('https://'));assert.ok(b.capacity>0);assert.equal(b.tare,undefined);assert.equal(b.fullWeightKg,undefined)}
for(const k of ref.kegs){assert.equal(k.status,'approximate');assert.ok(k.tare>0)}
console.log('PASS: calibration boundaries, fallback, source integrity and per-field verification');
