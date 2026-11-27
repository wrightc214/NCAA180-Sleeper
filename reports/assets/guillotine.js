/* Special Events → The Guillotine (CW, 2026-11-14; claude/todo-guillotine.md).
   Every team still alive, sorted by live projection, with score, minutes left and the chance to survive
   the cut; the current and projected cut lines on top; eliminated teams (and the week they went) below.
   Data: data/scoreboard/<season>/guillotine.json (scripts/guillotine.py) for who is still alive and every
   frozen week; the live week is scored in the browser from Sleeper + ESPN, same math as the Games page.
   Refresh: automatic only while Monday Night Football is on (30 s in Q4/OT); otherwise the Refresh button. */
(async function(){
  'use strict';
  const $=id=>document.getElementById(id),C=window.ScoreboardCore,G=window.GuillotineModel;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=p=>p==null?'—':p<1&&p>0?'<1%':p>99&&p<100?'>99%':`${Math.round(p)}%`;
  const params=new URLSearchParams(location.search);
  let cfg,index,gd,metadata,colors,season,week,baseline=null,controller,timer,busy=false,gen=0,failures=0;
  const settings=new Map(),rosters=new Map();
  let lastGames={},lastStats={},mnf={on:false,crunch:false};
  async function get(url,signal){
    const abort=new AbortController(),cancel=()=>abort.abort();
    signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)abort.abort();
    const t=setTimeout(cancel,20000);
    try{const r=await fetch(url,{signal:abort.signal,cache:'no-cache'});if(!r.ok)throw Error(`HTTP ${r.status}`);return await r.json();}
    finally{clearTimeout(t);signal?.removeEventListener('abort',cancel);}
  }
  const wkName=(w,short)=>ScoreboardCore.weekLabel(cfg,w,short);
  // Replay pages (guillotine-<year>.html, Dev only): a past season's leagues have other Sleeper IDs, so
  // colors/logos/labels come from this season's league of the same name; the team name is the one played.
  const replaySrc=document.getElementById('board')?.dataset.src||'';
  let byName={};
  const lid=t=>replaySrc?(byName[t.league]||t.l):t.l;
  const lname=id=>index.leagues[id]?.label||index.leagues[id]?.name||'';
  const ident=t=>{const x=index.leagues[lid(t)]?.teams?.[String(t.r)];return replaySrc?{...(x||{}),name:t.team}:x||{name:t.team};};
  const darkBg=h=>{const m=/^#?([0-9a-f]{6})$/i.exec(String(h||''));if(!m)return false;const c=[0,2,4].map(i=>parseInt(m[1].slice(i,i+2),16)/255).map(v=>v<=.03928?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]<.18;};
  const icon=t=>{const x=ident(t);return `<span class="team-icon" style="background:${esc(x.primary||'#14213a')}">${x.logo?`<img src="${esc(x.logo_forced||darkBg(x.primary)&&x.logo_dark||x.logo)}" alt="" onerror="this.hidden=true">`:''}</span>`;};
  let mine='';try{const m=window.NCAA180?.myTeam?.();if(m)mine=`${m.conf}:${m.roster}`;}catch(e){}
  const isMine=t=>mine&&`${index.leagues[lid(t)]?.label||''}:${t.r}`===mine;
  const teamHex=value=>/^#[0-9a-f]{3}(?:[0-9a-f]{3})?$/i.test(value)
    ? value.replace(/^#(.)(.)(.)$/,'#$1$1$2$2$3$3') : null;
  const adjustInk=(color,background)=>window.NCAA180?.access?.adjust(color,background)||color;
  function myRowStyle(t){
    const team=ident(t),primary=teamHex(team.primary),secondary=teamHex(team.secondary);
    const background=primary||'var(--accent)';
    const ink=primary&&secondary?adjustInk(secondary,primary)
      :primary?(darkBg(primary)?'#fff':'#000'):'var(--on-fill,#fff)';
    const pillInk=adjustInk(secondary||primary||'#14213a','#ffffff');
    return ` style="background:${background};color:${ink};--mute:${ink};--my-odds-ink:${pillInk};box-shadow:none;opacity:1"`;
  }
  const myLabel=' · <b>My Team</b>';
  const resultMark=advanced=>advanced
    ? '<strong aria-hidden="true" style="color:var(--good);background:var(--panel);border-radius:3px;padding:0 3px">✓</strong> '
    : '<strong aria-hidden="true" style="color:var(--bad);background:var(--panel);border-radius:3px;padding:0 3px">×</strong> ';
  function nflGames(data){
    if(Number(data.season?.year)!==season||Number(data.week?.number)!==week||!data.events?.length)throw Error('NFL schedule does not match the selected week');
    const games={};mnf={on:false,crunch:false};
    for(const ev of data.events){const st=ev.status||{},type=st.type||{};
      const game={state:type.state,period:Number(st.period||0),clock:st.displayClock||'',kickoff:ev.date,id:ev.id};
      if(type.state==='post'&&!type.completed)game.state='unknown';
      if(type.state==='in'&&!/^\d+:\d\d$/.test(game.clock))throw Error('Live NFL clock unavailable');
      // Monday Night Football in progress: the only time this page refreshes on its own (CW, 2026-11-14).
      const day=new Date(ev.date).toLocaleString('en-US',{timeZone:'America/New_York',weekday:'short'});
      if(type.state==='in'&&day==='Mon'){mnf.on=true;if(game.period>=4)mnf.crunch=true;}
      for(const comp of ev.competitions||[])for(const side of comp.competitors||[]){const a=side.team?.abbreviation;games[({WSH:'WAS',LA:'LAR',JAC:'JAX'})[a]||a]=game;}
    }return games;
  }
  const alive=()=>gd.teams.filter(t=>t.status==='alive');
  const liveWeek=()=>gd.next_week;
  const frozen=w=>(gd.weeks||[]).find(x=>x.week===w);
  // ---------- paint ----------
  let trophyRows=[];
  // Engraved trophy per champion once the event is final (shared component, task 5.1; season name as played).
  function trophies(){
    if(gd.status!=='final'||!window.NCAATrophy?.config)return '';
    const W=(NCAATrophy.config.display||{}).champion||240;
    return gd.champions.map(c=>{
      const row=trophyRows.find(r=>r.EventType==='Guillotine'&&String(r.Season)===String(gd.season)&&r.LeagueID===c.l&&r.RosterID===c.r)
        ||{EventType:'Guillotine',Event:gd.name,Team:c.team,Season:gd.season};
      return NCAATrophy.html(row,null,null,null,{width:W,lazy:false});
    }).join('');
  }
  function champBanner(){
    if(!gd.champions?.length)return '';
    const co=gd.champions.length>1;
    return `<section class="gl-champ"><img src="${esc(logoFor(gd.last_week))}" alt="${esc(gd.name)} final" onerror="this.hidden=true"><div><div class="eyebrow">${esc(gd.name)} ${co?'co-champions':'champion'}</div>${gd.champions.map(c=>gd.teams.find(t=>t.l===c.l&&t.r===c.r)||c).map(c=>`<div class="gl-cname">${icon(c)} ${esc(ident(c).name)}</div>`).join('')}</div>${trophies()}</section>`;
  }
  function rules(){
    const n=gd.entrants||gd.teams.length;
    return `<details class="gl-rules"><summary>How it works</summary><ul>
      <li>All ${n} teams play Rounds 1–${gd.last_week-gd.first_week+1} (${esc(wkName(gd.first_week,true))} – ${esc(wkName(gd.last_week,true))}), on top of any playoff, bowl or NIT game. No extra lineup work.</li>
      <li>Each week only that week's score counts (standard scoring). Half of the teams still alive survive, rounded down: ${n} → ${Math.floor(n/2)} → ${Math.floor(n/4)} → ${Math.floor(n/8)} → ${Math.floor(n/16)} → 1.</li>
      <li>Ties at the cut line all survive, like a golf cut. The next week's cut is half of whoever is left.</li>
      <li>${esc(wkName(gd.last_week,true))}: the top score wins. An exact tie goes to ${esc(wkName(gd.tiebreak_week,true))}'s score, then co-champions.</li>
      <li>Stat corrections can only add survivors; nobody already through is removed.</li>
      <li><b>% to survive</b> = chance of finishing above the cut, from live projections (points so far + projection × time left) and the same uncertainty as the Games page. Estimates, unofficial while games are live.</li></ul></details>`;
  }
  function weekNav(){
    const ws=(gd.weeks||[]).map(x=>x.week),lw=liveWeek();
    if(lw&&!ws.includes(lw))ws.push(lw);
    if(ws.length<2)return '';
    return `<nav class="weeks sub gl-weeks" aria-label="Weeks"><span>Week</span>${ws.map(w=>`<a href="?week=${w}"${w===week?' aria-current="page"':''}>${esc(wkName(w,true))}</a>`).join('')}</nav>`;
  }
  function outList(){
    const out=gd.teams.filter(t=>t.status==='out').sort((a,b)=>b.out-a.out||(b.scores[b.out]??0)-(a.scores[a.out]??0));
    if(!out.length)return '';
    return `<details class="gl-out sec-d" open><summary><h3 class="sec">Eliminated <small>${out.length} team${out.length===1?'':'s'}</small></h3></summary>
      <div class="gl-table out-t"><div class="gl-h"><span></span><span>Team</span><span>Out</span><span>Score</span></div>
      ${out.map(t=>`<div class="gl-r${isMine(t)?' mine':''}"${isMine(t)?myRowStyle(t):''}>${icon(t)}<span class="gl-t">${esc(ident(t).name)}<small>${esc(lname(lid(t)))} · ${esc(t.owner)}${isMine(t)?myLabel:''}</small></span><span class="gl-w">${isMine(t)?resultMark(false):''}${esc(wkName(t.out,true))}</span><span class="gl-n">${Number(t.scores[t.out]??0).toFixed(2)}</span></div>`).join('')}</div></details>`;
  }
  function liveRows(){
    const field=gd.status==='final'?[]:alive();
    const K=G.target(field.length,week,gd.last_week);
    const items=field.map(t=>{const r=rosters.get(`${t.l}|${t.r}`);
      if(!r||!baseline)return {t,m:null};
      const m=G.team(r.roster,r.scoring,metadata,baseline,lastGames,lastStats,cfg,week<index.week);
      return {t,m};});
    const have=items.filter(x=>x.m),started=have.some(x=>x.m.played),allFinal=have.length&&have.every(x=>x.m.final);
    for(const x of have){x.proj=started?x.m.projected:x.m.pregame;x.sd=allFinal?0:x.m.sd;}
    const odds=have.length===items.length?G.advanceOdds(have.map(x=>({mu:allFinal?x.m.actual:x.proj,sd:x.sd})),K):[];
    // Live: 100% / 0% only when proven (config live_bounds); an estimate never reaches either.
    const calls=started&&!allFinal&&have.length===items.length?G.provenCalls(have.map(x=>x.m),K,cfg.live_bounds):[];
    have.forEach((x,i)=>{
      const o=odds[i]??null;
      x.call=calls[i]||null;
      x.odds=x.call==='safe'?100:x.call==='cut'?0:o==null||allFinal||!started?o:Math.min(99.999,Math.max(0.001,o));
    });
    items.sort((a,b)=>(b.m?b.proj:-1e9)-(a.m?a.proj:-1e9)||ident(a.t).name.localeCompare(ident(b.t).name));
    const cur=started?G.cutLine(have.map(x=>x.m.actual),K):null,proj=G.cutLine(have.map(x=>x.proj),K);
    return {items,K,cur,proj,started,allFinal,missing:items.length-have.length};
  }
  let sortColumn='projection',sortDirection=-1;
  const scoreValue=x=>x.m&&(x.m.played||x.m.final)?x.m.actual:null;
  const sortValues={
    team:x=>ident(x.t).name,
    score:scoreValue,
    projection:x=>x.proj,
    minutes:x=>x.m?Math.round(x.m.minutes):null,
    odds:x=>x.odds,
  };
  function sortHeader(column,label){
    const active=column===sortColumn;
    const direction=sortDirection===1?'ascending':'descending';
    return `<span><button type="button" data-gl-sort="${column}" aria-label="${label}${active?`, sorted ${direction}`:''}" style="font:inherit;color:inherit;text-transform:inherit;letter-spacing:inherit;background:none;border:0;padding:0;cursor:pointer;text-align:inherit">${label}${active?` <span aria-hidden="true">${sortDirection===1?'↑':'↓'}</span>`:''}</button></span>`;
  }
  function liveView(){
    const L=liveRows(),last=week>=gd.last_week,n=L.items.length;
    const label=last?'% to win':'% to survive';
    const head=`<section class="gl-head card">
      <div class="gl-k"><b>${n}</b><span>alive</span></div>
      <div class="gl-k"><b>${L.K}</b><span>${last?'champion':'survive'}</span></div>
      <div class="gl-k"><b>${L.cur==null?'—':L.cur.toFixed(2)}</b><span>${last?'leading score':'current cut line'}</span></div>
      <div class="gl-k proj"><b>${L.proj==null?'—':L.proj.toFixed(1)}</b><span>${last?'projected winning score':'projected cut line'}</span></div></section>`;
    const value=sortValues[sortColumn];
    L.items.sort((a,b)=>{
      const left=value(a),right=value(b);
      if(left==null||right==null)return Number(left==null)-Number(right==null);
      return sortDirection*(sortColumn==='team'?left.localeCompare(right):left-right);
    });
    const projectedCut=sortColumn==='projection';
    const oddsCut=sortColumn==='odds';
    const cut=last?null:projectedCut?L.proj:sortColumn==='score'?L.cur:oddsCut?50:null;
    const cutLabel=cut==null?'':oddsCut?'50% to advance':projectedCut?`Projected cut · ${cut.toFixed(1)}`:`Current cut · ${cut.toFixed(2)}`;
    let rows='',previousBelow=null,hasBubble=false;
    L.items.forEach(x=>{
      const points=value(x);
      if(cut!=null&&points!=null){
        const below=points<cut-(oddsCut?0:G.EPS);
        if(previousBelow!=null&&previousBelow!==below){
          rows+=`<div class="gl-cut"><span>${cutLabel}</span></div>`;
        }
        previousBelow=below;
      }
      const bubble=x.odds!=null&&x.odds<50;
      hasBubble ||= bubble;
      const mineRow=isMine(x.t),m=x.m;
      const warning=bubble&&mineRow?`<strong role="img" aria-label="Less than 50% chance to ${last?'win':'survive'}" style="color:var(--on-fill);background:var(--bad-fill);border-radius:3px;padding:0 2px">!</strong> `:'';
      const oddsStyle=mineRow?' style="background:#fff;color:var(--my-odds-ink);border-radius:999px;padding:1px 3px;text-align:center;white-space:nowrap"'
        :bubble?' style="background:var(--bad-soft);border-radius:4px"':'';
      const cls=[m&&m.live?'live':'',mineRow?'mine':''].filter(Boolean).join(' ');
      rows+=`<div class="gl-r ${cls}"${mineRow?myRowStyle(x.t):''}>${icon(x.t)}<span class="gl-t">${esc(ident(x.t).name)}<small>${esc(lname(lid(x.t)))} · ${esc(x.t.owner)}${mineRow?myLabel:''}${m?.incomplete?' · stats incomplete':''}</small></span>
        <span class="gl-n sc">${m&&(m.played||m.final)?m.actual.toFixed(2):'–'}</span><span class="gl-n pj">${m?x.proj.toFixed(1):'–'}</span>
        <span class="gl-n mn">${m?Math.round(m.minutes):'–'}</span><span class="gl-n od"${oddsStyle}>${warning}${esc(pct(x.odds))}</span></div>`;
    });
    const state=L.allFinal?'Final · waiting for the weekly run to lock the cut':L.started?'Live':'Preview · Tuesday projections';
    const line=baseline?`<p class="gl-state">${esc(wkName(week))} · ${esc(state)}${L.missing?` · ${L.missing} team${L.missing===1?'':'s'} not loaded`:''}</p>`:'';
    const legend=hasBubble?`<p class="gl-state">Shading or ! indicates less than a 50% chance to ${last?'win':'survive'}.</p>`:'';
    return `${head}${line}${legend}
      <div class="gl-table live-t"><div class="gl-h"><span></span>${sortHeader('team','Team')}${sortHeader('score','Score')}${sortHeader('projection',L.started&&!L.allFinal?'Live proj':'Proj')}${sortHeader('minutes','Min left')}${sortHeader('odds',label)}</div>${rows}</div>`;
  }
  function frozenView(w){
    const f=frozen(w),last=w>=gd.last_week;
    const field=gd.teams.filter(t=>t.scores[w]!=null).sort((a,b)=>b.scores[w]-a.scores[w]);
    let rows='',drawn=false;
    field.forEach(t=>{
      const through=last?t.status==='champion':t.out!==w,added=(t.added||[]).includes(w);
      if(!drawn&&!through&&!last){rows+=`<div class="gl-cut final" aria-hidden="true"><span>Cut line · ${Number(f.cutline).toFixed(2)}</span></div>`;drawn=true;}
      const result=through?(last?'Champion':'Survived'):last&&t.status==='tied'?'Tied':t.out===w?'Out':'';
      const mark=isMine(t)&&(through||result==='Out')?resultMark(through):'';
      rows+=`<div class="gl-r${through?'':' gone'}${isMine(t)?' mine':''}"${isMine(t)?myRowStyle(t):''}>${icon(t)}<span class="gl-t">${esc(ident(t).name)}<small>${esc(lname(lid(t)))} · ${esc(t.owner)}${isMine(t)?myLabel:''}${added?' · added after stat corrections':''}</small></span><span class="gl-n sc">${t.scores[w].toFixed(2)}</span><span class="gl-w">${mark}${result}</span></div>`;
    });
    const head=`<section class="gl-head card"><div class="gl-k"><b>${f.field}</b><span>played</span></div><div class="gl-k"><b>${f.advanced}</b><span>${last?'champion':'survived'}</span></div><div class="gl-k"><b>${Number(f.cutline).toFixed(2)}</b><span>${last?'winning score':'cut line'}</span></div>${f.added?`<div class="gl-k"><b>${f.added}</b><span>added by stat corrections</span></div>`:''}</section>`;
    return `${head}<p class="gl-state">${esc(wkName(w))} · Final</p><div class="gl-table fz-t"><div class="gl-h"><span></span><span>Team</span><span>Score</span><span></span></div>${rows}</div>`;
  }
  // CW's logos: the round logo for the week on screen; the plain wordmark before the first week.
  function logoFor(w){const L=gd.logos||{},src=L.weeks?.[String(w)]||L.wordmark||'';return src?'../'+src.split(' ').join('%20'):'';}
  function paint(){
    const lg=$('gl-logo'),src=logoFor(gd.status==='upcoming'&&!frozen(week)&&!baseline?null:week);
    if(lg&&src&&lg.getAttribute('src')!==src){lg.setAttribute('src',src);lg.alt=`${gd.name} · ${wkName(week)}`;}
    let body=champBanner()+weekNav();
    if(gd.status==='upcoming'&&!baseline)body+=`<p class="gl-state">Starts ${esc(wkName(gd.first_week,true))}: all ${gd.entrants} teams. Projections appear here once that week's postseason games are set.</p>`;
    if(frozen(week))body+=frozenView(week);else if(week===liveWeek())body+=liveView();
    body+=outList()+rules();
    const focusedSort=document.activeElement?.dataset.glSort;
    $('board').innerHTML=body;
    if(focusedSort)$('board').querySelector(`[data-gl-sort="${focusedSort}"]`)?.focus({preventScroll:true});
  }
  // ---------- data ----------
  function schedule(){
    clearTimeout(timer);timer=null;
    if(document.hidden||week!==liveWeek())return;
    if(failures){timer=setTimeout(refresh,Math.min(cfg.refresh.max_backoff_ms,60000*2**Math.min(failures,5)));return;}
    if(mnf.on)timer=setTimeout(refresh,mnf.crunch?cfg.refresh.crunch_ms:cfg.refresh.normal_ms);
  }
  async function refresh(){
    if(busy)return;
    if(week!==liveWeek()||!baseline){paint();$('updated').textContent=frozen(week)?`${wkName(week)} · final`:'';$('refresh').disabled=week!==liveWeek();return;}
    busy=true;$('refresh').disabled=true;const turn=gen,signal=controller.signal;
    try{
      const [clock,feed]=await Promise.all([get(`${cfg.api.espn}?dates=${season}&week=${week}&seasontype=2`,signal),get(`${cfg.api.sleeper}/stats/nfl/regular/${season}/${week}`,signal)]);
      if(turn!==gen)return;
      lastGames=nflGames(clock);lastStats=C.statsMap(feed);
      // Only conferences that still have a team alive (week 1: all of them; later weeks far fewer).
      const ids=[...new Set(alive().map(t=>String(t.l)))];
      let cursor=0,failed=0;
      async function worker(){while(cursor<ids.length){const id=ids[cursor++];try{
        const [rs,league]=await Promise.all([get(`${cfg.api.sleeper}/league/${id}/matchups/${week}`,signal),settings.has(id)?settings.get(id):get(`${cfg.api.sleeper}/league/${id}`,signal)]);
        if(turn!==gen)return;settings.set(id,league);
        for(const r of rs)rosters.set(`${id}|${r.roster_id}`,{roster:r,scoring:league.scoring_settings});
      }catch(e){if(turn!==gen||signal.aborted)return;failed++;}}}
      await Promise.all(Array.from({length:Math.min(4,ids.length)},()=>worker()));
      if(turn!==gen)return;
      failures=failed?failures+1:0;paint();
      $('error').hidden=!failed;$('error').textContent=failed?`${failed} conference${failed===1?'':'s'} could not refresh; their last scores are kept.`:'';
      $('updated').textContent=`Updated ${new Date().toLocaleTimeString()} · Unofficial · ${mnf.on?`refreshes every ${mnf.crunch?'30 seconds':'5 minutes'} during Monday Night Football`:'tap Refresh for new scores'}`;
    }catch(e){if(turn!==gen||signal.aborted)return;failures++;paint();$('error').hidden=false;$('error').textContent=`Refresh failed: ${e.message}. Scores below have not been updated.`;}
    finally{if(turn===gen){busy=false;$('refresh').disabled=false;schedule();}}
  }
  async function select(){
    gen++;controller?.abort();controller=new AbortController();clearTimeout(timer);busy=false;failures=0;
    baseline=null;
    if(week===liveWeek()&&index.weeks.includes(week)){
      try{baseline=await get(`${cfg.data.scoreboard}/${season}/week-${String(week).padStart(2,'0')}.json`,controller.signal);}catch(e){baseline=null;}
    }
    paint();await refresh();
  }
  try{
    cfg=await get('../config/league.json');index=await get(`${cfg.data.scoreboard}/index.json`);season=Number(index.season);
    if(replaySrc){
      gd=await get(replaySrc);season=Number(gd.season);
      for(const [id,l] of Object.entries(index.leagues))byName[l.name]=id;
    }else gd=await get(`${cfg.data.scoreboard}/${season}/guillotine.json`);
    try{await window.NCAATrophy?.load('../');trophyRows=await window.NCAATrophy?.ledger('../')}catch(e){console.warn('trophy config unavailable',e)}
    // A replay is final: no live week, so no player feed.
    if(!replaySrc)[metadata,colors]=await Promise.all([get(`${cfg.data.scoreboard}/${season}/players.json`),get(`${cfg.data.scoreboard}/leagues.json`)]);
    const want=Number(params.get('week'));
    const choices=[...(gd.weeks||[]).map(x=>x.week),liveWeek()].filter(Boolean);
    week=choices.includes(want)?want:liveWeek()||Math.max(...choices);
    $('board').addEventListener('click',event=>{
      const button=event.target.closest('button[data-gl-sort]');
      if(!button)return;
      const column=button.dataset.glSort;
      sortDirection=column===sortColumn?-sortDirection:column==='team'?1:-1;
      sortColumn=column;
      paint();
    });
    $('refresh').addEventListener('click',()=>{failures=0;refresh();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(timer);timer=null;}else if(mnf.on)refresh();});
    await select();
  }catch(e){$('error').hidden=false;$('error').textContent=gd?e.message:`${e.message}. The Guillotine starts in the postseason.`;$('updated').textContent='';}
})();
