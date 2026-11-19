/* Publish the checked-out live-refresh commit without dropping a captured checkpoint. */
'use strict';
const fs=require('node:fs');
const {spawnSync}=require('node:child_process');

function git(args, capture=false){
  const result=spawnSync('git',args,{encoding:'utf8',stdio:capture?['ignore','pipe','inherit']:'inherit',
    env:{...process.env,GIT_EDITOR:'true'}});
  if(result.error)throw result.error;
  if(capture&&result.status!==0)throw Error('git '+args.join(' ')+' failed');
  return capture?result.stdout:result.status===0;
}

function reconcileTimelineConflicts(){
  const files=git(['diff','--name-only','--diff-filter=U','-z'],true).split('\0').filter(Boolean);
  if(!files.length||files.some(p=>!/^reports\/postseason\/selection-watch-timeline-\d{4}\.json$/.test(p)))return false;
  for(const file of files){
    // During rebase, stage 2 is upstream and stage 3 the local refresh commit.
    const published=JSON.parse(git(['show',':2:'+file],true));
    const local=JSON.parse(git(['show',':3:'+file],true));
    fs.writeFileSync(file,JSON.stringify({...local,...published})+'\n');
    if(!git(['add','--',file]))return false;
  }
  return git(['rebase','--continue']);
}

function publish(){
  if(git(['push']))return;
  console.error('Live refresh push failed; fetching and rebasing before one retry.');
  if(!git(['fetch']))throw Error('Could not fetch before live refresh push retry');
  if(!git(['rebase','@{upstream}'])){
    let resolved=false;
    try {resolved=reconcileTimelineConflicts();}
    finally {if(!resolved)git(['rebase','--abort']);}
    if(!resolved)throw Error('Could not rebase the live refresh commit');
  }
  if(!git(['push']))throw Error('Live refresh push failed again; check the recovery artifact');
}

try {publish();}
catch(error){console.error('::error::'+error.message);process.exitCode=1;}
