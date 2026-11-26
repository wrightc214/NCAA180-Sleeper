/* team-link.js -- team page links + season matching (task 5.20). Twin of scripts/team_pages.py
 * (norm_league, rid, season_key, current_team); tests/team-link.test.js and tests/test_team_pages.py
 * check both against the same cases.
 *
 * A team is one roster: league + Sleeper roster_id. Sleeper league IDs change every season, so a team
 * seen in any season is matched by league NAME + roster ID (index.ids maps every season's ID to its name).
 *
 *   NCAATeamLink.seasonKey(leagueName, roster)                 'NCAA ACC|12'
 *   NCAATeamLink.currentTeam(index, {leagueId|leagueName, roster})  {league, roster} this season, or null
 *   NCAATeamLink.matchingSeasons(key, keysByYear)             years the team existed, newest first
 *   NCAATeamLink.href(league, roster)                          'team.html?league=<id>&roster=<id>'
 *   NCAATeamLink.on()                                          links shown? follows config/nav.json's
 *       "team" tab: visible = everyone, hidden-dev = Dev view only, hidden/missing = nobody.
 *   NCAATeamLink.wrap(innerHtml, league, roster)               <a> around innerHtml when on(), else innerHtml
 */
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.NCAATeamLink = api;
})(typeof self !== 'undefined' ? self : this, function (root) {
  'use strict';
  const normLeague = name => String(name ?? '').trim().split(/\s+/).filter(Boolean).join(' ').toUpperCase();
  function rid(v) {
    const s = String(v ?? '').trim();
    if (!s || s.toLowerCase() === 'nan') return '';
    const n = Number(s);
    return Number.isFinite(n) ? String(Math.trunc(n)) : s;
  }
  const seasonKey = (leagueName, roster) => `${normLeague(leagueName)}|${rid(roster)}`;

  function currentTeam(index, {leagueId, leagueName, roster} = {}) {
    const name = leagueName ? normLeague(leagueName) : ((index && index.ids) || {})[String(leagueId ?? '')] || '';
    const r = rid(roster);
    if (!name || !r) return null;
    for (const [lid, lg] of Object.entries((index && index.leagues) || {})) {
      if (normLeague(lg.name) === name) return ((index.teams || {})[lid] || {})[r] ? {league: lid, roster: r} : null;
    }
    return null;
  }

  // Years (newest first) in which a season key existed. keysByYear: {year: [season keys]}.
  const matchingSeasons = (key, keysByYear) => Object.entries(keysByYear || {})
    .filter(([, ks]) => (ks instanceof Set ? ks.has(key) : (ks || []).includes(key))).map(([y]) => +y).sort((a, b) => b - a);

  const href = (league, roster) => `team.html?league=${encodeURIComponent(league)}&roster=${encodeURIComponent(rid(roster))}`;

  function state() {
    const menu = root && root.NCAA180 && root.NCAA180.menu;
    const tabs = (menu && menu.data && menu.data.tabs) || [];
    const t = tabs.find(x => x.id === 'team');
    return t ? (t.state || 'visible') : 'hidden';
  }
  function on() {
    const s = state();
    if (s === 'visible') return true;
    if (s !== 'hidden-dev') return false;
    try { return !!(root.NCAA180.menu.dev && root.NCAA180.menu.dev()); } catch (e) { return false; }
  }
  function wrap(inner, league, roster) {
    if (!league || !rid(roster) || !on()) return inner;
    return `<a class="team-link" href="${href(league, roster)}">${inner}</a>`;
  }
  if (root && root.document && !root.document.getElementById('team-link-css')) {
    const st = root.document.createElement('style'); st.id = 'team-link-css';
    st.textContent = 'a.team-link{color:inherit;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px}';
    root.document.head.append(st);
  }
  return {normLeague, rid, seasonKey, currentTeam, matchingSeasons, href, state, on, wrap};
});
