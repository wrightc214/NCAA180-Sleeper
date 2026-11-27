/* The Guillotine: pure model functions (browser + Node tests). Uses ScoreboardCore for scoring.
   Rules: config postseason.guillotine; claude/todo-guillotine.md (CW, 2026-11-14). */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./scoreboard-core.js'));else root.GuillotineModel=factory(root.ScoreboardCore);})(typeof globalThis!=='undefined'?globalThis:this,function(C){
  'use strict';
  const EPS=1e-9;
  // How many advance this week: half the field, rounded down; the last week crowns one.
  function target(field,week,last){return week>=last?1:Math.floor(field/2);}
  // One roster's live model (same inputs and math as the Games page, ScoreboardOverview.summarize).
  function team(r,scoring,metadata,baseline,games,stats,cfg,past=false){
    let incomplete=false;const players={};
    for(const id of (r.starters||[]).map(String)){
      if(id==='0')continue;
      let p=metadata[id];
      if(past&&baseline.player_info?.[id])p={...p,...baseline.player_info[id],status:''};
      if(p&&!p.team&&baseline.player_info?.[id]?.team)p={...p,team:baseline.player_info[id].team};
      let game=p?.team?games[p.team]||{state:'bye'}:null;
      if(!game&&past&&stats[id])game={state:'post'};
      if(game&&!['pre','bye'].includes(game.state)&&!stats[id]&&Math.abs(C.num(r.players_points?.[id]))>.01)incomplete=true;
      players[id]=C.playerModel(id,p,stats[id],baseline.projections[id],game,r.players_points?.[id],{...cfg,standard_scoring:baseline.scoring,official_scoring:scoring},past);
    }
    const m=C.teamModel(r,players);
    const st=m.starters;
    m.live=st.some(p=>p.phase==='in');
    m.final=!m.live&&!st.some(p=>p.phase==='pre'||p.phase==='unknown')&&st.some(p=>p.phase==='post');
    m.incomplete=incomplete;
    m.sd=Math.sqrt(Math.max(m.variance,0));
    return m;
  }
  // The k-th best value, with everyone tied with it counted in (PGA style).
  function cutLine(values,k){
    const v=values.filter(Number.isFinite).sort((a,b)=>b-a);
    if(!v.length||k<=0)return null;return v[Math.min(k,v.length)-1];
  }
  function mulberry(seed){return function(){seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
  // Chance each team finishes inside the top k (ties at the line advance). models: [{mu, sd}].
  // Monte Carlo with a fixed seed, so the same inputs always give the same numbers (no flicker on refresh).
  function advanceOdds(models,k,sims=4000,seed=180){
    const n=models.length;if(!n)return [];
    if(k>=n)return models.map(()=>100);
    const rnd=mulberry(seed),hits=new Float64Array(n),draw=new Float64Array(n),sorted=new Float64Array(n);
    for(let s=0;s<sims;s++){
      for(let i=0;i<n;i++){const m=models[i];
        if(m.sd>1e-6){let u=0,v=0;while(u===0)u=rnd();v=rnd();draw[i]=m.mu+m.sd*Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);}else draw[i]=m.mu;
        sorted[i]=draw[i];}
      sorted.sort();const line=sorted[n-k];
      for(let i=0;i<n;i++)if(draw[i]>=line-EPS)hits[i]++;
    }
    return Array.from(hits,h=>100*h/sims);
  }
  // Proven calls (CW, 2026-11-23; config live_bounds, ScoreboardCore.bounds). LIVE DISPLAY ONLY.
  // Safe: at most k-1 other teams can still finish above this team's floor (ties at the line survive).
  // Cut: at least k other teams are already certain to finish above this team's ceiling.
  function provenCalls(models,k,lb){
    const b=models.map(m=>C.bounds(m,lb));
    if(!lb||b.some(x=>!x))return models.map(()=>null);
    return b.map((me,i)=>{
      const above=b.filter((o,j)=>j!==i&&o.ceil>me.floor).length;
      if(above<=k-1)return 'safe';
      const sure=b.filter((o,j)=>j!==i&&o.floor>me.ceil).length;
      return sure>=k?'cut':null;
    });
  }
  return {target,team,cutLine,advanceOdds,provenCalls,EPS};
});
