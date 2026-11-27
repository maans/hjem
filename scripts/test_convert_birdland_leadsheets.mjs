import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
import {convert,validateABC,normalizeHarmony} from './convert_birdland_leadsheets.mjs';
const domModule=process.env.DOM_MODULE,converter=process.env.CONVERTER_PATH;
const xml=chords=>`<score-partwise version="4.0"><work><work-title>Test</work-title></work><part-list><score-part id="P1"><part-name>Melody</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths><mode>major</mode></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction><sound tempo="90"/></direction>${chords?'<harmony><root><root-step>C</root-step></root><kind>dominant</kind><bass><bass-step>G</bass-step></bass></harmony>':''}<note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type></note><note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type></note></measure></part></score-partwise>`;

test('ABC validation refuses missing chords, wrong key and invented source tempo',()=>{
 const meta={source_key:{fifths:-1,mode:'minor'},source_tempo:{abc:'1/4=120'},source_harmony_count:1};
 assert.equal(validateABC('X:1\nQ:1/4=120\nK:Dm\n"Dm"D2|',meta).abc_chord_count,1);
 assert.throws(()=>validateABC('X:1\nQ:1/4=120\nK:C\n"C"C2|',meta),/key signature/);
 assert.throws(()=>validateABC('X:1\nQ:1/4=120\nK:Dm\nD2|',meta),/needs_chords_review/);
 assert.throws(()=>validateABC('X:1\nQ:1/4=125\nK:Dm\n"Dm"D2|',{...meta,source_tempo:null}),/invented/);
});

test('MusicXML chord extensions and altered degrees survive normalization', {skip:!domModule},()=>{
 const {DOMParser}=createRequire(import.meta.url)(domModule);
 const doc=new DOMParser().parseFromString('<score-partwise><harmony><kind>major-sixth</kind></harmony><harmony><kind>dominant</kind><degree><degree-value>9</degree-value><degree-alter>-1</degree-alter><degree-type>add</degree-type></degree></harmony></score-partwise>','application/xml');
 normalizeHarmony(doc);
 assert.deepEqual(Array.from(doc.getElementsByTagName('kind'),node=>node.textContent),['6','7(b9)']);
});

test('real converter transposes melody and slash chords into Birdland key and tempo, retaining provenance', {skip:!domModule||!converter},async()=>{
 const directory=await mkdtemp(path.join(os.tmpdir(),'birdland-conversion-test-'));
 try{
  await mkdir(path.join(directory,'sources'));
  await writeFile(path.join(directory,'sources/test.musicxml'),xml(true));
  await writeFile(path.join(directory,'sources/nochords.musicxml'),xml(false));
  const source={path:'sources/test.musicxml',sha256:'1234567890abcdef',url:'https://example.invalid/original'};
  await writeFile(path.join(directory,'catalogue.json'),JSON.stringify({entries:[{title:'Test',status:'verified_musicxml_alternative',source},{title:'No reference',status:'verified_musicxml_alternative',source},{title:'No chords',status:'verified_musicxml_alternative',source:{...source,path:'sources/nochords.musicxml'}}]}));
  const references=path.join(directory,'references.json');
  await writeFile(references,JSON.stringify({'Test':{key:'D',bpm:120,beat:'1/4',reference:'Verified Birdland chart'},'No chords':{key:'D',bpm:120,beat:'1/4',reference:'Verified Birdland chart'}}));
  const report=await convert({research:directory,converter,domModule,references});
  assert.equal(report.converted,1);
  const row=report.entries[0];assert.equal(row.source_key.fifths,0);assert.equal(row.source_tempo.qpm,90);
  assert.equal(row.abc_key,'D');assert.equal(row.abc_tempo,'1/4=120');assert.equal(row.transpose_semitones,2);
  const abc=await readFile(path.join(directory,row.abc_path),'utf8');
  assert.match(abc,/^K:D$/m);assert.match(abc,/^Q:1\/4=120$/m);assert.match(abc,/"D7\/A"D4 F4/);
  assert.equal(report.entries[1].status,'needs_birdland_reference');assert.equal(report.entries[2].status,'needs_chords_review');
  const patches=JSON.parse(await readFile(path.join(directory,'leadsheet-patches.json'),'utf8'));
  assert.equal(patches[0].fields['repertoire-has-leadsheet'],'yes');assert.equal(patches[0].fields['repertoire-abc-label'],'Leadsheet · anden udgave');
  assert.equal(patches[0].fields['abc-source'],undefined,'existing guitar ABC is never a patch target');
  assert.equal(await readFile(path.join(directory,'sources/test.musicxml'),'utf8'),xml(true));
 }finally{await rm(directory,{recursive:true,force:true});}
});

test('An evidenced source-mode correction transposes mislabeled A minor to Birdland C minor without rewriting provenance', {skip:!domModule||!converter},async()=>{
 const directory=await mkdtemp(path.join(os.tmpdir(),'birdland-mode-test-'));
 try{
  await mkdir(path.join(directory,'sources'));
  const raw=xml(true).replace('<root-step>C</root-step>','<root-step>A</root-step>').replace('<kind>dominant</kind>','<kind>minor-seventh</kind>')
   .replace('<step>C</step><octave>4</octave>','<step>E</step><octave>5</octave>').replace('<step>E</step><octave>4</octave>','<step>C</step><octave>5</octave>');
  await writeFile(path.join(directory,'sources/summertime.musicxml'),raw);
  const source={path:'sources/summertime.musicxml',sha256:'f626328000000000',url:'https://example.invalid/summertime'};
  await writeFile(path.join(directory,'catalogue.json'),JSON.stringify({entries:['Summertime','Unreviewed mode'].map(title=>({title,status:'verified_musicxml_alternative',source}))}));
  const reference={key:'Cm',bpm:76,beat:'1/4',reference:'Birdland PDF main theme, bar 5'};
  const references=path.join(directory,'references.json');
  await writeFile(references,JSON.stringify({'Summertime':{...reference,source_mode_override:'minor',source_mode_evidence:'Source declares major, but harmony Am7/Bb7/Am7/E7 and melody establish A minor'},'Unreviewed mode':reference}));
  const report=await convert({research:directory,converter,domModule,references});
  assert.equal(report.converted,1);
  const row=report.entries[0];assert.equal(row.source_key.mode,'major','declared XML mode remains unchanged provenance');
  assert.equal(row.effective_source_key.mode,'minor');assert.equal(row.source_mode_override,'minor');assert.ok(row.source_mode_evidence);
  assert.equal(row.transpose_semitones,3);assert.equal(row.abc_key,'Cm');assert.equal(row.abc_tempo,'1/4=76');
  const abc=await readFile(path.join(directory,row.abc_path),'utf8');
  assert.match(abc,/^K:Cm$/m);assert.match(abc,/^Q:1\/4=76$/m);assert.match(abc,/"Cm7\/Bb"g4 e4/);
  assert.equal(report.entries[1].status,'needs_conversion_review','no automatic mode inference is allowed');
  assert.match(report.entries[1].error,/key modes differ/);
  assert.equal(await readFile(path.join(directory,'sources/summertime.musicxml'),'utf8'),raw);
 }finally{await rm(directory,{recursive:true,force:true});}
});
