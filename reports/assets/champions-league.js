/* Special Events → Champions League (Chris, 2026-11-21; planning repo todo/todo-champions-league*.md).
   One script for the Standings, Schedule, Scoreboard, Field and Selection pages (window.CL_PAGE).
   Data: data/scoreboard/<season>/champions-league.json (scripts/champions_league.py, weekly job).
   Team logos/colours: data/scoreboard/index.json (same as the Games page). ?season=YYYY shows another season. */
(async function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=(x,d=0)=>x==null?'—':Number(x).toFixed(d).replace(/\.0+$/,'');
  const ptsTxt=x=>{const v=Math.round(x*100)/100;return Number.isInteger(v)?String(v):v.toFixed(2).replace(/0$/,'');};
  const body=id=>document.querySelector(`.cl-body[data-for="${id}"]`);
  const PAGE=window.CL_PAGE||'standings';
  async function get(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error(`${url}: HTTP ${r.status}`);return r.json();}
  let cfg,index,d;
  try{
    cfg=await get('../config/league.json');
    index=await get(`${cfg.data.scoreboard}/index.json`).catch(()=>({leagues:{}}));
    const season=new URLSearchParams(location.search).get('season')||index.season;
    d=await get(`${cfg.data.scoreboard}/${season}/champions-league.json`);
  }catch(e){$('cl-state').textContent='';const er=$('cl-error');er.hidden=false;er.textContent=`No Champions League data yet (${e.message}).`;return;}

  const bySeed=new Map(d.teams.map(t=>[t.seed,t]));
  const darkBg=h=>{const m=/^#?([0-9a-f]{6})$/i.exec(String(h||''));if(!m)return false;const c=[0,2,4].map(i=>parseInt(m[1].slice(i,i+2),16)/255).map(v=>v<=.03928?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]<.18;};
  const ident=t=>(t&&index.leagues?.[t.lid]?.teams?.[String(t.roster)])||{};
  const icon=t=>{const x=ident(t);return `<span class="team-icon" style="background:${esc(x.primary||'#14213a')}">${x.logo?`<img src="${esc(x.logo_forced||darkBg(x.primary)&&x.logo_dark||x.logo)}" alt="" onerror="this.hidden=true">`:''}</span>`;};
  let mine='';try{const m=window.NCAA180?.myTeam?.();if(m)mine=`${m.conf}:${m.roster}`;}catch(e){}
  const isMine=t=>!!(mine&&t&&`${index.leagues?.[t.lid]?.label||t.league}:${t.roster}`===mine);
  const team=(t,sub)=>`<span class="cl-team">${icon(t)}<span><b>${esc(t.team)}</b><small>${esc(sub??t.league)}</small></span></span>`;
  const wkName=w=>{try{return window.ScoreboardCore?ScoreboardCore.weekLabel(cfg,w,true):`Wk ${w}`;}catch(e){return `Wk ${w}`;}};
  const built=new Date(d.built_at).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});

  if(d.banner){const b=$('cl-banner');b.hidden=false;b.textContent=d.banner;}
  const stateTxt={upcoming:'Starts week '+d.pod_weeks[0],pods:`Through week ${d.through_week} of ${d.pod_weeks[1]}`,cup:`${d.cup_name} in progress`,final:`${d.season} final`}[d.status]||'';
  $('cl-state').textContent=`${d.season} · ${stateTxt} · field from ${d.qualifying_season} · updated ${built} · Unofficial`;

  function standings(){
    const cut=d.cup_size, rows=d.standings;
    const cupSeeds=new Set(d.cup?.seeds||[]);
    let h=`<table class="cl-t"><thead><tr><th>#</th><th class="l">Team</th><th>Pts</th><th title="Weeks beating both">W2</th><th title="Weeks splitting">S</th><th title="Weeks losing both">L2</th><th title="All-play wins">All-play</th><th class="cl-hide-s">Seed</th></tr></thead><tbody>`;
    rows.forEach((r,i)=>{const t=bySeed.get(r.seed);
      const cls=[isMine(t)?'mine':'',i===cut?'cut':''].filter(Boolean).join(' ');
      h+=`<tr class="${cls}"><td>${r.rank}</td><td class="l">${team(t)}${cupSeeds.has(r.seed)?' <span class="cl-chip">'+esc(d.cup_name)+'</span>':''}</td><td><b>${ptsTxt(r.pts)}</b></td><td>${r.sweeps}</td><td>${r.splits}</td><td>${r.losses}</td><td>${ptsTxt(r.allplay)}</td><td class="cl-hide-s">${r.seed}</td></tr>`;});
    body('cl-table').innerHTML=h+`</tbody></table><p class="cl-note">Teams on equal points share a place. The dashed line marks the ${d.cup_name} cut (top ${cut}); a tie there is broken by all-play wins, then best-ball points, head-to-head and a coin toss.</p>`;
    const cupSec=$('cl-cup');
    if(!d.cup){cupSec.hidden=true;return;}
    let c=`<div class="cl-pods"><div class="cl-pod"><h3>${esc(d.cup_name)} · weeks ${d.cup_weeks[0]}–${d.cup_weeks[1]}${d.cup.final?' · final':''}</h3>`;
    const order=[...d.cup.rows].sort((a,b)=>b.total-a.total||a.cup_seed-b.cup_seed);
    order.forEach((r,i)=>{const t=bySeed.get(r.seed);const wk=Object.entries(r.weeks).map(([w,v])=>`Wk ${w}: ${num(v,2)}`).join(' · ');
      c+=`<div class="cl-pr ${i===0?'top':''} ${isMine(t)?'mine':''}"><span class="s">#${r.cup_seed}</span>${team(t,`head start ${r.head_start}${wk?' · '+wk:''}`)}<span class="n">${num(r.total,2)}</span><span class="p">${d.cup.final&&i===0?'🏆':''}</span></div>`;});
    if(d.cup.champion)c+=`<p class="cl-note">Champion: <b>${esc(d.cup.champion.team)}</b>. A tie on the total goes to the higher seed.</p>`;
    body('cl-cup').innerHTML=c+'</div></div>';
  }

  const result=w=>(d.weeks||[]).find(x=>x.week===w);
  function podCard(pod,i,w){
    const res=result(w);const scored=res?res.pods.find(p=>p.map(x=>x.seed).join()===pod.join()):null;
    const rows=pod.map(s=>({s,t:bySeed.get(s),r:scored?.find(x=>x.seed===s)}));
    if(scored)rows.sort((a,b)=>b.r.score-a.r.score);
    return `<div class="cl-pod"><h3>Pod ${i+1}${scored?' · final':''}</h3>`+rows.map((x,k)=>`<div class="cl-pr ${scored&&k===0?'top':''} ${scored&&k===2?'bot':''} ${isMine(x.t)?'mine':''}"><span class="s">#${x.s}</span>${team(x.t)}<span class="n">${x.r?num(x.r.score,2):''}</span><span class="p">${x.r?ptsTxt(x.r.pts):''}</span></div>`).join('')+'</div>';
  }
  function weekPods(w){return `<div class="cl-pods">${(d.schedule[String(w)]||[]).map((p,i)=>podCard(p,i,w)).join('')}</div>`;}
  const weeks=Object.keys(d.schedule).map(Number).sort((a,b)=>a-b);
  const nextWeek=Math.min(Math.max(d.through_week+1,weeks[0]),weeks[weeks.length-1]);

  function schedule(){
    const view=$('cl-view'),pick=$('cl-pick');
    const myT=d.teams.find(isMine);
    const fill=()=>{
      if(view.value==='week'){pick.innerHTML=weeks.map(w=>`<option value="${w}">${esc(wkName(w))}</option>`).join('');pick.value=String(nextWeek);}
      else{pick.innerHTML=[...d.teams].sort((a,b)=>a.team.localeCompare(b.team)).map(t=>`<option value="${t.seed}">${esc(t.team)}</option>`).join('');pick.value=String((myT||d.teams[0]).seed);}
      draw();
    };
    const draw=()=>{
      if(view.value==='week'){body('cl-sched').innerHTML=weekPods(Number(pick.value));return;}
      const s=Number(pick.value);let h=`<table class="cl-t"><thead><tr><th>Wk</th><th class="l">Opponents</th><th>Score</th><th>Pts</th></tr></thead><tbody>`;
      weeks.forEach(w=>{const pod=d.schedule[String(w)].find(p=>p.includes(s));const res=result(w);const me=res?.pods.flat().find(x=>x.seed===s);
        h+=`<tr><td>${w}</td><td class="l">${pod.filter(x=>x!==s).map(x=>team(bySeed.get(x),'#'+x+' · '+bySeed.get(x).league)).join('')}</td><td>${me?num(me.score,2):''}</td><td><b>${me?ptsTxt(me.pts):''}</b></td></tr>`;});
      body('cl-sched').innerHTML=h+'</tbody></table>';
    };
    view.onchange=fill;pick.onchange=draw;
    if(myT)view.value='team';
    fill();
  }

  function scoreboard(){
    const sel=$('cl-wk');sel.innerHTML=weeks.map(w=>`<option value="${w}">${esc(wkName(w))}</option>`).join('');
    sel.value=String(d.through_week&&d.through_week<=weeks[weeks.length-1]?Math.max(d.through_week,weeks[0]):nextWeek);
    const draw=()=>{const w=Number(sel.value);body('cl-week').innerHTML=weekPods(w)+(result(w)?'':'<p class="cl-note">Scores appear once the week is final (live pod scoring is the next build step).</p>');};
    sel.onchange=draw;draw();
  }

  function fieldTable(rows,withSeed=true){
    let h=`<table class="cl-t"><thead><tr>${withSeed?'<th>Seed</th>':''}<th class="l">Team</th><th class="l">Route</th><th title="All-play rank">AP</th><th title="Best-ball rank">BB</th><th title="Final bot poll rank">Poll</th><th title="Sum of the three ranks">Sum</th></tr></thead><tbody>`;
    rows.forEach(r=>{h+=`<tr>${withSeed?`<td>${r.seed}</td>`:''}<td class="l">${r.html}</td><td class="l">${esc(r.route)}</td><td>${r.ap}</td><td>${r.bb}</td><td>${r.poll}</td><td><b>${r.sum}</b></td></tr>`;});
    return h+'</tbody></table>';
  }
  function field(){
    const rows=d.teams.map(t=>({seed:t.seed,html:team(t,t.qualified.qualifying_name!==t.team?`${t.league} · ${t.qualified.qualifying_name} in ${d.qualifying_season}`:t.league),route:t.route,
      ap:t.qualified.allplay_rank,bb:t.qualified.bestball_rank,poll:t.qualified.poll_rank,sum:t.qualified.rank_sum}));
    body('cl-field').innerHTML=`<p class="cl-note">From ${d.qualifying_season} results. AP = all-play rank, BB = best-ball rank, Poll = final bot poll rank; lower sum = stronger. Seeds follow the sum.</p>`+fieldTable(rows);
    const per={};d.teams.forEach(t=>{per[t.league]=(per[t.league]||0)+1;});
    body('cl-leagues').innerHTML='<p>'+Object.entries(per).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([l,n])=>`<span class="cl-chip">${esc(l)} ${n}</span>`).join(' ')+'</p>';
  }

  function selection(){
    const p=d.projection;
    if(!p||!p.shown){body('cl-proj').innerHTML=`<p class="cl-note">The projected ${d.season+1} field appears from week ${p?.starts_week??10}.</p>`;$('cl-out').hidden=true;return;}
    document.body.dataset.snapState='projection';document.body.dataset.snapTime=d.built_at;
    const fmt=r=>({seed:r.Seed,html:`<span class="cl-team"><span><b>${esc(r.Team)}</b><small>${esc(r.League)}${p.playoff_known&&!r.Playoff?' · not in playoff':''}</small></span></span>`,route:r.Route,ap:r.AllPlayRank,bb:r.BestBallRank,poll:r.PollRank,sum:r.RankSum});
    const lines=(p.collapsed||[]).map(c=>`${esc(c.line)}: ${c.team?esc(c.team)+' (already in)':esc(c.why)}`).join(' · ');
    body('cl-proj').innerHTML=`<p class="cl-banner">Projected · Unofficial · ${p.final?'season final':'through week '+p.through_week} · poll week ${p.poll_week??'—'} · ${built}</p><p class="cl-note">If the season ended now: the ${p.for_season} field from ${d.season} results. ${lines?'Ladder lines not adding a team: '+lines+'.':''}</p>`+fieldTable(p.rows.map(fmt));
    body('cl-out').innerHTML=fieldTable(p.out.map(fmt),false);
  }

  ({standings,schedule,scoreboard,field,selection}[PAGE]||standings)();
})();
