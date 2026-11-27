import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,mkdir,copyFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'..');
test('missing Birdland key and tempo fall back independently to the actual source fields',async()=>{
 const tmp=await mkdtemp(path.join(tmpdir(),'birdland-fallback-'));
 try{
  const cat=JSON.parse(await readFile(path.join(root,'research/birdland/bulk/catalogue.json'),'utf8'));
  const titles=['A Foggy Day','Desafinado','Have You Met Miss Jones?'];
  const entries=cat.entries.filter(e=>titles.includes(e.title));
  await mkdir(path.join(tmp,'bulk/sources'),{recursive:true});
  for(const e of entries)for(const s of e.sources)await copyFile(path.join(root,'research/birdland/bulk',s.path),path.join(tmp,'bulk',s.path));
  await writeFile(path.join(tmp,'bulk/catalogue.json'),JSON.stringify({entries}));
  await writeFile(path.join(tmp,'leadsheet-patches.json'),'[]');
  await writeFile(path.join(tmp,'refs.json'),JSON.stringify({'Desafinado':{key:'Eb'},'Have You Met Miss Jones?':{beat:'1/4',bpm:180}}));
  const args=[path.join(root,'scripts/extend_birdland_leadsheets.mjs'),'--research',tmp,'--references',path.join(tmp,'refs.json'),'--forge',process.env.FORGE_SOURCE||path.join(root,'../forge')];
  if(process.env.DOM_MODULE)args.push('--dom-module',process.env.DOM_MODULE);
  const child=spawnSync(process.execPath,args,{encoding:'utf8'});assert.equal(child.status,0,child.stderr);
  const rows=JSON.parse(await readFile(path.join(tmp,'leadsheet-patches.json'),'utf8'));
  assert.equal(rows.length,3,child.stdout);
  const foggy=rows.find(e=>e.title==='A Foggy Day');assert.equal(foggy.abc_key,'F');assert.equal(foggy.abc_tempo,'120');assert.deepEqual(foggy.settings_origin,{key:'source',tempo:'source'});
  const desafinado=rows.find(e=>e.title==='Desafinado');assert.equal(desafinado.abc_key,'Eb');assert.equal(desafinado.abc_tempo,'160');assert.deepEqual(desafinado.settings_origin,{key:'birdland',tempo:'source'});
  const jones=rows.find(e=>e.title==='Have You Met Miss Jones?');assert.equal(jones.abc_key,'F');assert.equal(jones.abc_tempo,'1/4=180');assert.deepEqual(jones.settings_origin,{key:'source',tempo:'birdland'});
 }finally{await rm(tmp,{recursive:true,force:true});}
});
