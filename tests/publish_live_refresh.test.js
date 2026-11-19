const test=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'), os=require('node:os'), path=require('node:path');
const {spawnSync}=require('node:child_process');
const script=path.resolve(__dirname,'../scripts/publish_live_refresh.js');
const route='reports/postseason/selection-watch-timeline-2026.json';
function fixture(t){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'live-refresh-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const bare=path.join(root,'remote'), local=path.join(root,'local'), peer=path.join(root,'peer');
  const g=(cwd,...args)=>{
    const x=spawnSync('git',args,{cwd,encoding:'utf8'});
    assert.equal(x.status,0,x.stderr);return x.stdout;
  };
  const init=cwd=>{g(cwd,'config','user.name','Test');g(cwd,'config','user.email','test@example.invalid');};
  g(root,'init','--bare','--initial-branch=main',bare);
  g(root,'clone',bare,local);init(local);
  const commit=(cwd,value)=>{
    fs.mkdirSync(path.dirname(path.join(cwd,route)),{recursive:true});
    fs.writeFileSync(path.join(cwd,route),JSON.stringify(value)+'\n');
    g(cwd,'add',route);g(cwd,'commit','-m','checkpoint');
  };
  commit(local,{first:{recorded_at:'original'}});
  g(local,'push','-u','origin','main');g(root,'clone',bare,peer);init(peer);
  const run=()=>spawnSync(process.execPath,[script],{cwd:local,encoding:'utf8'});
  const remote=()=>JSON.parse(g(bare,'show','main:'+route));
  return {bare,local,peer,g,commit,run,remote};
}
test('a rejected push rebases once and preserves the first published checkpoint',t=>{
  const {local,peer,g,commit,run,remote}=fixture(t);
  commit(local,{first:{recorded_at:'original'},second:{recorded_at:'local'},third:{recorded_at:'local-only'}});
  commit(peer,{first:{recorded_at:'original'},second:{recorded_at:'published'}});
  g(peer,'push');
  const result=run();
  assert.equal(result.status,0,result.stderr);
  assert.match(result.stderr,/fetching and rebasing/);
  assert.deepEqual(remote(),{first:{recorded_at:'original'},second:{recorded_at:'published'},third:{recorded_at:'local-only'}});
});
test('two rejected pushes are visible failures and leave upstream unchanged',t=>{
  const {bare,local,commit,run,remote}=fixture(t);
  commit(local,{first:{recorded_at:'original'},second:{recorded_at:'unpublished'}});
  const hook=path.join(bare,'hooks','pre-receive');
  fs.writeFileSync(hook,'#!/bin/sh\necho test-push-rejection >&2\nexit 1\n',{mode:0o755});
  const result=run();
  assert.equal(result.status,1);
  assert.equal((result.stderr.match(/test-push-rejection/g)||[]).length,2);
  assert.match(result.stderr,/::error::Live refresh push failed again/);
  assert.deepEqual(remote(),{first:{recorded_at:'original'}});
});
