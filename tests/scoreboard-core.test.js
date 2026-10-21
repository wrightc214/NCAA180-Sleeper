const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs');
const C=require('../reports/assets/scoreboard-core.js');
const cfg=JSON.parse(fs.readFileSync('config/league.json'));
const rules={pass_yd:.04,pass_td:4,pass_int:-2,rec:1,rec_yd:.1,rec_td:6,xpmiss:0,yds_allow_550p:-7};
const config={...cfg,standard_scoring:rules};
test('standard corrections: Big Sky DEF and Ohio Valley XP; tiers not double counted',()=>{
 assert.equal(C.score({yds_allow:551,yds_allow_550p:1},rules),-7);
 assert.equal(C.score({xpmiss:1},rules),0);
 assert.equal(C.score({yds_allow:99},{yds_allow_0_100:5}),5);
 assert.equal(C.score({yds_allow:100},{yds_allow_0_100:5,yds_allow_100_199:3}),3);
});
test('game clock, halftime, final, overtime and pregame',()=>{
 assert.equal(C.remaining({state:'pre'}),1);
 assert.equal(C.remaining({state:'in',period:2,clock:'0:00'}),.5);
 assert.equal(C.remaining({state:'in',period:4,clock:'6:00'}),.1);
 assert.equal(C.remaining({state:'post'}),0);
 assert.equal(C.remaining({state:'in',period:5,clock:'8:00'}),0);
});
test('actual always counts in full; residual projection and variance shrink',()=>{
 const p=C.playerModel('1',{name:'QB',positions:['QB'],team:'KC'}, {},{pass_yd:500},{state:'in',period:3,clock:'0:00'},30,config);
 assert.equal(p.actual,30);assert.equal(p.projected,35);assert.equal(p.variance,4);
});
test('multi-position eligibility and flex assignment are exact',()=>{
 const r=C.bestLineup([{id:'dual',positions:['DB','WR'],points:20},{id:'rb',positions:['RB'],points:15},{id:'wr',positions:['WR'],points:10}],['WR','FLEX'],cfg);
 assert.equal(r.total,35);assert.equal(r.ids.length,2);
});
test('unavailable starters, empty slots, team adjustments and final ties',()=>{
 const p=C.playerModel('k',{positions:['K'],status:'Out'}, {},{pass_td:5},{state:'pre'},0,config);
 assert.equal(p.projected,0);assert.equal(p.variance,0);
 const t=C.teamModel({starters:['0','k'],points:2},{k:p});assert.equal(t.actual,2);assert.equal(t.adjustment,2);
 assert.equal(C.probability({projected:100,variance:0},{projected:100,variance:0}),50);
});
test('close pregame bench decisions are retained even when they did not pay off',()=>{
 const s={id:'s',positions:['WR'],projected:20,baseline:15,actual:20};
 const b={id:'b',positions:['WR'],position:'WR',projected:4,baseline:14,actual:4,phase:'post'};
 const r=C.benchPlayers({starters:['s'],players:['s','b']},{s,b},[s],['WR'],cfg,false);
 assert.equal(r.players.length,1);assert.equal(r.players[0].id,'b');assert.equal(r.players[0].close,true);
});
test('real completed-week raw stats reproduce all 12 Big Sky team scores in fixture',()=>{
 const d=JSON.parse(fs.readFileSync('tests/fixtures/scoreboard-week06.json'));
 for(const r of d.rosters) {
  const total=C.round(r.starters.reduce((sum,id)=>sum+C.score(d.stats[id],d.scoring),0));
  assert.equal(total,r.points,`roster ${r.roster_id}`);
 }
});
