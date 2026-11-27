import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..'),forge=path.resolve(process.env.FORGE_SOURCE||path.join(root,'.forge-source'));
const {assembleHtml}=await import(pathToFileURL(path.join(forge,'assembler/assemble.mjs')));
const tiddlers=JSON.parse(fs.readFileSync(path.join(root,'research/helles/tiddlers.json'),'utf8'));
const html=assembleHtml(fs.readFileSync(path.join(forge,'core/empty.html'),'utf8'),tiddlers)
 .replace(/^(<!-- saved from url=[^\r\n]*?-->)[ \t\r]+$/gm,'$1');
fs.writeFileSync(path.join(root,'wiki/helles/index.html'),html);
console.log('Assembled Helles wiki with '+tiddlers.length+' tiddlers');
