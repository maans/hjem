import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const forge=path.resolve(process.env.FORGE_SOURCE||'work/forge');
const root=path.resolve(import.meta.dirname,'../research/helles');
class Element{
 constructor(n,parent=null){this.localName=n.name;this.nodeName=n.name;this.nodeType=1;this.attrs=n.attrs;this.parentNode=parent;this.children=n.children.map(c=>new Element(c,this));this.childNodes=this.children;this.raw=n;}
 get firstElementChild(){return this.children[0]||null;}
 get nextElementSibling(){const peers=this.parentNode?.children||[];return peers[peers.indexOf(this)+1]||null;}
 get textContent(){return this.raw.text+this.children.map(c=>c.textContent+c.raw.tail).join('');}
 getAttribute(n){return this.attrs[n]??null;}
 getElementsByTagName(n){return this.children.flatMap(c=>[...(c.localName===n?[c]:[]),...c.getElementsByTagName(n)]);}
}
class Parser{parseFromString(raw){let n=JSON.parse(raw);const root=new Element(n);return {documentElement:root,getElementsByTagName:n=>root.getElementsByTagName(n)};}}
const cache={};function load(id){let file=id.split('/').at(-1);if(cache[file])return cache[file];let exp={};cache[file]=exp;vm.runInNewContext(fs.readFileSync(path.join(forge,'plugins/musescore-import/src',file),'utf8'),{exports:exp,require:load,DOMParser:Parser,console});return exp;}
const converter=load('converter.js');
const bundled=JSON.parse(JSON.parse(fs.readFileSync(path.join(forge,'plugins/abc/dist/plugin.json'),'utf8')).text).tiddlers;
let m={exports:{}};vm.runInNewContext(bundled['$:/plugins/huwiki/abc/vendor/abcjs.js'].text,{module:m,exports:m.exports,console});const ABC=m.exports;
let Transpose={};vm.runInNewContext(bundled['$:/plugins/huwiki/abc/transpose.js'].text,{exports:Transpose});
const refs=Object.fromEntries(JSON.parse(fs.readFileSync(path.join(root,'arrangements.json'))).map(r=>[r.title,r]));
const result=[];
for(const input of JSON.parse(fs.readFileSync(path.join(root,'source-manifest.json')))){
 const manifest=path.join(root,'sources',path.parse(input.original).name+'.manifest.json');const e=fs.existsSync(manifest)?JSON.parse(fs.readFileSync(manifest)):input;
 try{
 const raw=fs.readFileSync(path.join(root,'sources',e.xml+'.json'),'utf8');
 const model=converter.decodeScore(raw,e.xml);const staff=model.staves.find(s=>!s.percussion);const voices=staff.voices.map(v=>v.id);
 const rendered=converter.renderABC(model,voices,1,model.totalMeasures,{title:e.title});let abc=rendered.abc;
 const ref=refs[e.title],key=/^K:\s*(\S+)/m.exec(abc)?.[1];
 let target={Desafinado:'F',Wave:'Eb',Bluesette:'Eb','Those Who Were':'G'}[e.title]||key;
 const pc=k=>{let a=/^([A-G])([b#]?)/.exec(k);return ({C:0,D:2,E:4,F:5,G:7,A:9,B:11}[a[1]]+(a[2]==='b'?-1:a[2]==='#'?1:0)+12)%12;};
 const shift=(pc(target)-pc(key)+18)%12-6;
 if(shift)abc=Transpose.apply(ABC,abc,shift).replace(/^K:.*$/m,'K:'+target);
 if(ref)abc=abc.replace(/^Q:.*$/m,'Q:1/4='+ref.tempo);
 let tune=ABC.parseOnly(abc)[0],audio=tune.setUpAudio({chordsOff:true});let notes=audio.tracks.flat().filter(e=>e.cmd==='note');
 const actionableWarnings=(rendered.warnings||[]).filter(w=>!(e.preserve_modulations&&/^Gentagelse i anden toneart fra takt /.test(w)));
 let record={...e,key,target,shift,warnings:Array.from(rendered.warnings||[]),abcWarnings:tune.warnings||[],notes:notes.length,chords:(abc.match(/"[A-G][^"\n]*"/g)||[]).length,abc_source:abc,publish:['Desafinado','Wave','Bluesette','Those Who Were'].includes(e.title)&&!actionableWarnings.length&&!tune.warnings?.length};
 result.push(record);
 }catch(err){result.push({...e,error:String(err.stack)});}
}
fs.writeFileSync(path.join(root,'conversions.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result.map(({abc_source,...r})=>r),null,2));
if(result.filter(r=>r.publish).length!==4)throw Error('Expected four validated playable leadsheets');

