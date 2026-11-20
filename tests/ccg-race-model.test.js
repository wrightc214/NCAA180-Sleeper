/* Run with node tests/ccg-race-model.test.js */
'use strict';
const assert=require('node:assert/strict');
const M=require('../reports/assets/ccg-race-model.js');
const base=id=>({roster_id:id,team:id,wins:8,losses:2,ties:0,points_for:1000,
  points_against:1000,remaining_games:[{week:11,opponent_roster_id:id==='1'?'3':'4'}]});
const conf={league_id:'test',divisions:[{name:'South',clinched_before_week:false,
  contenders:[base('1'),base('2')]}]};
const cfg={sims:20000,seed:2026,order:['win_pct','points_for','points_against','coin_toss']};
const models=(a,b,variance=100,final=false)=>({
  'test|1':{mean:a,variance,final},'test|2':{mean:b,variance,final},
  'test|3':{mean:0,variance:0,final},'test|4':{mean:0,variance:0,final}
});
const strong=M.simulate(conf,models(200,120,4),cfg);
assert.ok(strong.odds['1']>99,'high-scoring contender should lead >99%');
const even=M.simulate(conf,models(150,150,400),cfg);
assert.ok(Math.abs(even.odds['1']-50)<=2,'equal projections within ±2%');
assert.deepEqual(even,M.simulate(conf,models(150,150,400),cfg),'fixed seed must be reproducible');
const final=M.simulate(conf,models(180,120,0,true),cfg);
assert.equal(final.odds['1'],100);assert.equal(final.odds['2'],0);
assert.equal(final.divisions[0].proven,'1');
const toss=M.simulate(conf,models(100,100,0,true),cfg);
assert.equal(toss.odds['1'],50);assert.equal(toss.odds['2'],50);
assert.equal(toss.divisions[0].proven,null,'unresolved coin toss is not clinched');
// Ties are decided to the hundredth, not by exact floating-point coincidence.
const hundredth=M.simulate(conf,models(100.004,100.003,0,true),cfg);
assert.equal(hundredth.odds['1'],50);assert.equal(hundredth.odds['2'],50);
console.log('CCG race model tests passed');
