const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs');
const S=require('../reports/assets/scoreboard-overview-model.js');
const cfg=JSON.parse(fs.readFileSync('config/league.json'));
const scoring={pass_yd:.04,pass_td:4,pass_int:-2};
const baseline={scoring,projections:{p:{pass_yd:250,pass_td:2}},player_info:{},odds:[{LeagueID:'l',RosterID:'1',OpponentRosterID:'2',WinPct:'37'}]};
const metadata={p:{name:'Player',position:'QB',positions:['QB'],team:'KC',status:''}};
function rosters(){return [1,2].map((id,i)=>({leagueId:'l',roster_id:id,starters:['p'],players_points:{p:i?10:20},points:i?10:20}));}
test('final cards retain Tuesday probability including original underdog wins and reversed sides',()=>{
 const result=S.summarize(rosters(),metadata,baseline,{KC:{state:'post'}},{p:{pass_yd:250}},scoring,cfg);
 assert.equal(result.final,true);assert.equal(result.oddsLabel,'Pregame %');assert.equal(result.probability,37);
 assert.equal(S.summarize(rosters().reverse(),metadata,baseline,{KC:{state:'post'}},{p:{}},scoring,cfg).probability,63);
});
test('live probabilities use shared player model and hide estimates on missing stats',()=>{
 const games={KC:{state:'in',period:3,clock:'15:00'}};
 const result=S.summarize(rosters(),metadata,baseline,games,{p:{pass_yd:250}},scoring,cfg);
 assert.equal(result.final,false);assert.equal(result.oddsLabel,'Live win %');assert.ok(result.probability>50);
 const missing=S.summarize(rosters(),metadata,baseline,games,{},scoring,cfg);
 assert.equal(missing.probability,null);assert.equal(missing.incomplete,true);
});
test('pregame uses baseline odds and unknown statuses cannot become final',()=>{
 const result=S.summarize(rosters().map(r=>({...r,points:0,players_points:{}})),metadata,baseline,{KC:{state:'pre',kickoff:'2026-10-25T17:00Z'}},{},scoring,cfg);
 assert.equal(result.status,'Upcoming');assert.equal(result.probability,37);
 const unknown=S.summarize(rosters(),{},baseline,{}, {},scoring,cfg);
 assert.equal(unknown.final,false);assert.equal(unknown.probability,null);
});
test('frozen odds must match both roster slots, not merely one team',()=>{
 const rs=rosters();rs[1].roster_id=3;
 assert.equal(S.summarize(rs,metadata,baseline,{KC:{state:'post'}},{p:{}},scoring,cfg).probability,null);
});
