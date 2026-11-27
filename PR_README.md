# Save Image second-tap sharing

The shared exporter generates the PNG, then offers Share image, Download PNG, and Cancel when file sharing and modal dialogs are available. Share image invokes the system share API directly from its click handler. Other browsers download directly. A failed dialog download closes the dialog and returns the error to the page. The bracket keeps its export menu and retry controls available while sharing is in progress. Team-specific styling is on main through #151.
Team section and trophy snapshots retain the Team color container. The renderer converts modern CSS colors on the document and body as well as inside the selected section. The old renderer failed on the Team background before it could produce a PNG.

Run `node --test tests/snapshot-share.test.js` for the simulated DOM checks. The PR browser suites generate an actual PNG from the Team Overview, cover Selection Watch downloads, and exercise bracket download failure and retry with a simulated native share API. The bracket suite also exercises WebKit download rendering.

Before approval, test on physical iPhone Safari and desktop on Team, Bracket, and Selection Watch. Check successful PNG contents, second-tap native sharing where available, cancel and retry, direct downloads, and visible failure feedback. On Team, also check exported chart patterns and totals from Season by Season. Native iPhone testing remains pending.
