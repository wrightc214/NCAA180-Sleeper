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
test('both-outside CCG guarantees exactly one steal', () => {
  const b = core.board(fixture(), {one:'A',two:'H'});
  assert.equal(b.k, 1);
  assert.equal(b.thieves.length, 2);
  assert.equal(b.thieves.find(x=>x.game==='two').both_out,true);
});
test('inside CCG team that can miss is not a thief', () => {
  const b = core.board(fixture(), {one:'F',two:'G'});
  assert.equal(b.thieves.some(x=>x.team==='A'),false);
  assert.equal(b.thieves.find(x=>x.game==='one').team,'F');
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
test('sort toggle preserves cut and paired risk order', () => {
  const d=fixture(), lead={one:'F',two:'H'};
  const a=core.sortedBoard(d,lead,{one:.2,two:.9},{one:8,two:2},'chance');
  const b=core.sortedBoard(d,lead,{one:.2,two:.9},{one:8,two:2},'margin');
  assert.equal(a.k,b.k); assert.deepEqual(a.atRisk,b.atRisk);
});

test('2025 actual Steal Board: six rows, two steals and the correct cut', () => {
  const fs=require('node:fs'),path=require('node:path');
  const d=JSON.parse(fs.readFileSync(path.join(__dirname,'../reports/postseason/selection-watch-2025.json'),'utf8'));
  const leaders=Object.fromEntries(d.ccg.map(g=>[g.id,g.winner]));
  const b=core.board(d,leaders),names=Object.fromEntries(d.order.map(t=>[t.k,t.team]));
  assert.equal(b.thieves.length,6);
  assert.equal(b.k,2);
  assert.deepEqual(b.thieves.filter(t=>t.leading).map(t=>names[t.team]).sort(),['Kansas State','Nevada']);
  assert.deepEqual(b.atRisk.slice(0,b.k).map(k=>names[k]).sort(),['UNLV','Youngstown State']);
  assert.equal(Object.values(core.field(d,d.ccg.map(g=>g.winner))).reduce((a,n)=>a+n,0),32);
});

test('inside natural-field CCG team can miss without being a thief', () => {
  const d={field_size:4,order:['A','B','C','D','E','F'].map((k,i)=>({k,rank:i+1})),
    ccg:[{id:'inside',a:'A',b:'D'},{id:'outside',a:'E',b:'F'}],tie:[]};
  const winnersWhenDloses=['A','E'], winnersWhenDwins=['D','E'];
  assert.equal(core.field(d,winnersWhenDloses).D||0,0);
  assert.equal(core.field(d,winnersWhenDwins).D,1);
  assert.equal(core.board(d,{inside:'A',outside:'E'}).thieves.some(t=>t.team==='D'),false);
  assert.equal(core.locks(d).includes('D'),false);
});
test('margin sorts trailing thieves by nearest comeback, without moving cut', () => {
  const d={field_size:4,order:'ABCDEF'.split('').map((k,i)=>({k,rank:i+1})),
    ccg:[{id:'one',a:'A',b:'E'},{id:'two',a:'B',b:'F'}],tie:[]};
  const leaders={one:'A',two:'B'},margins={one:20,two:3};
  const b=core.sortedBoard(d,leaders,{one:.1,two:.1},margins,'margin');
  assert.equal(b.k,0);
  assert.deepEqual(b.thieves.map(t=>t.game),['two','one']);
});


test('bid labels separate projected steals, possibilities and official finals', () => {
  const d={field_size:2,order:['A','B','C','D'].map((k,i)=>({k,rank:i+1})),ccg:[{id:'g',a:'A',b:'D'}]};
  const label=(p,w)=>core.implications(d,{g:p},w?{g:w}:{}).g;
  assert.equal(label(.7), 'Possible steal');
  assert.equal(label(.3), 'Steal');
  assert.equal(label(.2,'D'), 'Stolen');
  assert.equal(label(.8,'A'), 'Held');
});
