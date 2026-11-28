import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
const root=process.env.FORGE_SOURCE?path.resolve(process.env.FORGE_SOURCE):path.resolve(import.meta.dirname,'../../forge');
const plugin=JSON.parse(fs.readFileSync(path.join(root,'plugins/abc/dist/plugin.json'),'utf8'));
const tiddlers=JSON.parse(plugin.text).tiddlers,cache={};
function load(name){if(cache[name])return cache[name];const module={exports:{}};cache[name]=module.exports;runInNewContext(tiddlers[name].text,{module,exports:module.exports,require:load,console,setTimeout,clearTimeout});return cache[name]=module.exports;}
const ABC=load('$:/plugins/huwiki/abc/vendor/abcjs.js'),acc=load('$:/plugins/huwiki/abc/accompaniment.js');
const rows=JSON.parse(fs.readFileSync(new URL('../research/helles/tiddlers.json',import.meta.url))),index=new Map(rows.map(r=>[r.title,r]));
const summary=[];
for(const work of rows.filter(r=>r['repertoire-kind']==='piece')){
 const source=[work,index.get(work['repertoire-leadsheet-source']),index.get(work['repertoire-chord-stabs-source'])].find(r=>r?.['abc-source']);
 if(!source){summary.push({title:work.title,status:'missing'});continue;}
 const abc=source['abc-source'],tune=ABC.parseOnly(abc)[0];assert.ok(tune,source.title);assert.ok(!tune.warnings?.length,source.title+': '+tune.warnings);
 const settings=acc.read(source);assert.equal(settings.enabled,true,source.title);
 const config=acc.resolve(settings,abc,source);acc.prepare(ABC,tune,abc,config,true,source);
 const audio=tune.setUpAudio({}),notes=t=>t.filter(e=>e.cmd==='note'&&e.volume>0&&e.duration>0);
 for(const bus of ['bassVolume','chordVolume']){
  const events=audio.tracks.filter(t=>t.huwabcPart===bus).flatMap(notes);
  assert.ok(events.length,source.title+' has no '+bus);
  if(source['helles-written-bars'])for(let quarter=0;quarter<4;quarter++)assert.ok(events.some(e=>e.start>=audio.totalDuration*quarter/4&&e.start<audio.totalDuration*(quarter+1)/4),source.title+' '+bus+' is missing in quarter '+quarter);
 }
 summary.push({title:work.title,source:source.title,style:config.style,tracks:audio.tracks.map(t=>({bus:t.huwabcPart,notes:notes(t).length}))});
}
console.log(JSON.stringify(summary,null,2));
assert.equal(summary.filter(x=>x.status!=='missing').length,25);
assert.deepEqual(summary.filter(x=>x.status==='missing'),[]);
