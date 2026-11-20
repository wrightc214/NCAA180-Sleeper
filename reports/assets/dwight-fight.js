/* Dwight Fight: locked-bracket display and historical archive.
   Reads the committed event JSON; no live calculation or redraw in the browser. */
(async()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get=async url=>{const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error(url+' HTTP '+r.status);return r.json()};
  const path=v=>'../'+String(v||'').split(' ').join('%20');
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
      const c=data.champion, trophy=$('dw-trophy')?.dataset.src||'';
      html+='<section class="dw-champion"><div class="dw-trophy"><img src="'+esc(path(trophy))+'" alt="Dwight Fight trophy"><div class="dw-plaque"><strong>'+esc(c.team)+'</strong><span>'+esc(data.season)+' DWIGHT FIGHT CHAMPION</span></div></div><h2>'+esc(c.team)+' wins Dwight Fight</h2></section>';
    }
    html+='<section class="dw-bracket" aria-label="Dwight Fight bracket" style="--dw-rounds:'+rounds.length+'">'+rounds.map((r,i)=>'<div class="dw-round"><h2>'+roundName(i,rounds.length)+' · '+esc(ScoreboardCore.weekLabel(cfg,data.start_week+i,true))+'</h2>'+r.map(game).join('')+'</div>').join('')+'</section>';
    html += '<p class="dw-note">† Sleeper differs from the score used when advancement was frozen.</p>';
    $('dw-main').innerHTML=html;
    // Responsive plaque engraving: shrink long school names within the art's bounds.
    const plaque=document.querySelector('.dw-plaque');
    if(plaque){
      const fit=()=>{
        const items=[...plaque.children];
        for(const el of items){
          let size=10;
          el.style.fontSize=size+'px';
          while(size>4&&el.scrollWidth>plaque.clientWidth-2){
            el.style.fontSize=(--size)+'px';
          }
        }
      };
      requestAnimationFrame(fit);
      window.addEventListener('resize',fit,{passive:true});
    }
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
    const winners={'2019':'Penn','2020':'Finalist: Penn · champion unknown','2021':'Villanova','2022':'Arizona State','2023':'Arizona State','2024':'No record','2025':'No record'};
    let html='<h2>Past champions</h2><div class="dw-champs">'+Object.entries(winners).map(([y,w])=>'<div><b>'+y+'</b> '+esc(w)+'</div>').join('')+'</div>';
    const years=[...new Set(rows.map(r=>Number(r.Season)))]
      .filter(year=>Number.isInteger(year)&&year>0&&year!==inProgressYear)
      .sort((a,b)=>b-a);
    html+='<h2>Recorded brackets</h2>'+years.map(year=>{
      const season=rows.filter(r=>+r.Season===year),grp={};
      for(const r of season)(grp[r.Round]??=[]).push(r);
      return '<details class="dw-history"><summary>'+year+' · '+season.length+(season.length===1?' game':' games')+'</summary><div class="dw-past">'+Object.keys(grp).sort((a,b)=>a-b).map(k=>'<section><h3>'+esc(grp[k][0].RoundName)+' · Week '+esc(grp[k][0].Week)+'</h3>'+grp[k].map(g=>'<div class="dw-hgame"><span class="'+(g.Winner===g.TeamA?'dw-win':'')+'">#'+esc(g.SeedA)+' '+esc(g.TeamA)+' <b>'+score(g.ScoreA)+'</b></span><span class="'+(g.Winner===g.TeamB?'dw-win':'')+'">#'+esc(g.SeedB)+' '+esc(g.TeamB)+' <b>'+score(g.ScoreB)+'</b></span></div>').join('')+'</section>').join('')+'</div></details>';
    }).join('');
    $('dw-history').innerHTML=html;
  }
  try{
    const cfg=await get('../config/league.json');
    const idx=await get(cfg.data.scoreboard+'/index.json');
    const year=Number(idx.season),art=cfg.postseason.dwight_fight?.logos||{};
    $('dw-trophy').dataset.src=art.trophy||'';
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
