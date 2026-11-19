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
  const api = {field, odds, board, locks, sortedBoard};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SelectionWatchCore = api;
})(typeof window === 'undefined' ? globalThis : window);
