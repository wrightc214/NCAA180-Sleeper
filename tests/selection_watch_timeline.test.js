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
