'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const core = require('../reports/assets/selection-watch-core.js');
function fixture() {
  return {
    field_size: 4,
    order: ['A','B','C','D','E','F','G','H'].map((k,i)=>({k,rank:i+1})),
    ccg: [{id:'one',a:'A',b:'F'}, {id:'two',a:'G',b:'H'}],
    tie: []
  };
}
test('field adds winners and best remaining teams', () => {
  const f = core.field(fixture(), ['A','G']);
  assert.deepEqual(Object.keys(f).sort(), ['A','B','G','C'].sort());
});


test('exact odds match independent exhaustive weighting', () => {
  const d=fixture(), p={one:0.3,two:0.7}, actual=core.odds(d,p);
  const expected={};
  for(const [w1,q1] of [['A',.3],['F',.7]])
    for(const [w2,q2] of [['G',.7],['H',.3]])
      for(const [k,share] of Object.entries(core.field(d,[w1,w2])))
        expected[k]=(expected[k]||0)+q1*q2*share;
  for(const k of d.order.map(t=>t.k)) assert.ok(Math.abs((actual[k]||0)-(expected[k]||0))<1e-12,k);
});
test('tie at the cut shares the final place', () => {
  const d=fixture(); d.tie=[['C','D']];
  const f=core.field(d,['A','G']);
  assert.equal(f.C,.5); assert.equal(f.D,.5);
});
test('locks include teams present under every outcome', () => {
  assert.ok(core.locks(fixture()).includes('B'));
  assert.ok(!core.locks(fixture()).includes('D'));
});

const archive=require('../reports/postseason/selection-watch-history.json');
function replay(d, overrides={}){
  const final=Object.fromEntries(d.ccg.map(g=>[g.id,overrides[g.id]||g.winner]));
  const p=Object.fromEntries(d.ccg.map(g=>[g.id,+(final[g.id]===g.a)]));
  return core.cutBoard(d,final,p,final);
}
test('2025: two steals displace Youngstown State and UNLV; UTEP changes only the play-in',()=>{
  const d=archive['2025'].cut_board, actual=replay(d);
  assert.equal(actual.steals,2);
  assert.equal(actual.cut,29);
  assert.equal(actual.initialCut,31);
  assert.deepEqual(actual.thieves.filter(t=>t.active).map(t=>t.k).sort(),['Kansas State','Nevada']);
  assert.deepEqual(actual.rows.filter(r=>r.right?.active).map(r=>r.left.k),['Youngstown State','UNLV']);
  assert.equal(actual.playIns.length,1);
  const play=actual.playIns[0];
  assert.equal(play.final,'Georgia Southern');
  assert.equal(play.label,'Play-in winner');
  assert.equal(actual.rows.some(r=>[r.left?.k,r.right?.k].some(k=>[play.a.k,play.b.k].includes(k))),false);
  const whatIf=replay(d,{[play.g.id]:'UTEP'});
  assert.equal(whatIf.playIns[0].final,'UTEP');
  assert.equal(whatIf.playIns[0].label,'Play-in winner');
  assert.deepEqual(whatIf.rows,actual.rows);
  assert.equal(whatIf.cut,actual.cut);
  assert.equal(whatIf.steals,2);
});
test('2024: Eastern Kentucky vs Chattanooga is a play-in, not a third steal',()=>{
  const b=replay(archive['2024'].cut_board);
  assert.equal(b.cut,27);
  assert.equal(b.steals,2);
  assert.deepEqual(b.thieves.filter(t=>t.active).map(t=>t.k).sort(),['Jackson State','UAB']);
  assert.deepEqual(b.playIns.map(x=>[x.a.k,x.b.k].sort()),[['Chattanooga','Eastern Kentucky']]);
});

