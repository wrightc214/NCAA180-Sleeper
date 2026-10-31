/* League-block overview. A game/roster URL continues to use the detailed scoreboard. */
(async function(){
  'use strict';
  const params=new URLSearchParams(location.search);
  if(params.has('game')||params.has('roster')||params.get('view')==='game')return;
  const $=id=>document.getElementById(id),C=window.ScoreboardCore,S=window.ScoreboardOverview;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=p=>p===null?'—':p<1?'<1%':p>99?'>99%':`${Math.round(p)}%`;
  let cfg,index,metadata,baseline,colors,season,week,generation=0,controller,timer,busy=false,failures=0,metadataAt=0;
  // Only reload on becoming visible if work was interrupted while hidden or data is over a minute old (avoids a duplicate load).
  let pausedHidden=false,loadedAt=Date.now();
  const settings=new Map(),cards=new Map();
  $('game').hidden=true;$('overview-help').hidden=false;
  const wkName=w=>w===cfg.schedule.ccg_week?'CCG Week':`Week ${w}`;
  const title=()=>{document.querySelector('h1').innerHTML=`${esc(cfg.brand||'')} <em>${week===cfg.schedule.ccg_week?'Conference Championships':`Week ${week} Games`}</em>`;};
  async function get(url,signal){
    const abort=new AbortController(),cancel=()=>abort.abort();
    signal?.addEventListener('abort',cancel,{once:true});
    if(signal?.aborted)abort.abort();
    const timeout=setTimeout(cancel,20000);
    try {const r=await fetch(url,{signal:abort.signal,cache:'no-cache'});if(!r.ok)throw Error(`HTTP ${r.status}`);return await r.json();}
    finally{clearTimeout(timeout);signal?.removeEventListener('abort',cancel);}
  }
  function options(el,items,value){el.replaceChildren(...items.map(([v,t])=>{const o=document.createElement('option');o.value=v;o.textContent=t;return o;}));el.value=String(value);}
  function schedule(ms){clearTimeout(timer);if(!document.hidden)timer=setTimeout(()=>refresh(),ms);}
  let kick={next:null,sunday:null};
  function nflGames(data){
    if(Number(data.season?.year)!==season||Number(data.week?.number)!==week||!data.events?.length)throw Error('NFL schedule does not match the selected week');
    const games={};kick={next:null,sunday:null};
    for(const ev of data.events){const st=ev.status||{},type=st.type||{};
      const game={state:type.state,period:Number(st.period||0),clock:st.displayClock||'',kickoff:ev.date,id:ev.id};
      if(type.state==='post'&&!type.completed)game.state='unknown';
      if(type.state==='in'&&!/^\d+:\d\d$/.test(game.clock))throw Error('Live NFL clock unavailable');
      const t=Date.parse(ev.date);
      if(type.state==='pre'&&(kick.next===null||t<kick.next))kick.next=t;
      // First Sunday kickoff of the week: the preview callouts stay up until then.
      if(new Date(ev.date).toLocaleString('en-US',{timeZone:'America/New_York',weekday:'short'})==='Sun'&&(kick.sunday===null||t<kick.sunday))kick.sunday=t;
      for(const comp of ev.competitions||[])for(const side of comp.competitors||[]){const a=side.team?.abbreviation;games[({WSH:'WAS',LA:'LAR',JAC:'JAX'})[a]||a]=game;}
    }return games;
  }
  // CCG week: Sleeper's pairings are placeholders; the frozen baseline carries the real games.
  function pairs(rs,id){if(baseline.pairs){const by=new Map(rs.map(r=>[String(r.roster_id),r]));return baseline.pairs.filter(p=>String(p.LeagueID)===String(id)).map(p=>[p.game,p.rosters.map(x=>by.get(String(x)))]).filter(([,g])=>g.every(Boolean));}
    const groups=new Map();for(const r of rs){if(r.matchup_id==null)continue;const k=String(r.matchup_id);groups.set(k,[...(groups.get(k)||[]),r]);}return [...groups].sort((a,b)=>Number(a[0])-Number(b[0]));}
  // Tuesday odds row for a pair: records, poll ranks, every-week line.
  function oddsRow(id,a,b){return baseline.odds.find(o=>String(o.LeagueID)===String(id)&&[String(o.RosterID),String(o.OpponentRosterID)].sort().join(',')===[String(a),String(b)].sort().join(','));}
  function side(o,rid){if(!o)return {rec:'',rank:''};const mine=String(o.RosterID)===String(rid);return {rec:mine?o.Rec:o.OppRec,rank:mine?o.Rank:o.OppRank};}
  const kickTxt=t=>new Date(t).toLocaleString('en-US',{timeZone:'America/New_York',weekday:'short',hour:'numeric',minute:'2-digit'})+' ET';
  // One row: logo | team (+ record) | Score | Proj | Win %. Same columns in every state (Chris, 2026-10-30).
  function row(r,model,proj,probability,s,winner,info){
    const t=index.leagues[r.leagueId].teams[String(r.roster_id)]||{name:`Roster ${r.roster_id}`};
    const changed=Math.abs(model.actual-model.official)>.011;
    const score=model.played||s.final?`${model.actual.toFixed(2)}${changed?'†':''}`:'–';
    return `<div class="score-row r3${s.final&&winner?' winner':''}"><span class="team-icon" style="background:${esc(t.primary)}">${t.logo?`<img src="${esc(t.logo)}" alt="" onerror="this.hidden=true">`:''}</span><span class="school">${info.rank?`<b class="rk">#${esc(info.rank)}</b> `:''}${esc(t.name)}${info.rec?`<small class="rec">${esc(info.rec)}</small>`:''}</span><span class="score${model.played||s.final?'':' dash'}" title="${changed?`Sleeper: ${model.official.toFixed(2)}`:'Standard score'}">${score}</span><span class="proj">${proj.toFixed(1)}</span><span class="chance">${esc(pct(probability))}</span></div>`;
  }
  function card(g){
    const {id,game,match,s,o}=g,league=index.leagues[id];
    const p=s.probability===null?null:Math.round(s.probability),href=`scoreboard.html?${new URLSearchParams({season,week,league:id,game,overview:$('league').value||'all'})}`;
    const status=s.active?`● Live · ${s.active} playing`:s.final?'Final':s.started?'In progress':s.next?kickTxt(s.next.kickoff):s.status;
    const pre=s.live&&s.pregame!=null?`<div class="ew">Pregame: ${esc(league.teams[String(match[0].roster_id)]?.name)} ${esc(pct(s.pregame))}</div>`:'';
    const ew=!s.started&&o?.EveryWeek?`<div class="ew">If they'd played every week: ${esc(o.EveryWeekLeader?o.EveryWeekLeader+' ':'')}${esc(o.EveryWeek)}</div>`:'';
    return `<a class="mini-match" href="${esc(href)}" aria-label="${esc(league.teams[String(match[0].roster_id)]?.name)} versus ${esc(league.teams[String(match[1].roster_id)]?.name)} — player details"><div class="hdr3"><span></span><span class="match-status${s.active?' is-live':''}">${esc(status)}</span><span>Score</span><span>${s.live?'Live proj':'Proj'}</span><span>${s.live?'Live %':'Pre %'}</span></div>${row(match[0],s.models[0],s.proj[0],p,s,s.models[0].actual>s.models[1].actual,side(o,match[0].roster_id))}${row(match[1],s.models[1],s.proj[1],p===null?null:100-p,s,s.models[1].actual>s.models[0].actual,side(o,match[1].roster_id))}${pre}${ew}</a>`;
  }
  function block(id,rs,scoring,games,stats){
    const league=index.leagues[id],groups=pairs(rs,id);let allFinal=true,warning=false;
    if(rs.length!==Object.keys(league.teams).length||groups.some(([,g])=>g.length!==2)||(baseline.pairs?groups.length!==1:groups.length*2!==rs.length))throw Error('Incomplete matchup response');
    const list=[];
    for(const [game,group]of groups){
      const match=group.map(r=>({...r,leagueId:id})),s=S.summarize(match,metadata,baseline,games,stats,scoring,cfg,week<index.week);
      allFinal&&=s.final;warning||=s.incomplete||s.unknown||(s.started&&!s.final&&s.missing);
      list.push({id,game,match,s,o:oddsRow(id,match[0].roster_id,match[1].roster_id)});
    }
    return {games:list,allFinal,warning};
  }
  const lname=id=>index.leagues[id].label||index.leagues[id].name;
  // Folded conferences are a per-viewer convenience (this browser only).
  function folded(){try{return new Set(JSON.parse(localStorage.getItem('sb-folded')||'[]'));}catch(e){return new Set();}}
  function setFolded(id,on){try{const f=folded();on?f.add(id):f.delete(id);localStorage.setItem('sb-folded',JSON.stringify([...f]));}catch(e){}}
  function header(id,c){
    const theme=colors[id]||{},league=index.leagues[id],g=c?.games||[];
    const live=g.filter(x=>x.s.active).length,fin=g.filter(x=>x.s.final).length,under=g.filter(x=>x.s.started&&!x.s.final&&!x.s.active).length;
    const sum=!c?'':live||fin||under?[live&&`${live} live`,under&&`${under} underway`,fin&&`${fin} final`].filter(Boolean).join(' · '):`${g.length} game${g.length===1?'':'s'}`;
    return `<summary><h2 class="${theme.logo?'has-logo':''}" style="background:${esc(theme.background||'#14213a')};color:${esc(theme.text||'#fff')}">${theme.logo?`<span class="lgtag"><img src="${esc(theme.logo)}" alt="${esc(theme.label||league.name)}" onerror="this.parentElement.replaceWith(this.alt)"></span>`:esc(theme.label||league.name)}<span class="csum">${esc(sum)}</span></h2></summary>`;
  }
  function strip(all,ids){
    if(!all.length)return '';
    const live=all.reduce((a,g)=>a+g.s.active,0),started=all.filter(g=>g.s.started).length,fin=all.filter(g=>g.s.final).length;
    let cls='pre',txt;
    if(fin===all.length){cls='fin';txt=`<b>Final</b> All ${all.length} games final · pregame odds kept for reference`;}
    else if(live){cls='live';txt=`<b>● Live</b> ${live} player${live===1?'':'s'} playing · refreshes every 5 minutes`;}
    else if(started){txt=`<b>In progress</b> ${started} game${started===1?' has':'s have'} started${kick.next?` · next kickoff ${esc(kickTxt(kick.next))}`:''}`;}
    else{txt=`<b>Preview</b> Tuesday projections${kick.next?` · first kickoff ${esc(kickTxt(kick.next))}`:''}`;}
    return `<div class="wkstate wk-${cls}">${txt}</div>`;
  }
  function callouts(){
    if(!baseline||baseline.pairs||!(kick.sunday===null||Date.now()<kick.sunday))return '';
    const odds=baseline.odds.filter(o=>!$('league').value||String(o.LeagueID)===$('league').value);if(!odds.length)return '';
    const gap=o=>Math.abs(Number(o.Proj)-Number(o.OppProj)),wp=o=>Number(o.WinPct);
    const close=odds.reduce((a,o)=>gap(o)<gap(a)?o:a),blow=odds.reduce((a,o)=>gap(o)>gap(a)?o:a);
    const rvr=odds.filter(o=>o.Rank&&o.OppRank).sort((a,b)=>(+a.Rank+ +a.OppRank)-(+b.Rank+ +b.OppRank))[0];
    return `<div class="callouts">${rvr?`<div><b>Game of the week</b>#${esc(rvr.Rank)} ${esc(rvr.Team)} vs #${esc(rvr.OppRank)} ${esc(rvr.OppTeam)} · ${esc(pct(wp(rvr)))} / ${esc(pct(100-wp(rvr)))}</div>`:''}<div><b>Closest projected game</b>${esc(close.Team)} vs ${esc(close.OppTeam)} · ${gap(close).toFixed(1)} pts · ${esc(pct(wp(close)))}</div><div><b>Biggest mismatch</b>${esc(blow.Team)} over ${esc(blow.OppTeam)} by ${gap(blow).toFixed(1)} · ${esc(pct(wp(blow)))}</div></div>`;
  }
  function paint(ids){
    const all=ids.flatMap(id=>cards.get(id)?.games||[]),f=folded(),one=!!$('league').value;
    const rvr=all.filter(g=>g.o?.Rank&&g.o?.OppRank),ranked=all.filter(g=>(g.o?.Rank||g.o?.OppRank)&&!(g.o?.Rank&&g.o?.OppRank));
    const feat=list=>`<div class="feat">${list.map(g=>`<section class="feat-card">${card(g)}</section>`).join('')}</div>`;
    const open=(()=>{try{return localStorage.getItem('sb-ranked-open')==='1';}catch(e){return false;}})();
    let html=strip(all,ids)+callouts();
    if(rvr.length)html+=`<h3 class="sec">Ranked vs ranked <small>${rvr.length} game${rvr.length===1?'':'s'}</small></h3>${feat(rvr)}`;
    if(ranked.length)html+=`<details class="sec-d" id="ranked-d"${open?' open':''}><summary><h3 class="sec">Ranked teams in action <small>${ranked.length} game${ranked.length===1?'':'s'}</small></h3></summary>${feat(ranked)}</details>`;
    html+=`<h3 class="sec">${one?'Games':'By conference'}</h3><div class="conference-grid">`+ids.map(id=>{const c=cards.get(id);
      return `<details class="conference" data-id="${esc(id)}"${one||!f.has(id)?' open':''} aria-label="${esc(lname(id))}">${header(id,c)}${c?.games?c.games.map(card).join(''):'<p class="conference-note">Loading games…</p>'}${c?.warning?'<p class="conference-note">Some stats, projections or statuses are unavailable; estimates may be incomplete.</p>':''}${c?.error?`<p class="conference-error" role="status">${esc(c.error)}${c.updated?` · last updated ${c.updated.toLocaleTimeString()}`:''}</p>`:''}</details>`;}).join('')+'</div>';
    $('board').innerHTML=html;
    for(const d of $('board').querySelectorAll('details.conference'))d.addEventListener('toggle',()=>{if(!one)setFolded(d.dataset.id,!d.open);});
    $('ranked-d')?.addEventListener('toggle',e=>{try{localStorage.setItem('sb-ranked-open',e.target.open?'1':'0');}catch(x){}});
  }
  async function refresh(){
    if(busy||document.hidden)return;busy=true;clearTimeout(timer);$('refresh').disabled=true;
    const turn=generation,signal=controller.signal,ids=Object.keys(index.leagues).filter(id=>!$('league').value||id===$('league').value).sort((a,b)=>lname(a).localeCompare(lname(b)));
    try{
      const [clock,feed]=await Promise.all([get(`${cfg.api.espn}?dates=${season}&week=${week}&seasontype=2`,signal),get(`${cfg.api.sleeper}/stats/nfl/regular/${season}/${week}`,signal)]);
      if(turn!==generation)return;
      const games=nflGames(clock),stats=C.statsMap(feed);
      if(!feed||typeof feed!=='object')throw Error('NFL statistics are unavailable');
      if(Date.now()-metadataAt>900000){try{const m=await get(`${cfg.data.scoreboard}/${season}/players.json`,signal);if(Object.keys(m).length<100)throw Error('Incomplete metadata');metadata=m;metadataAt=Date.now();}catch(e){if(signal.aborted)throw e;throw Error('Player status file unavailable; last scores retained');}}
      let cursor=0,failed=0;
      async function worker(){while(cursor<ids.length){const id=ids[cursor++];try{
        const [rs,league]=await Promise.all([get(`${cfg.api.sleeper}/league/${id}/matchups/${week}`,signal),settings.has(id)?settings.get(id):get(`${cfg.api.sleeper}/league/${id}`,signal)]);
        if(turn!==generation||signal.aborted)return;
        if(!Object.keys(league.scoring_settings||{}).length)throw Error('Scoring settings missing');settings.set(id,league);
        cards.set(id,{...block(id,rs,league.scoring_settings,games,stats),updated:new Date()});
      }catch(e){if(turn!==generation||signal.aborted)return;failed++;cards.set(id,{...cards.get(id),error:`${cards.get(id)?.updated?'STALE — ':'Unavailable — '}${e.message}`});}
      if(turn===generation)paint(ids);}}
      await Promise.all(Array.from({length:Math.min(4,ids.length)},()=>worker()));
      if(turn!==generation||signal.aborted)return;
      failures=failed?failures+1:0;
      const times=ids.map(id=>cards.get(id)?.updated).filter(Boolean);
      loadedAt=Date.now();
      $('updated').textContent=failed?`${ids.length-failed} of ${ids.length} conferences refreshed · see warnings`:`Updated ${new Date().toLocaleTimeString()} · refreshes every 5 minutes until final`;
      $('error').hidden=!failed;$('error').textContent=failed?'Some conferences could not refresh. Last successful scores are retained where available.':'';
      if(failed||ids.some(id=>!cards.get(id)?.allFinal))schedule(failed?Math.min(cfg.refresh.max_backoff_ms,60000*2**Math.min(failures,5)):cfg.refresh.normal_ms);
      else $('updated').textContent=`Updated ${times.length?new Date(Math.min(...times)).toLocaleTimeString():''} · all games final`;
    }catch(e){if(turn!==generation||signal.aborted)return;failures++;for(const id of ids)cards.set(id,{...cards.get(id),error:`${cards.get(id)?.updated?'STALE — ':''}${e.message}`});paint(ids);$('error').hidden=false;$('error').textContent='Refresh failed. Scores below have not been updated. Use Refresh to retry.';$('updated').textContent='Live data unavailable / stale';schedule(Math.min(cfg.refresh.max_backoff_ms,60000*2**Math.min(failures-1,5)));}
    finally{if(turn===generation){busy=false;$('refresh').disabled=false;$('board').setAttribute('aria-busy','false');}}
  }
  async function select(){
    generation++;const turn=generation;controller?.abort();controller=new AbortController();clearTimeout(timer);busy=false;failures=0;
    const newWeek=Number($('week').value);if(newWeek!==week)cards.clear();week=newWeek;title();
    $('updated').textContent='Loading games…';$('board').setAttribute('aria-busy','true');$('refresh').disabled=true;
    const url=new URL(location.href);url.search=new URLSearchParams({season,week,...($('league').value?{league:$('league').value}:{})});history.replaceState(null,'',url);
    paint(Object.keys(index.leagues).filter(id=>!$('league').value||id===$('league').value).sort((a,b)=>lname(a).localeCompare(lname(b))));
    try{const b=await get(`${cfg.data.scoreboard}/${season}/week-${String(week).padStart(2,'0')}.json`,controller.signal);if(turn!==generation)return;baseline=b;await refresh();}
    catch(e){if(turn!==generation)return;$('error').hidden=false;$('error').textContent=`Unable to load this week's pregame data: ${e.message}`;$('updated').textContent='Unable to load games';$('refresh').disabled=false;}
  }
  try{
    cfg=await get('../config/league.json');index=await get(`${cfg.data.scoreboard}/index.json`);season=Number(params.get('season')||index.season);
    if(season!==index.season)throw Error('Only the active season is available');
    week=Number(params.get('week')||index.week);if(!index.weeks.includes(week)||week>cfg.schedule.ccg_week)throw Error('No supported baseline for this week');title();
    [metadata,colors]=await Promise.all([get(`${cfg.data.scoreboard}/${season}/players.json`),get(`${cfg.data.scoreboard}/leagues.json`)]);metadataAt=Date.now();
    options($('week'),index.weeks.filter(w=>w<=cfg.schedule.ccg_week).map(w=>[w,wkName(w)]),week);
    options($('league'),[['','All conferences'],...Object.entries(index.leagues).sort((a,b)=>lname(a[0]).localeCompare(lname(b[0]))).map(([id,l])=>[id,colors[id]?.label||l.label||l.name])],index.leagues[params.get('league')]?params.get('league'):'');
    $('chooser').addEventListener('submit',e=>e.preventDefault());for(const id of ['league','week'])$(id).addEventListener('change',select);
    $('refresh').addEventListener('click',select);
    document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(document.hidden){if(busy||timer)pausedHidden=true;generation++;controller?.abort();busy=false;}else if(pausedHidden||Date.now()-loadedAt>60000){pausedHidden=false;select();}});
    await select();
  }catch(e){$('error').hidden=false;$('error').textContent=e.message;$('updated').textContent='Unable to load scoreboard';}
})();
