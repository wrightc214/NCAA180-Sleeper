const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../reports/assets/snapshot.js'), 'utf8');
// Stub only rasterization. The tests exercise the public save API and its real dialog handlers.
const script = source.replace('const blob = await render(', 'const blob = await testRender(');

function setup({canShare = true, failDownload = false} = {}) {
  const dialogs = [];
  const shares = [];
  const downloads = [];
  class Element {
    constructor(tag) {
      this.tag = tag;
      this.style = {};
      this.events = {};
    }
    setAttribute() {}
    addEventListener(name, listener) { this.events[name] = listener; }
    append(...children) { this.children = children; }
    appendChild() {}
    remove() { this.removed = true; }
    showModal() { this.open = true; dialogs.push(this); }
    close() { this.open = false; }
    click() { downloads.push(this.download); }
  }
  const window = {};
  const navigator = {
    canShare: () => canShare,
    share: async data => shares.push(data),
  };
  class TestURL extends URL {
    static createObjectURL() {
      if (failDownload) throw new Error('download failed');
      return 'blob:png';
    }
    static revokeObjectURL() {}
  }
  const location = new URL('https://example.org/reports/team.html');
  vm.runInNewContext(script, {
    window, navigator, location, URL: TestURL, File: class File {
      constructor(parts, name) { this.name = name; }
    }, HTMLDialogElement: Element, setTimeout: callback => callback(),
    document: {createElement: tag => new Element(tag), body: new Element('body')},
    testRender: async () => ({size: 24}),
  });
  return {save: () => window.NCAASnap.save({html: '<section></section>', name: 'Team'}),
    dialogs, shares, downloads};
}

test('share runs only on a second click', async () => {
  const {save, dialogs, shares} = setup();
  const pending = save();
  await new Promise(setImmediate);
  assert.equal(shares.length, 0);
  const [dialog] = dialogs;
  await dialog.children[1].events.click();
  await pending;
  assert.equal(shares[0].files[0].name, 'Team.png');
  assert.equal(dialog.open, false);
  assert.equal(dialog.removed, true);
});

test('download failure removes the dialog and rejects to the caller', async () => {
  const {save, dialogs} = setup({failDownload: true});
  const pending = save();
  await new Promise(setImmediate);
  const [dialog] = dialogs;
  dialog.children[2].events.click();
  await assert.rejects(pending, /download failed/);
  assert.equal(dialog.open, false);
  assert.equal(dialog.removed, true);
});

test('desktop fallback downloads directly', async () => {
  const {save, dialogs, downloads} = setup({canShare: false});
  await save();
  assert.deepEqual(downloads, ['Team.png']);
  assert.equal(dialogs.length, 0);
});
