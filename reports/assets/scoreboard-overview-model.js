/* Shared scoring engine, compact matchup summaries. Also usable in Node checks. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./scoreboard-core.js'));else root.ScoreboardOverview=factory(root.ScoreboardCore);})(typeof globalThis!=='undefined'?globalThis:this,function(C){
  'use strict';
  function summarize(rosters,metadata,baseline,games,stats,scoring,cfg,past=false) {
    let incomplete=false;
    // scoring: one league's settings, or an array per roster (cross-league postseason games)
    const models=rosters.map((r,i)=>{const sc=Array.isArray(scoring)?scoring[i]:scoring;
      const players={};
      for(const id of (r.starters||[]).map(String)) {
        if(id==='0')continue;
        let p=metadata[id];
        if(past&&baseline.player_info?.[id])p={...p,...baseline.player_info[id],status:''};
        if(p&&!p.team&&baseline.player_info?.[id]?.team)p={...p,team:baseline.player_info[id].team};
        let game=p?.team?games[p.team]||{state:'bye'}:null;
        if(!game&&past&&stats[id])game={state:'post'};
        if(game&&!['pre','bye'].includes(game.state)&&!stats[id]&&Math.abs(C.num(r.players_points?.[id]))>.01)incomplete=true;
        players[id]=C.playerModel(id,p,stats[id],baseline.projections[id],game,r.players_points?.[id],{...cfg,standard_scoring:baseline.scoring,official_scoring:sc},past);
      }
      return C.teamModel(r,players);
    });
    const starters=models.flatMap(m=>m.starters),active=starters.filter(p=>p.phase==='in');
    const unknown=starters.some(p=>p.phase==='unknown');
    const next=starters.filter(p=>p.phase==='pre').map(p=>p.game).sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff))[0];
    const final=!active.length&&!next&&!unknown&&(starters.some(p=>p.phase==='post')||Object.values(games).every(g=>g.state==='post'));
    const started=starters.some(p=>p.phase==='post'||p.phase==='in'||p.actual!==0);
    const missing=unknown||incomplete||starters.some(p=>p.missingProjection);
    // Postseason weeks: pregame chance per side from the frozen game (win / finish top of the group).
    const key=r=>`${r.leagueId}|${r.roster_id}`,mine=new Set(rosters.map(key));
    const pg=(baseline.games||[]).find(g=>g.sides.length===rosters.length&&g.sides.every(x=>mine.has(`${x.LeagueID}|${x.RosterID}`)));
    const pregames=pg?rosters.map(r=>Number(pg.sides.find(x=>`${x.LeagueID}|${x.RosterID}`===key(r)).WinPct)):null;
    const saved=pg?null:(baseline.odds||[]).find(o=>String(o.LeagueID)===String(rosters[0].leagueId)&&
      [String(o.RosterID),String(o.OpponentRosterID)].sort().join(',')===rosters.map(r=>String(r.roster_id)).sort().join(','));
    const pregame=pregames?pregames[0]:saved?(String(saved.RosterID)===String(rosters[0].roster_id)?Number(saved.WinPct):100-Number(saved.WinPct)):null;
    const group=rosters.length>2,chances=group?(final||!started?pregames:missing||unknown?null:C.chanceTop(models)):null;
    // Proj column (Chris, 2026-10-30, Sleeper-style): pregame until the game's starters play, then
    // adjusted by known outcomes, back to the pregame value once the game is final.
    const proj=models.map(m=>final||!started?m.pregame:m.projected);
    return {models,group,chances,pregames,final,active:active.length,next,unknown,incomplete,missing,started,proj,pregame,
      probability:group?null:unknown?null:final||!started?pregame:missing?null:C.probability(...models),
      oddsLabel:final||!started?'Pregame %':'Live win %',live:!final&&started,
      status:unknown?'Status unavailable':final?'Final':active.length?'Live':started?'In progress':'Upcoming'};
  }
  return {summarize};
});
