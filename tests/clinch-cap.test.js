/* Task 5.15: run with node tests/clinch-cap.test.js
 * Same fixture as tests/test_clinch_cap.py: the browser proof must match Python case by case. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const M=require('../reports/assets/ccg-race-model.js');
const fx=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures','clinch-cap-cases.json'),'utf8'));

// Cap curve examples (Chris, 2026-11-23).
assert.equal(M.pointsCap(660,11,0.45,18),297);
assert.equal(M.pointsCap(20,2,0.45,18),36);
assert.equal(M.pointsCap(1,1,0.45,18),18);
assert.equal(M.pointsCap(0,0,0.45,18),0);
assert.equal(M.weekCap(11,0.45,18),297);

function runCase(c){
  const teams=Object.fromEntries(Object.entries(fx.teams).map(([k,v])=>[k,{...v,...(c.teams||{})[k]}]));
  const games=c.games||fx.games, live=c.live||{};
  const opp={};
  for(const [a,b] of games){(opp[a]=opp[a]||[]).push(b);(opp[b]=opp[b]||[]).push(a);}
  const conf={league_id:'T',divisions:[{name:'D',clinched_before_week:false,contenders:
    Object.keys(teams).filter(k=>teams[k].div==='D').map(k=>({roster_id:k,team:k,wins:teams[k].wins,
      losses:teams[k].losses,ties:0,points_for:teams[k].pf,points_against:1000,
      remaining_games:(opp[k]||[]).map(o=>({week:fx.week,opponent_roster_id:o}))}))}]};
  const models={};
  for(const k of Object.keys(teams)){
    const l=live[k]||{},actual=l.actual||0,final=!!l.final;
    models['T|'+k]={mean:final?actual:actual+100,variance:final?0:400,actual,final,
      minutes_left:l.minutes??60*fx.slots,players_left:l.players??fx.slots};
  }
  const r=M.simulate(conf,models,{sims:2000,seed:1,order:['win_pct','points_for','points_against','coin_toss'],
    clinch:{rate:c.rate,burst:c.burst,slots:fx.slots,week:fx.week}});
  const d=r.divisions[0];
  return {clinched:d.proven,out:[...d.out].sort()};
}
for(const c of fx.cases)assert.deepEqual(runCase(c),c.expect,c.name);
console.log('Clinch cap tests passed ('+fx.cases.length+' shared cases)');
