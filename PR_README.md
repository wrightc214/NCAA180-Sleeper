# 5.20b — Team color customization

Tasks 5.20.10–11. Team page remains hidden-dev; no navigation or export handler changes.

## Implementation
Existing full/frame/site identifiers are preserved. Inverted exchanges the base and foreground via shared CSS variables; headers reverse the pair and select the existing background-specific logo. Heading and foreground colors use a 4.5:1 contrast check with black/white fallback. Page and season surfaces mix 6% toward foreground to distinguish even black or white bases. Neutral islands and semantic tokens remain in place. The switch uses native button keyboard activation and radio buttons support arrows/Home/End.

Global storage remains ncaa180.teamColors; overrides use ncaa180.teamColors.byTeam keyed by d.key. Invalid modes are ignored; malformed maps are treated as empty; unrelated entries are preserved when a valid map is updated. Storage is probed and the switch hidden on failure. No cross-device sync.

## Reviewer instructions
Run `node --test tests/team_colors.test.js` and `RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest -q tests/test_team_pages_browser.py` from the repository root. The browser suite covers keyboard selection, override persistence through historical URLs, and the representative-team width and theme matrix. Regenerate the Team page with `PYTHONPATH=scripts python -c "import team_pages; team_pages.write_page()"` and check the generated page for drift.

Review Alabama (white ink `#FFFFFF`), Iowa (black ink `#000000`), and Michigan (maize ink `#FFCB05`). These values are verified against the committed team data. At 320, 390 and 1280 px in both themes, check all four modes, logo visibility, contrast, neutral panels, focus and overflow. Manager, head-to-head and season summary tables use the neutral panel colors; game rows use the team palette. Check override on/off, navigation, reload, historical URL resolution, invalid mode/map and blocked storage. Verify section exports after integration with 5.20a. Keep the page hidden-dev.

### Reviewer correction
Inverted headings explicitly prefer the primary team color against the ink background, with the existing 4.5:1 black/white fallback. Team mode retains accent headings. Added a regression assertion; reviewer to execute.
