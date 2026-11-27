# 5.20b — Team color customization

Tasks 5.20.10–11. Team page remains hidden-dev; no navigation or export handler changes.

## Implementation
Existing full/frame/site identifiers are preserved. Inverted exchanges the base and foreground via shared CSS variables; headers reverse the pair and select the existing background-specific logo. Heading and foreground colors use a 4.5:1 contrast check with black/white fallback. Page and season surfaces mix 6% toward foreground to distinguish even black or white bases. Neutral islands and semantic tokens remain in place. The switch uses native button keyboard activation and radio buttons support arrows/Home/End.

Global storage remains ncaa180.teamColors; overrides use ncaa180.teamColors.byTeam keyed by d.key. Invalid modes are ignored; malformed maps are treated as empty; unrelated entries are preserved when a valid map is updated. Storage is probed and the switch hidden on failure. No cross-device sync.

## Reviewer instructions
Run `node --test tests/team_colors.test.cjs` from repository root, then the normal project regression suite and regenerate the team page. Tests were not executed by the implementation developer per brief.

Review Alabama (white ink), a black-ink team (candidate Iowa), and a colored-ink team (candidate Michigan). Confirm actual generated ink values first: generated reports/data/teams/index.json was not available on the feature branch, so the latter two candidates are not verified; substitute teams with actual matching ink if necessary. At 320, 390 and 1280 px in both themes, check all four modes, logo visibility, contrast, neutral panels, focus and overflow. Check override on/off, navigation, reload, historical URL resolution, invalid mode/map and blocked storage. Verify section exports after integration with 5.20a; no export changes here. Check generated HTML is rebuilt before deploying; do not publish the page. Browser visual checks and representative team confirmation remain outstanding.

### Reviewer correction
Inverted headings explicitly prefer the primary team color against the ink background, with the existing 4.5:1 black/white fallback. Team mode retains accent headings. Added a regression assertion; reviewer to execute.
