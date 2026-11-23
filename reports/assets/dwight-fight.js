/* Dwight Fight: locked-bracket display and historical archive.
   Reads the committed event JSON; no live calculation or redraw in the browser. */
(async()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get=async url=>{const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error(url+' HTTP '+r.status);return r.json()};
  let trophyRows=[];
  const score=v=>v==null||v===''?'—':Number(v).toFixed(2);
  // Same round naming rule as scripts/dwight_fight.py's CSV writer.
  const roundName=(i,total)=>['Final','Semifinal','Quarterfinal'][total-i-1]??(i===0?'First Round':'Round '+(i+1));
  function participant(t){return t?'<span class="dw-team"><b>#'+esc(t.seed)+'</b> '+esc(t.team)+'<small>'+esc(t.display_name||t.username)+'</small></span>':'<span class="dw-team dw-empty">Bye / TBD</span>'}
  function game(g){
    const a=g.a,b=g.b,win=g.winner?.user_id;
    const shown=(t,s,orig)=>'<div class="dw-side '+(t&&win===t.user_id?'dw-win':'')+'">'+participant(t)+'<span class="dw-score">'+score(s)+'</span>'+(g.frozen&&orig!=null&&s!==orig?'<span class="dw-diff" title="Sleeper differs from the score frozen when this round became final">†</span>':'')+'</div>';
    return '<div class="dw-game">'+shown(a,g.score_a,g.snapshot_a)+shown(b,g.score_b,g.snapshot_b)+'</div>';
  }
  function draw(data,cfg){
    const rounds=data.rounds||[];
    const label=data.locked?'Locked bracket':'Initial bracket';
    const status=$('dw-status');
    status.textContent=label+' · '+data.entrants.length+' Dwights · Weeks '+data.start_week+'–'+data.last_week;
    let html='';
    if(data.warnings?.length)html+='<aside class="dw-warn"><strong>Resolution warning — bracket not locked.</strong><p>'+data.warnings.map(esc).join('<br>')+'</p></aside>';
    if(data.champion){
      // Shared trophy component (task 5.1): config/trophies.json holds the Dwight Fight's own plaque geometry.
      const c=data.champion;
      // The ledger row once the weekly job has recorded it; until then the frozen final from this file.
      const row=(trophyRows||[]).find(r=>r.EventType==='DwightFight'&&String(r.Season)===String(data.season))
        ||{EventType:'DwightFight',Event:'Dwight Fight',Team:c.team,Season:data.season};
      const trophy=window.NCAATrophy?.config?NCAATrophy.html(row,null,null,null,{width:300,lazy:false,cls:'dw-trophy'}):'';
      html+='<section class="dw-champion">'+trophy+'<h2>'+esc(c.team)+' wins Dwight Fight</h2></section>';
    }
    html+='<section class="dw-bracket" aria-label="Dwight Fight bracket" style="--dw-rounds:'+rounds.length+'">'+rounds.map((r,i)=>'<div class="dw-round"><h2>'+roundName(i,rounds.length)+' · '+esc(ScoreboardCore.weekLabel(cfg,data.start_week+i,true))+'</h2>'+r.map(game).join('')+'</div>').join('')+'</section>';
    html += '<p class="dw-note">† Sleeper differs from the score used when advancement was frozen.</p>';
    $('dw-main').innerHTML=html;
  }
  function csv(text){
    // Quoted CSV fields, embedded commas and CRLF supported.
    const out=[];let row=[],cell='',q=false;
    for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(q&&text[i+1]==='"'){cell+='"';i++}else q=!q}
      else if(c===','&&!q){row.push(cell);cell=''}
      else if((c==='\n'||c==='\r')&&!q){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(Boolean))out.push(row);row=[];cell=''}
      else cell+=c;
    }if(cell||row.length){row.push(cell);out.push(row)}
    const keys=out.shift()||[];return out.map(a=>Object.fromEntries(keys.map((k,i)=>[k,a[i]||''])));
  }
  function history(rows,inProgressYear){
    const archive=new Map();
    for(const row of rows){
      const year=Number(row.Season);
      if(!Number.isInteger(year)||year<1||year===inProgressYear)continue;
      if(!archive.has(year))archive.set(year,[]);
      archive.get(year).push(row);
    }
    const seasons=[...archive].sort(([a],[b])=>b-a).map(([year,games])=>({
      year,games,
      reconstructed:games.some(r=>r.Status?.startsWith('Reconstructed')),
      winner:games.find(r=>r.RoundName==='Final'&&r.Winner)?.Winner
    }));
    const winners=[{year:2019,winner:'Penn'},{year:2020,display:'Finalist: Penn · champion unknown'},
      ...seasons.filter(s=>s.winner).reverse()];
    const mark=s=>s.reconstructed?'<sup class="dw-reconstructed" aria-label="reconstructed" aria-describedby="dw-reconstruction-note">*</sup>':'';
    const totals=new Map();
    for(const champ of winners){
      if(!champ.winner)continue;
      if(!totals.has(champ.winner))totals.set(champ.winner,[]);
      totals.get(champ.winner).push(champ);
    }
    let html='<h2>Past champions</h2><div class="dw-champs">'+winners.map(c=>
      '<div><b>'+c.year+'</b> '+esc(c.winner||c.display)+mark(c)+'</div>').join('')+'</div>';
    html+='<h3>Title totals</h3><div class="dw-totals">'+[...totals]
      .sort(([a,x],[b,y])=>y.length-x.length||a.localeCompare(b))
      .map(([team,titles])=>'<div><b>'+esc(team)+' '+titles.length+'</b> ('+
        titles.map(c=>c.year+mark(c)).join(', ')+')</div>').join('')+'</div>';
    if(winners.some(c=>c.reconstructed))html+='<p id="dw-reconstruction-note">* Reconstructed bracket; managers may not have set lineups for this event.</p>';
    html+='<h2 class="dw-recorded-title">Recorded brackets</h2>'+seasons.map(({year,games:season,reconstructed})=>{
      const grp={};
      for(const r of season)(grp[r.Round]??=[]).push(r);
      return '<details class="dw-history"><summary>'+year+' · '+season.length+(season.length===1?' game':' games')+
        (reconstructed?' · Reconstructed':'')+'</summary>'+
        (reconstructed?'<p class="dw-reconstruction">Reconstructed: field = that season\'s poll voters; the event was likely not held.</p>':'')+
        '<div class="dw-past">'+Object.keys(grp).sort((a,b)=>a-b).map(k=>'<section><h3>'+esc(grp[k][0].RoundName)+' · Week '+esc(grp[k][0].Week)+'</h3>'+grp[k].map(g=>'<div class="dw-hgame"><span class="'+(g.Winner===g.TeamA?'dw-win':'')+'">#'+esc(g.SeedA)+' '+esc(g.TeamA)+' <b>'+score(g.ScoreA)+'</b></span><span class="'+(g.Winner===g.TeamB?'dw-win':'')+'">#'+esc(g.SeedB)+' '+esc(g.TeamB)+' <b>'+score(g.ScoreB)+'</b></span></div>').join('')+'</section>').join('')+'</div></details>';
    }).join('');
    $('dw-history').innerHTML=html;
  }
  try{
    const cfg=await get('../config/league.json');
    try{await window.NCAATrophy?.load('../');trophyRows=await window.NCAATrophy?.ledger('../')}catch(e){console.warn('trophy config unavailable',e)}
    const idx=await get(cfg.data.scoreboard+'/index.json');
    const year=Number(idx.season);
    let live;
    try{
      live=await get(cfg.data.scoreboard+'/'+year+'/dwight.json');
      draw(live,cfg);
    }
    catch(e){$('dw-status').textContent='Bracket pending · first draw follows the final regular-season week';}
    const response=await fetch('../data/Dwight_Historic.csv');
    if(response.ok)history(csv(await response.text()),live?.champion?null:year);
    else $('dw-history').textContent='History unavailable.';
  }catch(e){$('dw-status').textContent='Dwight Fight data unavailable: '+e.message}
})();
