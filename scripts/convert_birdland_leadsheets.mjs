#!/usr/bin/env node
/** Convert verified alternative lead sheets, preserving explicit musical metadata.
 * Birdland's explicitly supplied key and tempo control the output; source values remain provenance.
 * No wiki files are read or written. Converter paths point at the reviewed Forge checkout.
 */
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {fileURLToPath} from 'node:url';

const require=createRequire(import.meta.url),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
function args(argv){const result={research:path.join(root,'research/birdland'),domModule:process.env.DOM_MODULE||'@xmldom/xmldom'};for(let i=0;i<argv.length;i++){const key=argv[i];if(!['--research','--converter','--dom-module','--references'].includes(key)||!argv[i+1])throw Error('Usage: --converter PATH [--research PATH] [--dom-module PATH]');result[{'--research':'research','--converter':'converter','--dom-module':'domModule','--references':'references'}[key]]=argv[++i];}if(!result.converter||!result.references)throw Error('--converter and --references are required');return result;}
const first=(node,name)=>Array.from(node?.childNodes||[]).find(n=>n.nodeType===1&&n.localName===name)||null;
const children=(node,name)=>Array.from(node?.childNodes||[]).filter(n=>n.nodeType===1&&n.localName===name);
function descendants(node,name){return Array.from(node?.getElementsByTagName(name)||[]);}
const text=node=>String(node?.textContent||'').trim();
const num=node=>node&&text(node)!==''&&Number.isFinite(Number(text(node)))?Number(text(node)):null;
function adapt(node){if(!node)return node;Object.defineProperty(node,'firstElementChild',{configurable:true,get(){return Array.from(this.childNodes||[]).find(n=>n.nodeType===1)||null;}});Object.defineProperty(node,'nextElementSibling',{configurable:true,get(){let at=this.nextSibling;while(at&&at.nodeType!==1)at=at.nextSibling;return at;}});for(const child of Array.from(node.childNodes||[]))adapt(child);return node;}
export function sourceMetadata(doc){
 const score=doc.documentElement,parts=children(score,'part');
 if(score.localName!=='score-partwise')return {review:'needs_score_partwise_review'};
 if(parts.length!==1)return {review:'needs_multi_part_review'};
 const part=parts[0],attributes=descendants(part,'attributes');
 const transposes=attributes.map(a=>first(a,'transpose')).filter(Boolean);
 if(transposes.some(t=>(num(first(t,'chromatic'))||0)+12*(num(first(t,'octave-change'))||0)!==0))return {review:'needs_transposition_review'};
 const key=attributes.map(a=>first(a,'key')).find(Boolean),fifths=num(first(key,'fifths')),mode=text(first(key,'mode')).toLowerCase()||null;
 if(!Number.isInteger(fifths)||Math.abs(fifths)>7)return {review:'needs_key_review',source_key:null};
 if(mode&&!['major','minor'].includes(mode))return {review:'needs_key_mode_review',source_key:{fifths,mode}};
 const tempos=[];
 for(const direction of descendants(part,'direction')){
  const sound=first(direction,'sound'),qpm=num(sound?.getAttribute('tempo')===null?null:{textContent:sound?.getAttribute('tempo')}),metronome=descendants(direction,'metronome')[0];
  const beat=text(first(metronome,'beat-unit')),bpm=num(first(metronome,'per-minute'));
  const lengths={whole:1,half:.5,quarter:.25,eighth:.125,'16th':.0625,'32nd':.03125};
  let unit=lengths[beat],dots=children(metronome,'beat-unit-dot').length;
  if(unit)unit*=2-1/(2**dots);
  if(qpm>0)tempos.push({qpm,abc:unit&&bpm>0&&Math.abs(unit*4*bpm-qpm)<.001?fraction(unit)+'='+bpm:'1/4='+qpm,basis:'sound'});
  else if(unit&&bpm>0)tempos.push({qpm:unit*4*bpm,abc:fraction(unit)+'='+bpm,basis:'metronome'});
 }
 for(const sound of children(part,'sound')){const bpm=Number(sound.getAttribute('tempo'));if(bpm>0)tempos.push({qpm:bpm,abc:'1/4='+bpm,basis:'sound'});}
 return {source_key:{fifths,mode},source_tempo:tempos[0]||null,source_tempo_changes:tempos.length,
  source_harmony_count:descendants(part,'harmony').length};
}
function fraction(value){for(let denominator=1;denominator<=64;denominator*=2){const numerator=Math.round(value*denominator);if(Math.abs(numerator/denominator-value)<1e-9)return numerator+'/'+denominator;}throw Error('Unsupported metronome beat');}
const MAJOR=['Cb','Gb','Db','Ab','Eb','Bb','F','C','G','D','A','E','B','F#','C#'];
const MINOR=['Abm','Ebm','Bbm','Fm','Cm','Gm','Dm','Am','Em','Bm','F#m','C#m','G#m','D#m','A#m'];
export function validateABC(abc,metadata){
 const key=/^K:\s*(\S+)/m.exec(abc)?.[1],tempo=/^Q:\s*(.+)$/m.exec(abc)?.[1]||null;
 const keyIndex=MAJOR.indexOf(key)>=0?MAJOR.indexOf(key):MINOR.indexOf(key);
 if(keyIndex<0||keyIndex-7!==metadata.source_key.fifths)throw Error('ABC key signature differs from source');
 if(metadata.source_key.mode==='minor'&&!MINOR.includes(key)||metadata.source_key.mode==='major'&&!MAJOR.includes(key))throw Error('ABC key mode differs from source');
 if(metadata.source_tempo&&tempo!==metadata.source_tempo.abc)throw Error('ABC tempo differs from source');
 if(!metadata.source_tempo&&tempo!==null)throw Error('Missing source tempo must not acquire an invented ABC tempo');
 const body=abc.split('\n').filter(line=>!/^\s*(?:[A-Za-z]:|%%)/.test(line)).join('\n');
 const chords=Array.from(body.matchAll(/"([^"\r\n]+)"/g),match=>match[1]).filter(value=>/^(?:[A-G](?:[#b♯♭])?|N\.?C\.?)/.test(value));
 if(!metadata.source_harmony_count||!chords.length)throw Error('needs_chords_review');
 return {abc_key:key,abc_tempo:tempo,abc_chord_count:chords.length};
}
const NAT={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
function pitchClass(name){const match=/^([A-G])([#b]*)(?:m)?$/.exec(name);if(!match)throw Error('Invalid reference key');return (NAT[match[1]]+[...match[2]].reduce((n,c)=>n+(c==='#'?1:-1),0)+120)%12;}
export function referenceSettings(reference){
 if(!reference||typeof reference.key!=='string'||!(Number(reference.bpm)>0)||!/^\d+\/\d+$/.test(reference.beat||''))return null;
 const minor=/m$/.test(reference.key),list=minor?MINOR:MAJOR,index=list.indexOf(reference.key);
 if(index<0)return null;
 if(reference.source_mode_override!==undefined&&(!['major','minor'].includes(reference.source_mode_override)||typeof reference.source_mode_evidence!=='string'||!reference.source_mode_evidence.trim()))throw Error('Source mode override requires an explicit major/minor mode and evidence');
 return {key:reference.key,fifths:index-7,mode:minor?'minor':'major',bpm:Number(reference.bpm),beat:reference.beat,reference:reference.reference||'',abcTempo:reference.beat+'='+Number(reference.bpm),
  ...(reference.source_mode_override?{source_mode_override:reference.source_mode_override,source_mode_evidence:reference.source_mode_evidence}:{} )};
}
export function normalizeHarmony(doc){
 const suffixes={major:'',minor:'m',dominant:'7','major-seventh':'maj7','minor-seventh':'m7','diminished-seventh':'dim7',diminished:'dim','half-diminished':'m7b5',augmented:'aug','minor-major':'mMaj7','major-sixth':'6','minor-sixth':'m6','dominant-ninth':'9','major-ninth':'maj9','minor-ninth':'m9','dominant-11th':'11','major-11th':'maj11','minor-11th':'m11','dominant-13th':'13','major-13th':'maj13','minor-13th':'m13','suspended-second':'sus2','suspended-fourth':'sus4',power:'5',none:'none'};
 for(const harmony of descendants(doc,'harmony')){
  const kind=first(harmony,'kind');if(!kind)throw Error('Missing source chord kind');
  const value=text(kind);if(!(value in suffixes))throw Error('Unsupported source chord kind: '+value);
  let suffix=suffixes[value];const degrees=[];
  for(const degree of children(harmony,'degree')){
   const value=num(first(degree,'degree-value')),alter=num(first(degree,'degree-alter'))||0,type=text(first(degree,'degree-type'));
   if(!Number.isInteger(value)||!['add','alter'].includes(type)||![-2,-1,0,1,2].includes(alter))throw Error('Unsupported source chord degree');
   degrees.push((alter<0?'b'.repeat(-alter):alter>0?'#'.repeat(alter):type==='add'?'add':'')+value);
  }
  kind.textContent=suffix+(degrees.length?'('+degrees.join(',')+')':'');
 }
}
export function transposeXML(doc,metadata,target){
 const effectiveMode=target.source_mode_override||metadata.source_key.mode;
 if(target.source_mode_override&&(!['major','minor'].includes(target.source_mode_override)||!target.source_mode_evidence?.trim()))throw Error('Source mode override requires explicit evidence');
 if(effectiveMode&&effectiveMode!==target.mode)throw Error('Source and Birdland key modes differ; needs review');
 const oldKey=((effectiveMode||target.mode)==='minor'?MINOR:MAJOR)[metadata.source_key.fifths+7];
 let shift=(pitchClass(target.key)-pitchClass(oldKey)+18)%12-6;
 const flat=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'],sharp=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
 function set(parent,name,value){let node=first(parent,name);if(value===null){if(node)parent.removeChild(node);return;}if(!node){node=doc.createElement(name);parent.appendChild(node);}node.textContent=String(value);}
 const letters='CDEFGAB',letterShift=letters.indexOf(target.key[0])-letters.indexOf(oldKey[0]);
 function transposed(step,alter){
  const pc=(NAT[step]+alter+shift+120)%12,nextStep=letters[(letters.indexOf(step)+letterShift+14)%7];
  const nextAlter=(pc-NAT[nextStep]+18)%12-6;
  if(Math.abs(nextAlter)<=2)return {step:nextStep,alter:nextAlter};
  const name=(target.fifths<0?flat:sharp)[pc];return {step:name[0],alter:name[1]==='b'?-1:name[1]==='#'?1:0};
 }
 for(const pitch of descendants(doc,'pitch')){
  const step=text(first(pitch,'step')),alter=num(first(pitch,'alter'))||0,octave=num(first(pitch,'octave'));if(!(step in NAT)||octave===null)throw Error('Invalid source pitch');
  const midi=(octave+1)*12+NAT[step]+alter+shift,next=transposed(step,alter);
  set(pitch,'step',next.step);set(pitch,'alter',next.alter||null);set(pitch,'octave',Math.round((midi-NAT[next.step]-next.alter)/12)-1);
  const accidental=first(pitch.parentNode,'accidental');if(accidental)set(pitch.parentNode,'accidental',next.alter===2?'double-sharp':next.alter===-2?'flat-flat':next.alter===1?'sharp':next.alter===-1?'flat':null);
 }
 for(const harmony of descendants(doc,'harmony'))for(const [name,stepName,alterName] of [['root','root-step','root-alter'],['bass','bass-step','bass-alter']]){
  const base=first(harmony,name),step=text(first(base,stepName));if(!base)continue;if(!(step in NAT))throw Error('Invalid source harmony root');
  const next=transposed(step,num(first(base,alterName))||0);set(base,stepName,next.step);set(base,alterName,next.alter||null);
 }
 let firstKey=true;
 for(const key of descendants(doc,'key')){
  const fifths=num(first(key,'fifths'));if(!Number.isInteger(fifths)||Math.abs(fifths)>7)throw Error('Unsupported key change');
  const oldMajor=MAJOR[fifths+7],nextPc=(pitchClass(oldMajor)+shift+12)%12;
  const candidates=MAJOR.map((name,index)=>({name,fifths:index-7})).filter(item=>pitchClass(item.name)===nextPc).sort((a,b)=>Math.abs(a.fifths)-Math.abs(b.fifths)||a.fifths-b.fifths);
  set(key,'fifths',firstKey?target.fifths:candidates[0].fifths);if(firstKey)set(key,'mode',target.mode);firstKey=false;
 }
 for(const sound of descendants(doc,'sound'))sound.removeAttribute('tempo');
 return shift;
}
export async function convert(options){
 const dom=require(options.domModule),research=path.resolve(options.research);
 const Parser=class{parseFromString(value,type){return adapt(new dom.DOMParser({errorHandler:{warning(){},error(message){throw Error(message);},fatalError(message){throw Error(message);}}}).parseFromString(value,type));}};
 const files=['converter.js','percussion.js'],modules={};
 for(const file of files)modules[file]=await readFile(path.join(path.dirname(options.converter),file),'utf8');
 const cache={};function load(id){const file=id.split('/').pop();if(cache[file])return cache[file];const out={};cache[file]=out;runInNewContext(modules[file],{exports:out,require:load,DOMParser:Parser,console});return out;}
 const converter=load('converter.js'),catalogue=JSON.parse(await readFile(path.join(research,'catalogue.json'),'utf8'));
 const references=JSON.parse(await readFile(options.references,'utf8'));
 const results=[],patches=[];await mkdir(path.join(research,'leadsheets'),{recursive:true});
 for(const entry of catalogue.entries){
  const result={title:entry.title,status:entry.status,arrangement_verified:false};
  if(!entry.source){results.push(result);continue;}
  try{
   const sourcePath=path.resolve(research,entry.source.path);if(!sourcePath.startsWith(research+path.sep))throw Error('Source path outside research');
   const raw=await readFile(sourcePath,'utf8'),doc=new Parser().parseFromString(raw,'application/xml'),meta=sourceMetadata(doc);Object.assign(result,meta);
   if(meta.review){result.status=meta.review;results.push(result);continue;}
   const reference=referenceSettings(references[entry.title]);
   if(!reference){result.status='needs_birdland_reference';results.push(result);continue;}
   result.birdland_reference=reference;
   result.effective_source_key={...meta.source_key,mode:reference.source_mode_override||meta.source_key.mode};
   if(reference.source_mode_override){result.source_mode_override=reference.source_mode_override;result.source_mode_evidence=reference.source_mode_evidence;}
   if(!meta.source_harmony_count){result.status='needs_chords_review';results.push(result);continue;}
   normalizeHarmony(doc);
   result.transpose_semitones=transposeXML(doc,meta,reference);
   const transposed=new dom.XMLSerializer().serializeToString(doc);
   const model=converter.parseMusicXML(transposed,path.basename(sourcePath)),selection=model.staves.flatMap(staff=>staff.voices.map(voice=>voice.id));
   const rendered=converter.renderABC(model,selection,1,model.totalMeasures,{minor:reference.mode==='minor',title:entry.title});
   let abc=rendered.abc;
   abc=abc.replace(/^Q:.*$/m,'Q:'+reference.abcTempo);
   const validation=validateABC(abc,{...meta,source_key:{fifths:reference.fifths,mode:reference.mode},source_tempo:{abc:reference.abcTempo}});Object.assign(result,validation);
   const slug=entry.title.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'score';
   const relative='leadsheets/'+slug+'-'+entry.source.sha256.slice(0,8)+'.abc';
   await writeFile(path.join(research,relative),abc,'utf8');
   result.status='converted_birdland_key_tempo_verified';result.tempo_status='birdland_reference';result.source_tempo_status=meta.source_tempo?'source_tempo':'tempo_unverified';result.key_status='birdland_reference';result.abc_path=relative;
   result.warnings=Array.from(rendered.warnings||[]);
   patches.push({title:entry.title,fields:{'repertoire-has-leadsheet':'yes','repertoire-abc-label':'Leadsheet · anden udgave',
    'repertoire-leadsheet-tempo-status':result.tempo_status},abc_source:abc,abc_path:relative,
    target:'alternative_leadsheet_only',arrangement_verified:false,source:entry.source.url,
    source_key:meta.source_key,effective_source_key:result.effective_source_key,source_tempo:meta.source_tempo,birdland_reference:reference,transpose_semitones:result.transpose_semitones,...validation});
  }catch(error){result.status=error.message==='needs_chords_review'?'needs_chords_review':'needs_conversion_review';result.error=String(error.message).slice(0,240);}
  results.push(result);
 }
 const report={schema_version:1,scope:'Alternative lead sheets for comparison; no Birdland arrangement is verified and no existing guitar ABC is replaced.',converted:patches.length,entries:results};
 await writeFile(path.join(research,'conversion.json'),JSON.stringify(report,null,2)+'\n');
 await writeFile(path.join(research,'leadsheet-patches.json'),JSON.stringify(patches,null,2)+'\n');
 return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const report=await convert(args(process.argv.slice(2)));console.log(JSON.stringify({converted:report.converted,needs_review:report.entries.filter(row=>row.status.startsWith('needs_')).length}));
}
