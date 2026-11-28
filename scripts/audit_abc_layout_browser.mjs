import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {assembleHtml} from '../.forge-source/assembler/assemble.mjs';
import {chromium} from 'playwright-core';
const rows=JSON.parse(await readFile('abc-layout-inventory.json','utf8'));
const plugin=JSON.parse(await readFile('.forge-source/plugins/abc/dist/plugin.json','utf8'));
await writeFile('abc-layout-test.html',assembleHtml(await readFile('.forge-source/core/empty.html','utf8'),[plugin,{title:'$:/DefaultTiddlers',text:'Audit'},{title:'Audit',text:'Notation layout audit'}]));
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage({viewport:{width:1180,height:1050}});
 await page.goto(pathToFileURL(process.cwd()+'/abc-layout-test.html').href);
 await page.getByText('Notation layout audit',{exact:true}).waitFor();
 const report=await page.evaluate(rows=>{
  const ABC=$tw.modules.execute('$:/plugins/huwiki/abc/vendor/abcjs.js');
  const sheet=$tw.modules.execute('$:/plugins/huwiki/abc/sheet-layout.js'),balance=$tw.modules.execute('$:/plugins/huwiki/abc/balanced-layout.js');
  const audio=t=>(t.setUpAudio({chordsOff:true}).tracks||[]).map(t=>t.filter(e=>e.cmd==='note').map(e=>[Math.round(e.start*1e7),Math.round(e.duration*1e7),e.pitch,e.instrument]).sort((a,b)=>a[0]-b[0]||a[2]-b[2]||a[1]-b[1]));
  const results=[];
  for(const row of rows){
   const source=row.fields['abc-source']||row.fields.text;
   const result={wiki:row.wiki,title:row.title,mode:row.mode,modes:[]};
   if(row.title==='Majčin čoček · Hm-greb · capo I'){
    const view=$tw.modules.execute('$:/plugins/huwiki/abc/instrument-view.js'),tabs=$tw.modules.execute('$:/plugins/huwiki/abc/tabs.js');
    view.change('eb');view.setCapo(3);view.setTranspose(2);view.setTab('mandolin');
    const host=document.createElement('div');document.body.appendChild(host);
    try{
     const t=tabs.view(row.fields),tabOptions=tabs.options(ABC,source,t.enabled,t.config);
     const tune=ABC.renderAbc(host,source,{staffwidth:720,oneSvgPerLine:true,visualTranspose:view.current().semitones,tablature:tabOptions.options,...sheet.options(ABC,source,row.fields),afterParsing:tune=>{
      sheet.prepare(tune,row.fields,source);tabs.notation.project(ABC,tune,t.config,t.enabled);
      tune.tablatures=ABC.parseOnly(source,{visualTranspose:view.current().semitones,tablature:tabOptions.options})[0].tablatures;
     }})[0];tabs.finish(tune,t.config);result.tabDiagnostic={ok:true};
    }catch(error){result.tabDiagnostic={ok:false,stack:error.stack};}
    finally{host.remove();view.change('c');view.setCapo(0);view.setTranspose(0);view.setTab('off');}
   }
   try{
    const before=JSON.stringify(audio(ABC.parseOnly(source)[0]));
    for(const strategy of ['existing','noParts','balanced']){
     const automatic=strategy==='balanced';
     const fields={...row.fields,...(strategy==='noParts'?{'abc-parts-new-line':'no'}:automatic?{'abc-bars-per-line':'balanced','abc-parts-new-line':'no'}:{})};
     for(const transpose of [0,2,9]){
      const host=document.createElement('div');host.style.width='900px';document.body.appendChild(host);
      try{
       const options=sheet.options(ABC,source,fields);
       const tune=ABC.renderAbc(host,source,{staffwidth:720,oneSvgPerLine:true,add_classes:true,expandToWidest:true,jazzchords:true,format:{stretchlast:true,gchordfont:'Helvetica 18 bold'},wrap:{minSpacing:1.5,maxSpacing:2.8,preferredMeasuresPerLine:3},...options,visualTranspose:transpose,afterParsing:t=>sheet.prepare(t,fields,source)})[0];
       const systems=tune.lines.filter(l=>l.staff).map(l=>balance.measures(l.staff[0].voices[0],false).length).filter(Boolean);
       result.modes.push({strategy,automatic,transpose,systems,measured:!!options.lineBreaks,audioUnchanged:transpose===0?before===JSON.stringify(audio(tune)):true});
      }finally{host.remove();}
     }
    }
   }catch(error){result.error=error.message;}
   results.push(result);
  }
  return results;
 },rows);
 await writeFile('abc-layout-measured.json',JSON.stringify(report,null,2)+'\n');
 for(const r of report)console.log(JSON.stringify(r));
 assert.equal(report.filter(r=>r.error).length,0,'all scores must render');
 assert.ok(report.every(r=>r.modes.filter(m=>m.automatic).every(m=>m.audioUnchanged)),'layout must preserve audio');
 console.log('MEASURED_LAYOUT_SCORES='+report.length);
}finally{await browser.close();}
