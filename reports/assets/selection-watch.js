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
  // Whole numbers only (Chris, 2026-11-24). 0% / 100% only once every CCG is final; before that a
  // near-certain value shows <1% / >99% so the board never claims a result that hasn't happened.
  let allFinal=false;
  const percent = x => !Number.isFinite(x) ? '—' :
    allFinal&&x<.005 ? '0%' : allFinal&&x>=.995 ? '100%' :
    x < .005 ? '&lt;1%' : x >= .995 ? '&gt;99%' : Math.round(x*100)+'%';
  const clamp = x => Math.max(0,Math.min(1,x));
  let d,cfg,index,metadata,brand,featureName,exportPrefix,refreshMs,rankingOrder=false,modelCache=new Map(),liveScores={},
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
  function leading(g) {
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
  const devView=()=>window.NCAA180?.menu?.dev?.()===true;
  function syncDraftButton() {
    const button=$('sw-discord-draft');
    button.hidden=Boolean(preview)||!devView();
    button.disabled=button.hidden||!discordDraft;
  }
  const pickText=()=>[...picks.values()].map(k=>team(k).name+' wins');
  function paintPicks() {
    const controls=$('sw-whatif'), options=[];
    for(const g of d.ccg){
      if(g.winner||liveScores[g.id]?.final){picks.delete(g.id);continue;}
      options.push('<label>'+E(team(g.a).name)+' vs '+E(team(g.b).name)+
        '<small class="sw-muted" data-game-label="'+E(g.id)+'"></small>'+
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
  function margin(g, k) {
    const score=liveScores[g.id];
    if(!score?.live||picks.has(g.id)||!Number.isFinite(score.scoreA)||!Number.isFinite(score.scoreB))return '';
    const delta=(score.scoreA-score.scoreB)*(k===g.a?1:-1);
    return '<small class="sw-margin" aria-label="Live margin '+E(delta.toFixed(1))+'">'+
      (delta>0?'+':'')+E(delta.toFixed(1))+'</small>';
  }
  const winMetric=(t,extra='')=>'<small class="sw-win">'+percent(t.win)+'</small>'+extra;
  function cutHTML(board, {archive=false,odds={},formatTeam,name,detail=()=>'',metric=winMetric,exceptions=[]}){
    // Owner-listed admin errors (config field_exceptions): the board stays by rule; ‡ marks the swapped teams.
    const entryNote=k=>exceptions.some(x=>x.out===k)?' ‡ · left out by entry error':
      exceptions.some(x=>x.in===k)?' ‡ · in field by entry error':'';
    const rows=[...board.rows];
    // Automatic bids can be safe even when their rank follows the last at-large bid.
    // Split the displayed row statuses, keeping Saved/held teams on the at-risk side.
    const qualified=status=>status==='Above cut'||status==='Automatic bid';
    // A plays/leads placard (PR 141) is not at risk: only a saved-leader hold sits on the at-risk side.
    const cutIndex=rows.findIndex(({left,hold})=>left&&(hold&&!hold.plays||!qualified(left.status)));
    const line='<div class="sw-cut-line" aria-hidden="true"></div>';
    const markup=rows.map(({left:l,right:r,hold})=>{
      const leftIn=l&&(qualified(l.status)||l.status==='Saved'||hold);
      const rightIn=!leftIn&&l?.status!=='Coin toss'&&r?.active;
      const leftExtra=archive?'<small>#'+E(l?.rank)+'</small>':'<small>'+percent(odds[l?.k]||0)+'</small>';
      const leftHTML=l?formatTeam(l.k,!leftIn,leftExtra)+'<div class="sw-inline">'+E(l.status+entryNote(l.k))+'</div>':'';
      const note=hold&&(hold.final?hold.conf+' Champion':hold.plays?hold.conf+' CCG · '+name(l.k)+(hold.leads?' leads':' plays'):
        hold.conf+' CCG · '+name(l.k)+' leads'+(hold.pair?'':' — a win keeps this spot'));
      const link=hold&&!hold.final?detail({game:hold.game,label:' '}):'';
      const rightHTML=hold?(hold.pair?formatTeam(hold.pair.k,true,metric(hold.pair))+
        '<div class="sw-inline">'+E(note)+'</div>':'<div class="sw-placard">'+E(note)+link+'</div>'):
        r?formatTeam(r.k,!rightIn,metric(r))+'<div class="sw-inline">'+E(r.label)+detail(r)+'</div>':'';
      return '<div class="sw-cut-row"'+(hold?' data-held="'+(hold.pair?'pair':'placard')+'"':'')+'>'+
        '<div'+(l?' data-at-large="'+E(l.k)+'"':'')+'>'+leftHTML+'</div>'+
        '<div'+(r||hold?.pair?' data-thief="'+E((r||hold.pair).k)+'"':'')+'>'+rightHTML+'</div></div>';
    });
    if(rows.length)markup.splice(cutIndex<0?markup.length:cutIndex,0,line);
    if(!rankingOrder)markup.reverse();
    let html='<p class="sw-cut-note">'+(archive?'Last':'Projected last')+' at-large bid: #'+E(board.cut)+'</p>';
    if(board.playIns.length)html+='<p class="sw-muted">Cut starts at #'+E(board.initialCut)+' · '+board.playIns.length+
      ' play-in'+(board.playIns.length===1?'':'s')+' below</p>';
    html+='<div class="sw-head"><span>AT-LARGE TEAMS AT RISK</span><span>BID THIEVES · '+
      (rankingOrder?'LOW TO HIGH':'HIGH TO LOW')+'</span></div>'+markup.join('');
    if(!rows.length)html+='<p>No CCG outcomes change the cut.</p>';
    exceptions.forEach(x=>{html+='<p class="sw-muted sw-exception">‡ '+E(x.note)+'</p>';});
    if(archive)html+='<p class="sw-muted">100% and 0% reflect final CCG results, not historical pregame odds.</p>';
    return html;
  }
  function playInHTML(board,{name,conf,metric=winMetric,source=()=>''}){
    return board.playIns.map(({g,a,b,final,label})=>{
      const side=t=>'<div><strong>#'+E(t.rank)+' '+E(name(t.k))+'</strong><span class="sw-metrics">'+
        metric(t)+'</span>'+(final===t.k?'<small class="sw-playin-winner">'+E(label)+'</small>':'')+'</div>';
      return '<div class="sw-playin-game" data-play-in="'+E(g.id)+'"><p><strong>'+E(conf(g.a)||'Conference championship')+
        '</strong>'+(final?'':' · '+E(label))+(source(g)?' · '+E(source(g)):'')+'</p><div class="sw-pair">'+side(a)+side(b)+'</div></div>';
    }).join('');
  }
  function bindOrder(id, render){
    const button=$(id);
    if(!button)return;
    button.addEventListener('click',()=>{
      rankingOrder=!rankingOrder;
      button.setAttribute('aria-pressed',String(rankingOrder));
      render();
    });
  }
  function paint() {
    if(!lastGood)return;
    paintPicks();
    allFinal=d.ccg.length>0&&d.ccg.every(g=>g.winner||liveScores[g.id]?.final);
    const games=gameById(),leaders={},p={},settled={},holding={};
    for(const g of d.ccg){
      const live=liveScores[g.id]||{},last=g.winner;
      leaders[g.id]=leading(g);
      if(live.live&&live.leader)holding[g.id]=live.leader;
      p[g.id]=last?(last===g.a?1:0):clamp(live.pA??.5);
      if(last)settled[g.id]=last;
      else if(live.final&&live.leader)settled[g.id]=live.leader;
      else if(picks.has(g.id)){
        leaders[g.id]=picks.get(g.id);p[g.id]=leaders[g.id]===g.a?1:0;settled[g.id]=leaders[g.id];
      }
    }
    const board=W.cutBoard(d,leaders,p,settled,holding),odds=W.odds(d,p);
    const locks=absoluteLocks || (absoluteLocks=W.locks(d));
    const shownLocks=picks.size?d.order.filter(t=>(odds[t.k]||0)>=1-1e-10).map(t=>t.k):locks;
    const locked=new Set(shownLocks);
    const labels=board.labels;
    document.querySelectorAll('[data-game-label]').forEach(el=>{el.textContent=labels[el.dataset.gameLabel]||'';});
    const projected=board.projected;
    const toss=new Set(Object.entries(projected).filter(([,v])=>v>0&&v<1).map(([k])=>k));
    const status=d.ccg.filter(g=>g.winner||liveScores[g.id]?.final).length;
    const confirmed=d.ccg.filter(g=>labels[g.id]==='Stolen'&&!picks.has(g.id)).length;
    const whatIfSteals=board.steals-confirmed;
    const provisional=preview==='provisional'||d.provisional, historical=preview==='historical';
    const stamp=updated?updated.toLocaleString('en-US',{timeZone:'America/New_York',dateStyle:'medium',timeStyle:'short'})+' ET':'not yet refreshed';
    const freshness=historical?d.year+' CCG finals · Historical replay':'Updated '+stamp;
    $('sw-status').innerHTML='<b class="sw-flag">'+(provisional?'PROVISIONAL · ':'')+'UNOFFICIAL</b>'+
      '<span>'+E(freshness)+'</span>'+
      '<span>'+status+'/'+d.ccg.length+' CCGs final</span>'+
      '<span><b>'+confirmed+'</b> steals confirmed</span>'+
      (whatIfSteals?'<span><b>'+whatIfSteals+'</b> additional in What-if</span>':'')+
      '<span><b>'+board.leading+'</b> additional currently leading</span>'+
      '<span><b>'+board.possible+'</b> additional possible</span>';
    const name=k=>team(k).name;
    const metric=t=>winMetric(t,margin(games[t.game],t.k));
    content('sw-board-rows',cutHTML(board,{odds,formatTeam:tile,name,metric,detail:t=>{
      const source=picks.has(t.game)?'What-if pick':liveScores[t.game]?.source;
      return (source?(t.label?' · ':'')+E(source):'')+gameLinks(games[t.game]);
    }}));
    $('sw-playins').hidden=!board.playIns.length;
    content('sw-playin-rows',playInHTML(board,{name,conf:k=>team(k).conf,metric,
      source:g=>picks.has(g.id)?"What-if pick":liveScores[g.id]?.source}));
    const bubble=[...new Set([...board.atLarge.map(t=>t.k),...toss])];
    discordDraft=null;
    if(!preview&&!picks.size){
      const complete=d.ccg.every(g=>settled[g.id])&&!toss.size;
      const title=complete?'Projected field locked — pending committee approval':featureName;
      discordDraft={title,html:'<section><h2>'+E(title)+'</h2><p>'+status+'/'+d.ccg.length+
        ' CCGs final · '+confirmed+' steals confirmed</p>'+
        (toss.size?'<p>Coin toss pending at the cut.</p>':'')+
        (bubble.length?'<ul>'+bubble.slice(0,6).map(k=>'<li>'+E(team(k).name)+' · '+percent(odds[k]||0)+'</li>').join('')+'</ul>':'')+
        '<p>DRAFT · Held for owner approval</p></section>'};
    }
    syncDraftButton();
    const bubbleReason=k=>{
      if(toss.has(k))return 'Coin toss · Tied at the projected cut.';
      const row=board.atLarge.find(t=>t.k===k);
      return (row?.status||'At the cut')+' · Can qualify without a CCG win.';
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
    const relevant=new Set([...board.thieves.map(t=>t.game),...board.playIns.map(t=>t.g.id),
      ...board.rows.flatMap(row=>row.hold?[row.hold.game]:[])]);
    const noimpact=d.ccg.filter(g=>!relevant.has(g.id)&&(labels[g.id]==='No bubble impact'||(locked.has(g.a)&&locked.has(g.b))));
    const otherImpact=d.ccg.filter(g=>!relevant.has(g.id)&&!noimpact.includes(g));
    if(otherImpact.length) $('sw-bubble-rows').insertAdjacentHTML('beforeend',
      '<p class="sw-muted"><b>Additional CCGs affecting the bubble:</b> '+
      otherImpact.map(g=>E(team(g.a).name)+' vs '+E(team(g.b).name)+' ('+E(labels[g.id])+')').join(' · ')+'</p>');
    content('sw-noimpact-rows',noimpact.length?noimpact.map(g=>
      '<p>'+E(team(g.a).name)+' vs '+E(team(g.b).name)+' · '+E(labels[g.id])+gameLinks(g)+'</p>').join(''):
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
            source:'Final result',leader:g.winner || (g.pa>g.pb?g.a:g.b),pA:g.winner?(g.winner===g.a?1:0):.5};
        }
      } else if(preview==='provisional') {
        // The CCG baseline does not exist until the real weekly run. Explicitly labeled
        // provisional 50/50 placeholders allow the entire page to render beforehand.
        for(const g of d.ccg){
          nextScores[g.id]={pA:.5,final:false,leader:null,source:'Provisional 50/50',status:'PROVISIONAL · 50/50 placeholder'};
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
        copy.open=true;copy.querySelectorAll('.sw-save, .sw-order button').forEach(b=>b.remove());
        try {await NCAASnap.save({html:copy.outerHTML,title:brand+' '+featureName,name:exportPrefix+'-'+(finalYear?finalYear+'-':'')+btn.dataset.save,
          stamp:finalYear?null:{state:'projection',time:preview==='historical'?null:updated,
            note:preview==='historical'?d.year+' CCG finals · Historical replay':
              preview==='provisional'?'PROVISIONAL':''},
          whatif:finalYear?[]:pickText(),
          footer:brand+' '+featureName+(finalYear?' · '+finalYear+' final results':''),width:650});}
        catch(err){alert('Could not save image: '+err.message);}
        finally{btn.disabled=false;}
      });
    });
  }
  function showFinals(year, archive, sample) {
    const season=archive[year];
    if(!season?.ccg?.length || !season.field?.length)throw Error('No final results available for '+year);
    if(season.cut_board){
      const d=season.cut_board, finals=Object.fromEntries(d.ccg.map(g=>[g.id,g.winner]));
      const p=Object.fromEntries(d.ccg.map(g=>[g.id,g.a===g.winner?1:0]));
      const archivedTile=(k,dim,extra)=>{
        const fill=dim?'':teamFill(d.colors?.[k]||'');
        return '<div class="sw-team'+(dim?' dim':fill?' admitted':'')+'" style="--team:'+
          E(d.colors?.[k]||'var(--neutral)')+fill+'"><strong>'+E(k)+'</strong>'+extra+'</div>';
      };
      const board=W.cutBoard(d,finals,p,finals);
      const render=()=>content('sw-final-cut',cutHTML(board,{archive:true,formatTeam:archivedTile,name:k=>k,
        exceptions:d.exceptions||[]}));
      render();
      bindOrder('sw-final-sort',render);
      $('sw-final-playins').hidden=!board.playIns.length;
      const teams=new Map(d.order.map(t=>[t.k,t]));
      content('sw-final-playin-rows',playInHTML(board,{name:k=>k,conf:k=>teams.get(k)?.conf}));
      const label=board.steals+' steal'+(board.steals===1?'':'s');
      $('sw-final-sort').insertAdjacentHTML('afterend',' <span class="sw-muted">'+E(label)+'</span>');
    }else{
      $('sw-final-sort').hidden=true;
      content('sw-final-cut','<p>A verified cut reconstruction is not available for this season. Recorded finals and the actual field are below.</p>');
    }
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
      season.ccg.map(g=>'<tr><th scope="row">'+E(g.conference)+(g.label?'<small class="sw-score-note">'+E(g.label)+'</small>':'')+'</th><td>'+side(g.a,g.score_a,g.winner===g.a,g.standard_a)+
        '</td><td>'+side(g.b,g.score_b,g.winner===g.b,g.standard_b)+'</td></tr>').join('')+'</tbody></table>'+
      (hasStandard?'<p class="sw-muted">† As played. Standard scoring differs. Recorded results stand.</p>':''));
    const seeded=season.field.every(t=>Number.isInteger(t.seed));
    content('sw-final-field','<'+(seeded?'ol':'ul')+' class="sw-field">'+
      season.field.map(t=>'<li'+(seeded?' value="'+t.seed+'"':'')+'>'+E(t.team)+
        (season.cut_board?.exceptions?.some(x=>x.in===t.team)?' ‡':'')+
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
    fold();
    bindOrder('sw-sort',paint);
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
    window.addEventListener?.('storage',event=>{
      if(event.key==='ncaa180.dev'||event.key===null)syncDraftButton();
    });
    $('sw-discord-draft').addEventListener('click',async()=>{
      if(!devView()||!discordDraft)return;
      const button=$('sw-discord-draft');button.disabled=true;
      try {await NCAASnap.save({...discordDraft,name:exportPrefix+'-discord-draft',
        stamp:{state:'projection',time:updated,note:'Draft · held for approval'},
        footer:brand,width:500});}
      catch(error){alert('Could not save draft: '+error.message);}
      finally{syncDraftButton();}
    });
    if(!preview)document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(timer);else refresh();});
    await refresh();
  } catch(err){alert('Selection Watch unavailable: '+err.message);$('sw-updated').textContent='Unavailable · Unofficial';}
})();