function savedFixture(opponent){
  return {field_size:5,play_ins:[],tie:[],
    order:'ABCDEFGHI'.split('').map((k,i)=>({k,rank:i+1,conf:'Example'})),
    ccg:[{id:'x',a:'A',b:'H'},{id:'y',a:'B',b:'I'},{id:'save',a:'D',b:opponent}]};
}
test('two steals hold the natural team with an outside opponent, then resolve to Saved',()=>{
  const d=savedFixture('F'), leaders={x:'H',y:'I',save:'D'}, odds={x:.15,y:.25,save:.7};
  const lead=core.cutBoard(d,leaders,odds);
  const held=lead.rows.find(r=>r.left?.k==='D');
  assert.equal(held.hold.pair.k,'F');
  assert.ok(!held.right);
  assert.ok(!lead.thieves.some(t=>t.k==='F'));
  assert.equal(lead.labels.save,'Possible steal');
  const saved=core.cutBoard(d,leaders,{...odds,save:1},{save:'D'});
  assert.equal(saved.labels.save,'Saved');
  assert.equal(saved.rows.find(r=>r.left?.k==='D').left.status,'Saved');
  const lost=core.cutBoard(d,{...leaders,save:'F'},{...odds,save:.1});
  assert.equal(lost.rows.find(r=>r.left?.k==='D').hold,undefined);
  assert.equal(lost.labels.save,'Steal');
  assert.ok(lost.thieves.some(t=>t.k==='F'&&t.active));
});
test('a placard skips the leader’s held row against a lock or an at-risk opponent',()=>{
  for(const opponent of ['C','E']){
    const d=savedFixture(opponent), leaders={x:'H',y:'I',save:'D'}, odds={x:.15,y:.25,save:.7};
    const live=core.cutBoard(d,leaders,odds,{x:'H',y:'I'});
    const held=live.rows.find(r=>r.left?.k==='D');
    assert.ok(held.hold);
    assert.equal(held.hold.pair,null);
    assert.equal(held.right,undefined);
    assert.equal(live.rows.filter(r=>r.right?.active).length,2);
    assert.equal(live.rows.find(r=>r.left?.k==='D').left.status,'Leading CCG');
    const final=core.cutBoard(d,leaders,odds,{...leaders});
    assert.equal(final.labels.save,'Saved');
    const trailing=core.cutBoard(d,{...leaders,save:opponent},odds,{x:'H',y:'I'});
    assert.equal(trailing.rows.find(r=>r.left?.k==='D').hold,undefined);
    assert.equal(trailing.rows.find(r=>r.left?.k==='D').left.status,'Below cut');
  }
});
test('a decided CCG winner shows Automatic bid; a live leader keeps its projected status',()=>{
  const d=savedFixture('E'), odds={x:.9,y:.9,save:.3};
  const live=core.cutBoard(d,{x:'A',y:'B',save:'E'},odds,{x:'A',y:'B'});
  const status=b=>b.rows.find(r=>r.left?.k==='E')?.left.status;
  assert.notEqual(status(live),'Automatic bid');
  const decided=core.cutBoard(d,{},odds,{x:'A',y:'B',save:'E'});
  assert.equal(status(decided),'Automatic bid');
  assert.equal(decided.projected.E,1);
  const saved=core.cutBoard(savedFixture('F'),{},{},{x:'H',y:'I',save:'D'});
  assert.equal(saved.rows.find(r=>r.left?.k==='D').left.status,'Saved');
});
test('a non-play-in stays untagged when other What-if games make it win-or-out',()=>{
  const d=savedFixture('F');
  assert.deepEqual(core.cutBoard(d).playIns,[]);
  const board=core.cutBoard(d,{save:'F'},{x:0,y:0,save:.1},{x:'H',y:'I'});
  assert.deepEqual(board.playIns,[]);
  assert.equal(board.steals,2);
  assert.equal(board.labels.save,'Steal');
});
test('a tied loser with a partial at-large path prevents a play-in tag',()=>{
  const d={field_size:2,order:'ABCD'.split('').map((k,i)=>({k,rank:i+1})),
    ccg:[{id:'g',a:'A',b:'D'}],tie:[['A','B']]};
  assert.deepEqual(core.cutBoard(d).playIns,[]);
});
