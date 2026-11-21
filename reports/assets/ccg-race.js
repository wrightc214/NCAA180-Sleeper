/* CCG race live feed: follows Games scoreboard fetches, throttling and scoring.
 * Never substitutes official Sleeper standings for NCAA 180 standard scoring.
 */
(async function(){
 'use strict';
 const $=id=>document.getElementById(id), C=window.ScoreboardCore,
       S=window.ScoreboardOverview, M=window.CCGRaceModel;
 const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>Number(x)||0;
 const route=new URLSearchParams(location.search);
 let cfg,settings,index,metadata,baseline,data,leagueColors,week,season;
 let timer=null,busy=false,failures=0,lastGood=null,started=false;
 const records=new Map(),leagueCfg=new Map();
 let refreshMs=300000,gen=0,unit='conference';
 async function get(path){const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),20000);
   try{const r=await fetch(path,{cache:'no-cache',signal:abort.signal});if(!r.ok)throw Error('HTTP '+r.status+' — '+path);return await r.json();}
   finally{clearTimeout(timeout);}
 }
 function warn(text){$('warning').hidden=!text;$('warning').textContent=text||'';}
 function date(d){return new Date(d).toLocaleString('en-US',{timeZone:'America/New_York',dateStyle:'short',timeStyle:'short'})+' ET';}
 const fmt=p=>p<1?'<1%':p>99?'>99%':Math.round(p)+'%';
 function contrast(color,requested){
   const lum=h=>{const v=/^#([0-9a-f]{6})$/i.exec(h||'');if(!v)return 0;
     const a=[0,2,4].map(i=>parseInt(v[1].slice(i,i+2),16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
     return .2126*a[0]+.7152*a[1]+.0722*a[2];};
   const bg=lum(color),ok=lum(requested);
   const ratio=x=>(Math.max(bg,x)+.05)/(Math.min(bg,x)+.05);
   return /^#[\da-f]{6}$/i.test(requested||'')&&ratio(ok)>=4.5?requested:
     (ratio(0)>ratio(1)?'#000000':'#ffffff');
 }
 function nflGames(clock){
   if(num(clock.season?.year)!==season||num(clock.week?.number)!==week||!clock.events?.length)throw Error('NFL schedule mismatch');
   const games={};
   for(const ev of clock.events){
     const st=ev.status||{},type=st.type||{};
     const game={state:type.state,period:num(st.period),clock:st.displayClock||'',kickoff:ev.date};
     if(type.state==='post'&&!type.completed)game.state='unknown';
     if(type.state==='in'&&!/^\d+:\d\d$/.test(game.clock))throw Error('Live NFL clock unavailable');
     for(const comp of ev.competitions||[])for(const side of comp.competitors||[]){
       const a=side.team?.abbreviation,alias={WSH:'WAS',LA:'LAR',JAC:'JAX'};
       games[alias[a]||a]=game;
     }
   }
   return games;
 }
 function renderShell(){
   const host=$('conferences');host.replaceChildren();
   const byId=new Map(data.conferences.map(c=>[String(c.league_id),c]));
   const ids=Object.keys(index.leagues).filter(id=>byId.has(id));
   for(const id of ids){
     const conf=byId.get(id),sec=document.createElement('section');sec.id='ccg-'+id;
     const head=document.createElement('h2');head.textContent=conf.name;
     const body=document.createElement('div');body.className='content';body.textContent='Loading live projections…';
     sec.append(head,body);host.append(sec);
   }
   if(!started){
     started=true;
     const script=document.createElement('script');script.src='assets/sections.js';document.body.append(script);
   }
 }
 // Colour strength = chance to win the division (Chris, 2026-11-20): the card is the team colour
 // blended into the card background by the odds (Colorado 70% -> 70% colour, ASU 30% -> 30%);
 // <1% and Out get none, Clinched is full. Text and logo are picked for the blended colour, so every
 // card stays readable at any strength. Out teams are also dimmed (eliminated rule).
 function strength(id,odds,proven,out){
   if(proven)return proven===id?100:0;
   if(out?.includes(id))return 0;
   const p=Number(odds[id])||0;
   return p<1?0:Math.min(100,p);
 }
 function panelHex(){
   const raw=getComputedStyle(document.documentElement).getPropertyValue('--panel').trim();
   if(/^#[\da-f]{6}$/i.test(raw))return raw;
   const m=raw.match(/\d+/g);return m&&m.length>=3?'#'+m.slice(0,3).map(x=>(+x).toString(16).padStart(2,'0')).join(''):'#ffffff';
 }
 function mix(team,base,p){
   if(!/^#[\da-f]{6}$/i.test(team))return base;
   const c=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
   const t=c(team),b=c(base),f=p/100;
   return '#'+t.map((v,i)=>Math.round(v*f+b[i]*(1-f)).toString(16).padStart(2,'0')).join('');
 }
 function isDark(hex){
   return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).reduce((acc,v,i)=>acc+[.2126,.7152,.0722][i]*(v<=.04045?v/12.92:((v+.055)/1.055)**2.4),0)<.18;
 }
 function lumHex(h){
   return [1,3,5].map(i=>parseInt(h.slice(i,i+2),16)/255).reduce((acc,v,i)=>acc+[.2126,.7152,.0722][i]*(v<=.04045?v/12.92:((v+.055)/1.055)**2.4),0);
 }
 const ratioHex=(a,b)=>{const x=lumHex(a),y=lumHex(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
 const HEX=/^#[\da-f]{6}$/i;
 // Dark-mode colour swap (Chris, 2026-11-20): on the dark panel a team whose main colour nearly matches
 // the card (Auburn #0C2340 on #16213a is 1.01:1) would show no tint at any odds. When its text colour
 // stands out from the panel, use that as the card colour and the main colour as the preferred text.
 // Thresholds live in config (ccg.dark_swap); light mode never swaps.
 function cardColours(info,panel){
   const bg=info.background||info.primary||'#14213a',text=info.text;
   const sw=settings.dark_swap||{},maxBg=Number(sw.max_background_contrast)||1.5,minText=Number(sw.min_text_contrast)||3;
   if(isDark(panel)&&HEX.test(bg)&&HEX.test(text||'')&&ratioHex(bg,panel)<maxBg&&ratioHex(text,panel)>=minText)
     return {team:text,text:bg,swapped:true};
   return {team:bg,text:text,swapped:false};
 }
 // Game indicator (Chris, 2026-11-20): record and PF share one line; the next line is the team's own game.
 // Margin = this team's mean minus the opponent's mean, from the same models the odds use.
 //   Record   8-2 · PF 1752.16
 //   Pregame  Proj W by 22.16 vs Oregon
 //   Live     Leading by 8.40 vs Oregon · Proj W by 22.16
 //   Final    W 141.20–118.94 vs Oregon
 // PF before final = season PF + this week's projection; after final = the actual total. No ± on the card.
 // Missing game model (team or opponent): PF only, no margin.
 const f2=x=>Number(x).toFixed(2);
 function gameState(m){return m.state||(m.final?'final':(Number(m.actual)||0)>0?'live':'pregame');}
 function gameLine(conf,t,models){
   const lid=String(conf.league_id),me=models?.[M.key(lid,t.roster_id)];
   const game=(t.remaining_games||[]).find(g=>Number(g.week)===Number(data.week));
   const oppId=game?String(game.opponent_roster_id):null;
   const opp=oppId?models?.[M.key(lid,oppId)]:null;
   const season=Number(t.points_for)||0;
   if(!me||!opp||!oppId)return {text:'',pf:'PF '+f2(season),state:'missing'};
   const st=gameState(me),final=st==='final';
   const oppName=index.leagues[lid]?.teams?.[oppId]?.name||'opponent';
   const vs=' vs '+oppName;
   const pf='PF '+f2(final?season+Number(me.actual):season+Number(me.mean));
   if(final){
     const a=Number(me.actual),b=Number(opp.actual),r=a>b?'W':a<b?'L':'T';
     return {text:r+' '+f2(a)+'–'+f2(b)+vs,pf,state:st};
   }
   const d=Math.round((Number(me.mean)-Number(opp.mean))*100)/100;
   const proj=d>0?'Proj W by '+f2(d):d<0?'Proj L by '+f2(-d):'Proj even';
   if(st==='pregame')return {text:proj+vs,pf,state:st};
   const g=Math.round((Number(me.actual)-Number(opp.actual))*100)/100;
   const now=g>0?'Leading by '+f2(g):g<0?'Trailing by '+f2(-g):'Tied';
   return {text:now+vs+' · '+proj,pf,state:st};
 }
 function teamTile(conf,t,models,odds,leader,proven,out,stamp){
   const id=String(t.roster_id),info=index.leagues[String(conf.league_id)]?.teams?.[id]||{};
   const panel=panelHex(),colours=cardColours(info,panel),team=colours.team;
   const isOut=proven?proven!==id:!!out?.includes(id);
   const p=strength(id,odds,proven,out);
   const bg=p>0?mix(team,panel,p):panel;
   const style=p>0?'background:'+bg+';border-color:'+bg+';color:'+contrast(bg,colours.text):'';
   const img=(p>=50&&info.logo_forced)||(isDark(bg)&&info.logo_dark?info.logo_dark:info.logo)||info.logo_forced||''; // logos.force (#124) on strong team colour
   const status=proven?(proven===id?(settings.labels?.clinched||'Clinched'):(settings.labels?.out||'Out')):(out?.includes(id)?(settings.labels?.out||'Out'):fmt(odds[id]||0));
   const line=gameLine(conf,t,models);
   return '<div class="race-team'+(leader===id?' leader':'')+(isOut?' out':'')+'" data-strength="'+p.toFixed(1)+'"'+
     (colours.swapped?' data-swapped="1"':'')+
     (style?' style="'+E(style)+'"':'')+'>'+
     (img?'<img src="'+E(img)+'" alt="">':'<span aria-hidden="true"></span>')+
     '<div><strong>'+E(t.team)+'</strong><small class="owner">@'+E(t.owner)+'</small>'+
     '<small class="record">'+E(t.wins)+'-'+E(t.losses)+(t.ties?'-'+E(t.ties):'')+' · '+E(line.pf)+'</small>'+
     (line.text?'<small class="game" data-state="'+E(line.state)+'">'+E(line.text)+'</small>':'')+'</div><span class="prob">'+E(status)+'</span></div>';
 }
 const cap=w=>String(w).replace(/(^|\s)\S/g,c=>c.toUpperCase());
 function CCGRaceOrder(status,odds){
   const out=new Set(status.out||[]),pos=new Map(status.projected.map((x,i)=>[x,i]));
   const tier=x=>status.proven===x?0:out.has(x)?2:1;
   return status.projected.slice().sort((a,b)=>tier(a)-tier(b)||(odds[b]||0)-(odds[a]||0)||pos.get(a)-pos.get(b));
 }
 let lastPaint=null;
 try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(lastPaint)paint(...lastPaint);});}catch(e){}
 function paint(models,results,stamp,stale=false){
   lastPaint=[models,results,stamp,stale];
   $('updated').textContent=(stale?'Stale — last verified ':'Last updated ')+date(stamp);
   document.body.dataset.snapTime=new Date(stamp).toISOString();
   const map=new Map(data.conferences.map(c=>[String(c.league_id),c]));
   for(const [id,conf]of map){
     const node=document.querySelector('#ccg-'+CSS.escape(id)+' .content');
     if(!node)continue;
     const result=results[id];
     if(!result){node.textContent='Live projections unavailable for this '+unit+'.';continue;}
     const divs=conf.divisions.map((d,i)=>{
       const status=result.divisions[i];
       const byId=new Map(d.contenders.map(t=>[String(t.roster_id),t]));
       // Highlight and order by the page's own odds (Chris, 2026-11-20): clinched team first, then
       // highest chance, Out last; projected record only breaks exact ties.
       const ids=CCGRaceOrder(status,result.odds);
       const leader=ids[0];
       const shown=d.clinched_before_week?[byId.get(status.proven||ids[0])]:ids.map(x=>byId.get(x));
       return '<div class="division"><h3>'+E(d.name)+'</h3>'+
         shown.filter(Boolean).map(t=>teamTile(conf,t,models,
           result.odds,leader,status.proven,status.out,stamp)).join('')+'</div>';
     });
     node.innerHTML='<div class="divisions">'+divs.join('')+'</div>'+
       '<div class="capture-note">Unofficial — live projections · '+E(date(stamp))+
       ' · '+E(result.draws)+' simulations · Standard scoring</div>';
   }
 }
 function teamScores(id,rs,scoring,events,stats){
   const groups=new Map();
   for(const r of rs){if(r.matchup_id==null)continue;const k=String(r.matchup_id);
     groups.set(k,[...(groups.get(k)||[]),r]);}
   const all={};
   for(const group of groups.values()){
     if(group.length!==2)throw Error('Incomplete matchup in '+id);
     const match=group.map(r=>({...r,leagueId:id}));
     const summary=S.summarize(match,metadata,baseline,events,stats,scoring,cfg,false);
     if(summary.missing||summary.unknown||summary.incomplete)
       throw Error('Missing live player score or baseline for '+id);
     for(let i=0;i<2;i++){
       const r=match[i],m=summary.models[i],rid=String(r.roster_id);
       // Preserve the Tuesday baseline for games that have not started.
       const pre=!summary.started&&!summary.final;
       all[M.key(id,rid)]={
         mean:summary.final?C.round(m.actual):pre?m.pregame:m.projected,
         variance:summary.final?0:pre?Math.pow(Number(cfg.spread)||24,2):m.variance,actual:m.actual,final:summary.final,
         state:summary.final?'final':pre?'pregame':'live'
       };
     }
   }
   return all;
 }
 async function fetchLive(){
   const [clock,raw]=await Promise.all([
     get(cfg.api.espn+'?dates='+season+'&week='+week+'&seasontype=2'),
     get(cfg.api.sleeper+'/stats/nfl/regular/'+season+'/'+week)
   ]);
   const events=nflGames(clock),stats=C.statsMap(raw);
   if(!raw||typeof raw!=='object')throw Error('Missing live statistics');
   const ids=data.conferences.map(c=>String(c.league_id)),models={};
   let n=0;const errors=[];
   async function worker(){
     while(n<ids.length){
       const id=ids[n++];
       try{
         const [rs,lg]=await Promise.all([
           get(cfg.api.sleeper+'/league/'+id+'/matchups/'+week),
           leagueCfg.has(id)?leagueCfg.get(id):get(cfg.api.sleeper+'/league/'+id)
         ]);
         if(!Object.keys(lg.scoring_settings||{}).length)throw Error('Missing scoring settings');
         leagueCfg.set(id,lg);
         Object.assign(models,teamScores(id,rs,lg.scoring_settings,events,stats));
       }catch(e){errors.push(id+': '+e.message);}
     }
   }
   await Promise.all(Array.from({length:Math.min(4,ids.length)},()=>worker()));
   const results={};
   for(const conf of data.conferences){
     const id=String(conf.league_id);
     try{results[id]=M.simulate(conf,models,{
       sims:settings.simulations||20000,seed:(settings.seed??2026)+Number(id.slice(-7)),
       order:data.tiebreak_order
     });}catch(e){errors.push(id+': '+e.message);}
   }
   if(!Object.keys(results).length)throw Error('No complete live '+unit+' models — '+errors.slice(0,2).join('; '));
   return {models,results,errors,stamp:new Date().toISOString()};
 }
 function schedule(delay){clearTimeout(timer);if(!document.hidden)timer=setTimeout(refresh,delay);}
 async function refresh(){
   if(busy||document.hidden)return;busy=true;clearTimeout(timer);$('refresh').disabled=true;
   try{
     const next=await fetchLive();lastGood=next;failures=0;
     paint(next.models,next.results,next.stamp);
     warn(next.errors.length?next.errors.length+' '+unit+' issue(s): '+next.errors.join(' · '):'');
     const allFinal=Object.values(next.models).length&&Object.values(next.models).every(m=>m.final);
     // Incomplete conferences must continue retrying even if the other games are all final.
     if(next.errors.length||!allFinal)schedule(next.errors.length?Math.min(num(cfg.refresh?.max_backoff_ms)||1800000,120000):refreshMs);
   }catch(e){
     failures++;if(lastGood)paint(lastGood.models,lastGood.results,lastGood.stamp,true);
     warn('Live update failed; '+(lastGood?'showing last verified projections. ':'no verified projections. ')+e.message);
     schedule(Math.min(num(cfg.refresh?.max_backoff_ms)||1800000,60000*2**Math.min(failures,5)));
   }finally{busy=false;$('refresh').disabled=false;}
 }
 try{
   [cfg,settings]=await Promise.all([get('../config/league.json'),get('../config/selection_watch.json')]);
   settings=settings.ccg||{};
   if(settings.labels?.title){document.querySelector('h1').textContent=settings.labels.title;document.title=settings.labels.title+' | '+(cfg.brand||'NCAA 180');}
   if(settings.labels?.unofficial)$('flag').textContent=settings.labels.unofficial;
   document.body.dataset.snapTag=settings.export_filename_prefix||'ncaa180-ccg-race';
   week=Number(cfg.schedule.ccg_week)-1;
   const current=await get(cfg.data.scoreboard+'/index.json');
   season=Number(current.season);
   index=current;
   // Configurable unit term (config unit_term; league_config.term()): "Conference Championships".
   unit=cfg.unit_term?.singular||'conference';
   document.querySelector(".eyebrow").textContent="Selection Watch / "+cap(unit)+" Championships";
   const q=route.get('preview');
   if(q===null && Number(index.week)!==week)throw Error(settings.availability_message||"CCG race is active only during the final regular-season week.");
   let dataURL='postseason/ccg-race-'+season+'.json';
   if(q!==null){
     const matches=Object.values(settings.previews||{}).filter(profile=>
       profile.enabled===true&&profile.query===q&&typeof profile.url==='string'&&profile.url);
     if(matches.length!==1)throw Error('Unknown or disabled preview');
     dataURL=matches[0].url;
   }
   try{data=await get(dataURL);}catch(e){
     if(e.message.includes('404'))throw Error(settings.availability_message||'CCG races are not yet available.');
     throw e;
   }
   if(data.season!==season||data.week!==week||!data.conferences?.length)
     throw Error('CCG race data has the wrong season, week or no conferences.');
   refreshMs=Number(settings.refresh_interval_ms||cfg.refresh?.normal_ms)||300000;
   if(!Number.isFinite(refreshMs)||refreshMs<1000)refreshMs=300000;
   [metadata,baseline,leagueColors]=await Promise.all([
     get(cfg.data.scoreboard+'/'+season+'/players.json'),
     get(cfg.data.scoreboard+'/'+season+'/week-'+String(week).padStart(2,'0')+'.json'),
     get(cfg.data.scoreboard+'/leagues.json')
   ]);
   if(!baseline.projections||!baseline.scoring)throw Error('Tuesday baseline unavailable');
   renderShell();
   if(q!==null){
     // Preview is entirely local: no Sleeper/ESPN calls or fabricated live percentages.
     const models=data.preview_models;
     if(!models)throw Error('Preview model fixture missing');
     const results={};
     for(const conf of data.conferences)results[String(conf.league_id)]=M.simulate(conf,models,{
       sims:settings.simulations||20000,seed:settings.seed??2026,order:data.tiebreak_order
     });
     paint(models,results,new Date().toISOString());
     $('updated').textContent='PREVIEW fixture — not live · '+date(new Date());
     $('flag').textContent='PREVIEW — unofficial, simulated';
     $('refresh').hidden=true;
     return;
   }
   $('refresh').addEventListener('click',refresh);
   document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden)refresh();});
   await refresh();
 }catch(e){warn(e.message);$('updated').textContent='CCG races unavailable';}
})();
