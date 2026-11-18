/* 5.4 regression tests for the overview renderer's pure ordering and color helpers.
   Extract the actual production helper declarations rather than maintaining a copy. */
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('reports/assets/scoreboard-overview.js','utf8');
const css=fs.readFileSync('reports/assets/scoreboard-overview.css','utf8');
const menu=fs.readFileSync('templates/menu.js','utf8');
function helper(start,end,extra=''){
  const a=source.indexOf(start),b=source.indexOf(end,a);
  assert.ok(a>=0&&b>a,'production helper source found');
  return vm.runInNewContext(extra+'\n'+source.slice(a,b)+'\n({validRank,bestRank,rankedSections,cardOrder,winStrength,chanceStyle})');
}
const h=helper('  const validRank=', '  // One row: logo', 'const side=(o,rid)=>({rank:String(o.RosterID)===String(rid)?o.Rank:o.OppRank});');
const game=(a,b)=>({o:{RosterID:'1',Rank:a,OppRank:b},match:[{roster_id:1},{roster_id:2}]});
test('ranked sections sort by best rank, not sum or conference position',()=>{
  const games=[game(5,6),game(3,18),game(7,9)];
  const sections=h.rankedSections(games);
  assert.deepEqual(Array.from(sections.rvr,h.bestRank),[3,5,7]);
  assert.equal(sections.ranked.length,0);
  const mixed=[game('',5),game(7,''),game('',''),game(3,18),game(5,6)];
  const result=h.rankedSections(mixed);
  assert.deepEqual(Array.from(result.rvr,h.bestRank),[3,5]);
  assert.deepEqual(Array.from(result.ranked,h.bestRank),[5,7]);
  assert.equal(result.ranked.length,2);
  const tied=h.rankedSections([game(5,20),game(5,8)]);
  assert.equal(tied.rvr[0].o.OppRank,20); // stable equal-rank order
});
test('higher ranked regular season side is on top; unranked is stable',()=>{
  assert.deepEqual(Array.from(h.cardOrder(game(18,3))),[1,0]);
  assert.deepEqual(Array.from(h.cardOrder(game('',5))),[1,0]);
  assert.deepEqual(Array.from(h.cardOrder(game('',''))),[0,1]);
});
test('postseason retains frozen seed order',()=>{
  const g=game(18,3);g.post={round:'Playoff',sides:[{Seed:1},{Seed:2}]};
  assert.deepEqual(Array.from(h.cardOrder(g)),[0,1]);
});
test('50 percent is neutral and favorites remain bold without relying on color',()=>{
  assert.equal(h.winStrength(50),0);
  assert.equal(h.winStrength(90),0.8);
  assert.match(h.chanceStyle(50),/--win-mix:0.0%/);
  assert.match(h.chanceStyle(90),/--win-mix:80.0%/);
  assert.match(h.chanceStyle(90),/--win-final-mix:24.0%/);
  assert.match(h.chanceStyle(50),/--win-final-mix:0.0%/);
  assert.match(css,/\.r3\.favorite \.chance\{font-weight:800\}/);
  assert.match(css,/var\(--good,var\(--neutral,var\(--mute\)\)\)/);
  assert.match(css,/var\(--bad,var\(--neutral,var\(--mute\)\)\)/);
  const probabilityRules=css.slice(css.indexOf('/* 5.4: probability diverges'));
  assert.equal((probabilityRules.match(/color-mix\(in oklab,/g)||[]).length,6);
  assert.equal((probabilityRules.match(/color-mix\(in srgb,/g)||[]).length,0);
  assert.match(probabilityRules,/\.r3 \.chance\{color:var\(--neutral,var\(--mute\)\)/);
  assert.match(probabilityRules,/var\(--win-pre-mix,0%\)/);
  assert.match(probabilityRules,/var\(--win-mix,0%\)/);
  assert.match(probabilityRules,/var\(--win-final-mix,0%\)/);
  assert.match(probabilityRules,/\.r3\.final-odds \.chance\{font-weight:500\}/);
  assert.match(source,/s\.final\?' final-odds'/);
  assert.match(source,/probability!=null&&probability>50\?' favorite'/); // final still gets green, but not bold
  assert.match(probabilityRules,/\.r3\.final-odds\.favorite \.chance\{/);
  assert.match(source,/s\.final\?'Pregame %'/);
  assert.match(menu,/var TOKENS_LIGHT = \{"--good":/);
  assert.match(menu,/var TOKENS_DARK = \{"--good":/);
});
test('accessible card label follows visible row order',()=>{
  assert.match(source,/match\[order\[0\]\]\.roster_id/);
  assert.match(source,/match\[order\[1\]\]\.roster_id/);
});

test('live pregame summary follows the displayed top team',()=>{
  assert.match(source,/match\[order\[0\]\]\.roster_id/);
  assert.match(source,/order\[0\]===0\?s\.pregame:100-s\.pregame/);
});
