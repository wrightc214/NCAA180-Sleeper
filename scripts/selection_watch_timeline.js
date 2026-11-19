/* Persist the first completed, verified Selection Watch result per checkpoint. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const C=require('../reports/assets/scoreboard-core.js');
const S=require('../reports/assets/scoreboard-overview-model.js');
const W=require('../reports/assets/selection-watch-core.js');
const Games=require('../reports/assets/selection-watch-games.js');
const read=(p,fallback)=>{try{return JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));}catch(e){if(e.code==='ENOENT'&&fallback!==undefined)return fallback;throw e;}};
const active=(windows,points,now)=>windows.find(w=>now>=Date.parse(w.opens)&&now<Date.parse(w.closes)&&!Object.hasOwn(points,w.id));
const windowComplete=(events,w)=>{
  const through=Date.parse(w.through);
  if(!Number.isFinite(through)||events.some(event=>!Number.isFinite(Date.parse(event.date))))return false;
  const games=events.filter(event=>Date.parse(event.date)<through);
  return games.length>0&&games.every(event=>event.status?.type?.state==='post'&&event.status.type.completed===true);
};
async function main(){
  const settings=read('config/selection_watch.json',{});
  const windows=settings.timeline?.windows||[], now=Date.now();
  if(!active(windows,{},now))return;
  const board=read('reports/postseason/selection-watch.json',null);
  if(!board || board.year!==Number(new Date(now).toISOString().slice(0,4)) || board.provisional || !board.ccg?.length)return;
  const nav=read('config/nav.json');
  if(nav.tabs?.find(t=>t.id==='selection-watch')?.state==='hidden')return;
  const out='reports/postseason/selection-watch-timeline-'+board.year+'.json', points=read(out,{});
  const checkpoint=active(windows,points,now);
  if(!checkpoint)return;
  const league=read('config/league.json'), dir='data/scoreboard';
  const index=read(dir+'/index.json');
  const metadata=read(dir+'/'+board.year+'/players.json');
  const get=async url=>{
    if(url.startsWith(league.data.scoreboard+'/'))return read(dir+url.slice(league.data.scoreboard.length));
    const result=await fetch(url,{signal:AbortSignal.timeout(15000)});
    if(!result.ok)throw Error('Games input returned '+result.status);
    return result.json();
  };
  const {scores,events}=await Games.load(board,league,index,metadata,{get,C,S});
  if(!windowComplete(events,checkpoint))return;
  if(checkpoint.id==='final'&&!board.ccg.every(g=>scores[g.id].final))return;
  const p=Object.fromEntries(Object.entries(scores).map(([id,s])=>[id,s.pA]));
  const odds=W.odds(board,p);
  const byTeam=Object.fromEntries(board.order.map(t=>[t.team,Math.round((odds[t.k]||0)*1000)/10]));
  points[checkpoint.id]={recorded_at:new Date().toISOString(),odds:byTeam};
  fs.writeFileSync(path.join(root,out),JSON.stringify(points)+'\n');
  console.log('Captured Selection Watch '+checkpoint.label);
}
if(require.main===module)main().catch(error=>{console.error(error.message);process.exitCode=1;});
module.exports={active,windowComplete};
