/* Pure CCG race probability model. Same inputs in browser and Node tests.
 * A real coin toss is NEVER simulated: an unresolved n-way tie awards 1/n
 * probability to each team. Score comparisons are rounded to 0.01.
 * Clinched / Out (Chris, 2026-11-23): with options.bounds (config live_bounds, via
 * ScoreboardCore.bounds), a tie on wins is settled when one team's points-for floor
 * beats the other's ceiling. Each model carries `upside` (most it can still add) and
 * `drop` (most it can still lose) for this week; a model without them settles nothing.
 * LIVE DISPLAY ONLY: the weekly run's postseason flags keep the strict rule.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.CCGRaceModel=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const cents=x=>Math.round((Number(x)||0)*100)/100;
  const key=(league,id)=>String(league)+'|'+String(id);
  const MAX_PROOF_GAMES=16;
  // Exact proof by enumerating every unfinished game that involves a contender.
  // bound: {id: {wins (current, finals counted), floor, ceil}}; games: [{a,b}] unfinished.
  // Returns {clinched: id|null, out: Set} for one division, or null if too many games.
  function proveDivision(ids,bound,games){
    if(games.length>MAX_PROOF_GAMES)return null;
    const beats=(a,b)=>bound[a].floor>bound[b].ceil;
    const gone=Object.fromEntries(ids.map(id=>[id,true]));
    const sure=Object.fromEntries(ids.map(id=>[id,true]));
    for(let mask=0;mask<(1<<games.length);mask++){
      const w=Object.fromEntries(ids.map(id=>[id,bound[id].wins]));
      games.forEach((g,i)=>{const win=(mask>>i)&1?g.a:g.b;if(win in w)w[win]+=1;});
      for(const a of ids){
        const top=ids.every(b=>b===a||w[a]>w[b]||(w[a]===w[b]&&beats(a,b)));
        if(!top)sure[a]=false;
        const behind=ids.some(b=>b!==a&&(w[b]>w[a]||(w[b]===w[a]&&beats(b,a))));
        if(!behind)gone[a]=false;
      }
    }
    const clinched=ids.find(id=>sure[id])||null;
    return {clinched,out:new Set(ids.filter(id=>gone[id]))};
  }
  function random(seed){
    let state=(Number(seed)>>>0)||1, spare=null;
    return function normal(mean,variance){
      if(variance<=0)return cents(mean);
      let z;
      if(spare!==null){z=spare;spare=null;}
      else {
        state^=state<<13;state^=state>>>17;state^=state<<5;
        const u=((state>>>0)+1)/4294967297;
        state^=state<<13;state^=state>>>17;state^=state<<5;
        const v=((state>>>0)+1)/4294967297;
        const amp=Math.sqrt(-2*Math.log(u));
        z=amp*Math.cos(2*Math.PI*v);spare=amp*Math.sin(2*Math.PI*v);
      }
      return cents(Number(mean)+z*Math.sqrt(variance));
    };
  }
  function value(team,field){
    switch(field){
      case 'win_pct': {
        const games=team.wins+team.losses+team.ties;
        return games?(team.wins+team.ties/2)/games:0;
      }
      case 'wins':return team.wins;
      case 'points_for':return cents(team.points_for);
      case 'points_against':return cents(team.points_against);
      default:throw Error('Unsupported tiebreak: '+field);
    }
  }
  function leaders(rows,order){
    let tied=rows.slice();
    for(const field of order){
      if(field==='coin_toss')continue; // a real, never-hidden toss remains undecided
      const best=Math.max(...tied.map(x=>value(x,field)));
      tied=tied.filter(x=>Math.abs(value(x,field)-best)<1e-9);
      if(tied.length<2)break;
    }
    return tied;
  }
  function rank(a,b,order){
    for(const field of order){
      if(field==='coin_toss')continue;
      const delta=value(b,field)-value(a,field);
      if(Math.abs(delta)>1e-9)return delta;
    }
    return String(a.roster_id).localeCompare(String(b.roster_id));
  }
  function simulate(conference,models,options={}){
    const draws=Number(options.sims)||20000,seed=options.seed??2026;
    if(!Number.isInteger(draws)||draws<1||draws>1000000)throw Error('Invalid simulations');
    const order=options.order||['win_pct','points_for','points_against','coin_toss'];
    const normal=random(seed);
    const contestants=conference.divisions.flatMap(d=>d.contenders);
    const unique=new Map(), rosterLeague=String(conference.league_id);
    for(const t of contestants)for(const game of t.remaining_games||[]){
      const a=String(t.roster_id),b=String(game.opponent_roster_id);
      if(a===b)throw Error('Invalid self matchup');
      const id=[a,b].sort().join('|')+'@'+game.week;
      unique.set(id,{a,b,week:game.week});
    }
    const games=[...unique.values()];
    const gamemodel=new Map();
    for(const game of games)for(const id of [game.a,game.b]){
      const k=key(rosterLeague,id);
      if(!models[k])throw Error('Missing live score model for '+k);
      gamemodel.set(k,models[k]);
    }
    const score=(id,drawsByTeam)=>drawsByTeam.get(key(rosterLeague,id));
    const start=t=>({roster_id:String(t.roster_id),wins:t.wins,losses:t.losses,
      ties:t.ties||0,points_for:t.points_for,points_against:t.points_against});
    const winCounts=new Map(contestants.map(t=>[String(t.roster_id),0]));
    const sums=new Map(contestants.map(t=>[String(t.roster_id),{wins:0,losses:0,ties:0,points_for:0,points_against:0}]));
    // Every team in a matchup draws only once, even if both sides are contenders.
    const run=()=>{
      const rows=new Map(contestants.map(t=>[String(t.roster_id),start(t)]));
      const sampled=new Map();
      for(const [k,m]of gamemodel)sampled.set(k,normal(m.mean,m.variance));
      for(const g of games){
        const a=score(g.a,sampled),b=score(g.b,sampled);
        for(const [id,pf,pa] of [[g.a,a,b],[g.b,b,a]]){
          const r=rows.get(id);
          if(!r)continue;
          r.points_for=cents(r.points_for+pf);
          r.points_against=cents(r.points_against+pa);
          if(a===b)r.ties++;
          else if(pf>pa)r.wins++;
          else r.losses++;
        }
      }
      return rows;
    };
    for(let i=0;i<draws;i++){
      const rows=run();
      for(const [id,r]of rows){
        const sum=sums.get(id);
        for(const field of ['wins','losses','ties','points_for','points_against'])sum[field]+=r[field];
      }
      for(const division of conference.divisions){
        const eligible=division.contenders.map(t=>rows.get(String(t.roster_id)));
        const top=leaders(eligible,order);
        for(const t of top)winCounts.set(t.roster_id,winCounts.get(t.roster_id)+1/top.length);
      }
    }
    const expected={};
    for(const [id,sum]of sums){
      expected[id]={roster_id:id};
      for(const field of ['wins','losses','ties','points_for','points_against'])
        expected[id][field]=sum[field]/draws;
    }
    const odds=Object.fromEntries([...winCounts].map(([k,v])=>[k,100*v/draws]));
    const divisions=conference.divisions.map(d=>{
      const projected=d.contenders.map(t=>expected[String(t.roster_id)]).sort((a,b)=>rank(a,b,order))
        .map(t=>t.roster_id);
      const exact=d.contenders.map(t=>start(t));
      const remaining=new Map(d.contenders.map(t=>[String(t.roster_id),
        (t.remaining_games||[]).filter(g=>!models[key(rosterLeague,t.roster_id)]?.final ||
          !models[key(rosterLeague,g.opponent_roster_id)]?.final).length]));
      // A contender with no uncertain games has an exact current record;
      // others can win at most one additional game per unfinished matchup.
      const candidates=d.contenders.map(t=>{
        const id=String(t.roster_id),base=expected[id],left=remaining.get(id);
        return {id,lo:base.wins+base.ties/2-left,hi:base.wins+base.ties/2+left};
      });
      // Only declare a winner early if its guaranteed floor beats all other ceilings.
      let proven=null;
      if(d.clinched_before_week)proven=String(d.contenders[0].roster_id);
      else if(games.every(g=>gamemodel.get(key(rosterLeague,g.a)).final&&gamemodel.get(key(rosterLeague,g.b)).final)){
        const rows=run(),top=leaders(d.contenders.map(t=>rows.get(String(t.roster_id))),order);
        if(top.length===1)proven=top[0].roster_id;
      }else{
        for(const a of candidates)if(candidates.every(b=>a===b||a.lo>b.hi))proven=a.id;
      }
      // Out is also provable individually: once a team has finished its own
      // games, an opponent already above its maximum attainable win total
      // cannot fall behind it. Equal wins leave PF/PA tiebreak possibilities.
      const played=new Map(d.contenders.map(t=>[String(t.roster_id),start(t)]));
      for(const g of games){
        const a=gamemodel.get(key(rosterLeague,g.a)),b=gamemodel.get(key(rosterLeague,g.b));
        if(!a.final||!b.final)continue;
        const sa=cents(a.mean),sb=cents(b.mean);
        for(const [id,pf,pa] of [[g.a,sa,sb],[g.b,sb,sa]]){
          const t=played.get(id);if(!t)continue;
          t.points_for=cents(t.points_for+pf);t.points_against=cents(t.points_against+pa);
          if(sa===sb)t.ties++;else if(pf>pa)t.wins++;else t.losses++;
        }
      }
      const out=d.contenders.filter(t=>{
        const id=String(t.roster_id);
        if(proven)return proven!==id;
        if(!t.remaining_games.every(g=>{
          return gamemodel.get(key(rosterLeague,id))?.final &&
            gamemodel.get(key(rosterLeague,String(g.opponent_roster_id)))?.final;
        }))return false;
        const mine=played.get(id),score=mine.wins+mine.ties/2;
        return [...played].some(([other,row])=>other!==id && row.wins+row.ties/2>score);
      }).map(t=>String(t.roster_id));
      // Proven calls (config live_bounds). Off -> the result above, unchanged.
      if(!d.clinched_before_week&&options.bounds){
        const ids=d.contenders.map(t=>String(t.roster_id)),bound={},open=[];
        const week=Number(options.week);
        for(const t of d.contenders){
          const id=String(t.roster_id),m=models[key(rosterLeague,id)]||{},row=played.get(id);
          // Floor = points so far - drop; ceiling = points so far + upside. Finished games are already
          // in `played`; this week's live points are added while the game is open. A later week, or a
          // model without upside/drop, can't be bounded: its ties stay unknown.
          let ceil=0,live=0,drop=0;
          for(const g of t.remaining_games||[]){
            const now=Number.isFinite(week)?Number(g.week)===week:true;
            if(!now){ceil=Infinity;drop=Infinity;continue;}
            if(m.final&&models[key(rosterLeague,g.opponent_roster_id)]?.final)continue; // counted in played
            live+=Number(m.actual)||0;
            if(m.final)continue;
            ceil+=Number.isFinite(m.upside)?m.upside:Infinity;
            drop+=Number.isFinite(m.drop)?m.drop:Infinity;
          }
          const now=row.points_for+live;
          bound[id]={wins:row.wins+row.ties/2,floor:now-drop,ceil:now+ceil};
        }
        for(const g of games){
          const a=gamemodel.get(key(rosterLeague,g.a)),b=gamemodel.get(key(rosterLeague,g.b));
          if(a.final&&b.final)continue;
          if(ids.includes(g.a)||ids.includes(g.b))open.push(g);
        }
        const res=proveDivision(ids,bound,open);
        if(res){
          if(!proven&&res.clinched)proven=res.clinched;
          const outs=new Set(out);
          for(const id of res.out)outs.add(id);
          if(proven)for(const id of ids)if(id!==proven)outs.add(id);
          return {name:d.name,projected,proven,out:ids.filter(id=>outs.has(id)),bounds:bound};
        }
      }
      return {name:d.name,projected,proven,out};
    });
    return {odds,expected,divisions,draws};
  }
  return {simulate,leaders,rank,key,cents,proveDivision};
});
