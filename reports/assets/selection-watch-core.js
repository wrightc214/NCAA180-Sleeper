/* Selection Watch exact field/odds engine. Mirrors scripts/selection_watch.py field(), odds(), board(). */
(function(root) {
  'use strict';
  function field(d, winners) {
    const win = new Set(winners), result = Object.fromEntries([...win].map(k => [k, 1]));
    const tieOf = new Map((d.tie || []).flatMap((group, i) => group.map(k => [k, i])));
    const order = d.order.map(t => t.k).filter(k => !win.has(k));
    let left = d.field_size - d.ccg.length;
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
  function board(d, leaders = {}) {
    const ranks = Object.fromEntries(d.order.map(t => [t.k, t.rank]));
    const thieves = [], protectedTeams = new Set(), N = d.field_size;
    for (const g of d.ccg) {
      const aOut = ranks[g.a] > N, bOut = ranks[g.b] > N;
      const lead = leaders[g.id] || g.winner || null;
      if (aOut && bOut) {
        thieves.push({game:g.id, team:lead || g.a, both_out:true, leading:true});
      } else if (aOut || bOut) {
        const team = aOut ? g.a : g.b;
        thieves.push({game:g.id, team, both_out:false, leading:lead === team});
      }
      if (lead && ranks[lead] <= N) protectedTeams.add(lead);
    }
    const k = thieves.filter(t => t.leading).length;
    const atRisk = d.order.slice(0, N).map(t => t.k)
      .filter(k => !protectedTeams.has(k)).reverse().slice(0, thieves.length);
    return {thieves, atRisk, k};
  }
  function locks(d) {
    const zero = {}, one = {};
    for (const g of d.ccg) { zero[g.id] = 0; one[g.id] = 1; }
    // Every outcome has positive weight with p=0.5, so exactly-one odds means a lock.
    const o = odds(d, {});
    return d.order.filter(t => Math.abs((o[t.k] || 0) - 1) < 1e-10).map(t => t.k);
  }
  function sortedBoard(d, leaders, probabilities, margins, sort = 'chance') {
    const b = board(d, leaders);
    b.thieves.sort((a, c) => {
      const aGame = d.ccg.find(g => g.id === a.game), cGame = d.ccg.find(g => g.id === c.game);
      const chance = t => {
        const g = d.ccg.find(x => x.id === t.game);
        const q = probabilities[g.id] ?? 0.5;
        return t.team === g.a ? q : 1-q;
      };
      const metric = t => sort === 'margin' ? (margins[t.game] ?? 0) : chance(t);
      return Number(c.leading)-Number(a.leading) ||
        (sort === 'margin' && !a.leading ? metric(a)-metric(c) : metric(c)-metric(a)) ||
        String(a.game).localeCompare(String(c.game));
    });
    return b;
  }
  // A possible impact must be reachable without changing games whose outcomes are locked.
  function implications(d, p, settled, locked = []) {
    const games = d.ccg, N = d.field_size;
    const rank = new Map(d.order.map(t => [t.k, t.rank]));
    const absolute = new Set(locked);
    const likely = games.map(g => settled[g.id] || ((p[g.id] ?? .5) >= .5 ? g.a : g.b));
    const signature = winners => JSON.stringify(Object.entries(field(d, winners)).sort());
    const same = (winners, index) => {
      const alternate = [...winners], g = games[index];
      alternate[index] = winners[index] === g.a ? g.b : g.a;
      return signature(winners) === signature(alternate);
    };
    const labels = {};
    games.forEach((g, index) => {
      const aOut = rank.get(g.a) > N, bOut = rank.get(g.b) > N;
      const winner = settled[g.id];
      if (winner) {
        labels[g.id] = aOut || bOut ? (rank.get(winner) > N ? 'Stolen' : 'Held') : 'Final';
        return;
      }
      if (absolute.has(g.a) && absolute.has(g.b)) {
        labels[g.id] = 'No bubble impact';
        return;
      }
      if (aOut || bOut) {
        const q=p[g.id] ?? .5, outsidePossible=(aOut&&q>0)||(bOut&&q<1);
        labels[g.id]=rank.get(likely[index])>N?'Steal':outsidePossible?'Possible steal':'No bubble impact';
        return;
      }
      if (!same(likely, index)) {
        labels[g.id] = 'Bubble impact';
        return;
      }
      // A game whose hypothetical flip changes nothing in the likely field may still matter
      // when other games go differently. Enumerate those alternatives, with early exit.
      const variable = games.flatMap((other, j) => j !== index && !settled[other.id] &&
        (p[other.id] ?? .5) > 0 && (p[other.id] ?? .5) < 1 ? [j] : []);
      let possible = false;
      for (let mask = 1; mask < 2 ** variable.length && !possible; mask++) {
        const candidate = [...likely];
        variable.forEach((j, bit) => {
          if (mask & (1 << bit)) candidate[j] = likely[j] === games[j].a ? games[j].b : games[j].a;
        });
        possible = !same(candidate, index);
      }
      labels[g.id] = possible ? 'Possible bubble impact' : 'No bubble impact';
    });
    return labels;
  }
  // Freeze the range of roles over all CCG outcomes, including the paths that did not happen.
  // This lets a settled board retain the same bubble and show who actually fell below the cut.
  const roleCache=new WeakMap();
  function bubbleRoles(d){
    if(roleCache.has(d))return roleCache.get(d);
    const games=d.ccg, n=games.length;
    if(n>20)throw Error('Unexpected CCG count');
    const possible=new Set(), full=new Map(), participants=new Set(games.flatMap(g=>[g.a,g.b]));
    const count=2**n;
    for(let mask=0;mask<count;mask++){
      const winners=games.map((g,i)=>mask&(1<<i)?g.a:g.b), automatic=new Set(winners);
      for(const [k,share] of Object.entries(field(d,winners))){
        if(automatic.has(k))continue;
        if(share>0)possible.add(k);
        if(share===1)full.set(k,(full.get(k)||0)+1);
      }
    }
    const canMiss=k=>(full.get(k)||0)<(participants.has(k)?count/2:count);
    const roles={atLarge:d.order.filter(t=>possible.has(t.k)&&canMiss(t.k)),
      thieves:games.flatMap(g=>[g.a,g.b].filter(canMiss).map(k=>({k,g}))), possible};
    roleCache.set(d,roles);
    return roles;
  }
  function cutBoard(d, leaders, probabilities, settled={}){
    const roles=bubbleRoles(d);
    const winners=d.ccg.map(g=>leaders[g.id]||g.winner||g.a), winnersSet=new Set(winners);
    const projected=field(d,winners);
    const cut=d.order.reduce((out,t)=>!winnersSet.has(t.k)&&projected[t.k]>0?Math.max(out,t.rank):out,0);
    const ranks=new Map(d.order.map(t=>[t.k,t.rank]));
    const thieves=roles.thieves.map(({k,g})=>{
      const q=probabilities[g.id]??.5;
      const loss=field(d,d.ccg.map((other,i)=>other===g?(k===g.a?g.b:g.a):winners[i]));
      const needsWin=(loss[k]||0)<1;
      const final=settled[g.id];
      return {k,game:g.id,win:k===g.a?q:1-q,needsWin,
        inField:projected[k]===1&&winnersSet.has(k)&&needsWin,
        both:roles.possible.has(k),
        status:final===k?(needsWin?'Stolen':'Won · at-large safe'):
          final?'Lost':needsWin?'Needs a win at this cut':'Conditional thief'};
    }).sort((a,b)=>a.win-b.win||ranks.get(a.k)-ranks.get(b.k)||a.k.localeCompare(b.k));
    const atLarge=roles.atLarge.map(t=>({...t,status:winnersSet.has(t.k)?'Automatic bid in this scenario':
      projected[t.k]===1?'Above cut':projected[t.k]>0?'COIN TOSS':'Below cut'}));
    return {atLarge,thieves,cut,projected};
  }
  const api = {field, odds, board, locks, sortedBoard, implications, cutBoard};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SelectionWatchCore = api;
})(typeof window === 'undefined' ? globalThis : window);
