/* Shared scoring engine, compact matchup summaries. Also usable in Node checks. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./scoreboard-core.js'));else root.ScoreboardOverview=factory(root.ScoreboardCore);})(typeof globalThis!=='undefined'?globalThis:this,function(C){
  'use strict';
  function summarize(rosters,metadata,baseline,games,stats,scoring,cfg,past=false) {
    let incomplete=false;
    const models=rosters.map(r=>{
      const players={};
      for(const id of (r.starters||[]).map(String)) {
        if(id==='0')continue;
        let p=metadata[id];
        if(past&&baseline.player_info?.[id])p={...p,...baseline.player_info[id],status:''};
        if(p&&!p.team&&baseline.player_info?.[id]?.team)p={...p,team:baseline.player_info[id].team};
        let game=p?.team?games[p.team]||{state:'bye'}:null;
        if(!game&&past&&stats[id])game={state:'post'};
        if(game&&!['pre','bye'].includes(game.state)&&!stats[id]&&Math.abs(C.num(r.players_points?.[id]))>.01)incomplete=true;
        players[id]=C.playerModel(id,p,stats[id],baseline.projections[id],game,r.players_points?.[id],{...cfg,standard_scoring:baseline.scoring,official_scoring:scoring},past);
      }
      return C.teamModel(r,players);
    });
    const starters=models.flatMap(m=>m.starters),active=starters.filter(p=>p.phase==='in');
    const unknown=starters.some(p=>p.phase==='unknown');
    const next=starters.filter(p=>p.phase==='pre').map(p=>p.game).sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff))[0];
    const final=!active.length&&!next&&!unknown&&(starters.some(p=>p.phase==='post')||Object.values(games).every(g=>g.state==='post'));
    const started=starters.some(p=>p.phase==='post'||p.phase==='in'||p.actual!==0);
    const missing=unknown||incomplete||starters.some(p=>p.missingProjection);
    const saved=baseline.odds.find(o=>String(o.LeagueID)===String(rosters[0].leagueId)&&
      [String(o.RosterID),String(o.OpponentRosterID)].sort().join(',')===rosters.map(r=>String(r.roster_id)).sort().join(','));
    const pregame=saved?(String(saved.RosterID)===String(rosters[0].roster_id)?Number(saved.WinPct):100-Number(saved.WinPct)):null;
    return {models,final,active:active.length,next,unknown,incomplete,missing,started,
      probability:unknown?null:final||!started?pregame:missing?null:C.probability(...models),
      oddsLabel:final||!started?'Pregame %':'Live win %',
      status:unknown?'Status unavailable':final?'Final':active.length?'Live':started?'In progress':'Upcoming'};
  }
  return {summarize};
});
