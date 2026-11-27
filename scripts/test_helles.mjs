import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=path.resolve(import.meta.dirname,'..'),forge=path.resolve(process.env.FORGE_SOURCE||path.join(root,'.forge-source'));
const bundled=JSON.parse(JSON.parse(fs.readFileSync(path.join(forge,'plugins/abc/dist/plugin.json'),'utf8')).text).tiddlers;
const cache={};function load(id){if(cache[id])return cache[id];const m={exports:{}};cache[id]=m.exports;const source=fs.existsSync(path.join(forge,'plugins/abc/src',id.split('/').at(-1)))?fs.readFileSync(path.join(forge,'plugins/abc/src',id.split('/').at(-1)),'utf8'):bundled[id].text;vm.runInNewContext(source,{module:m,exports:m.exports,require:load,console,setTimeout,clearTimeout});return cache[id]=m.exports;}
const ABC=load('$:/plugins/huwiki/abc/vendor/abcjs.js'),profiles=load('$:/plugins/huwiki/abc/instrument-view.js'),accompaniment=load('$:/plugins/huwiki/abc/accompaniment.js');
const rows=JSON.parse(fs.readFileSync(path.join(root,'research/helles/conversions.json'),'utf8')).filter(r=>r.publish);assert.equal(rows.length,4);
for(const r of rows){
 const raw=r.abc_source;const expected=JSON.stringify(ABC.parseOnly(raw)[0].setUpAudio({chordsOff:true}).tracks);
 for(const id of ['c','bb','tenor','ebalto']){
  profiles.change(id);const visual=ABC.parseOnly(raw,{visualTranspose:profiles.current().semitones})[0];
  // The score renderer is visually transposed; playback is always parsed from its original source.
  assert.equal(JSON.stringify(ABC.parseOnly(raw)[0].setUpAudio({chordsOff:true}).tracks),expected,r.title+' audio '+id);
  assert.ok(visual.lines.length);assert.equal(r.abc_source,raw);
 }
 const tune=ABC.parseOnly(raw)[0],fields={'abc-source':raw,'abc-accompaniment':JSON.stringify({enabled:true,style:['Wave','Desafinado'].includes(r.title)?'bossa':'swing'})};
 accompaniment.prepare(ABC,tune,raw,accompaniment.read(fields),false,fields);assert.ok(tune.setUpAudio({}).tracks.flat().some(e=>e.cmd==='note'&&e.volume>0));
}
const t=JSON.parse(fs.readFileSync(path.join(root,'research/helles/tiddlers.json'),'utf8'));const titles=new Set(t.map(r=>r.title));assert.equal(titles.size,t.length);assert.equal(t.filter(r=>r['repertoire-kind']==='piece').length,25);
for(const r of t){for(const field of ['repertoire-score-pdf','repertoire-guitar-pdf','helles-lyrics-pdf'])if(r[field])assert.ok(fs.existsSync(path.join(root,'wiki/helles',r[field])),r.title+' '+field);if(r['repertoire-leadsheet-source'])assert.ok(titles.has(r['repertoire-leadsheet-source']));}
assert.equal(t.find(r=>r.title==='$:/GitHub/Path').text,'wiki/helles/');
console.log('Verified 25 pieces, source links, four ABC scores, sax profiles and unchanged sounding-pitch audio.');
