/* Proven calls on live pages (Chris, 2026-11-23; config live_bounds). Run: node tests/live-bounds.test.js
 * ScoreboardCore.bounds / decided, CCG race Clinched / Out, Guillotine Safe / Cut. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const C=require('../reports/assets/scoreboard-core.js');
const M=require('../reports/assets/ccg-race-model.js');
const G=require('../reports/assets/guillotine-model.js');
const lb=JSON.parse(fs.readFileSync(path.join(__dirname,'..','config','league.json'),'utf8')).live_bounds;

assert.deepEqual([lb.team_upside,lb.burst,lb.max_drop],[100,18,11.01]);
assert.deepEqual(lb.player_upside,{QB:40,RB:40,WR:45,TE:35,K:20,DEF:30});

// A starter: phase pre / in / post / bye / out, minutes left, Tuesday projection (baseline).
const P=(position,phase,minutes,baseline,id)=>({id:id||position+Math.random(),position,phase,minutes,baseline});
const done=n=>Array.from({length:n},(_,i)=>P('WR','post',0,10,'d'+i));
const team=(actual,starters)=>({actual,starters});
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);

// Josh Allen (proj 25) with 60 minutes left, everyone else done: 25 + max(100*60/660, 40, 18) = 65.
let b=C.bounds(team(100,[...done(10),P('QB','pre',60,25)]),lb);
near(b.ceil,165);near(b.floor,100-11.01);
// A kicker (proj 8) with 60 minutes left: 8 + max(9.09, 20, 18) = 28.
b=C.bounds(team(100,[...done(10),P('K','pre',60,8)]),lb);
near(b.ceil,128);
// A full lineup projecting 130 at kickoff: 130 + max(100, 45, 18) = 230.
const full=[P('QB','pre',60,20),P('RB','pre',60,12),P('RB','pre',60,12),P('WR','pre',60,13),P('WR','pre',60,13),P('WR','pre',60,12),
  P('TE','pre',60,8),P('WR','pre',60,10),P('RB','pre',60,10),P('K','pre',60,8),P('DEF','pre',60,12)];
b=C.bounds(team(0,full),lb);
near(b.ceil,130+100);near(b.floor,-11.01);
// Half a game left for a WR projected 16: 8 + max(100*30/660, 45*.5, 18) = 30.5.
b=C.bounds(team(50,[...done(10),P('WR','in',30,16)]),lb);
near(b.ceil,50+8+22.5);
// Overtime: live at 0 minutes still counts as a player to play (burst 18 + drop).
b=C.bounds(team(50,[...done(10),P('RB','in',0,15)]),lb);
near(b.ceil,68);near(b.floor,50-11.01);
// Nobody left: floor = ceiling = points so far. No game data counts a full game.
b=C.bounds(team(80,done(11)),lb);near(b.ceil,80);near(b.floor,80);
b=C.bounds(team(80,[...done(10),P('TE','unknown',0,6)]),lb);near(b.ceil,80+6+35);
// Empty slot ('0') is ignored. No live_bounds = no call.
b=C.bounds(team(80,[...done(10),{id:'0',phase:'out',minutes:0,baseline:0}]),lb);near(b.ceil,80);
assert.equal(C.bounds(team(80,done(11)),undefined),null);

// decided(): Chris's game -- up ~135, both with one starter (60 minutes) left.
const asu=team(250,[...done(10),P('WR','pre',60,14)]),cal=team(115,[...done(10),P('WR','pre',60,14)]);
assert.equal(C.decided(asu,cal,lb),'a');assert.equal(C.decided(cal,asu,lb),'b');
// Leader 1 point up with its kicker still to play, trailer done: open (one negative could flip it).
assert.equal(C.decided(team(101,[...done(10),P('K','pre',60,8)]),team(100,done(11)),lb),null);
assert.equal(C.decided(team(101,done(11)),team(100,done(11)),lb),'a');
// Josh Allen still to play, trailing by 60: not decided (he can add up to 65).
assert.equal(C.decided(team(160,done(11)),team(100,[...done(10),P('QB','pre',60,25)]),lb),null);
assert.equal(C.decided(team(160,done(11)),team(100,[...done(10),P('K','pre',60,8)]),lb),'a');
assert.equal(C.decided(asu,cal,undefined),null);

// CCG race: Clinched / Out from the same bounds. Division D (A, B, C) vs opponents X, Y, Z, week 11.
function race(pf,live,{bounds=true,games=[['A','X'],['B','Y'],['C','Z']]}={}){
  const wins={A:8,B:7,C:7,X:0,Y:0,Z:0},opp={};
  for(const [a,c] of games){(opp[a]=opp[a]||[]).push(c);(opp[c]=opp[c]||[]).push(a);}
  const conf={league_id:'T',divisions:[{name:'D',clinched_before_week:false,contenders:['A','B','C'].map(k=>({roster_id:k,team:k,
    wins:wins[k],losses:10-wins[k],ties:0,points_for:pf[k]??1000,points_against:1000,
    remaining_games:(opp[k]||[]).map(o=>({week:11,opponent_roster_id:o}))}))}]};
  const models={};
  for(const k of Object.keys(wins)){
    const l=live[k]||{},actual=l.actual||0,final=!!l.final;
    // bounds from ScoreboardCore, as ccg-race.js builds them
    const m=team(actual,final?done(11):[...done(10),P(l.pos||'WR',l.phase||'pre',l.minutes??60,l.proj??14)]);
    const bd=C.bounds(m,lb);
    models['T|'+k]={mean:final?actual:actual+(l.proj??14),variance:final?0:100,actual,final,
      ...(bd?{upside:bd.ceil-actual,drop:actual-bd.floor}:{})};
  }
  const r=M.simulate(conf,models,{sims:2000,seed:1,order:['win_pct','points_for','points_against','coin_toss'],bounds,week:11});
  return {clinched:r.divisions[0].proven,out:[...r.divisions[0].out].sort()};
}
const allFinal={A:{actual:90,final:true},X:{actual:120,final:true},B:{actual:110,final:true},Y:{actual:90,final:true},C:{actual:50,final:true},Z:{actual:60,final:true}};
// A lost (8-3, PF 1390), B won (8-3, PF 1300+110): B wins the points tie -> B clinched.
assert.deepEqual(race({A:1300,B:1300,C:1000},allFinal),{clinched:'B',out:['A','C']});
// One starter left each (60 minutes, WR proj 14): ceiling +59, floor -11.01. A leads B by 150 on points:
// if A loses and B wins (tie at 8), A's floor 1650+20-11.01 beats B's ceiling 1500+20+59 -> A clinched.
const oneLeft={A:{actual:20},X:{actual:20},B:{actual:20},Y:{actual:20},C:{actual:20},Z:{actual:20}};
assert.deepEqual(race({A:1650,B:1500,C:1400},oneLeft),{clinched:'A',out:['B','C']});
// Same with a 60-point gap: B's ceiling (+59) and A's drop (-11.01) keep it open.
assert.deepEqual(race({A:1560,B:1500,C:1000},oneLeft).clinched,null);
// Bounds off: the old rule (no points-for tie is ever settled before the games end).
assert.deepEqual(race({A:1650,B:1500,C:1400},oneLeft,{bounds:false}),{clinched:null,out:[]});

// Guillotine: 4 teams, 2 survive. Safe / Cut only when proven.
const g=[team(200,done(11)),team(150,[...done(10),P('QB','pre',60,25)]),team(60,[...done(10),P('K','pre',60,8)]),team(40,done(11))];
assert.deepEqual(G.provenCalls(g,2,lb),['safe','safe','cut','cut']);
const g3=[team(200,done(11)),team(150,[...done(10),P('QB','pre',60,25)]),team(140,[...done(10),P('WR','pre',60,14)]),team(40,done(11))];
assert.deepEqual(G.provenCalls(g3,2,lb),['safe',null,null,'cut']);
assert.deepEqual(G.provenCalls(g,2,undefined),[null,null,null,null]);

console.log('Live bounds tests passed');
