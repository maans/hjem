/** Acceptance test against the actual assembled Birdland wikis in CI Chromium. */
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const root=path.resolve(import.meta.dirname,'..'),artifacts='/tmp/repertoire-navigation-artifacts';
await mkdir(artifacts,{recursive:true});
const server=spawn('python3',['-m','http.server','8765','--bind','127.0.0.1'],{cwd:root,stdio:'ignore'});
for(let i=0;i<50;i++){try{if((await fetch('http://127.0.0.1:8765/')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
const errors=[],checked=[];
let page;
try{
 const context=await browser.newContext({viewport:{width:1280,height:900},hasTouch:true});
 // The local wiki, PDF.js and chart originals are allowed. Sound downloads
 // are irrelevant to control visibility; MIDI generation is tested separately.
 await context.route('**/*',route=>{const url=route.request().url();return /^(?:http:\/\/127\.0\.0\.1:8765\/|https:\/\/xn--mns-ula\.dk\/wiki\/)/.test(url)?route.continue():route.abort();});
 page=await context.newPage();page.setDefaultTimeout(60000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/wiki/birdland/guitar/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.$tw&&$tw.wiki&&$tw.rootWidget);
 async function localReferences(){
  // The real reader deliberately requires same-origin PDFs. Point fixture
  // addresses at this checkout, preserving that protection in the test.
  await page.evaluate(()=>{
   const origin=location.origin,production='https://xn--mns-ula.dk';
   for(const title of $tw.wiki.allTitles()){
    const t=$tw.wiki.getTiddler(title),updates={};
    for(const key of ['repertoire-pdf','repertoire-guitar-pdf','repertoire-score-pdf'])if(String(t.fields[key]||'').startsWith(production+'/'))updates[key]=origin+t.fields[key].slice(production.length);
    if(title==='$:/config/maans/repertoire/pdf-viewer'&&String(t.fields.text||'').startsWith(production+'/'))updates.text=origin+t.fields.text.slice(production.length);
    if(Object.keys(updates).length)$tw.wiki.addTiddler(new $tw.Tiddler(t,updates));
   }
  });
 }
 await localReferences();
 async function open(title){
  await page.evaluate(title=>$tw.wiki.addTiddler(new $tw.Tiddler({title:'$:/StoryList',list:[title]})),title);
  await page.waitForFunction(title=>{
   const books=document.querySelectorAll('.huwrep-book');
   return books.length===1&&books[0].closest('.tc-tiddler-frame')?.getAttribute('data-tiddler-title')===title;
  },title);
 }
 const leads=await page.evaluate(()=>$tw.wiki.allTitles().filter(title=>$tw.wiki.getTiddler(title).fields['repertoire-abc-label']==='Leadsheet (ABC)'));
 assert.equal(leads.length,34);
 for(const title of leads){
  await open(title);
  await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});
  await page.locator('.huwrep-book-stage .huwabc-page svg').first().waitFor({state:'visible'});
  assert.equal(await page.locator('.huwrep-book').count(),1,title+': one book');
  assert.equal(await page.locator('.abcjs-midi-start').count(),1,title+': one actual transport');
  assert.equal(await page.locator('.huwabc-reader-active').count(),0,title+': no nested immersive reader');
  checked.push(title);
 }
 await open('All of Me · Leadsheet');
 await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});
 await page.getByRole('button',{name:'Lyd og akkompagnement',exact:true}).click();
 const style=page.locator('.huwrep-style-choice select');await style.waitFor({state:'visible'});await style.selectOption('bossa');
 await page.waitForFunction(()=>JSON.parse($tw.wiki.getTiddler('All of Me · Leadsheet').fields['abc-accompaniment']).style==='bossa');
 await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});assert.equal(await page.locator('.abcjs-midi-start').count(),1);
 await page.getByRole('button',{name:'Lyd og akkompagnement',exact:true}).click();
 assert.equal(await page.locator('.huwrep-performance .abcjs-midi-start').isVisible(),true,'closing sound settings leaves playback visible');
 await page.locator('.huwrep-book-fullscreen-button').click();
 assert.equal(await page.locator('.huwrep-book-fullscreen').count(),1);
 await page.screenshot({path:path.join(artifacts,'leadsheet-desktop.png'),fullPage:false});
 await page.locator('.huwrep-book-source').selectOption('guitar');
 await page.locator('.huwrep-book-pdf-frame').waitFor({state:'visible'});
 await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});
 assert.equal(await page.locator('.huwrep-book-fullscreen').count(),1,'PDF switch preserves fullscreen');
 assert.match(await page.locator('.huwrep-audio-source').textContent(),/Leadsheet.*PDF-siderne følger ikke afspilningen/);
 await page.locator('.huwrep-book-source').selectOption('leadsheet');
 await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});
 assert.equal(await page.locator('.huwrep-book-fullscreen').count(),1,'ABC switch preserves fullscreen');
 await page.setViewportSize({width:1024,height:768});await page.screenshot({path:path.join(artifacts,'leadsheet-tablet.png'),fullPage:false});
 for(const title of ['Easy Money','I Left My Heart in San Francisco','The Legend','The Wiggle Walk']){
  await open(title);await page.locator('.huwrep-book-pdf-frame').waitFor({state:'visible'});
  await page.locator('.huwrep-performance .abcjs-midi-start').waitFor({state:'visible'});
  assert.equal(await page.locator('.huwrep-book').count(),1);assert.equal(await page.locator('.abcjs-midi-start').count(),1);assert.match(await page.locator('.huwrep-audio-source').textContent(),/Guitar.*chord stabs/);
 }
 await open('Four Brothers');await page.locator('.huwrep-book-pdf-frame').waitFor({state:'visible'});
 assert.equal(await page.getByRole('button',{name:'Afspil',exact:true}).isDisabled(),true,'PDF without ABC explains unavailable audio');
 await page.evaluate(()=>$tw.wiki.addTiddler(new $tw.Tiddler({title:'$:/StoryList',list:['HUWiki Repertoire – Start']})));
 await page.getByRole('button',{name:'Numre',exact:true}).click();
 await page.getByRole('searchbox',{name:'Søg efter et nummer'}).fill('The Legend');
 const before=await page.evaluate(()=>$tw.wiki.allTitles().filter(t=>$tw.wiki.getTiddler(t).fields['repertoire-kind']==='setlist').map(t=>[t,$tw.wiki.getTiddler(t).fields.list]));
 await page.locator('.huwrep-library-song').filter({hasText:'The Legend'}).click();await page.locator('.huwrep-book').waitFor();
 const after=await page.evaluate(()=>$tw.wiki.allTitles().filter(t=>$tw.wiki.getTiddler(t).fields['repertoire-kind']==='setlist').map(t=>[t,$tw.wiki.getTiddler(t).fields.list]));
 assert.deepEqual(after,before,'reading from the library cannot add/remove/reorder setlist entries');
 assert.equal(await page.locator('.huwrep-book').count(),1);
 await page.goto('http://127.0.0.1:8765/wiki/birdland/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.$tw&&$tw.wiki&&$tw.rootWidget);
 await localReferences();
 const fullScore=await page.evaluate(()=>$tw.wiki.allTitles().find(t=>$tw.wiki.getTiddler(t).fields['repertoire-kind']==='piece'&&$tw.wiki.getTiddler(t).fields['repertoire-score-pdf']));
 assert.ok(fullScore,'orchestra library has a full score for the conductor');await open(fullScore);await page.locator('.huwrep-book-pdf-frame').waitFor({state:'visible'});
 assert.deepEqual(errors,[],'no unhandled browser errors');
 await writeFile(path.join(artifacts,'report.json'),JSON.stringify({leadsheets:checked.length,guitarParts:4,widths:[1280,1024],checks:['one shared reader','permanent transport','sound style change','PDF audio provenance','source switch keeps fullscreen','PDF-only explanation','library click preserves setlists'],errors},null,2));
 console.log('Browser acceptance passed for '+checked.length+' leadsheets and four guitar arrangements.');
}catch(error){
 if(page){await page.screenshot({path:path.join(artifacts,'failure.png'),fullPage:false}).catch(()=>{});await writeFile(path.join(artifacts,'failure.json'),JSON.stringify({error:error.message,checked,errors,books:await page.locator('.huwrep-book').evaluateAll(nodes=>nodes.map(n=>({title:n.closest('.tc-tiddler-frame')?.getAttribute('data-tiddler-title'),text:n.textContent.slice(0,900)}))).catch(()=>[])},null,2));}
 throw error;
}finally{await browser.close();server.kill();}
