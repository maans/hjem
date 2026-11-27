#!/usr/bin/env node
/** Add reviewed native MuseScore/ABC melodies to the existing MusicXML conversions. */
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const options={};for(let i=2;i<process.argv.length;i+=2)options[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const forge=path.resolve(options.forge||path.join(root,'../forge'));
const research=path.join(root,'research/birdland'),bulk=path.join(research,'bulk');
const plugin=JSON.parse(await readFile(path.join(forge,'plugins/abc/dist/plugin.json'),'utf8'));
const tiddlers=JSON.parse(plugin.text).tiddlers,mod={exports:{}};
runInNewContext(tiddlers['$:/plugins/huwiki/abc/vendor/abcjs.js'].text,{module:mod,exports:mod.exports,console,window:{}});
const ABC=mod.exports,transpose={};runInNewContext(tiddlers['$:/plugins/huwiki/abc/transpose.js'].text,{exports:transpose});
const dom=require(options['dom-module']||process.env.DOM_MODULE||'@xmldom/xmldom');
function adapt(node){if(!node)return node;Object.defineProperty(node,'firstElementChild',{configurable:true,get(){return Array.from(this.childNodes||[]).find(n=>n.nodeType===1)||null;}});Object.defineProperty(node,'nextElementSibling',{configurable:true,get(){let at=this.nextSibling;while(at&&at.nodeType!==1)at=at.nextSibling;return at;}});for(const c of Array.from(node.childNodes||[]))adapt(c);return node;}
class Parser{parseFromString(raw,type){return adapt(new dom.DOMParser({errorHandler:{warning(){},error(m){throw Error(m);},fatalError(m){throw Error(m);}}}).parseFromString(raw,type));}}
const cache={};async function loadConverter(){
 const modules={};for(const file of ['converter.js','percussion.js'])modules[file]=await readFile(path.join(forge,'plugins/musescore-import/src',file),'utf8');
 function load(id){const file=id.split('/').pop();if(cache[file])return cache[file];const out={};cache[file]=out;runInNewContext(modules[file],{exports:out,require:load,DOMParser:Parser,console});return out;}
 return load('converter.js');
}
const converter=await loadConverter();
const cat=JSON.parse(await readFile(path.join(bulk,'catalogue.json'),'utf8'));
const refs=JSON.parse(await readFile(path.join(root,'scripts/birdland-arrangement-settings.json'),'utf8'));
const patches=JSON.parse(await readFile(path.join(research,'leadsheet-patches.json'),'utf8'));
const report=[];
const pc=k=>{const m=/^([A-G])([b#]?)(m?)$/.exec(k);if(!m)throw Error('Unsupported key '+k);return ({C:0,D:2,E:4,F:5,G:7,A:9,B:11}[m[1]]+(m[2]==='b'?-1:m[2]==='#'?1:0)+12)%12;};
function inspect(abc){
 const tunes=ABC.parseOnly(abc);if(tunes.length!==1)throw Error('Expected one complete tune');const tune=tunes[0];
 if(tune.warnings?.length)throw Error('ABC parse warnings: '+tune.warnings.join('; '));
 const events=tune.lines.flatMap(l=>l.staff||[]).flatMap(s=>s.voices||[]).flat();
 const notes=events.filter(e=>e.el_type==='note'&&e.pitches?.length);
 const pitches=new Set(notes.flatMap(e=>e.pitches.map(p=>p.pitch)));
 const chords=events.flatMap(e=>e.chord||[]).filter(c=>!c.position||c.position==='default');
 if(notes.length<24||pitches.size<5||!chords.length)throw Error('Needs playable melody and chord review');
 return {tune,notes:notes.length,pitches:pitches.size,chords:chords.length};
}
for(const e of cat.entries){
 if(!e.sources.length)continue;
 if(patches.some(p=>p.title===e.title)){report.push({title:e.title,status:'existing_reviewed_leadsheet'});continue;}
 const ref=refs[e.title];if(!ref?.key||!ref.bpm){report.push({title:e.title,status:'needs_birdland_tempo_or_key'});continue;}
 const native=e.sources.find(s=>s.format==='mscz'),source=native||e.sources.find(s=>s.format==='abc');if(!source)continue;
 const result={title:e.title,source:source.url};
 try{
  let abc,warnings=[];
  if(native){
   const raw=await readFile(path.join(bulk,source.path.replace(/\.mscz$/,'.mscx')),'utf8');
   const model=converter.parseMuse(raw,e.title+'.mscx');
   if(model.staves.length!==1||model.staves[0].percussion)throw Error('Expected a single melody staff');
   const rendered=converter.renderABC(model,model.staves[0].voices.map(v=>v.id),1,model.totalMeasures,{title:e.title});
   abc=rendered.abc;warnings=Array.from(rendered.warnings||[]);if(warnings.length)throw Error(warnings.join('; '));
  }else abc=await readFile(path.join(bulk,source.path),'utf8');
  abc=abc.split(/\r?\n/).filter(l=>l.trim()).join('\n')+'\n';
  abc=abc.replace(/"([^"\n]+)"/g,(all,chord)=>'"'+chord.replace(/\^7/g,'maj7').replace(/\^6/g,'6').replace(/\^9/g,'maj9')+'"');
  const before=inspect(abc),key=before.tune.getKeySignature(),originalKey=key.root+(key.acc||'')+(key.mode||'');
  let effectiveKey=ref.abc_source_key_override||originalKey;
  if(ref.abc_source_key_override&&!ref.abc_source_key_evidence)throw Error('A source-key correction requires evidence');
  if(/m$/.test(effectiveKey)!==/m$/.test(ref.key))throw Error('Source/target mode mismatch needs review');
  const shift=(pc(ref.key)-pc(effectiveKey)+18)%12-6;
  abc=transpose.apply(ABC,abc,shift).replace(/^K:.*$/m,'K:'+ref.key).replace(/^T:.*$/m,'T:'+e.title);
  if(/^Q:/m.test(abc))abc=abc.replace(/^Q:.*$/m,'Q:'+ref.beat+'='+ref.bpm);else abc=abc.replace(/^K:/m,'Q:'+ref.beat+'='+ref.bpm+'\nK:');
  const after=inspect(abc);
  if(after.notes!==before.notes||after.chords!==before.chords)throw Error('Transposition changed event counts');
  // Sequencing proves the melody has real playable notes, with chord markers.
  const audio=after.tune.setUpAudio({chordsOff:true});
  const pitches=sequence=>(sequence.tracks||[]).flat().filter(event=>event.cmd==='note').map(event=>event.pitch);
  const beforePitches=pitches(before.tune.setUpAudio({chordsOff:true})),afterPitches=pitches(audio);
  if(!afterPitches.length)throw Error('No playable MIDI melody');
  if(beforePitches.length!==afterPitches.length||beforePitches.some((pitch,i)=>afterPitches[i]!==pitch+shift))throw Error('Played melody pitches did not transpose by the requested interval');
  const slug=e.title.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const relative='leadsheets/'+slug+'-'+source.sha256.slice(0,8)+'.abc';await mkdir(path.dirname(path.join(research,relative)),{recursive:true});await writeFile(path.join(research,relative),abc);
  patches.push({title:e.title,abc_source:abc,abc_path:relative,source:source.url,source_format:native?'mscz':'abc',source_key:originalKey,effective_source_key:effectiveKey,birdland_reference:ref,transpose_semitones:shift,abc_key:ref.key,abc_tempo:ref.beat+'='+ref.bpm,abc_chord_count:after.chords,melody_notes:after.notes,arrangement_verified:false,target:'alternative_leadsheet_only'});
  Object.assign(result,{status:'converted_birdland_key_tempo_verified',notes:after.notes,chords:after.chords,source_format:native?'mscz':'abc',abc_key:ref.key,abc_tempo:ref.beat+'='+ref.bpm,transpose_semitones:shift});
 }catch(error){Object.assign(result,{status:'needs_conversion_review',error:String(error.message).slice(0,350)});}
 report.push(result);
}
await writeFile(path.join(research,'leadsheet-patches.json'),JSON.stringify(patches,null,2)+'\n');
await writeFile(path.join(research,'bulk-conversion.json'),JSON.stringify({converted:patches.length,entries:report},null,2)+'\n');
console.log(JSON.stringify({converted:patches.length,added:report.filter(x=>x.status==='converted_birdland_key_tempo_verified').length,entries:report}));
