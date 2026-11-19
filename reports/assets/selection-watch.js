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
  const probability = value => {
    if(typeof value!=='number' && (typeof value!=='string' || !value.trim()))return null;
    const n=Number(value);
    return Number.isFinite(n)&&n>=0&&n<=100?n/100:null;
  };
  function frozenProbability(baseline,lid,a,b) {
    const ids=[String(a.roster_id),String(b.roster_id)];
    const sameLeague = side => String(side.LeagueID)===lid;
    const game=(baseline.games||[]).find(g=>g.sides?.length===2&&
      ids.every(id=>g.sides.some(side=>sameLeague(side)&&String(side.RosterID)===id)));
    const modern=probability(game?.sides.find(side=>String(side.RosterID)===ids[0])?.WinPct);
    if(modern!==null)return modern;
    const legacy=(baseline.odds||[]).find(o=>sameLeague(o)&&
      [String(o.RosterID),String(o.OpponentRosterID)].sort().join(',')===ids.slice().sort().join(','));
    const fallback=probability(legacy?.WinPct);
    return fallback===null?null:String(legacy.RosterID)===ids[0]?fallback:1-fallback;
  }
  let d,cfg,index,baseline,metadata,brand,featureName,exportPrefix,refreshMs,sort='chance',modelCache=new Map(),liveScores={},
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
  function paint() {
    if(!lastGood)return;
    const games=gameById(),leaders={},p={},margins={};
    for(const g of d.ccg){
      const live=liveScores[g.id]||{},last=g.winner;
      leaders[g.id]=leading(g);
      p[g.id]=last?(last===g.a?1:0):clamp(live.pA??.5);
      margins[g.id]=Math.abs(live.scoreA-live.scoreB)||0;
    }
    const b=W.sortedBoard(d,leaders,p,margins,sort),odds=W.odds(d,p);
    const locks=absoluteLocks || (absoluteLocks=W.locks(d)), locked=new Set(locks);
    const riskOrder=b.atRisk, status=d.ccg.filter(g=>g.winner||liveScores[g.id]?.final).length;
    const confirmed=b.thieves.filter(t=>t.leading&&(games[t.game].winner||liveScores[t.game]?.final)).length;
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
      html+='<div class="sw-pair'+(i===b.k&&b.k<b.thieves.length?' cut':'')+'">'+
        '<div>'+tile(t.team,!t.leading,'<small>'+percent(win)+'</small>')+
        '<span class="sw-inline">'+E(score)+' · '+E(lm.final?'Final':lm.status||'Projected')+
        (t.both_out?' · guaranteed steal':'')+gameLinks(g)+'</span></div>'+
        '<div>'+tile(at,i<b.k,at?'<small>'+percent(risk)+'</small>':'')+
        '<span class="sw-inline">'+(i<b.k?'Below current cut':'Holds if current leaders win')+'</span></div></div>';
    });
    if(!b.thieves.length)html+='<p class="sw-empty">No possible steals. No CCG participants are outside the natural field.</p>';
    content('sw-board-rows',html);
    const bubble=b.atRisk.filter(k=>!locked.has(k));
    const bubbleReason=k=>{
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
    content('sw-lock-rows','<p class="sw-muted">'+locks.length+' teams qualify in every possible outcome.</p><div class="sw-locks">'+
      locks.map(k=>'<span class="sw-lock" style="--tc:'+E(team(k).primary)+'">'+E(team(k).name)+'</span>').join('')+'</div>');
    const relevant=new Set(b.thieves.map(t=>t.game));
    const noimpact=d.ccg.filter(g=>!relevant.has(g.id)&&locked.has(g.a)&&locked.has(g.b));
    const otherImpact=d.ccg.filter(g=>!relevant.has(g.id)&&!(locked.has(g.a)&&locked.has(g.b)));
    if(otherImpact.length) $('sw-bubble-rows').insertAdjacentHTML('beforeend',
      '<p class="sw-muted"><b>Additional CCGs affecting the bubble:</b> '+
      otherImpact.map(g=>E(team(g.a).name)+' vs '+E(team(g.b).name)).join(' · ')+'</p>');
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
        if(!index||Number(index.season)!==Number(d.year))throw Error('Active scoreboard does not match Selection Watch season');
        if(!index.weeks.includes(d.ccg_week))throw Error('CCG live baseline is not yet published');
        const baseURL=cfg.data.scoreboard+'/'+d.year+'/week-'+String(d.ccg_week).padStart(2,'0')+'.json';
        baseline=await get(baseURL);
        const [nfl,raw]=await Promise.all([
          get(cfg.api.espn+'?dates='+d.year+'&week='+d.ccg_week+'&seasontype=2'),
          get(cfg.api.sleeper+'/stats/nfl/regular/'+d.year+'/'+d.ccg_week)]);
        const stats=C.statsMap(raw), clock={};
        if(Number(nfl.season?.year)!==d.year||Number(nfl.week?.number)!==d.ccg_week||!nfl.events?.length)
          throw Error('NFL feed does not match selected week');
        for(const ev of nfl.events){
          const s=ev.status||{},type=s.type||{};
          const gm={state:type.state,period:Number(s.period||0),clock:s.displayClock||'',kickoff:ev.date};
          if(type.state==='post'&&!type.completed)gm.state='unknown';
          for(const comp of ev.competitions||[])for(const side of comp.competitors||[]){
            const ab=side.team?.abbreviation;
            clock[({WSH:'WAS',LA:'LAR',JAC:'JAX'})[ab]||ab]=gm;
          }
        }
        const leagues=[...new Set(d.ccg.flatMap(g=>[g.a.split('|')[0],g.b.split('|')[0]]))];
        let cursor=0;
        async function worker(){
          while(cursor<leagues.length){
            const lid=leagues[cursor++];
            const [rs,league]=await Promise.all([
              get(cfg.api.sleeper+'/league/'+lid+'/matchups/'+d.ccg_week),
              modelCache.has(lid)?modelCache.get(lid):get(cfg.api.sleeper+'/league/'+lid)]);
            if(!modelCache.has(lid))modelCache.set(lid,league);
            const byRoster=Object.fromEntries(rs.map(r=>[String(r.roster_id),{...r,leagueId:lid}]));
            for(const g of d.ccg.filter(g=>g.a.split('|')[0]===lid)){
              const a=byRoster[g.a.split('|')[1]],b=byRoster[g.b.split('|')[1]];
              if(!a||!b)throw Error('CCG lineup unavailable for '+g.id);
              if(!league.scoring_settings)throw Error('League scoring settings unavailable for '+lid);
              const summary=S.summarize([a,b],metadata,baseline,clock,stats,league.scoring_settings,cfg,false);
              // Winner from the real postseason file always takes precedence over a projected leader.
              const winner=g.winner;
              const scoreA=summary.models[0].actual,scoreB=summary.models[1].actual;
              // CCG final ties use the better-ranked team, matching shared postseason rules.
              // If the teams remain tied after all ranking tiebreakers, preserve uncertainty
              // rather than silently choosing whichever the feed listed first.
              const tied=(d.tie||[]).some(group=>group.includes(g.a)&&group.includes(g.b));
              const finalP=scoreA===scoreB?(tied?.5:(byKey()[g.a].rank<byKey()[g.b].rank?1:0)):(scoreA>scoreB?1:0);
              // Games coerces its pregame value to Number, so validate the original frozen
              // input here. A blank must not masquerade as a genuine 0% probability.
              const liveP=summary.live?probability(summary.probability):null;
              const pA=winner?(winner===g.a?1:0):summary.final?finalP:
                liveP??frozenProbability(baseline,lid,a,b);
              if(pA===null)throw Error('CCG win chance unavailable: '+g.id);
              nextScores[g.id]={scoreA,scoreB,pA,final:!!winner||summary.final,
                leader:winner || (summary.final ? (tied&&scoreA===scoreB?null:(finalP===1?g.a:g.b)) :
                  (summary.started ? scoreA>scoreB?g.a:scoreB>scoreA?g.b:null : null)),
                status:summary.status};
            }
          }
        }
        await Promise.all(Array.from({length:Math.min(4,leagues.length)},worker));
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
    if(!finalYear){
      const details=[...document.querySelectorAll(region+' details.sw-section')], collapse=$('sw-collapse');
      const label=()=>{collapse.textContent=details.some(d=>d.open)?'Collapse all':'Expand all';};
      collapse.addEventListener('click',()=>{
        const open=!details.some(d=>d.open); details.forEach(d=>{d.open=open;}); label();
      });
      details.forEach(d=>d.addEventListener('toggle',label));
    }
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
          footer:brand+' '+featureName+(finalYear?' · '+finalYear+' final results':' · Unofficial'),width:650});}
        catch(err){alert('Could not save image: '+err.message);}
        finally{btn.disabled=false;}
      });
    });
  }
  function showFinals(year, archive) {
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
      season.ccg.map(g=>'<tr><th scope="row">'+E(g.conference)+'</th><td>'+side(g.a,g.score_a,g.winner===g.a,g.standard_a)+
        '</td><td>'+side(g.b,g.score_b,g.winner===g.b,g.standard_b)+'</td></tr>').join('')+'</tbody></table>'+
      (hasStandard?'<p class="sw-muted">† As played. Standard scoring differs. Recorded results stand.</p>':''));
    const seeded=season.field.every(t=>Number.isInteger(t.seed));
    content('sw-final-field','<'+(seeded?'ol':'ul')+' class="sw-field">'+
      season.field.map(t=>'<li'+(seeded?' value="'+t.seed+'"':'')+'>'+E(t.team)+
        (!seeded&&Number.isInteger(t.seed)?' (#'+t.seed+')':'')+'</li>').join('')+(seeded?'</ol>':'</ul>'));
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
    exportPrefix=stringSetting(settings?.export_filename_prefix,'ncaa180-selection-watch');
    $('sw-season-picker').hidden=false;
    if(archiveYear){
      if(previewQuery!==null || !/^\d{4}$/.test(archiveYear))throw Error('Choose a season from the archive');
      showFinals(archiveYear,await get('postseason/selection-watch-history.json'));
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
    fold();$('sw-sort').addEventListener('change',e=>{sort=e.target.value;paint();});
    $('sw-refresh').addEventListener('click',refresh);
    if(!preview)document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(timer);else refresh();});
    await refresh();
  } catch(err){alert('Selection Watch unavailable: '+err.message);$('sw-updated').textContent='Unavailable · Unofficial';}
})();
