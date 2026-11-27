# Save Image second-tap share

PNG generation is asynchronous. Share-capable browsers now present an explicit Share image button whose click calls navigator.share directly. Download and cancel remain available. Desktop without file sharing downloads directly. Section error alerts retained. Team table CSS stays in #151.

Required acceptance tests (not executed): physical iPhone Safari and desktop browser, each on Team, Bracket and Selection Watch. Verify PNG generation, second-tap native share, cancellation/retry, download, error alert, correct section content and labels, and repeated saves. Check desktop direct download where file sharing is unsupported. No physical iPhone or browser execution environment was available to implementation developer. Do not merge until reviewer records results.

The download button now rejects to the calling handler on failure and closes the dialog. Browsers without file sharing or modal dialog support use the direct download path. Run `node --test tests/snapshot-share.test.js` for simulated DOM regression coverage. It stubs rasterization and checks the second click, cleanup on a failed download, and the direct download path. Native sharing and real PNG contents still require device testing. Apply #151 locally when checking Team charts and season totals.
