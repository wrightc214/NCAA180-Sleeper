const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const js=fs.readFileSync('reports/assets/team.js','utf8');
const css=fs.readFileSync('scripts/team_pages.py','utf8');
const source=js.slice(js.indexOf("  const COLOR_KEY"),js.indexOf("  async function main()"));
const globalKey='ncaa180.teamColors', teamKey=globalKey+'.byTeam';
function page(store,key='a',blocked=false){
  const element=(dataset={})=>({dataset,attrs:{},events:{},setAttribute(k,v){this.attrs[k]=v},addEventListener(k,v){this.events[k]=v},focus(){}});
  const buttons=['full','inverted','frame','site'].map(c=>element({c}));
  const toggle=element(), box={querySelectorAll:()=>buttons}, img={dataset:{logo:'primary',logoInv:'ink'}}, classes=new Set();
  const style={};
  const storage={getItem:k=>store.get(k)??null,setItem(k,v){if(blocked)throw Error('blocked');store.set(k,v)},removeItem:k=>store.delete(k)};
  vm.runInNewContext(source+'\ncolors(d)',{d:{key,bg:'#990000',ink:'#ffffff'},localStorage:storage,$:id=>id==='tm-colors'?box:toggle,document:{getElementById:()=>style,querySelector:()=>img,body:{classList:{add:k=>classes.add(k),remove:(...ks)=>ks.forEach(k=>classes.delete(k))}}}});
  return {mode:()=>[...classes][0],choose:m=>buttons.find(b=>b.dataset.c===m).events.click(),toggle:()=>toggle.events.click(),switch:toggle,img};
}
test('global and stable-team override lifecycle',()=>{
 const s=new Map([[globalKey,'frame']]);let a=page(s);assert.equal(a.mode(),'tm-c-frame');
 a.toggle();a.choose('inverted');assert.equal(s.get(globalKey),'frame');assert.equal(a.img.src,'primary');
 let b=page(s,'b');b.choose('site');a=page(s);assert.equal(a.mode(),'tm-c-inverted');
 a.toggle();assert.equal(a.mode(),'tm-c-site');assert.deepEqual(JSON.parse(s.get(teamKey)),{});
 a.choose('full');assert.equal(a.img.src,'ink');
});
test('invalid and blocked storage',()=>{
 const s=new Map([[globalKey,'invalid'],[teamKey,'{']]);assert.equal(page(s).mode(),'tm-c-full');
 const a=page(s,'a',true);assert.equal(a.switch.hidden,true);a.choose('inverted');assert.equal(a.mode(),'tm-c-inverted');
});
test('button order and shared CSS',()=>{
 assert.match(css,/data-c="full">Team.*data-c="inverted">Inverted.*data-c="frame">Accent.*data-c="site">Site/);
 assert.match(css,/body:is\(\.tm-c-full,\.tm-c-inverted\) #tm-sections section/);
 assert.match(css,/body\.tm-c-inverted\{--tm-base:var\(--t1ink\)/);
});

test('inverted headings prefer primary rather than accent',()=>{
 assert.ok(js.includes("--tm-inverted-heading:'+readable(bg,ink)"));
 assert.ok(js.includes("--tm-full-heading:'+readable(accent,bg)"));
});
