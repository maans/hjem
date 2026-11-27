import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'),forge=path.resolve(process.env.FORGE_SOURCE||path.join(root,'../forge'));
const bundled=JSON.parse(JSON.parse(readFileSync(path.join(forge,'plugins/abc/dist/plugin.json'),'utf8')).text).tiddlers,cache={};
function load(name){
 if(cache[name])return cache[name];const module={exports:{}};cache[name]=module.exports;
 const local=path.join(forge,'plugins/abc/src',name.split('/').at(-1));
 runInNewContext(existsSync(local)?readFileSync(local,'utf8'):bundled[name].text,{module,exports:module.exports,require:load,console,setTimeout,clearTimeout});
 return cache[name]=module.exports;
}
const ABC=load('$:/plugins/huwiki/abc/vendor/abcjs.js'),backing=load('$:/plugins/huwiki/abc/accompaniment.js');
const leads=JSON.parse(readFileSync(path.join(root,'research/birdland/leadsheet-patches.json'),'utf8'));
const refs=JSON.parse(readFileSync(path.join(root,'scripts/birdland-arrangement-settings.json'),'utf8'));
assert.ok(leads.length>=34);
for(const lead of leads){
 const source=lead.abc_source,tune=ABC.parseOnly(source)[0],ref=refs[lead.title]||{};
 assert.ok(!tune.warnings?.length,lead.title+': ABC must parse without warnings');
 const fields={'abc-source':source,'abc-accompaniment':JSON.stringify({enabled:true,style:ref.style||'swing'})};
 const config=backing.read(fields);assert.equal(config.enabled,true);
 const baseline=tune.setUpAudio({chordsOff:true});
 backing.prepare(ABC,tune,source,config,false,fields);const audio=tune.setUpAudio({});
 assert.equal(audio.tempo,ref.bpm||baseline.tempo,lead.title+': Birdland tempo or unchanged source tempo');
 if(lead.settings_origin?.tempo==='source')assert.equal(lead.abc_tempo,lead.source_tempo,lead.title+': preserve the original source tempo');
 if(lead.settings_origin?.key==='source')assert.equal(lead.abc_key,lead.source_key,lead.title+': preserve the original source key');
 if(lead.settings_origin?.tempo==='player_default')assert.ok(!/^Q:/m.test(source),'Do not invent a source tempo');
 assert.equal(audio.totalDuration,baseline.totalDuration,lead.title+': accompaniment cannot change the musical duration');
 for(const name of ['bassVolume','chordVolume','drumVolume']){
  const track=audio.tracks.find(t=>t.huwabcPart===name);
  assert.ok(track?.some(e=>e.cmd==='note'&&e.volume>0&&e.duration>0),lead.title+': playable '+name);
 }
}
console.log('Verified '+leads.length+' melody leadsheets with playable bass, chords and jazz drums, using Birdland settings or the original source settings.');
