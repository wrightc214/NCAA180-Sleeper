const test=require('node:test'), assert=require('node:assert/strict');
const {active,windowComplete}=require('../scripts/selection_watch_timeline.js');
test('timeline never duplicates, backfills, or saves an unfinished window',()=>{
  const w={id:'early',opens:'2026-11-29T16:00:00-05:00',closes:'2026-11-29T17:00:00-05:00',through:'2026-11-29T16:00:00-05:00'};
  assert.equal(active([w],{},Date.parse(w.closes)),undefined);
  assert.equal(active([w],{early:{}},Date.parse(w.opens)),undefined);
  assert.equal(active([w],{},Date.parse(w.opens)).id,'early');
  const game={date:'2026-11-29T13:00:00-05:00',status:{type:{state:'in',completed:false}}};
  const late={...game,date:'2026-11-29T16:05:00-05:00'};
  assert.equal(windowComplete([game,late],w),false);
  assert.equal(windowComplete([{...game,status:{type:{state:'post',completed:true}}},late],w),true);
});

const fs=require('node:fs'), os=require('node:os'), path=require('node:path');
const {main}=require('../scripts/selection_watch_timeline.js');

function fixture(t){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'selection-watch-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  function write(name,value){
    fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});
    fs.writeFileSync(path.join(root,name),JSON.stringify(value));
  }
  const w={id:'early',label:'Sun Early',opens:'2026-11-29T16:00:00-05:00',closes:'2026-11-29T17:00:00-05:00',through:'2026-11-29T16:00:00-05:00'};
  write('config/selection_watch.json',{timeline:{windows:[w]}});
  write('config/nav.json',{tabs:[]});
  write('config/league.json',{data:{scoreboard:'../data/scoreboard'}});
  write('data/scoreboard/index.json',{});
  write('data/scoreboard/2026/players.json',{});
  write('reports/postseason/selection-watch.json',{year:2026,field_size:2,
    order:['Alpha','Beta','Delta'].map((team,i)=>({k:team,team,rank:i+1})),ccg:[{id:'g',a:'Alpha',b:'Delta'}]});
  const complete={date:'2026-11-29T13:00:00-05:00',status:{type:{state:'post',completed:true}}};
  return {root,w,complete,recoveryDir:path.join(root,'recovery'),
    out:path.join(root,'reports/postseason/selection-watch-timeline-2026.json')};
}
test('a verified recording persists once and retains the exact timestamp and odds for recovery',async t=>{
  const {root,w,complete,recoveryDir,out}=fixture(t);
  const clock=()=>Date.parse(w.opens)+120000;
  let reads=0;
  const load=async()=>{reads++;return {events:[complete],scores:{g:{pA:.6}}};};
  const opts={root,clock,load,recoveryDir};
  await main(opts);
  const first=fs.readFileSync(out,'utf8'), point=JSON.parse(first).early;
  assert.deepEqual(point,{recorded_at:new Date(clock()).toISOString(),odds:{Alpha:100,Beta:60,Delta:40}});
  const recovery=JSON.parse(fs.readFileSync(path.join(recoveryDir,'selection-watch-2026-early.json')));
  assert.deepEqual(recovery,{year:2026,checkpoint:'early',point});
  await main(opts);
  assert.equal(reads,1);
  assert.equal(fs.readFileSync(out,'utf8'),first);
});
test('unfinished, invalid, missing, or out-of-window data never writes a point',async t=>{
  const {root,w,complete,recoveryDir,out}=fixture(t);
  for(const result of [
    {events:[{...complete,status:{type:{state:'in',completed:false}}}],scores:{g:{pA:.6}}},
    {events:[complete],scores:{}},
    {events:[complete],scores:{g:{pA:null}}},
    {events:[complete],scores:{g:{pA:1.2}}},
    {events:[{...complete,date:'invalid'}],scores:{g:{pA:.6}}},
  ])await main({root,recoveryDir,clock:()=>Date.parse(w.opens),load:async()=>result});
  let ticks=0;
  await main({root,recoveryDir,clock:()=>Date.parse(ticks++?w.closes:w.opens),
    load:async()=>({events:[complete],scores:{g:{pA:.6}}})});
  assert.equal(fs.existsSync(out),false);
  assert.equal(fs.existsSync(recoveryDir),false);
});
