/* Pure scoring/model functions shared by the browser and Node validation tests. */
(function(root) {
  'use strict';
  const num = x => Number.isFinite(Number(x)) ? Number(x) : 0;
  const round = x => Math.round((x + Number.EPSILON) * 100) / 100;
  function statsMap(feed) {
    if (Array.isArray(feed)) return Object.fromEntries(feed.filter(p => p.player_id).map(p => [String(p.player_id), p.stats || {}]));
    if (feed && typeof feed === 'object') return Object.fromEntries(Object.entries(feed).map(([k,v]) => [k, v.stats || v]));
    throw new Error('Unrecognized statistics response');
  }
  function normalizedStats(raw) {
    const s = {...raw};
    // Some feeds expose raw DEF totals, some already expose one-hot scoring tiers.
    const tier = (rawKey, prefix, bands) => {
      if (s[rawKey] === undefined || s[rawKey] === null) return;
      // Projection feeds can use fractional totals with explicitly selected tiers.
      if (Object.keys(s).some(k => k.startsWith(prefix))) return;
      for (const k of Object.keys(s)) if (k.startsWith(prefix)) delete s[k];
      const v = num(s[rawKey]);
      const b = bands.find(([lo,hi]) => v >= lo && v <= hi);
      if (b) s[b[2]] = 1;
    };
    tier('pts_allow','pts_allow_',[[0,0,'pts_allow_0'],[1,6,'pts_allow_1_6'],[7,13,'pts_allow_7_13'],[14,20,'pts_allow_14_20'],[21,27,'pts_allow_21_27'],[28,34,'pts_allow_28_34'],[35,Infinity,'pts_allow_35p']]);
    tier('yds_allow','yds_allow_',[[0,99,'yds_allow_0_100'],[100,199,'yds_allow_100_199'],[200,299,'yds_allow_200_299'],[300,349,'yds_allow_300_349'],[350,399,'yds_allow_350_399'],[400,449,'yds_allow_400_449'],[450,499,'yds_allow_450_499'],[500,549,'yds_allow_500_549'],[550,Infinity,'yds_allow_550p']]);
    return s;
  }
  function score(raw, rules) {
    const s = normalizedStats(raw || {});
    return round(Object.entries(rules).reduce((a,[k,v]) => a + num(s[k]) * num(v),0));
  }
  function remaining(game) {
    if (!game || game.state === 'bye' || game.state === 'post') return 0;
    if (game.state === 'pre') return 1;
    if (game.period > 4) return 0; // Version A treats overtime as regulation complete.
    const parts = String(game.clock || '0:00').split(':');
    const seconds = num(parts[0])*60 + num(parts[1]);
    return Math.max(0,Math.min(1,((4 - Math.max(1,game.period))*900 + seconds)/3600));
  }
  function eligible(positions, slot, cfg) {
    return positions.some(p => (cfg.eligibility[slot] || []).includes(p));
  }
  // Exact slot assignment handles overlapping flex types and multiple eligible positions.
  function bestLineup(players, slots, cfg) {
    let states = new Map([[0,{total:0,ids:[]}]]);
    for (const p of players) {
      const next = new Map(states);
      for (const [mask,v] of states) for (let i=0;i<slots.length;i++) {
        if ((mask & (1<<i)) || !eligible(p.positions,slots[i],cfg)) continue;
        const key=mask|(1<<i), total=v.total+num(p.points);
        if (!next.has(key) || next.get(key).total<total) next.set(key,{total,ids:[...v.ids,p.id]});
      }
      states=next;
    }
    const full=states.get((1<<slots.length)-1);
    if (full) return {...full,total:round(full.total)};
    // Incomplete rosters: fill as many legal slots as possible, then maximize points.
    return [...states.entries()].sort((a,b)=>b[0].toString(2).replace(/0/g,'').length-a[0].toString(2).replace(/0/g,'').length || b[1].total-a[1].total)[0][1];
  }
  function erf(x) {
    const sign=x<0?-1:1, a=Math.abs(x), t=1/(1+0.3275911*a);
    return sign*(1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-a*a));
  }
  function probability(a,b) {
    const variance=a.variance+b.variance;
    if (variance<1e-10) return a.projected===b.projected?50:(a.projected>b.projected?100:0);
    return 50*(1+erf((a.projected-b.projected)/Math.sqrt(2*variance)));
  }
  function playerModel(id, metadata, raw, projection, game, official, cfg, past=false) {
    const p=metadata || {name:`Player ${id}`,positions:[],team:'',status:''};
    const positions=p.positions || [p.position];
    const pos=positions.find(x => cfg.position_sd[x]) || p.position;
    const inactive=!past && /^(out|inactive|ir|pup|sus|suspended)$/i.test(p.status||'') && (!game || game.state!=='post');
    const fraction=inactive?0:remaining(game);
    const hasStarted=game && game.state!=='pre' && game.state!=='bye';
    const correction=score(raw,cfg.standard_scoring)-score(raw,cfg.official_scoring||cfg.standard_scoring);
    const actual=hasStarted?round(num(official)+correction):0;
    const projected=score(projection,cfg.standard_scoring);
    const phase=inactive?'out':!game?'unknown':game.state==='bye'?'bye':game.state;
    return {id,...p,positions,position:pos,phase,game,actual,baseline:projected,
      projected:round(actual+projected*fraction),variance:(num(cfg.position_sd[pos])*fraction)**2,
      minutes:60*fraction,official:num(official),missingMetadata:!metadata,missingProjection:projection===undefined};
  }
  function teamModel(roster, players) {
    const starters=(roster.starters||[]).map(id=>players[String(id)] || {id:'0',name:'Empty slot',positions:[],position:'',phase:'out',actual:0,baseline:0,projected:0,variance:0,minutes:0,official:0});
    const adjustment=num(roster.points)-starters.reduce((a,p)=>a+p.official,0);
    return {starters,adjustment:round(adjustment),actual:round(starters.reduce((a,p)=>a+p.actual,0)+adjustment),
      projected:round(starters.reduce((a,p)=>a+p.projected,0)+adjustment),pregame:round(starters.reduce((a,p)=>a+p.baseline,0)),
      played:starters.some(p=>p.phase==='post'||p.phase==='in'||p.actual!==0),variance:starters.reduce((a,p)=>a+p.variance,0),
      minutes:starters.reduce((a,p)=>a+p.minutes,0),official:num(roster.points)};
  }
  function benchPlayers(roster, players, starters, slots, cfg, pregame) {
    const started=new Set((roster.starters||[]).map(String));
    let zeros=0;
    const candidates=(roster.players||[]).map(String).filter(id=>!started.has(id)).map(id=>players[id]).filter(Boolean);
    const keep=[];
    for (const p of candidates) {
      if (['bye','out'].includes(p.phase) || (!p.baseline&&!p.actual)) { zeros++;continue; }
      if (pregame) { keep.push({...p,gain:0});continue; }
      const alternatives=starters.filter((s,i)=>eligible(p.positions,slots[i],cfg));
      const gain=Math.max(-Infinity,...alternatives.map(s=>p.projected-s.projected));
      const close=alternatives.some(s=>p.baseline>=s.baseline-cfg.bench_near_points);
      if (gain>0 || close) keep.push({...p,gain,close});
    }
    const order=['QB','RB','WR','TE','K','DEF'];
    keep.sort(pregame?(a,b)=>order.indexOf(a.position)-order.indexOf(b.position)||b.baseline-a.baseline:(a,b)=>b.gain-a.gain);
    return {players:pregame?keep:keep.slice(0,5),zeros,others:candidates.length-zeros-(pregame?keep.length:Math.min(5,keep.length))};
  }
  const api={num,round,statsMap,normalizedStats,score,remaining,eligible,bestLineup,probability,playerModel,teamModel,benchPlayers};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  root.ScoreboardCore=api;
})(typeof window==='undefined'?globalThis:window);
