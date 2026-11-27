import {readFile,readdir} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';

let checked=0,collections=0,fallbacks=0;
const files=process.argv.length>2?process.argv.slice(2):(await readdir('wiki',{recursive:true})).filter(p=>p==='index.html'||p.endsWith('/index.html')).map(p=>'wiki/'+p);
for(const file of files){
 const html=await readFile(file,'utf8'),rows=[];
 for(const m of html.matchAll(/<script\b[^>]*class=["'][^"']*\btiddlywiki-tiddler-store\b[^"']*["'][^>]*>([\s\S]*?)<\/script>/g))rows.push(...JSON.parse(m[1]));
 const index=new Map(rows.map(r=>[r.title,{fields:r}])),pkg=index.get('$:/plugins/huwiki/repertoire');if(!pkg)continue;
 const model={},module=JSON.parse(pkg.fields.text).tiddlers['$:/plugins/huwiki/repertoire/model.js'];
 const $tw={Tiddler:class{constructor(fields){this.fields=fields;}},utils:{}};
 runInNewContext(module.text,{exports:model,$tw});
 const wiki={getTiddler:t=>index.get(t),allTitles:()=>[...index.keys()],getTiddlerText:(t,f='')=>index.get(t)?.fields.text??f,
  getTiddlerList:(t,field='list')=>{const value=index.get(t)?.fields[field];return Array.isArray(value)?value:Array.from(String(value||'').matchAll(/\[\[([^\]]+)\]\]|([^\s]+)/g),m=>m[1]||m[2]);}};
 for(const row of rows){
  if(!['setlist','orchestra'].includes(row['repertoire-kind']))continue;
  collections++;
  for(const item of model.entries(wiki,row.title)){
   const available=model.availableViews(wiki,item).filter(v=>v.role!=='youtube');
   const view=model.presentation(wiki,row.title,item);
   if(!available.length||view.role==='youtube')continue;
   if(view.missing||!view.abc&&!view.pdf)throw Error(`${file}: ${row.title}: existing notation hidden for ${item}`);
   checked++;if(view.fallbackFrom)fallbacks++;
  }
 }
}
if(!checked)throw Error('No real repertoire entries checked');
console.log(JSON.stringify({wikiFiles:files.length,collections,existingNotationViews:checked,automaticFallbacks:fallbacks}));
