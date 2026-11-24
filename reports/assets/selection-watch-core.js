/* Selection Watch exact field/odds engine. Mirrors scripts/selection_watch.py field(), odds(), final_labels(). */
(function(root) {
  'use strict';
  function field(d, winners, extraAtLarge=0) {
    const win = new Set(winners), result = Object.fromEntries([...win].map(k => [k, 1]));
    const tieOf = new Map((d.tie || []).flatMap((group, i) => group.map(k => [k, i])));
    const order = d.order.map(t => t.k).filter(k => !win.has(k));
    let left = d.field_size - d.ccg.length + extraAtLarge;
    for (let i = 0; i < order.length && left > 0;) {
      const group = [order[i]];
      if (tieOf.has(order[i])) {
        while (i + group.length < order.length &&
               tieOf.get(order[i + group.length]) === tieOf.get(order[i])) {
          group.push(order[i + group.length]);
        }
      }
      const share = Math.min(1, left / group.length);
      for (const k of group) result[k] = share;
      left -= Math.min(left, group.length);
      i += group.length;
    }
    return result;
  }
  function odds(d, p = {}) {
    const games = d.ccg, out = {};
    if (games.length > 20) throw new Error('Unexpected CCG count');
    for (let mask = 0; mask < 2 ** games.length; mask++) {
      let probability = 1;
      const winners = [];
      for (let j = 0; j < games.length; j++) {
        const game = games[j], chooseA = Boolean(mask & (1 << j));
        const q = Object.hasOwn(p, game.id) ? Number(p[game.id]) : 0.5;
        if (!(q >= 0 && q <= 1)) throw new Error('Invalid win probability: ' + game.id);
        probability *= chooseA ? q : (1 - q);
        winners.push(chooseA ? game.a : game.b);
      }
      if (probability === 0) continue;
      for (const [key, share] of Object.entries(field(d, winners))) {
        out[key] = (out[key] || 0) + probability * share;
      }
    }
    return out;
  }
  // Cache immutable, all-open roles. Production and archive data carry frozen play-in IDs.
  // Old cached payloads can be classified from their schedule, never their current results.
  const roleCache=new WeakMap();
  function roles(d){
    if(roleCache.has(d))return roleCache.get(d);
    const games=d.ccg, n=games.length;
    if(n>20)throw new Error('Unexpected CCG count');
    const possible=new Set(), full=new Map(), guaranteed=new Map();
    const participants=new Set(games.flatMap(g=>[g.a,g.b]));
    const count=2**n;
    for(let mask=0;mask<count;mask++){
      const winners=games.map((g,i)=>mask&(1<<i)?g.a:g.b), automatic=new Set(winners);
      for(const [k,share] of Object.entries(field(d,winners))){
        if(share===1)guaranteed.set(k,(guaranteed.get(k)||0)+1);
        if(automatic.has(k))continue;
        if(share>0)possible.add(k);
        if(share===1)full.set(k,(full.get(k)||0)+1);
      }
    }
    const playIns=new Set(d.play_ins ?? games.filter(g=>!possible.has(g.a)&&!possible.has(g.b)).map(g=>g.id));
    const playInTeams=new Set(games.filter(g=>playIns.has(g.id)).flatMap(g=>[g.a,g.b]));
    const rank=new Map(d.order.map(t=>[t.k,t.rank])), team=new Map(d.order.map(t=>[t.k,t]));
    const atLarge=d.order.filter(t=>t.rank<=d.field_size&&!playInTeams.has(t.k)&&possible.has(t.k)&&
      (full.get(t.k)||0)<(participants.has(t.k)?count/2:count));
    const data={playIns,rank,team,atLarge,locks:d.order.filter(t=>guaranteed.get(t.k)===count).map(t=>t.k)};
    roleCache.set(d,data);
    return data;
  }
  const locks=d=>roles(d).locks;
  const opponent=(g,k)=>k===g.a?g.b:g.a;
  const chance=(g,k,p)=>k===g.a?(p[g.id]??.5):1-(p[g.id]??.5);
  const isSteal=(d,g,k,r)=>!r.playIns.has(g.id)&&r.rank.get(k)>d.field_size;

  function cutBoard(d, leaders={}, probabilities={}, settled={}, holding=leaders){
    const r=roles(d), games=d.ccg, {rank,team,playIns}=r;
    const winners=games.map(g=>settled[g.id]||g.winner||leaders[g.id]||
      (chance(g,g.a,probabilities)>=.5?g.a:g.b));
    const winnersSet=new Set(winners), projected=field(d,winners);
    const cut=d.order.reduce((out,t)=>!winnersSet.has(t.k)&&projected[t.k]>0?Math.max(out,t.rank):out,0);
    const labels={}, held=new Map(), thieves=[], playInGames=[];
    const atLarge=r.atLarge.map(t=>({...t,status:projected[t.k]===1?'Above cut':projected[t.k]>0?'Coin toss':'Below cut'}));
    const byBubble=new Map(atLarge.map(t=>[t.k,t]));
    const cutChoices=[];
    let steals=0, possible=0, leading=0;
    const signature=f=>JSON.stringify(Object.entries(f).sort());
    const likely=signature(projected);
    const noSteals=winners.map((k,i)=>isSteal(d,games[i],k,r)?opponent(games[i],k):k);

    games.forEach((g,index)=>{
      const k=winners[index], other=opponent(g,k), final=settled[g.id]||g.winner;
      const win=side=>chance(g,side,probabilities);
      const thief=side=>({k:side,rank:rank.get(side),game:g.id,win:win(side),active:side===k});
      if(playIns.has(g.id)){
        labels[g.id]=final?'Play-in winner':'Play-in';
        playInGames.push({g,a:thief(g.a),b:thief(g.b),final,leader:k,label:labels[g.id]});
        return;
      }
      const alternate=[...winners]; alternate[index]=other;
      const loss=field(d,alternate);
      const outside=isSteal(d,g,k,r), otherOutside=isSteal(d,g,other,r);
      // Ignore the opponent's own outside bid when determining whether OTHER steals pushed
      // the natural-field winner out. Its own win must be what saves it from those steals.
      const neutralLoss=otherOutside&&(loss[k]||0)<1?field(d,alternate,1):loss;
      // A permanent play-in slot can leave a natural team out before any steals. That is
      // not a saved row: the other outside wins must actually move it past the cut.
      const saved=!outside&&(neutralLoss[k]||0)<1&&
        field(d,noSteals.map((v,j)=>j===index?other:v),Number(otherOutside))[k]===1;
      if(final){
        labels[g.id]=outside?'Stolen':saved?'Saved':otherOutside&&loss[k]===1?'Held':'Final';
      }else if(outside){
        labels[g.id]='Steal';
      }else if(otherOutside&&win(other)>0){
        labels[g.id]='Possible steal';
      }else{
        cutChoices.push({g,index,alternate,loss});
      }
      if(outside)final?steals++:leading++;
      else if(!final&&otherOutside&&win(other)>0)possible++;
      if(saved&&byBubble.has(k)&&(final||holding[g.id]===k)){
        const conf=team.get(k)?.conf||team.get(other)?.conf||'Conference';
        const row=byBubble.get(k);
        row.status=final?'Saved':'Leading CCG';
        held.set(k,{conf,game:g.id,final,pair:otherOutside?thief(other):null});
      }else if(outside||otherOutside){
        thieves.push(thief(outside?k:other));
      }
    });

    for(const {g,index,alternate,loss} of cutChoices){
      let impact=likely!==signature(loss);
      // Look beyond the projected field, but only flip games that can still go either way.
      const variable=games.flatMap((v,j)=>j!==index&&!settled[v.id]&&!v.winner&&
        chance(v,v.a,probabilities)>0&&chance(v,v.a,probabilities)<1?[j]:[]);
      if(!impact&&!(r.locks.includes(g.a)&&r.locks.includes(g.b))){
        const first=[...winners];
        for(let mask=1;mask<2**variable.length&&!impact;mask++){
          variable.forEach((j,bit)=>{
            first[j]=alternate[j]=mask&(1<<bit)?opponent(games[j],winners[j]):winners[j];
          });
          impact=signature(field(d,first))!==signature(field(d,alternate));
        }
      }
      labels[g.id]=impact?'Bubble impact':'No bubble impact';
    }
    // A decided CCG winner is in on its own bid; say so even when it would also be in at-large.
    // Saved keeps its own label, and live leaders keep their projected status.
    games.forEach(g=>{
      const k=settled[g.id]||g.winner, row=k&&!playIns.has(g.id)&&byBubble.get(k);
      if(row&&row.status!=='Saved')row.status='Automatic bid';
    });
    // Thieves sort by live win chance once games start (pregame odds before kickoff).
    thieves.sort((a,b)=>a.win-b.win||a.rank-b.rank||a.k.localeCompare(b.k));
    for(const t of thieves)t.label=labels[t.game]==='Stolen'&&!t.active?'':labels[t.game];
    const rows=atLarge.map(left=>({left,hold:held.get(left.k)}));
    const active=thieves.filter(t=>t.active);
    const out=rows.filter(row=>row.left.status==='Below cut');
    // In rank order the most likely active thief goes against the first-out (worst rank).
    // Held rows do not consume a thief. A coin toss row never implies a team has lost.
    const recipients=out.slice(-active.length);
    active.forEach((t,i)=>{
      const row=recipients[i];
      if(row)row.right=t;
      else rows.push({right:t});
    });
    // Each possible thief sits beside the team it would knock out (Chris, 2026-11-24): the most likely
    // goes against the last team above the cut, the next most likely against the one above that, and so
    // on. A held row (that team leads its own CCG) keeps its placard and does not take a thief. Thieves
    // beyond the free rows stack above the board, least likely furthest from the cut.
    const inactive=thieves.filter(t=>!t.active).sort((a,b)=>b.win-a.win||a.rank-b.rank||a.k.localeCompare(b.k));
    const free=rows.filter(row=>row.left&&row.left.status!=='Below cut'&&!row.hold&&!row.right).reverse();
    inactive.forEach((t,i)=>{
      if(i<free.length)free[i].right=t;
      else rows.unshift({right:t});
    });
    return {atLarge,thieves,playIns:playInGames,cut,initialCut:d.field_size-playIns.size,
      projected,labels,steals,leading,possible,rows};
  }
  const api = {field, odds, locks, cutBoard};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SelectionWatchCore = api;
})(typeof window === 'undefined' ? globalThis : window);
