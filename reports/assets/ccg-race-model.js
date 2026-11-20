/* Pure CCG race probability model. Same inputs in browser and Node tests.
 * A real coin toss is NEVER simulated: an unresolved n-way tie awards 1/n
 * probability to each team. Score comparisons are rounded to 0.01.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.CCGRaceModel=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const cents=x=>Math.round((Number(x)||0)*100)/100;
  const key=(league,id)=>String(league)+'|'+String(id);
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
      return {name:d.name,projected,proven};
    });
    return {odds,expected,divisions,draws};
  }
  return {simulate,leaders,rank,key,cents};
});
