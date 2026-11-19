/* The same Games inputs and CCG scoring logic for the browser and timeline recorder. */
(function(root){
  'use strict';
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
  async function load(d,cfg,index,metadata,{get,C,S,modelCache=new Map()}){
    const nextScores={},rank=Object.fromEntries(d.order.map(t=>[t.k,t.rank]));
        if(!index||Number(index.season)!==Number(d.year))throw Error('Active scoreboard does not match Selection Watch season');
        if(!index.weeks.includes(d.ccg_week))throw Error('CCG live baseline is not yet published');
        const baseURL=cfg.data.scoreboard+'/'+d.year+'/week-'+String(d.ccg_week).padStart(2,'0')+'.json';
        const baseline=await get(baseURL);
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
              const finalP=scoreA===scoreB?(tied?.5:(rank[g.a]<rank[g.b]?1:0)):(scoreA>scoreB?1:0);
              // Games coerces its pregame value to Number, so validate the original frozen
              // input here. A blank must not masquerade as a genuine 0% probability.
              const liveP=summary.live?probability(summary.probability):null;
              const pA=winner?(winner===g.a?1:0):summary.final?finalP:
                liveP??frozenProbability(baseline,lid,a,b);
              if(pA===null)throw Error('CCG win chance unavailable: '+g.id);
              const source=winner?'Final result':summary.final?(scoreA===scoreB&&tied?'Coin toss pending':'Final result'):
                liveP!==null?'Live odds':summary.live?'Pregame fallback · live odds unavailable':'Pregame odds';
              nextScores[g.id]={scoreA,scoreB,pA,source,final:!!winner||summary.final,
                leader:winner || (summary.final ? (tied&&scoreA===scoreB?null:(finalP===1?g.a:g.b)) :
                  (summary.started ? scoreA>scoreB?g.a:scoreB>scoreA?g.b:null : null)),
                status:summary.status};
            }
          }
        }
        await Promise.all(Array.from({length:Math.min(4,leagues.length)},worker));
    if(Object.keys(nextScores).length!==d.ccg.length)throw Error('Incomplete CCG update');
    return {scores:nextScores, events:nfl.events};
  }
  const api={load};
  if(typeof module !== 'undefined' && module.exports) module.exports=api;
  root.SelectionWatchGames=api;
})(typeof window==='undefined'?globalThis:window);
