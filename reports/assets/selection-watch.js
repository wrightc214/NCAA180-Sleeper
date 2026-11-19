/* Selection Watch board: live CCG odds from the existing Games scoring model. */
(async function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const E = x => String(x ?? '').replace(/[&<>"']/g,c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const C = window.ScoreboardCore, S = window.ScoreboardOverview, W = window.SelectionWatchCore;
  const route = new URLSearchParams(location.search);
  const previewQuery = route.get('preview');
  const archiveYear = route.get('season');
  const stringSetting = (value, fallback='') =>
    typeof value==='string' && value.trim() ? value.trim() : fallback;
  let preview=null;
  const dollar = x => Number(x).toFixed(2);
  const percent = x => !Number.isFinite(x) ? '—' :
    x < .00001 ? '0%' : x > .99999 ? '100%' : (x*100).toFixed(1)+'%';
  const clamp = x => Math.max(0,Math.min(1,x));
  let d,cfg,index,metadata,brand,featureName,exportPrefix,refreshMs,sort='chance',modelCache=new Map(),liveScores={},
    lastGood=null,updated=null,timer=null,loading=false,absoluteLocks=null;
  const byKey = () => Object.fromEntries(d.order.map(t=>[t.k,t]));
  const gameById = () => Object.fromEntries(d.ccg.map(g=>[g.id,g]));
  function alert(message) { $('sw-error').hidden=!message; $('sw-error').textContent=message || ''; }
  async function get(url) {
    const ac=new AbortController(),timeout=setTimeout(()=>ac.abort(),22000);
    try {
      const res=await fetch(url,{cache:'no-store',signal:ac.signal});
      if(!res.ok)throw Object.assign(Error(url+' (HTTP '+res.status+')'),{status:res.status});
      return res.json();
    }
    finally {clearTimeout(timeout);}
  }
  function team(k) {
    const t=byKey()[k], [lid,rid]=k.split('|');
    const club=index?.leagues?.[lid]?.teams?.[rid] || {};
    const approved=d?.style?.[t?.team] || {};
    return {name:t?.team || club.name || k,rank:t?.rank,short:t?.short,
      conf:t?.conf,primary:approved.background || club.primary || 'var(--neutral)',background:approved.background || club.background,
      logo:approved.logo || club.logo || '',logoHtml:approved.logo_html || ''};
  }
  function teamFill(color) {
    const hex=/^#([\da-f]{6}|[\da-f]{3})$/i.exec(color)?.[1];
    if(!hex)return '';
    const rgb=(hex.length===3?[...hex].map(c=>c+c):hex.match(/../g)).map(channel=>{
      const v=parseInt(channel,16)/255;
      return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;
    });
    const luminance=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];
    return ';--team-fill:#'+hex+';--team-ink:'+(luminance>.179?'#000':'#fff');
  }
  function tile(k,dim,extra) {
    if(!k)return '<span class="sw-empty">—</span>';
    const t=team(k),note=byKey()[k];
    const logo=t.logoHtml || (t.logo?'<img src="'+E(t.logo)+'" alt="" loading="lazy" onerror="this.hidden=true">':'');
    const fill=dim?'':teamFill(t.primary);
    return '<div class="sw-team'+(dim?' dim':fill?' admitted':'')+'" style="--team:'+E(t.primary)+fill+'">'+
      '<span class="sw-logo">'+logo+'</span><div class="sw-name">'+E(t.short||t.name)+
      '<small>#'+E(t.rank)+' · '+E(note?.conf||'')+'</small></div>'+
      '<div class="sw-number">'+(extra||'')+'</div></div>';
  }
  function content(id,text){$(id).innerHTML=text;}
  function gameLinks(g) {
    const l=g.a.split('|')[0];
    const url='scoreboard.html?'+new URLSearchParams({season:d.year,week:d.ccg_week,league:l});
    return preview==='provisional'?'':' · <a href="'+E(url)+'" class="sw-inline">View game ↗</a>';
  }
  function leading(g,item) {
    const result=liveScores[g.id];
    if(g.winner)return g.winner;
    if(result?.leader)return result.leader;
    return (result?.pA??.5)>=.5?g.a:g.b;
  }
  let timeline={}, checkpoints=[];
  function renderTimeline(teams, sample=false) {
    const table=teams.map(name=>'<div class="sw-track"><strong>'+E(name)+'</strong><div>'+
      checkpoints.map(w=>{
        const value=timeline[w.id]?.odds?.[name];
        return '<span><b>'+E(w.label)+'</b><small>'+ (Number.isFinite(value)?E(value)+'%':'Not recorded')+'</small></span>';
      }).join('')+'</div></div>').join('');
    return '<div class="sw-timeline"><h3>Bubble odds timeline</h3>'+
      (sample?'<p><b>SAMPLE TIMELINE · Illustrative, not recorded results</b></p>':'')+
      (table||'<p>No checkpoints recorded for this season.</p>')+'</div>';
  }
  async function loadTimeline(year, getData=get) {
    try {return await getData('postseason/selection-watch-timeline-'+year+'.json');}
    catch (_) {return {};}
  }
  const picks=new Map();
  let discordDraft=null;
  const pickText=()=>[...picks.values()].map(k=>team(k).name+' wins');
  function paintPicks() {
    const controls=$('sw-whatif'), options=[];
    for(const g of d.ccg){
      if(g.winner||liveScores[g.id]?.final){picks.delete(g.id);continue;}
      options.push('<label>'+E(team(g.a).name)+' vs '+E(team(g.b).name)+
        '<select data-game="'+E(g.id)+'"><option value="">Use current odds</option>'+
        [g.a,g.b].map(k=>'<option value="'+E(k)+'"'+(picks.get(g.id)===k?' selected':'')+'>'+E(team(k).name)+' wins</option>').join('')+'</select></label>');
    }
    controls.hidden=!options.length;
    const box=$('sw-picks');
    if(box.dataset.options!==options.join('')){
      box.innerHTML=options.join('');box.dataset.options=box.innerHTML;
    }
    const banner=$('sw-whatif-banner');
    banner.hidden=!picks.size;
    banner.textContent=picks.size?'WHAT-IF · '+pickText().join(' · '):'';
    $('sw-reset-picks').disabled=!picks.size;
  }
  function paint() {
    if(!lastGood)return;
    paintPicks();
    const games=gameById(),leaders={},p={},margins={},settled={};
    for(const g of d.ccg){
      const live=liveScores[g.id]||{},last=g.winner;
      leaders[g.id]=leading(g);
      p[g.id]=last?(last===g.a?1:0):clamp(live.pA??.5);
      if(last)settled[g.id]=last;
      else if(live.final&&live.leader)settled[g.id]=live.leader;
      else if(picks.has(g.id)){
        leaders[g.id]=picks.get(g.id);p[g.id]=leaders[g.id]===g.a?1:0;settled[g.id]=leaders[g.id];
      }
      margins[g.id]=Math.abs(live.scoreA-live.scoreB)||0;
    }
    const b=W.sortedBoard(d,leaders,p,margins,sort),odds=W.odds(d,p);
    const locks=absoluteLocks || (absoluteLocks=W.locks(d));
    const shownLocks=picks.size?d.order.filter(t=>(odds[t.k]||0)>=1-1e-10).map(t=>t.k):locks;
    const locked=new Set(shownLocks);
    const labels=W.implications(d,p,settled,locks);
    const projected=W.field(d,d.ccg.map(g=>leaders[g.id]));
    const toss=new Set(Object.entries(projected).filter(([,v])=>v>0&&v<1).map(([k])=>k));
    const tossBadge='<small class="sw-toss">COIN TOSS</small>';
    const riskOrder=b.atRisk, status=d.ccg.filter(g=>g.winner||liveScores[g.id]?.final).length;
    const confirmed=b.thieves.filter(t=>labels[t.game]==='Stolen'&&!picks.has(t.game)).length;
    const pendingLeads=b.k-confirmed;
    const potential=b.thieves.filter(t=>!(games[t.game].winner||liveScores[t.game]?.final)&&!t.leading).length;
    const provisional=preview==='provisional'||d.provisional, historical=preview==='historical';
    const stamp=updated?updated.toLocaleString('en-US',{timeZone:'America/New_York',dateStyle:'medium',timeStyle:'short'})+' ET':'not yet refreshed';
    const freshness=historical?d.year+' CCG finals · Historical replay':'Updated '+stamp;
    $('sw-status').innerHTML='<b class="sw-flag">'+(provisional?'PROVISIONAL · ':'')+'UNOFFICIAL</b>'+
      '<span>'+E(freshness)+'</span>'+
      '<span>'+status+'/'+d.ccg.length+' CCGs final</span>'+
      '<span><b>'+confirmed+'</b> steals confirmed</span>'+
      '<span><b>'+pendingLeads+'</b> additional currently leading</span>'+
      '<span><b>'+potential+'</b> additional possible</span>';
    let html='<div class="sw-head"><span>THIEVES</span><span>AT-LARGE TEAMS AT RISK</span></div>';
    b.thieves.forEach((t,i)=>{
      const g=games[t.game],lm=liveScores[g.id]||{};
      const win=t.team===g.a?p[g.id]:1-p[g.id];
      const score=lm.scoreA!=null&&lm.scoreB!=null?
        'Score '+dollar(t.team===g.a?lm.scoreA:lm.scoreB)+'–'+dollar(t.team===g.a?lm.scoreB:lm.scoreA) : 'No live score';
      const at=riskOrder[i],risk=at?odds[at]??0:null;
      const gameToss=lm.final&&!settled[g.id];
      const cutToss=toss.has(at)||toss.has(t.team);
      html+='<div class="sw-pair'+(i===b.k&&b.k<b.thieves.length?' cut':'')+'">'+
        '<div>'+tile(t.team,gameToss||cutToss||!t.leading,(toss.has(t.team)?tossBadge:'')+'<small>'+percent(win)+'</small>')+
        '<span class="sw-inline">'+E(score)+' · '+E(lm.final?'Final':lm.status||'Projected')+
        ' · '+(gameToss?'COIN TOSS':picks.has(g.id)?'What-if: '+labels[g.id]:labels[g.id])+gameLinks(g)+'</span></div>'+
        '<div>'+tile(at,cutToss||gameToss||i<b.k,at?(cutToss?tossBadge:'')+'<small>'+percent(risk)+'</small>':'')+
        '<span class="sw-inline">'+(cutToss||gameToss?'Cut depends on a coin toss':i<b.k?'Below current cut':'Holds if current leaders win')+'</span></div></div>';
    });
    if(!b.thieves.length)html+='<p class="sw-empty">No possible steals. No CCG participants are outside the natural field.</p>';
    content('sw-board-rows',html);
    const bubble=[...new Set([...b.atRisk,...toss])].filter(k=>!locked.has(k));
    discordDraft=null;
    const draftButton=$('sw-discord-draft');
    draftButton.hidden=Boolean(preview);
    if(!preview&&!picks.size){
      const complete=d.ccg.every(g=>settled[g.id])&&!toss.size;
      const title=complete?'Projected field locked — pending committee approval':featureName;
      discordDraft={title,html:'<section><h2>'+E(title)+'</h2><p>'+status+'/'+d.ccg.length+
        ' CCGs final · '+confirmed+' steals confirmed</p>'+
        (toss.size?'<p>COIN TOSS pending at the cut.</p>':'')+
        (bubble.length?'<ul>'+bubble.slice(0,6).map(k=>'<li>'+E(team(k).name)+' · '+percent(odds[k]||0)+'</li>').join('')+'</ul>':'')+
        '<p>DRAFT · Held for owner approval</p></section>'};
    }
    draftButton.disabled=!discordDraft;
    const bubbleReason=k=>{
      if(toss.has(k))return 'COIN TOSS · Tied at the projected cut.';
      const index=b.atRisk.indexOf(k)+1;
      const game=d.ccg.find(g=>g.a===k||g.b===k);
      const stealCount=index===1?'one steal':index+' steals';
      return (game?'Can qualify by winning its CCG; otherwise needs ':'Needs ')+
        'fewer than '+stealCount+' to hold its at-large spot.';
    };
    content('sw-bubble-rows',bubble.length?
      '<table class="sw-odds"><thead><tr><th>At-large team</th><th>Why</th><th>Make field</th></tr></thead><tbody>'+
      bubble.map(k=>'<tr><td>'+E(team(k).name)+' <span class="sw-muted">#'+team(k).rank+'</span></td>'+
        '<td class="sw-muted">'+E(bubbleReason(k))+'</td>'+
        '<td>'+percent(odds[k]||0)+'</td></tr>').join('')+'</tbody></table>':
      '<p class="sw-empty">No at-large teams currently on the bubble.</p>');
    if (checkpoints.length) $('sw-bubble-rows').insertAdjacentHTML('beforeend',renderTimeline(bubble.map(k=>team(k).name)));
    content('sw-lock-rows','<p class="sw-muted">'+shownLocks.length+' teams qualify in every '+(picks.size?'remaining':'possible')+' outcome.</p><div class="sw-locks">'+
      shownLocks.map(k=>'<span class="sw-lock" style="--tc:'+E(team(k).primary)+'">'+E(team(k).name)+'</span>').join('')+'</div>');
    const relevant=new Set(b.thieves.map(t=>t.game));
    const noimpact=d.ccg.filter(g=>!relevant.has(g.id)&&(labels[g.id]==='No bubble impact'||(locked.has(g.a)&&locked.has(g.b))));
    const otherImpact=d.ccg.filter(g=>!relevant.has(g.id)&&!noimpact.includes(g));
    if(otherImpact.length) $('sw-bubble-rows').insertAdjacentHTML('beforeend',
      '<p class="sw-muted"><b>Additional CCGs affecting the bubble:</b> '+
      otherImpact.map(g=>E(team(g.a).name)+' vs '+E(team(g.b).name)+' ('+E(labels[g.id])+')').join(' · ')+'</p>');
    content('sw-noimpact-rows',noimpact.length?noimpact.map(g=>
      '<p>'+E(team(g.a).name)+' vs '+E(team(g.b).name)+gameLinks(g)+'</p>').join(''):
      '<p class="sw-empty">No CCG is completely without selection impact.</p>');
    $('sw-updated').textContent=freshness+' · Unofficial';
    if(historical)delete document.body.dataset.snapTime;
    else document.body.dataset.snapTime=updated.toISOString();
  }
  async function refresh() {
    if(loading)return;loading=true;clearTimeout(timer);
    $('sw-refresh').disabled=true;
    try{
      const nextScores={};
      // Historical previews replay final scores without the live Games model.
      if(preview==='historical'){
        for(const g of d.ccg){
          nextScores[g.id]={scoreA:g.pa,scoreB:g.pb,final:!!g.winner,status:'Final',
            leader:g.winner || (g.pa>g.pb?g.a:g.b),pA:g.winner?(g.winner===g.a?1:0):.5};
        }
      } else if(preview==='provisional') {
        // The CCG baseline does not exist until the real weekly run. Explicitly labeled
        // provisional 50/50 placeholders allow the entire page to render beforehand.
        for(const g of d.ccg){
          nextScores[g.id]={pA:.5,final:false,leader:null,status:'PROVISIONAL · 50/50 placeholder'};
        }
      } else {
        const verified=await window.SelectionWatchGames.load(d,cfg,index,metadata,{get,C,S,modelCache});
        Object.assign(nextScores,verified.scores);
        if(checkpoints.length)timeline=await loadTimeline(d.year);
      }
      if(Object.keys(nextScores).length!==d.ccg.length)throw Error('Incomplete CCG update');
      liveScores=nextScores;
      const firstVerified=!lastGood;
      updated=new Date();lastGood={...liveScores};alert('');paint();
      if(firstVerified)document.querySelectorAll('#sw-content button.sw-save').forEach(btn=>{btn.disabled=false;});
    }catch(err){
      if(lastGood){liveScores=lastGood;paint();alert('Live refresh failed. Showing last verified data: '+err.message);}
      else {alert('Live data unavailable: '+err.message+' · no verified current probabilities.');$('sw-updated').textContent='Live data unavailable · Unofficial';}
    }finally{
      loading=false;$('sw-refresh').disabled=false;
      if(!document.hidden && !preview && refreshMs)timer=setTimeout(refresh,refreshMs);
    }
  }
  function fold(finalYear=null){
    const region=finalYear?'#sw-final':'#sw-content';
    const details=[...document.querySelectorAll(region+' details.sw-section')];
    const visible=()=>details.filter(d=>!d.hidden);
    const collapse=$(finalYear?'sw-final-collapse':'sw-collapse');
    const label=()=>{collapse.textContent=visible().some(d=>d.open)?'Collapse all':'Expand all';};
    collapse.addEventListener('click',()=>{
      const open=!visible().some(d=>d.open); visible().forEach(d=>{d.open=open;}); label();
    });
    details.forEach(d=>d.addEventListener('toggle',label));
    label();
    document.querySelectorAll(region+' button.sw-save').forEach(btn=>{
      btn.disabled=!finalYear;
      btn.addEventListener('click',async e=>{
        e.stopPropagation();
        if(!lastGood&&!finalYear)return;
        btn.disabled=true;
        const el=$(btn.dataset.save),copy=el.cloneNode(true);
        copy.open=true;copy.querySelectorAll('.sw-save').forEach(b=>b.remove());
        try {await NCAASnap.save({html:copy.outerHTML,title:brand+' '+featureName,name:exportPrefix+'-'+(finalYear?finalYear+'-':'')+btn.dataset.save,
          stamp:finalYear?null:{state:'projection',time:preview==='historical'?null:updated,
            note:(preview==='historical'?d.year+' CCG finals · Historical replay · ':
              preview==='provisional'?'PROVISIONAL · ':'')+'Unofficial'},
          whatif:finalYear?[]:pickText(),
          footer:brand+' '+featureName+(finalYear?' · '+finalYear+' final results':' · Unofficial'),width:650});}
        catch(err){alert('Could not save image: '+err.message);}
        finally{btn.disabled=false;}
      });
    });
  }
  function showFinals(year, archive, sample) {
    const season=archive[year];
    if(!season?.ccg?.length || !season.field?.length)throw Error('No final results available for '+year);
    content('sw-final-status','<b class="sw-flag">FINAL RESULTS</b><strong>'+E(year)+' season</strong>'+
      '<span>'+season.ccg.length+' conference championships</span><span>'+season.field.length+' playoff teams</span>'+
      '<span>National champion: '+E(season.champion)+'</span>');
    const side=(name,score,winner,standard)=>{
      const rescored=Number.isFinite(standard);
      const result=E(name)+' · '+dollar(score)+(rescored?'<sup>†</sup>':'');
      return (winner?'<strong>'+result+' (winner)</strong>':result)+
        (rescored?'<small class="sw-score-note">Standard scoring: '+dollar(standard)+'</small>':'');
    };
    const hasStandard=season.ccg.some(g=>Number.isFinite(g.standard_a)||Number.isFinite(g.standard_b));
    content('sw-final-ccg','<table class="sw-odds"><thead><tr><th scope="col">'+
      '<span class="sw-conf-full">Conference</span><abbr class="sw-conf-short" title="Conference">Conf.</abbr></th>'+
      '<th scope="col">Team and score</th><th scope="col">Team and score</th></tr></thead><tbody>'+
      season.ccg.map(g=>'<tr><th scope="row">'+E(g.conference)+(g.steal?'<small class="sw-score-note">'+E(g.steal)+'</small>':'')+'</th><td>'+side(g.a,g.score_a,g.winner===g.a,g.standard_a)+
        '</td><td>'+side(g.b,g.score_b,g.winner===g.b,g.standard_b)+'</td></tr>').join('')+'</tbody></table>'+
      (hasStandard?'<p class="sw-muted">† As played. Standard scoring differs. Recorded results stand.</p>':''));
    const seeded=season.field.every(t=>Number.isInteger(t.seed));
    content('sw-final-field','<'+(seeded?'ol':'ul')+' class="sw-field">'+
      season.field.map(t=>'<li'+(seeded?' value="'+t.seed+'"':'')+'>'+E(t.team)+
        (!seeded&&Number.isInteger(t.seed)?' (#'+t.seed+')':'')+'</li>').join('')+(seeded?'</ol>':'</ul>'));
    if(checkpoints.length){
      const names=[...new Set(Object.values(timeline).flatMap(point=>Object.entries(point.odds||{})
        .filter(([,value])=>value>0&&value<100).map(([name])=>name)))];
      $('sw-final-field').insertAdjacentHTML('beforeend',renderTimeline(names,sample));
    }
    $('sw-intro').textContent='Recorded conference championship scores and the final playoff field.';
    $('sw-final').hidden=false;
    $('sw-season').value=year;
    fold(year);
  }
  try {
    const nav=await get('../config/nav.json');
    const tab=nav.tabs?.find(t=>t.id==='selection-watch');
    if(tab?.state==='hidden'){
      alert('Selection Watch is disabled.');
      return;
    }
    let settings={};
    try {settings=await get('../config/selection_watch.json') || {};}
    catch(err){if(err.status!==404)throw err;}
    cfg=await get('../config/league.json');
    const brandElement=$('sw-brand');
    brand=stringSetting(cfg.brand,brandElement.textContent.trim());
    brandElement.textContent=brand;
    document.querySelectorAll('[data-sw-label]').forEach(el=>{
      el.textContent=stringSetting(settings?.labels?.[el.dataset.swLabel],el.textContent);
      if(el.dataset.swLabel==='title')featureName=el.textContent;
    });
    document.title=featureName+' | '+brand;
    checkpoints=settings.timeline?.windows||[];
    exportPrefix=stringSetting(settings?.export_filename_prefix,'ncaa180-selection-watch');
    $('sw-season-picker').hidden=false;
    if(archiveYear){
      if(previewQuery!==null || !/^\d{4}$/.test(archiveYear))throw Error('Choose a season from the archive');
      const sample=archiveYear==='2025'&&route.get('timeline')==='sample';
      if(checkpoints.length)timeline=sample?await get('postseason/selection-watch-timeline-sample.json'):await loadTimeline(archiveYear);
      showFinals(archiveYear,await get('postseason/selection-watch-history.json'),sample);
      return;
    }
    let dataURL='postseason/selection-watch.json';
    if(previewQuery!==null){
      const matches=['historical','provisional'].filter(mode=>{
        const profile=settings?.previews?.[mode];
        return profile?.enabled===true && stringSetting(profile.query)===previewQuery &&
          previewQuery!=='' && stringSetting(profile.url)!=='';
      });
      if(matches.length!==1)throw Error('Unknown or disabled preview');
      preview=matches[0];
      dataURL=stringSetting(settings.previews[preview].url);
    }
    try {d=await get(dataURL);}
    catch(err){
      if(!preview && err.status===404){
        alert(stringSetting(settings.availability_message,'Available after the regular season is final.'));
        return;
      }
      throw err;
    }
    if(!d.order?.length||!d.ccg?.length||!d.field_size)throw Error('Selection file incomplete');
    if(preview==='provisional' && d.provisional!==true)throw Error('Preview file missing PROVISIONAL label');
    if(preview!=='provisional' && d.provisional)throw Error('Provisional data cannot be used in '+(preview?'the historical preview':'the live page'));
    const interval=cfg.refresh?.normal_ms;
    refreshMs=Number.isInteger(interval)&&interval>0&&interval<=2147483647?interval:null;
    try {index=await get(cfg.data.scoreboard+'/index.json');metadata=await get(cfg.data.scoreboard+'/'+d.year+'/players.json');}
    catch(err){if(preview!=='historical')throw err;}
    $('sw-content').hidden=false;
    if(checkpoints.length&&!preview)timeline=await loadTimeline(d.year);
    fold();$('sw-sort').addEventListener('change',e=>{sort=e.target.value;paint();});
    $('sw-refresh').addEventListener('click',refresh);
    $('sw-picks').addEventListener('change',event=>{
      const id=event.target.dataset.game, g=d.ccg.find(game=>game.id===id);
      if(!g||g.winner||liveScores[id]?.final)return;
      const value=event.target.value;
      if(value===g.a||value===g.b)picks.set(id,value);
      else picks.delete(id);
      paint();
    });
    $('sw-reset-picks').addEventListener('click',()=>{picks.clear();paint();});
    $('sw-discord-draft').addEventListener('click',async()=>{
      if(!discordDraft)return;
      const button=$('sw-discord-draft');button.disabled=true;
      try {await NCAASnap.save({...discordDraft,name:exportPrefix+'-discord-draft',
        stamp:{state:'projection',time:updated,note:'Draft · held for approval'},
        footer:brand+' · Unofficial',width:500});}
      catch(error){alert('Could not save draft: '+error.message);}
      finally{button.disabled=!discordDraft;}
    });
    if(!preview)document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(timer);else refresh();});
    await refresh();
  } catch(err){alert('Selection Watch unavailable: '+err.message);$('sw-updated').textContent='Unavailable · Unofficial';}
})();
