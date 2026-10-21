/* One static page; URL selects league/week/game. No credentials or Discord calls. */
(async function() {
  'use strict';
  const C=window.ScoreboardCore, $=id=>document.getElementById(id);
  const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=x=>Number(x).toFixed(2), pct=x=>x<1?'<1%':x>99?'>99%':`${Math.round(x)}%`;
  let cfg,index,baseline,metadata,leagueId,week,season,rosters=[],chosen=[],timer,lastGood=null,failures=0,busy=false,live=false,crunch=false;
  let metadataAt=0,metadataWarning='',abort,resumeNeeded=false;
  const params=new URLSearchParams(location.search);
  async function get(url, signal) {
    const controller=new AbortController();
    const cancel=()=>controller.abort();
    if(signal) signal.addEventListener('abort',cancel,{once:true});
    const timeout=setTimeout(()=>controller.abort(),20000);
    try {
      const r=await fetch(url,{signal:controller.signal,cache:'no-cache'});
      if(!r.ok) {const e=new Error(`Data request failed (HTTP ${r.status})`);e.retry=Number(r.headers.get('Retry-After'))*1000;e.status=r.status;throw e;}
      return await r.json();
    } finally { clearTimeout(timeout);if(signal)signal.removeEventListener('abort',cancel); }
  }
  function setOptions(el, options, value) {
    el.replaceChildren(...options.map(([v,label])=>{const o=document.createElement('option');o.value=v;o.textContent=label;return o;}));
    if(value!==undefined) el.value=String(value);
  }
  function team(rid) {return index.leagues[leagueId].teams[String(rid)] || {name:`Roster ${rid}`,background:'#fff',text:'#14213a',primary:'#14213a',secondary:'#888'};}
  function pairs(rs) {
    const groups=new Map();
    for(const r of rs) {if(r.matchup_id===null||r.matchup_id===undefined)continue;const k=String(r.matchup_id);groups.set(k,[...(groups.get(k)||[]),r]);}
    return [...groups].filter(([,g])=>g.length===2);
  }
  function gameMap(data) {
    if(Number(data.week?.number)!==week || Number(data.season?.year)!==season) throw new Error('Game-clock feed returned a different season/week. Keeping the last good display.');
    if(!Array.isArray(data.events) || !data.events.length) throw new Error('Game-clock feed has no schedule for this week.');
    const map={};
    for(const ev of data.events) {
      const st=ev.status || {}, type=st.type || {};
      const game={id:ev.id,state:type.state,period:Number(st.period||0),clock:st.displayClock||'',kickoff:ev.date,
        label:type.shortDetail||type.detail||'',completed:!!type.completed};
      if(type.state==='post' && !type.completed) game.state='unknown';
      if(type.state==='in' && !/^\d+:\d\d$/.test(game.clock)) throw new Error('Live game clock is missing; keeping the last good display.');
      for(const comp of ev.competitions||[]) for(const side of comp.competitors||[]) {
        const aliases={WSH:'WAS',LA:'LAR',JAC:'JAX'};const ab=side.team?.abbreviation;map[aliases[ab]||ab]=game;
      }
    }
    return map;
  }
  function refreshMetadata(full) {
    for(const [id,p] of Object.entries(full)) {
      const positions=p.fantasy_positions || [p.position];
      if(!positions.some(s=>cfg.position_sd[s])) continue;
      metadata[id]={name:p.full_name || [p.first_name,p.last_name].filter(Boolean).join(' ') || `${id} DEF`,
        position:p.position,positions,team:p.team||'',status:p.injury_status||p.status||''};
    }
    metadataAt=Date.now();metadataWarning='';
  }
  function title(games,models) {
    const starters=models.flatMap(x=>x.starters),active=starters.filter(p=>p.phase==='in');
    live=active.length>0;
    const unique=[...new Map(active.map(p=>[p.game.id,p.game])).values()];
    crunch=unique.some(g=>isNight(g)&&g.period>=4);
    if(active.length) return `<span class="pill"><i class="dot"></i>LIVE</span><div>${unique.length===1?escape(clockLabel(unique[0])):`${active.length} players playing`}</div>`;
    const next=starters.filter(p=>p.phase==='pre').map(p=>p.game).sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff))[0];
    if(next) return `NEXT KICKOFF<div>${escape(new Date(next.kickoff).toLocaleString('en-US',{timeZone:'America/New_York',weekday:'short',hour:'numeric',minute:'2-digit'}))} ET</div>`;
    if(starters.some(p=>p.phase==='unknown')) return 'STATUS UNAVAILABLE';
    return '<span class="pill">FINAL</span>';
  }
  function isNight(g) {
    const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',weekday:'short',hour:'numeric',hourCycle:'h23'}).formatToParts(new Date(g.kickoff));
    const d=parts.find(p=>p.type==='weekday').value,h=Number(parts.find(p=>p.type==='hour').value);
    return (d==='Sun'&&h>=19)||(d==='Mon'&&h>=17);
  }
  function clockLabel(g) {return `${g.period>4?'OT':`Q${g.period}`} ${g.clock}`;}
  function cell(p,right=false) {
    if(!p) return '<div class="pc"></div><div class="ps"></div>';
    const isLive=p.phase==='in',pre=p.phase==='pre';
    const tag=isLive?`<span class="lv"><i class="dot"></i>${p.game.period>4?'OT':`Q${p.game.period}`}<span class="clk"> ${escape(p.game.clock)}</span></span>`:escape(({post:'Final',pre:'',bye:'Bye',out:p.status||'Out',unknown:'No game data'})[p.phase]);
    const name=p.position==='DEF'?`${p.team||p.id} DEF`:p.name.replace(/^(\S)\S+\s/,'$1. ');
    const diff=p.actual-p.baseline,k=Math.min(1,Math.abs(diff)/(cfg.position_sd[p.position]||7));
    const style=p.phase==='post'&&Math.abs(diff)>2?` style="color:color-mix(in srgb,${diff>0?'#1d7a43':'#b3261e'} ${35+65*k}%,var(--ink))"`:'';
    const a=`<div class="pc${right?' r':''}" title="${escape(p.name)}"><b>${escape(name)}</b><small>${escape(p.position)} · ${escape(p.team)} ${tag}</small><small>${p.missingProjection?'proj unavailable':`proj ${p.baseline.toFixed(1)}`}${isLive?` · live ${p.projected.toFixed(1)}`:''}</small></div>`;
    const b=`<div class="ps${isLive?' on':''}"${style}>${p.phase==='unknown'?'—':pre?p.baseline.toFixed(1):money(p.actual)}</div>`;
    return right?b+a:a+b;
  }
  function paired(a,b,slots) {return slots.map((s,i)=>`<div class="pr">${cell(a[i])}<div class="sb s-${escape(s)}">${escape(s)}</div>${cell(b[i],true)}</div>`).join('');}
  function header(r,model,right) {
    const t=team(r.roster_id),odds=baseline.odds.find(o=>o.LeagueID===leagueId && [o.RosterID,o.OpponentRosterID].includes(String(r.roster_id)));
    const record=odds?(odds.RosterID===String(r.roster_id)?odds.Rec:odds.OppRec):'';
    const changed=Math.abs(model.actual-model.official)>.011;
    return `<div class="tm${right?' r':''}">${t.logo?`<img class="logo" src="${escape(t.logo)}" alt="" onerror="this.hidden=true">`:''}<div><span class="pt" style="background:${escape(t.background)};color:${escape(t.text)}">${escape(t.name)}</span><small>${escape(r.ownerName||'Unassigned')} ${record?`· ${escape(record)}`:''}</small></div><div class="sc"><div class="big">${money(model.actual)}${changed?'†':''}</div><small>live proj ${model.projected.toFixed(1)} · ${Math.round(model.minutes)} min left</small>${Math.abs(model.adjustment)>.01?`<small>Includes ${model.adjustment>0?'+':''}${money(model.adjustment)} team adjustment</small>`:''}${changed?`<small>† Sleeper shows ${money(model.official)}</small>`:''}</div></div>`;
  }
  function oddsBar(a,b,p,pre=false,label='LIVE WIN CHANCE · ESTIMATE') {
    const ca=team(a.roster_id),cb=team(b.roster_id);
    // Similar primaries: switch the right side to its official Secondary.
    const rgb=h=>String(h||'').replace('#','').match(/../g)?.map(x=>parseInt(x,16))||[0,0,0];
    const ar=rgb(ca.primary),br=rgb(cb.primary),distance=Math.sqrt(ar.reduce((s,x,i)=>s+(x-br[i])**2,0));
    const colorB=distance<120?cb.secondary:cb.primary;
    return `<div class="olab"><span>${escape(ca.name)} ${escape(pct(p))}</span><span>${label}</span><span>${escape(cb.name)} ${escape(pct(100-p))}</span></div><div class="bar${pre?' pre':''}" role="img" aria-label="${escape(label)}: ${escape(ca.name)} ${escape(pct(p))}"><span style="width:${p}%;background:${escape(ca.primary)}"></span><span style="flex:1;background:${escape(colorB)}"></span></div>`;
  }
  function render(stats,games) {
    const config={...cfg,standard_scoring:baseline.scoring},models=[],playerSets=[];
    const past=week<index.week;
    const warns=[];
    for(const roster of chosen) {
      const players={};
      for(const id of new Set([...(roster.players||[]),...(roster.starters||[])].map(String))) {
        if(id==='0')continue;
        let p=metadata[id];
        if(p && !p.team && baseline.player_info?.[id]?.team) p={...p,team:baseline.player_info[id].team};
        if(past && baseline.player_info?.[id]) p={...p,...baseline.player_info[id],status:''};
        let game=p?.team?games[p.team]||{state:'bye'}:null;
        // A player with real final points but no NFL team is still final, not an empty slot.
        if(!game && past && stats[id]) game={state:'post'};
        const raw=stats[id];
        if(game && game.state!=='pre' && game.state!=='bye' && !raw && Math.abs(C.num(roster.players_points?.[id]))>.01) throw new Error(`Statistics missing for ${p?.name||id}; retaining last good scores.`);
        players[id]=C.playerModel(id,p,raw,baseline.projections[id],game,roster.players_points?.[id],{...config,official_scoring:roster.scoring},past);
        if(players[id].missingMetadata) warns.push(`Missing player metadata: ${id}`);
      }
      const model=C.teamModel(roster,players);
      if(model.starters.some(p=>p.phase==='unknown')) warns.push('Some player game statuses are unavailable; estimates may be incomplete.');
      if(model.starters.some(p=>p.missingProjection)) warns.push('Some starters have no Tuesday projection; live odds are unavailable.');
      // Cross-check complete raw scoring against Sleeper's current rules before showing it.
      const officialRules=roster.scoring;
      const rawOfficial=C.round(model.starters.reduce((sum,p)=>sum+C.score(stats[p.id],officialRules),0));
      if(Math.abs(rawOfficial-model.official)>.12) warns.push(`Raw stats and Sleeper differ for ${team(roster.roster_id).name}; showing Sleeper points plus the standard-rule correction. Please report persistent discrepancies.`);
      models.push(model);playerSets.push(players);
    }
    const [a,b]=models,center=title(games,models),pregame=models.every(m=>m.starters.every(p=>['pre','bye','out'].includes(p.phase)));
    const slots=index.leagues[leagueId].slots;
    const benches=chosen.map((r,i)=>C.benchPlayers(r,playerSets[i],models[i].starters,slots,cfg,pregame));
    let html=`<div class="eyebrow">${escape(index.leagues[leagueId].name)} · ${season} · Week ${week}</div><div class="top">${header(chosen[0],a,false)}<div class="mid">${center}</div>${header(chosen[1],b,true)}</div><div class="odds">`;
    const missing=models.some(m=>m.starters.some(p=>p.missingProjection||p.phase==='unknown'));
    if((a.actual!==0||b.actual!==0||center.includes('FINAL'))&&!missing) html+=oddsBar(...chosen,C.probability(a,b),false,center.includes('FINAL')?'FINAL RESULT':'LIVE WIN CHANCE · ESTIMATE');
    const saved=baseline.odds.find(o=>o.LeagueID===leagueId && [o.RosterID,o.OpponentRosterID].includes(String(chosen[0].roster_id)));
    if(saved) html+=oddsBar(...chosen,saved.RosterID===String(chosen[0].roster_id)?Number(saved.WinPct):100-Number(saved.WinPct),true,'PREGAME · TUESDAY');
    html+=`</div><div class="board"><h2>Starters${pregame?' · projected points':''}</h2>${paired(a.starters,b.starters,slots)}<h2>Bench · ${pregame?'available by position':'would have helped / close calls'}</h2>${paired(benches[0].players,benches[1].players,Array(Math.max(...benches.map(x=>x.players.length))).fill('BN'))}<div class="bz">${benches.map(x=>`<span>${x.zeros} others · 0 pts / bye / out${x.others?` · ${x.others} not shown`:''}</span>`).join('')}</div></div>`;
    $('board').innerHTML=html;
    return [...new Set([...warns,...(metadataWarning?[metadataWarning]:[])])];
  }
  function schedule(ms) {clearTimeout(timer);if(!document.hidden)timer=setTimeout(()=>refresh(),ms);}
  async function refresh() {
    if(busy)return;
    busy=true;clearTimeout(timer);$('refresh').disabled=true;
    for(const id of ['league','week','game']) $(id).disabled=true;
    abort=new AbortController();
    try {
      const base=cfg.api.sleeper;
      const result=await Promise.all([
        get(`${base}/league/${leagueId}/matchups/${week}`,abort.signal),
        get(`${cfg.api.espn}?dates=${season}&week=${week}&seasontype=2`,abort.signal),
        get(`${base}/stats/nfl/regular/${season}/${week}`,abort.signal),
        get(`${base}/league/${leagueId}`,abort.signal),
        get(`${base}/league/${leagueId}/users`,abort.signal),
        get(`${base}/league/${leagueId}/rosters`,abort.signal)
      ]);
      const [rs,espn,feed,league,users,owners]=result;
      if(!Array.isArray(rs)||rs.length!==Object.keys(index.leagues[leagueId].teams).length)throw new Error('Incomplete matchup response; last good display retained.');
      const games=gameMap(espn),stats=C.statsMap(feed);
      if(Object.values(games).some(g=>g.state!=='pre') && Object.keys(stats).length<100)throw new Error('Statistics response is incomplete.');
      if(Date.now()-metadataAt>900000) {
        try {const full=await get(`${base}/players/nfl`,abort.signal);if(Object.keys(full).length<100)throw new Error();refreshMetadata(full);}
        catch(e) {if(abort.signal.aborted)throw e;metadataWarning='Live injury metadata unavailable; saved player metadata is in use.';metadataAt=Date.now()-840000;}
      }
      rosters=rs.map(r=>({...r,scoring:league.scoring_settings||{},ownerName:users.find(u=>u.user_id===owners.find(o=>o.roster_id===r.roster_id)?.owner_id)?.display_name||'Orphan'}));
      if(!Object.keys(league.scoring_settings||{}).length)throw new Error('League scoring settings are missing.');
      const gamesList=pairs(rosters);
      const requested=params.get('game');const requestedRoster=params.get('roster');
      const selected=$('game').value||requested||gamesList.find(([,g])=>g.some(r=>String(r.roster_id)===requestedRoster))?.[0]||gamesList[0]?.[0];
      setOptions($('game'),gamesList.map(([k,g])=>[k,`${team(g[0].roster_id).name} vs ${team(g[1].roster_id).name}`]),selected);
      chosen=gamesList.find(([k])=>k===selected)?.[1];
      if(!chosen)throw new Error('Requested game not found. Select a game above.');
      const warnings=render(stats,games);
      failures=0;lastGood=new Date();
      $('updated').textContent=`Updated ${lastGood.toLocaleTimeString()} · ${live?`auto-refresh ${crunch?'30 seconds':'5 minutes'}`:'manual refresh while no starters are live'}`;
      $('error').hidden=!warnings.length;$('error').textContent=warnings.join(' ');
      const url=new URL(location.href);url.search=new URLSearchParams({season:String(season),league:leagueId,week:String(week),game:selected}).toString();history.replaceState(null,'',url);
      if(live)schedule(crunch?cfg.refresh.crunch_ms:cfg.refresh.normal_ms);
    } catch(e) {
      if(e.name==='AbortError' && document.hidden)return;
      failures++;
      $('error').hidden=false;
      $('error').textContent=`${e.message||'Unable to refresh.'} ${lastGood?`Last successful update: ${lastGood.toLocaleTimeString()}.`:'No live scores have loaded yet.'} Use Refresh to retry. Ping @${cfg.contact.username} on Discord if this persists.`;
      $('updated').textContent=lastGood?`STALE · last good update ${lastGood.toLocaleTimeString()}`:'Live data unavailable';
      schedule(Math.min(cfg.refresh.max_backoff_ms,Math.max(e.retry||0,60000*2**Math.min(failures-1,5))));
    } finally {busy=false;for(const id of ['league','week','game']) $(id).disabled=false;$('refresh').disabled=false;$('board').setAttribute('aria-busy','false');if(resumeNeeded&&!document.hidden){resumeNeeded=false;schedule(0);}}
  }
  async function select() {
    clearTimeout(timer);lastGood=null;$('board').innerHTML='';$('board').setAttribute('aria-busy','true');
    leagueId=$('league').value;week=Number($('week').value);chosen=[];
    for(const id of ['league','week','game']) $(id).disabled=true;
    $('refresh').disabled=true;
    $('updated').textContent='Loading games…';
    $('game').replaceChildren();
    try {
      baseline=await get(`${cfg.data.scoreboard}/${season}/week-${String(week).padStart(2,'0')}.json`);
      await refresh();
    } finally {for(const id of ['league','week','game']) $(id).disabled=false;$('refresh').disabled=false;}
    params.delete('game');params.delete('roster');
  }
  try {
    cfg=await get('../config/league.json');index=await get(`${cfg.data.scoreboard}/index.json`);season=Number(params.get('season')||index.season);
    if(season!==index.season)throw new Error('This scoreboard currently supports the active season only.');
    metadata=await get(`${cfg.data.scoreboard}/${season}/players.json`);
    leagueId=params.get('league')||Object.keys(index.leagues)[0];week=Number(params.get('week')||index.week);
    if(!index.leagues[leagueId])throw new Error('Unknown league in scoreboard URL.');
    if(!index.weeks.includes(week))throw new Error('No frozen pregame data for this week.');
    if(week>=cfg.schedule.ccg_week)throw new Error('Postseason games must use real bracket pairings; Sleeper postseason pairings are not supported.');
    setOptions($('league'),Object.entries(index.leagues).map(([id,v])=>[id,v.name]),leagueId);
    setOptions($('week'),index.weeks.map(w=>[w,`Week ${w}`]),week);
    $('chooser').addEventListener('submit',e=>{e.preventDefault();if(!busy)select().catch(showError);});
    for(const id of ['league','week']) $(id).addEventListener('change',()=>{if(!busy)select().catch(showError);});
    $('game').addEventListener('change',()=>{if(!busy)refresh();});
    $('refresh').addEventListener('click',()=>refresh());
    document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(document.hidden)abort?.abort();else if(!busy)refresh();else resumeNeeded=true;});
    await select();
  } catch(e) {showError(e);}
  function showError(e) {$('error').hidden=false;$('error').textContent=e.message;$('updated').textContent='Unable to load scoreboard';$('board').setAttribute('aria-busy','false');}
})();
