/* Optional developer-only browser checks; launched by run.py with isolated HOME/data. */
const {chromium, firefox} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = process.env.BROWSER_TEST_ROOT, base = process.env.BROWSER_TEST_BASE;
if (!root || !base) throw Error('Use run.py to create a safe isolated fixture');
if (new URL(base).hostname!=='127.0.0.1' || new URL(base).protocol!=='http:' || fs.readFileSync(path.join(root,'server-url.txt'),'utf8')!==base) throw Error('Use only the isolated loopback server started by run.py');
const home = process.env.BROWSER_TEST_HOME, results = [], exceptions = [];
const engine = process.env.BROWSER_TEST_ENGINE;
const headed = process.env.BROWSER_TEST_HEADED === '1';
let failed = 0, browser;
function record(name, status, detail='') { results.push({name, status, detail}); console.log(`${status} ${name}${detail ? ': '+detail : ''}`); }
async function test(name, fn) { if(process.env.BROWSER_TEST_FILTER && !name.includes(process.env.BROWSER_TEST_FILTER)) return; try { await fn(); record(name, 'PASS'); } catch (e) { failed++; record(name, 'FAIL', String(e.message)); } }
(async () => {
  if (engine === 'firefox') {
    browser = await firefox.launch({headless: !headed});
  } else if (engine === 'chromium') {
    browser = await chromium.launch({executablePath: process.env.CHROME_BIN, headless: !headed,
      args: headed ? ['--ozone-platform=x11'] : [], chromiumSandbox: true});
  } else {
    throw Error('Use run.py to select a browser engine');
  }
  const browserVersion = browser.version();
  console.log(`Browser: ${engine} ${browserVersion}`);
  const context = await browser.newContext({viewport:{width:1280,height:900}});
  const page = await context.newPage(); page.setDefaultTimeout(5000);
  page.on('pageerror', e => exceptions.push(e.message));
  let navigation = 0;
  async function go(route) { route = ({home:'skills?view=agents', map:'skills?view=map'})[route] || route; await page.goto(base+'/?fixture-step='+(++navigation)+'#/'+route); await page.locator('main').waitFor(); await page.waitForLoadState('networkidle'); if (route.startsWith('skill/')) await page.locator('.jf-reader-heading').waitFor(); await page.waitForTimeout(200); }
  async function theme(t) { for (let i=0;i<3 && await page.locator('html').getAttribute('data-theme')!==t;i++) { const button = page.locator('.themebtn:visible').first(); if (await button.count()) await button.click(); else { await page.keyboard.press('Control+k'); await page.getByRole('combobox', {name:'Search skills, actions and pages'}).fill('Switch theme'); await page.getByRole('option', {name:/Switch theme/}).click(); } } assert.equal(await page.locator('html').getAttribute('data-theme'),t); }
  const file=(scope,name='same-everywhere')=>path.join(home,scope,'skills',name,'SKILL.md');
  const libraryFile = name => path.join(root, 'data', 'jackfield', 'skills', name, 'SKILL.md');
  const trashScreen = page.locator('.jf-trash-screen');
  const trashList = trashScreen.locator('section[aria-labelledby="rec-trash"]');
  const restoreButton = (name, place, copy = '') => trashList.getByRole('button', {
    name:`Review restore for ${name} in ${place}${copy ? ', ' + copy : ''}`, exact:true,
  });
  const attention = page.locator('.jf-attention');
  const attentionHeading = attention.locator('#attention-detail-heading');
  const attentionItem = id => attention.locator(`[data-attention-id=${JSON.stringify(id)}]`);
  const attentionNav = page.locator('.tabs a[href="#/attention"]');
  const attentionWrites = request => request.method() === 'POST' &&
    ['/api/sync', '/api/batch/execute'].includes(new URL(request.url()).pathname);
  async function openAttention(id) {
    await go(id ? 'attention?item=' + encodeURIComponent(id) : 'attention');
    await attention.getByRole('heading', {name:'Needs attention', exact:true}).waitFor();
    if (id) await attentionHeading.waitFor();
  }
  async function expectAttentionCount(count) {
    if (count) await attention.getByRole('heading', {name:`To fix · ${count}`, exact:true}).waitFor();
    assert.equal(await attentionNav.getAttribute('aria-label'), count ? `Needs attention, ${count} ${count === 1 ? 'item' : 'items'}` : null);
  }
  async function turnOffCodexFromReader() {
    await page.getByRole('button', {name:'same-everywhere in Codex: On'}).click();
    await page.locator('.jf-panel').getByRole('button', {name:/^Turn off/}).click();
  }
  await test('Default entry serves the interface at / with query and hash intact',async()=>{await page.goto(base+'/?window=claude#/skills');await page.waitForLoadState('networkidle');assert.equal(page.url(),base+'/?window=claude#/skills');const show=page.getByRole('button',{name:'Show my skills'});if(await show.isVisible())await show.click();assert(await page.getByRole('grid',{name:'Skills table'}).locator('tbody tr').count()>0);});
  await test('Four primary places navigate and identify the current page', async () => {
    try {
      for (const width of [1280, 390]) {
        await page.setViewportSize({width, height:900});
        await go('skills');
        const nav = page.locator(width === 1280 ? '.tabs' : '.bottomnav');
        const places = [['Skills', '#/skills'], ['Needs attention', '#/attention'],
          ['Trash & backups', '#/trash'], ['Advanced', '#/advanced']];
        assert.equal(await nav.locator('a').count(), places.length);
        for (const [name, hash] of places) {
          const link = nav.locator(`a[href="${hash}"]`);
          assert.match(await link.innerText(), new RegExp(name));
          await link.click();
          await page.waitForURL(url => url.hash === hash);
          await page.waitForFunction(selector => document.querySelector(selector)?.getAttribute('aria-current') === 'page',
            `${width === 1280 ? '.tabs' : '.bottomnav'} a[href="${hash}"]`);
        }
      }
    } finally { await page.setViewportSize({width:1280, height:900}); }
  });
  await test('Skills notices an external file change and highlights the refreshed row (F8)', async () => {
    const name = 'phase-four-disk-change';
    const active = file('.claude', name), disabled = active + '.disabled';
    const folder = path.dirname(active);
    const document = `---\nname: ${name}\ndescription: Exercise a disk change in the browser.\n---\n# Original instructions\n`;
    assert(!fs.existsSync(folder));
    const view = await browser.newContext({viewport:{width:1440, height:900}});
    try {
      fs.mkdirSync(folder);
      fs.writeFileSync(active, document);
      const watcher = await view.newPage();
      watcher.setDefaultTimeout(5000);
      watcher.on('pageerror', error => exceptions.push(error.message));
      await watcher.clock.install();
      await watcher.goto(base + '/#/skills');
      const welcome = watcher.getByRole('button', {name:'Show my skills', exact:true});
      const on = watcher.getByRole('button', {name:`${name} in Claude Code: On`, exact:true});
      await welcome.or(on).first().waitFor();
      if (await welcome.isVisible()) await welcome.click();
      await on.waitFor();

      fs.renameSync(active, disabled);
      await watcher.bringToFront();
      await watcher.clock.fastForward(15_001);
      await watcher.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      const notice = watcher.getByRole('region', {name:/^1 skill changed on disk/});
      await notice.waitFor();
      assert(await on.isVisible());
      await notice.getByRole('button', {name:'Refresh', exact:true}).click();
      const off = watcher.getByRole('button', {name:`${name} in Claude Code: Off`, exact:true});
      await off.waitFor();
      const highlight = watcher.locator('tr.is-changed').filter({has:off});
      await highlight.waitFor();
      await notice.waitFor({state:'hidden'});
      await watcher.clock.fastForward(3501);
      await highlight.waitFor({state:'hidden'});
      assert(await off.isVisible());
      assert.equal(fs.readFileSync(disabled, 'utf8'), document);
    } finally {
      await view.close();
      fs.rmSync(folder, {recursive:true, force:true});
    }
  });
  await test('Canonical routes replace legacy history and retain query strings', async () => {
    await go('skills');
    await page.evaluate(() => { location.hash = '#/home?fixture=kept'; });
    await page.waitForURL(url => url.hash === '#/skills?fixture=kept');
    await page.goBack();
    await page.waitForURL(url => url.hash === '#/skills');
    await page.evaluate(() => { location.hash = '#/skill/sole-copy?view=file'; });
    await page.waitForURL(url => url.hash === '#/skills/sole-copy?view=file');
    await page.locator('#h1').getByText('sole-copy').waitFor();
    await page.evaluate(() => { location.hash = '#/new'; });
    await page.getByRole('heading', {name:'New skill', exact:true}).waitFor();
    await page.getByRole('button', {name:'Cancel', exact:true}).click();
  });
  await test('Direct editor route survives reload', async () => {
    await page.goto(base + '/#/skills/sole-copy/edit');
    await page.locator('.ed-area').waitFor();
    await page.reload();
    await page.locator('.ed-area').waitFor();
    assert.equal(new URL(page.url()).hash, '#/skills/sole-copy/edit');
    assert.match(await page.locator('.ed-area').inputValue(), /single fixture copy/);
  });
  await test('Editor leaves differing copies unchecked and stops on an external change (F5)', async () => {
    const name = 'majority-minor';
    const codex = file('.codex', name), claude = file('.claude', name);
    const originalCodex = fs.readFileSync(codex), originalClaude = fs.readFileSync(claude);
    try {
      await go('skill/' + name);
      await page.getByRole('button', {name:'Edit', exact:true}).click();
      const places = page.getByRole('complementary', {name:'Save to'});
      const codexRow = places.getByRole('checkbox', {name:/Codex/});
      assert.equal(await codexRow.isChecked(), false);
      assert.match(await codexRow.locator('..').innerText(), /Different copy/);
      for (const row of await places.getByRole('checkbox').all()) {
        if (await row.isChecked()) await row.uncheck();
      }
      await codexRow.check();
      await page.locator('#ed-desc').fill('A newly reviewed description.');
      await page.locator('#ed-desc').press('Control+s');
      await page.locator('.jf-reader-heading').getByRole('button',{name:'File text'}).waitFor();
      assert.match(fs.readFileSync(codex, 'utf8'), /A newly reviewed description[\s\S]*Majority text/);
      assert.deepEqual(fs.readFileSync(claude), originalClaude);
      await page.getByRole('button',{name:'Undo',exact:true}).click();
      await page.locator('.toast').getByText('Undone',{exact:true}).waitFor();
      assert.deepEqual(fs.readFileSync(codex), originalCodex);

      await page.getByRole('button', {name:'Edit', exact:true}).click();
      await page.locator('#ed-desc').fill('Preserve this draft.');
      const target = url => url.pathname === '/api/skills/' + name && url.searchParams.get('scope') === 'claude-code';
      const editBeforeWrite = route => {
        if (route.request().method() === 'PATCH') {
          fs.writeFileSync(claude, Buffer.concat([originalClaude, Buffer.from('External edit.\n')]));
        }
        return route.continue();
      };
      await page.route(target, editBeforeWrite);
      try {
        await page.locator('#ed-desc').press('Control+s');
        await page.locator('.jf-editor').getByRole('alert').getByText(/changed on disk/i).waitFor();
      } finally { await page.unroute(target, editBeforeWrite); }
      assert.equal(await page.locator('#ed-desc').inputValue(), 'Preserve this draft.');
      assert.match(fs.readFileSync(claude, 'utf8'), /External edit/);
      await page.getByRole('button', {name:'Cancel', exact:true}).click();
      await page.getByRole('button', {name:'Discard changes', exact:true}).click();
    } finally {
      fs.writeFileSync(codex, originalCodex);
      fs.writeFileSync(claude, originalClaude);
    }
  });
  for (const changeAfterSave of [false, true]) {
    const outcome = changeAfterSave ? 'Undo preserves a changed supporting file' : 'Undo restores the source and removes the added copy';
    await test('Editor adds a missing copy and ' + outcome, async () => {
      const name = changeAfterSave ? 'phase-three-editor-guard' : 'phase-three-editor-add';
      const source = file('.claude', name), target = file('.codex', name);
      const companion = 'references/café.txt';
      const sourceCompanion = path.join(path.dirname(source), companion);
      const targetCompanion = path.join(path.dirname(target), companion);
      const original = Buffer.from(`---\nname: ${name}\ndescription: Original description.\n---\n# Original instructions\n`);
      const notes = Buffer.from('Original companion notes\r\n');
      const newDescription = 'Use this skill to review an edited draft.';
      const newBody = '# Revised instructions\n\nReview the draft before publishing.\n';
      assert(!fs.existsSync(path.dirname(source)) && !fs.existsSync(path.dirname(target)));
      try {
        fs.mkdirSync(path.dirname(sourceCompanion), {recursive:true});
        fs.writeFileSync(source, original);
        fs.writeFileSync(sourceCompanion, notes);
        await go('skill/' + name);
        await page.getByRole('button', {name:'Edit', exact:true}).click();
        const places = page.getByRole('complementary', {name:'Save to'});
        const codex = places.getByRole('checkbox', {name:/Codex/});
        assert(await places.getByRole('checkbox', {name:/Claude Code/}).isChecked());
        assert.equal(await codex.isChecked(), false);
        await codex.locator('..').getByText('Not here', {exact:true}).waitFor();
        await codex.locator('..').getByText(/No copy here/).waitFor();
        const editor = page.locator('.jf-editor');
        await editor.getByLabel('Description', {exact:true}).fill(newDescription);
        await editor.getByLabel('Instructions', {exact:true}).fill(newBody);
        await editor.getByRole('button', {name:'Save to 1 place', exact:true}).waitFor();
        await codex.check();
        await codex.locator('..').getByText('A new copy will be added here.', {exact:true}).waitFor();
        assert(!fs.existsSync(path.dirname(target)), 'selecting a place should not create the copy');
        await editor.getByRole('button', {name:'Save to 2 places', exact:true}).click();
        const notice = page.locator('.toast').filter({hasText:`${name} saved to 2 places.`});
        const undo = notice.getByRole('button', {name:'Undo', exact:true});
        await undo.waitFor();
        const saved = fs.readFileSync(source);
        assert(saved.includes(newDescription) && saved.includes(newBody.trim()));
        assert.deepEqual(fs.readFileSync(target), saved);
        assert.deepEqual(fs.readFileSync(sourceCompanion), notes);
        assert.deepEqual(fs.readFileSync(targetCompanion), notes);
        assert(!fs.existsSync(file('.config/opencode', name)), 'unselected place should remain empty');

        const changedNotes = Buffer.from('Edited outside Jackfield after Save.\n');
        if (changeAfterSave) fs.writeFileSync(targetCompanion, changedNotes);
        await undo.click();
        if (changeAfterSave) {
          await page.locator('.toast').getByText(/couldn.t undo/i).waitFor();
          assert.deepEqual(fs.readFileSync(target), saved);
          assert.deepEqual(fs.readFileSync(targetCompanion), changedNotes);
        } else {
          await page.locator('.toast').getByText('Undone', {exact:true}).waitFor();
          assert(!fs.existsSync(path.dirname(target)), 'Undo should remove the added folder from the place');
          const trash = await page.request.get(base + '/api/trash?scope=codex');
          assert(trash.ok());
          const moved = (await trash.json()).find(entry => entry.name === name)?.trash_path;
          assert(moved, 'Undo should move the added folder to Trash');
          assert.deepEqual(fs.readFileSync(path.join(moved, companion)), notes);
        }
        assert.deepEqual(fs.readFileSync(source), original);
        assert.deepEqual(fs.readFileSync(sourceCompanion), notes);
      } finally {
        fs.rmSync(path.dirname(source), {recursive:true, force:true});
        fs.rmSync(path.dirname(target), {recursive:true, force:true});
      }
    });
  }
  await test('New skill draft survives Back, Keep editing and explicit Cancel', async () => {
    await go('skills');
    await page.evaluate(() => { location.hash = '#/new'; });
    const create = page.locator('.jf-create');
    await create.getByLabel('Name', {exact:true}).fill('draft-browser-test');
    await create.getByLabel('Instructions', {exact:true}).fill('Draft instructions retained.');
    await page.goBack();
    const discard = page.getByRole('dialog', {name:/Discard/});
    await discard.waitFor();
    await discard.getByRole('button', {name:'Keep editing'}).click();
    await create.waitFor();
    assert.equal(await create.getByLabel('Name', {exact:true}).inputValue(), 'draft-browser-test');
    assert.equal(await create.getByLabel('Instructions', {exact:true}).inputValue(), 'Draft instructions retained.');
    await create.getByLabel('Instructions', {exact:true}).fill('Still editable after Back.');
    await create.getByRole('button', {name:'Cancel', exact:true}).click();
    await discard.waitFor();
    await discard.getByRole('button', {name:'Keep editing'}).click();
    assert.equal(await create.getByLabel('Instructions', {exact:true}).inputValue(), 'Still editable after Back.');
    await create.getByRole('button', {name:'Cancel', exact:true}).click();
    await discard.getByRole('button', {name:/Discard/}).click();
    await page.waitForURL(url => url.hash === '#/skills');
    await create.waitFor({state:'hidden'});
  });
  await test('New skill previews exact file bytes for two selected places (F4)', async () => {
    const name = 'phase-three-create';
    const paths = [file('.claude',name), file('.codex',name)];
    await go('new');
    const create = page.locator('.jf-create');
    await create.getByLabel('Name', {exact:true}).fill(' Phase THREE Create ');
    await create.getByRole('button', {name:'Use phase-three-create'}).click();
    await create.getByLabel('What it does and when to use it').fill('Use this: review café. # preserve this\nA second line.');
    await create.getByRole('button', {name:'Checklist', exact:true}).click();
    await create.getByRole('checkbox', {name:/Codex/}).check();
    const preview = create.getByRole('complementary', {name:'What will be created'}).locator('pre');
    await preview.waitFor();
    const before = await preview.textContent();
    assert.match(before, /## Checklist/);
    assert.match(before, /A second line/);
    assert(paths.every(path => !fs.existsSync(path)), 'preview did not create any file');
    await create.getByRole('button', {name:'Create in 2 places'}).click();
    await page.waitForURL(url => url.hash === '#/skills/' + name);
    for (const path of paths) assert.deepEqual(fs.readFileSync(path), Buffer.from(before));
    assert(!fs.existsSync(file('.config/opencode',name)));
  });
  await test('New skill reports a partial create and keeps confirmed files', async () => {
    const name = 'phase-three-partial';
    const codex = url => url.pathname === '/api/skills' && url.searchParams.get('scope') === 'codex';
    let rejected = 0;
    const fail = route => { rejected++; return route.fulfill({status:409, json:{error:'Fixture write refused'}}); };
    await page.route(codex, fail);
    try {
      await go('new');
      const create = page.locator('.jf-create');
      await create.getByLabel('Name', {exact:true}).fill(name);
      await create.getByLabel('What it does and when to use it').fill('Use for a partial creation fixture.');
      await create.getByRole('checkbox', {name:/Codex/}).check();
      await create.getByRole('button', {name:'Create in 2 places'}).click();
      await create.getByText(/Some places couldn.t be confirmed/).waitFor();
      assert.equal(rejected, 1);
      assert(fs.existsSync(file('.claude', name)));
      assert(!fs.existsSync(file('.codex', name)));
      assert(await create.getByRole('checkbox', {name:/Codex/}).isDisabled());
      await create.getByRole('link', {name:'Open it'}).click();
      await page.waitForURL(url => url.hash === '#/skills/' + name);
    } finally { await page.unroute(codex, fail); }
  });
  await test('New skill can target the library before it has a folder', async () => {
    const scopes = url => url.pathname === '/api/scopes';
    const records = url => url.pathname === '/api/skills' && url.searchParams.get('scope') === 'all';
    const library = path.join(root, 'data/jackfield/skills');
    const absent = route => route.fulfill({json:[{id:'global', kind:'global', label:'Global', path:library,
      exists:false, writable:true, availability:'missing'}]});
    const empty = route => route.fulfill({json:[]});
    await page.route(scopes, absent);
    await page.route(records, empty);
    try {
      await go('new');
      const create = page.locator('.jf-create');
      assert(await create.getByRole('checkbox', {name:/Your library/}).isChecked());
      await create.getByLabel('Name', {exact:true}).fill('phase-three-library');
      await create.getByLabel('What it does and when to use it').fill('Use for the empty library fixture.');
    } finally {
      await page.unroute(scopes, absent);
      await page.unroute(records, empty);
    }
    await page.getByRole('button', {name:'Create in 1 place', exact:true}).click();
    await page.waitForURL(url => url.hash === '#/skills/phase-three-library');
    assert(fs.existsSync(path.join(library, 'phase-three-library/SKILL.md')));
  });
  await test('Delayed initial template lookup preserves new skill input', async () => {
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    const matches = url => url.pathname === '/api/templates';
    const handler = async route => { await gate; await route.fulfill({json:{templates:['delayed-fixture']}}); };
    const detail = url => url.pathname === '/api/templates/delayed-fixture';
    let detailReads = 0;
    const detailHandler = route => { detailReads++; return route.fulfill({json:{body:'# Different stored template body'}}); };
    await page.route(matches, handler);
    await page.route(detail, detailHandler);
    try {
      await go('skills');
      await page.evaluate(() => { location.hash = '#/new?template=delayed-fixture'; });
      const create = page.locator('.jf-create');
      await create.getByLabel('Instructions', {exact:true}).fill('Typed before template lookup finished.');
      const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/templates');
      release();
      await response;
      await page.waitForTimeout(200);
      assert.equal(detailReads, 0, 'a delayed lookup must not apply a template over typed instructions');
      assert.equal(await create.getByLabel('Instructions', {exact:true}).inputValue(), 'Typed before template lookup finished.');
      await create.getByRole('button', {name:'Cancel', exact:true}).click();
      await page.getByRole('dialog', {name:'Discard this skill draft?'}).getByRole('button', {name:'Discard draft'}).click();
      await page.waitForURL(url => url.hash === '#/skills');
    } finally { release(); await page.unroute(matches, handler); await page.unroute(detail, detailHandler); }
  });
  await test('Tracking draft survives a query-only route change', async () => {
    await go('settings/tracking/add-agent');
    await page.locator('#trk-name').fill('Unfinished agent');
    await page.evaluate(() => { location.hash = '#/settings/tracking/add-agent?source=fixture'; });
    await page.waitForURL(url => url.hash === '#/settings/tracking/add-agent?source=fixture');
    await page.waitForTimeout(200);
    assert.equal(await page.locator('#trk-name').inputValue(), 'Unfinished agent');
    await page.locator('.trk-form').getByRole('button', {name:'Cancel'}).click();
    await page.getByRole('dialog', {name:/Discard/}).getByRole('button', {name:'Discard'}).click();
    await page.waitForURL(url => url.hash === '#/settings/tracking');
  });
  await test('Direct editor recovers after a failed document read and retry', async () => {
    let failures = 0;
    const matches = url => url.pathname === '/api/skills/sole-copy' && url.searchParams.get('scope') === 'claude-code';
    const handler = route => failures++ === 0
      ? route.fulfill({status:503, json:{error:'Fixture body unavailable'}}) : route.continue();
    await page.route(matches, handler);
    try {
      await page.goto(base + '/#/skills/sole-copy/edit');
      await page.getByRole('button', {name:'Retry document'}).click();
      await page.locator('.ed-area').waitFor();
      assert.match(await page.locator('.ed-area').inputValue(), /single fixture copy/);
      assert.equal(new URL(page.url()).hash, '#/skills/sole-copy/edit');
      assert(failures >= 2);
    } finally { await page.unroute(matches, handler); }
  });
  await test('Unknown page and missing skill offer recovery and a close name (S13)', async () => {
    await go('unknown-fixture');
    await page.getByRole('heading', {name:'Page not found'}).waitFor();
    assert(await page.getByRole('link', {name:'Go to Skills'}).isVisible());
    assert(await page.getByRole('link', {name:'Look in Trash'}).isVisible());
    await page.evaluate(() => { location.hash = '#/skills/sole-cop'; });
    await page.getByText('Did you mean', {exact:true}).waitFor();
    await page.getByRole('link', {name:'sole-copy', exact:true}).click();
    await page.waitForURL(url => url.hash === '#/skills/sole-copy');
    await page.locator('.jf-reader-heading').waitFor();
  });
  await test('Home listing budgets use real evidence and recover from a failed read', async () => {
    await go('home');
    let card = page.getByRole('region', {name:'Skill listing budgets', exact:true});
    assert.equal(await card.locator('.listing-budget').count(), 2);
    assert.match(await card.innerText(), /Claude Code[\s\S]*characters[\s\S]*Codex[\s\S]*tokens/);
    assert.match(await card.innerText(), /partial evidence/);
    const report = await (await context.request.get(base+'/api/doctor?scope=all&hygiene=1')).json();
    assert((await card.innerText()).includes('~'+new Intl.NumberFormat().format(report.hygiene.claude_listing.listing_chars)));
    for (const width of [1280, 320]) for (const mode of ['dark', 'light']) {
      await page.setViewportSize({width,height:900});
      await theme(mode);
      await card.scrollIntoViewIfNeeded();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await card.screenshot({path:path.join(root,`listing-budget-${mode}-${width}.png`)});
    }
    await page.setViewportSize({width:1280,height:900});
    const matches = url => url.pathname==='/api/doctor' && url.searchParams.get('hygiene')==='1';
    let attempts = 0;
    const handler = route => attempts++===0 ? route.fulfill({status:503,contentType:'application/json',body:'{"error":"fixture unavailable"}'}) : route.continue();
    await page.route(matches, handler);
    try {
      await go('home');
      card = page.getByRole('region', {name:'Skill listing budgets', exact:true});
      assert.match(await card.getByRole('alert').innerText(), /Couldn't read listing estimates/);
      assert(await page.locator('.room').count()>0, 'inventory remains usable');
      await card.getByRole('button', {name:'Retry listing estimates', exact:true}).focus();
      await page.keyboard.press('Enter');
      await card.getByRole('heading', {name:'Claude Code', exact:true}).waitFor();
      assert.equal(await card.getByRole('alert').count(), 0);
      await card.getByRole('link', {name:'Review listing evidence'}).click();
      await page.waitForURL(url => url.hash === '#/advanced/quality');
    } finally { await page.unroute(matches, handler); }
  });
  await test('Unmodified shortcuts leave focused controls alone', async () => {
    await go('home');
    for (const control of [page.getByRole('button', {name:'Keyboard shortcuts'}), page.getByRole('link', {name:'Skills', exact:true})]) {
      await control.focus();
      // Dispatch to the page so Firefox's own quick-find shortcut cannot take focus.
      for (const key of ['/', '?']) {
        await control.dispatchEvent('keydown', {key, bubbles:true, cancelable:true});
        assert(await control.evaluate(el => document.activeElement === el));
        assert.equal(await page.getByRole('dialog', {name:'Keyboard shortcuts'}).count(), 0);
      }
    }
    await page.locator('#h1').focus();
    await page.keyboard.press('/');
    assert(await page.getByRole('combobox', {name:'Search skills, actions and pages'}).evaluate(el => document.activeElement === el));
  });
  await test('Skill page opens from search and shows the exact file bytes for the chosen copy (F1)', async () => {
    const codexFile = file('.codex', 'majority-minor'), original = fs.readFileSync(codexFile);
    const exact = Buffer.from('\ufeff' + original.toString('utf8').replace(/\n/g, '\r\n'));
    fs.writeFileSync(codexFile, exact);
    try {
      await go('skills');
      await page.getByRole('button', {name:'Search skills, actions and pages'}).click();
      const search = page.getByRole('combobox', {name:'Search skills, actions and pages'});
      await search.fill('majority-minor');
      await page.getByRole('option', {name:/^majority-minor/}).waitFor();
      await search.press('Enter');
      await page.waitForURL(url => url.hash === '#/skills/majority-minor');
      await page.locator('#h1').getByText('majority-minor', {exact:true}).waitFor();
      await page.getByRole('button', {name:'File text', exact:true}).click();
      const text = page.locator('.jf-file-text');
      await text.waitFor();
      assert.match(await text.textContent(), /Majority text/);
      await page.getByLabel('Read copy').selectOption({label:'Codex'});
      await page.waitForFunction(expected => document.querySelector('.jf-file-text')?.textContent === expected, exact.toString('utf8'));
      assert.equal(await text.textContent(), exact.toString('utf8'));
      await page.reload();
      await text.waitFor();
      assert.equal(await text.textContent(), exact.toString('utf8'));
      await page.getByRole('button', {name:'Read', exact:true}).click();
      assert.match(await page.getByRole('article', {name:'Skill document'}).locator('.doc').innerText(), /Different text/);
    } finally { fs.writeFileSync(codexFile, original); }
  });
  await test('Skill page reads exact instances within one recursive scope (S3)', async () => {
    const name = 'reader-exact-instance';
    const fixture = fs.mkdtempSync(path.join(home, '.config/opencode/skills/reader-fixture-'));
    const notes = 'references/notes & checks.md';
    const copies = [
      {branch:'alpha', body:'Read the first OpenCode copy.', notes:'First line\n', lines:'1 line'},
      {branch:'beta', body:'Read the second OpenCode copy.', notes:'One\r\nTwo\r\nThree', lines:'3 lines'},
    ];
    try {
      for (const copy of copies) {
        const folder = path.join(fixture, copy.branch, name);
        fs.mkdirSync(path.join(folder, 'references'), {recursive:true});
        copy.label = 'OpenCode — ' + fs.realpathSync(folder);
        copy.raw = `---\nname: ${name}\ndescription: Use this fixture for exact reader checks.\n---\n\n${copy.body}\n`;
        fs.writeFileSync(path.join(folder, 'SKILL.md'), copy.raw);
        fs.writeFileSync(path.join(folder, notes), copy.notes);
        if (copy.branch === 'beta') {
          fs.writeFileSync(path.join(folder, 'references/binary.bin'), Buffer.from([0xff, 0xfe]));
        }
      }
      await go('skill/' + name);
      const picker = page.getByLabel('Read copy');
      const document = page.getByRole('article', {name:'Skill document'});
      const raw = document.locator('.jf-file-text');
      const files = page.getByRole('complementary', {name:'Details'}).locator('section')
        .filter({has:page.getByRole('heading', {name:'Files', exact:true})});
      for (const copy of [...copies].reverse()) {
        await picker.selectOption({label:copy.label});
        await document.locator('.doc').getByText(copy.body, {exact:true}).waitFor();
        await files.getByText(notes, {exact:true}).locator('..').getByText(copy.lines, {exact:true}).waitFor();
        const binary = files.getByText('references/binary.bin', {exact:true});
        if (copy.branch === 'beta') {
          await binary.locator('..').getByText('Line count unavailable', {exact:true}).waitFor();
        } else {
          assert.equal(await binary.count(), 0);
        }
        await page.getByRole('button', {name:'File text', exact:true}).click();
        await raw.waitFor();
        assert.equal(await raw.textContent(), copy.raw);
        await page.getByRole('button', {name:'Read', exact:true}).click();
      }
    } finally {
      fs.rmSync(fixture, {recursive:true, force:true});
    }
  });
  await test('Skill page square uses the shared panel and restores phone focus', async () => {
    await page.setViewportSize({width:390,height:844});
    try {
      await go('skill/same-everywhere');
      const square = page.getByRole('button', {name:'same-everywhere in Codex: On'});
      await square.focus();
      await square.press('Enter');
      const panel = page.getByRole('dialog', {name:'same-everywhere'});
      await panel.getByRole('button', {name:/^Turn off/}).waitFor();
      await page.keyboard.press('Escape');
      await panel.waitFor({state:'hidden'});
      assert(await square.evaluate(el => el === document.activeElement));
      assert(!fs.existsSync(file('.codex') + '.disabled'));
      await page.getByLabel('Read copy').selectOption({label:'Codex'});
      const details = page.getByRole('complementary', {name:'Details'});
      await details.getByText('SKILL.md', {exact:true}).waitFor();
      await turnOffCodexFromReader();
      await panel.waitFor({state:'hidden'});
      const undo = page.getByRole('button', {name:'Undo', exact:true});
      await undo.waitFor();
      assert(fs.existsSync(file('.codex') + '.disabled'));
      await details.getByText('SKILL.md.disabled', {exact:true}).waitFor();
      await undo.click();
      await square.waitFor();
      assert(fs.existsSync(file('.codex')));
      await details.getByText('SKILL.md', {exact:true}).waitFor();
      await go('skills?view=shelf&sel=same-everywhere%3Acodex');
      assert(await page.getByRole('link', {name:'Jackfield home'}).isVisible());
      assert.equal(await page.getByRole('dialog', {name:'same-everywhere'}).count(), 0);
    } finally { await page.setViewportSize({width:1280,height:900}); }
  });
  await test('Skill history follows navigation and ignores an older response', async () => {
    await go('skill/same-everywhere');
    let release;
    const delayed = new Promise(resolve => { release = resolve; });
    const matches = url => url.pathname === '/api/history' && url.searchParams.has('name') && !url.searchParams.has('snapshots');
    const handler = async route => {
      const name = new URL(route.request().url()).searchParams.get('name');
      if (name === 'sole-copy') await delayed;
      await route.fulfill({status:200, contentType:'application/json', body:JSON.stringify([{action:'fixture-'+name, timestamp:'2026-01-01T00:00:00Z'}])});
    };
    await page.route(matches, handler);
    try {
      await Promise.all([
        page.waitForRequest(request => request.url().includes('/api/history?limit=20&name=sole-copy')),
        page.evaluate(() => { location.hash = '#/skills/sole-copy'; }),
      ]);
      await Promise.all([
        page.waitForResponse(response => response.url().includes('/api/history?limit=20&name=same-everywhere')),
        page.evaluate(() => { location.hash = '#/skills/same-everywhere'; }),
      ]);
      const older = page.waitForResponse(response => response.url().includes('/api/history?limit=20&name=sole-copy'));
      release();
      await older;
      await page.waitForTimeout(200);
      assert.match(await page.getByRole('complementary', {name:'Details'}).innerText(), /fixture-same-everywhere/);
      assert.doesNotMatch(await page.getByRole('complementary', {name:'Details'}).innerText(), /fixture-sole-copy/);
    } finally { release(); await page.unroute(matches, handler); }
  });
  await test('Retired /v2 and /classic addresses open the interface at / keeping query and hash', async () => {
    await page.goto(base + '/classic/?window=claude#/skills');
    await page.getByRole('heading',{name:'Skills',exact:true}).waitFor();
    assert.equal(page.url(), base + '/?window=claude#/skills');
    await page.goto(base + '/v2?window=claude#/skills');
    await page.getByRole('heading',{name:'Skills',exact:true}).waitFor();
    assert.equal(page.url(), base + '/?window=claude#/skills');
    assert(await page.getByRole('heading',{name:'Skills',exact:true}).isVisible());
  });
  await test('Needs attention gives manual guidance and preserves unreadable bytes', async () => {
    const target = file('.codex', 'damaged-one'), before = fs.readFileSync(target);
    const writes = [];
    const observe = req => { if (attentionWrites(req)) writes.push(req.url()); };
    page.on('request', observe);
    try {
      await openAttention('damaged-one:codex:unreadable');
      assert.match(await attentionHeading.innerText(), /damaged-one/);
      assert.match(await attention.innerText(), /cannot be read as text|by hand|manually/i);
      assert.equal(await attention.getByRole('button', {name:'Replace with the readable copy'}).count(), 0);
      await attentionHeading.focus();
      await page.keyboard.press('f');
      assert.deepEqual(writes, []);
      assert.deepEqual(fs.readFileSync(target), before);
    } finally { page.off('request', observe); }
  });
  await test('Needs attention requires an explicit version before fixing a tied copy', async () => {
    const target = file('.codex', 'split-even'), before = fs.readFileSync(target);
    const writes = [];
    const observe = req => { if (attentionWrites(req)) writes.push(req.url()); };
    page.on('request', observe);
    try {
      await go('inbox?item=warn%3Asplit-even');
      await page.waitForURL(url => url.hash.startsWith('#/attention?'));
      await attentionHeading.waitFor();
      assert.match(await attentionHeading.innerText(), /split-even/);
      for (const name of ['Version 1', 'Version 2']) {
        const choice = attention.getByRole('button', {name:new RegExp('^' + name)});
        assert.equal(await choice.getAttribute('aria-pressed'), 'false');
      }
      assert(await attention.getByRole('button', {name:'Choose a version first', exact:true}).isDisabled());
      await attentionHeading.focus();
      await page.keyboard.press('Enter');
      await page.keyboard.press('f');
      assert.deepEqual(writes, []);
      assert.deepEqual(fs.readFileSync(target), before);
    } finally { page.off('request', observe); }
  });
  await test('Needs attention Open skill follows Enter without fixing (SR-1)', async () => {
    const target = file('.codex', 'damaged-fm'), before = fs.readFileSync(target);
    const writes = [];
    const observe = req => { if (attentionWrites(req)) writes.push(req.url()); };
    page.on('request', observe);
    try {
      await openAttention('damaged-fm:codex:unreadable');
      const open = attention.getByRole('link', {name:'Open skill', exact:true});
      await open.focus();
      await page.keyboard.press('f');
      await page.keyboard.press('Enter');
      await page.waitForURL(url => url.hash.startsWith('#/skills/damaged-fm'));
      assert.deepEqual(writes, []);
      assert.deepEqual(fs.readFileSync(target), before);
    } finally { page.off('request', observe); }
  });
  await test('Needs attention Check again counts two problems on one skill (F7)', async () => {
    const name = 'majority-minor';
    const damaged = file('.agents', name), original = fs.readFileSync(damaged);
    const endpoint = url => url.pathname === '/api/skills' && url.searchParams.get('scope') === 'all' && url.searchParams.get('body') === '0';
    let includeProblems = false;
    const restrictInventory = async route => {
      const response = await route.fetch();
      const records = await response.json();
      const names = ['sole-copy', 'same-everywhere', '.system'];
      if (includeProblems) names.push(name);
      await route.fulfill({response, json:records.filter(record => names.includes(record.name))});
    };
    await page.route(endpoint, restrictInventory);
    try {
      await openAttention();
      await attention.getByRole('heading', {name:'Nothing left to fix', exact:true}).waitFor();
      assert.match(await attention.innerText(), /We checked .* skills in .* places/);
      await attention.getByText(/^Last checked /).waitFor();
      await expectAttentionCount(0);
      fs.writeFileSync(damaged, Buffer.from([0xff, 0xfe]));
      includeProblems = true;
      await attention.getByRole('button', {name:'Check again', exact:true}).click();
      await expectAttentionCount(2);
      const issues = attention.getByRole('region', {name:'To fix · 2', exact:true});
      assert.equal(await issues.locator('[data-attention-id]').count(), 2);
      await issues.locator('[data-attention-id="majority-minor:codex:different"]').waitFor();
      await issues.locator('[data-attention-id="majority-minor:agents:unreadable"]').waitFor();
    } finally {
      fs.writeFileSync(damaged, original);
      await page.unroute(endpoint, restrictInventory);
    }
  });
  await test('Needs attention keyboard navigation, Skip and Undo preserve the issue group (F7)', async () => {
    const name = 'majority-minor', id = `${name}:codex:different`;
    const target = file('.codex', name), original = fs.readFileSync(target);
    const writes = [];
    const observe = req => { if (attentionWrites(req)) writes.push(req.postDataJSON().operation); };
    page.on('request', observe);
    try {
      await openAttention(id);
      const count = Number(await attentionNav.locator('.sm-nav__count').innerText());
      await expectAttentionCount(count);
      const ids = await attention.getByRole('region', {name:`To fix · ${count}`, exact:true})
        .locator('[data-attention-id]').evaluateAll(items => items.map(item => item.dataset.attentionId));
      const index = ids.indexOf(id);
      assert(index >= 0 && ids.length > 1);
      const forward = index < ids.length - 1;
      const adjacent = ids[index + (forward ? 1 : -1)];
      await attentionHeading.focus();
      await page.keyboard.press(forward ? 'j' : 'k');
      await page.waitForURL(url => new URLSearchParams(url.hash.split('?')[1]).get('item') === adjacent);
      await page.keyboard.press(forward ? 'k' : 'j');
      await page.waitForURL(url => new URLSearchParams(url.hash.split('?')[1]).get('item') === id);
      await attention.getByRole('button', {name:'Skip for now', exact:true}).click();
      const skipped = attention.getByRole('region', {name:'Skipped · 1', exact:true});
      const skippedItem = skipped.locator(`[data-attention-id="${id}"]`);
      await skippedItem.waitFor();
      await expectAttentionCount(count - 1);
      assert.deepEqual(writes, []);
      assert.deepEqual(fs.readFileSync(target), original);
      await skippedItem.click();
      await attention.getByRole('button', {name:'The shared version', exact:true}).click();
      await attention.locator('[data-primary]:enabled').waitFor();
      await attentionHeading.focus();
      await page.keyboard.press('f');
      const undo = page.locator('.toast').getByRole('button', {name:'Undo', exact:true});
      await undo.waitFor();
      await attention.getByRole('region', {name:'Fixed · 1', exact:true}).locator(`[data-attention-id="${id}"]`).waitFor();
      assert.deepEqual(writes, ['remove', 'sync']);
      assert.deepEqual(fs.readFileSync(target), fs.readFileSync(file('.claude', name)));
      await expectAttentionCount(count - 1);
      await undo.click();
      await page.locator('.toast').getByText(/^Undone/).waitFor();
      await skippedItem.waitFor();
      await expectAttentionCount(count - 1);
      assert.deepEqual(fs.readFileSync(target), original);
    } finally {
      page.off('request', observe);
      fs.mkdirSync(path.dirname(target), {recursive:true});
      fs.writeFileSync(target, original);
    }
  });
  await test('Skip link keeps the current page and focuses its heading (SR-2)',async()=>{await go('skill/same-everywhere');await page.locator('a.skip').focus();await page.keyboard.press('Enter');await page.waitForTimeout(200);assert(page.url().endsWith('#/skills/same-everywhere'),page.url());assert.equal(await page.evaluate(()=>document.activeElement&&document.activeElement.id),'h1');});
  await test('Navigation names the Needs attention count and stays outside the dialog tab order', async () => {
    await go('home');
    const badge = page.locator('.tabs a[href="#/attention"] .sm-nav__count');
    const count = Number(await badge.innerText());
    assert(count > 1, 'fixture includes multiple problems');
    const review = page.getByRole('link', {name: `Needs attention, ${count} items`, exact: true});
    const skipLink = page.getByRole('link', {name: 'Skip to content', exact: true});
    try {
      for (const width of [1280, 390]) {
        await page.setViewportSize({width, height: 900});
        await review.waitFor();
        assert.equal(await review.count(), 1);
      }
    } finally {
      await page.setViewportSize({width: 1280, height: 900});
    }
    const shortcuts = page.getByRole('button', {name: 'Keyboard shortcuts', exact: true});
    await shortcuts.click();
    await page.getByRole('dialog', {name: 'Keyboard shortcuts'}).waitFor();
    assert(await page.locator('.toasts').evaluate(element => element.inert));
    assert(await page.locator('a.skip').evaluate(element => {
      const focused = document.activeElement;
      element.focus();
      return element.inert && document.activeElement === focused;
    }));
    await page.keyboard.press('Escape');
    assert(!(await page.locator('.toasts').evaluate(element => element.inert)));
    assert.equal(await skipLink.count(), 1);
    assert(await shortcuts.evaluate(element => document.activeElement === element));
  });
  await test('Search accepts typing, keyboard navigation and returns all matches', async () => {
    await go('skill/sole-copy');
    await page.getByRole('button', {name:'Search skills, actions and pages'}).click();
    const search = page.getByRole('combobox', {name:'Search skills, actions and pages'});
    await page.waitForFunction(() => document.activeElement?.id === 'command-q');
    await search.pressSequentially('same');
    assert.equal(await search.inputValue(), 'same', 'the palette retains the typed query');
    const option = page.getByRole('option', {name:/same-everywhere/});
    await option.waitFor();
    await search.press('ArrowDown');
    assert.notEqual(await search.getAttribute('aria-activedescendant'), null);
    await page.getByRole('option', {name:'Show 1 match in Skills'}).click();
    await page.waitForURL(url => url.hash === '#/skills?q=same');
    await page.waitForFunction(() => document.querySelector('.jf-skills-filter input')?.value === 'same');
  });
  await test('New skill shows multiple lines of instructions and cancels cleanly', async () => {
    await go('skills');
    await page.getByRole('link', {name:'New skill', exact:true}).click();
    const dialog = page.locator('.jf-create');
    const instructions = dialog.getByLabel('Instructions', {exact:true});
    assert(await instructions.evaluate(element => element.clientHeight > 100));
    await dialog.getByRole('button', {name:'Cancel', exact:true}).click();
    await dialog.waitFor({state:'hidden'});
  });
  await test('Search includes skills despite prior Skills filters and excludes observations', async () => {
    await go('skills?view=shelf');
        await page.getByLabel('Agent', {exact:true}).selectOption('codex');
    await page.getByRole('button', {name:/Turned off/}).click();
    await page.getByRole('button', {name:'Search skills, actions and pages'}).click();
    const search = page.getByRole('combobox', {name:'Search skills, actions and pages'});
    await search.fill('sole-copy');
    await page.getByRole('option', {name:'Show 1 match in Skills'}).click();
    await page.waitForURL(url => url.hash === '#/skills?q=sole-copy');
    assert.equal(await page.getByRole('searchbox', {name:'Filter skills'}).inputValue(), 'sole-copy');
    assert(await page.getByRole('button', {name:/sole-copy in Claude Code/}).isVisible());
    await go('skill/sole-copy');
    assert.equal(await page.locator('.tree a').filter({hasText:'.system'}).count(), 0);
    await page.getByRole('button', {name:'Search skills, actions and pages'}).click();
    await search.fill('.system');
    assert.equal(await page.locator('#command-list [role="option"]').count(), 0);
    await page.keyboard.press('Escape');
    await openAttention();
    assert.equal(await attention.locator('[data-attention-id]').filter({hasText:'.system'}).count(), 0);
  });
  await test('Command palette has a desktop pointer entry and restores focus', async () => {
    await page.setViewportSize({width:1366,height:768});
    try {
      await go('home');
      const launcher = page.getByRole('button', {name:'Search skills, actions and pages'});
      await launcher.click();
      const dialog = page.getByRole('dialog', {name:'Search skills, actions and pages'});
      assert(await dialog.isVisible());
      await page.keyboard.press('Escape');
      assert(await launcher.evaluate(el => el === document.activeElement));
    } finally {
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Browser Back leaves a pristine New skill page and focuses the destination', async () => {
    await go('home');
    await page.locator('.tabs').getByRole('link', {name:'Skills', exact:true}).click();
    await page.getByRole('link', {name:'New skill', exact:true}).click();
    const dialog = page.locator('.jf-create');
    await dialog.waitFor();
    await page.goBack();
    await dialog.waitFor({state:'hidden'});
    const heading = page.getByRole('heading', {level:1, name:'Skills', exact:true});
    await heading.waitFor();
    assert(await heading.evaluate(el => el === document.activeElement));
  });
  await test('Sync map sidebar actions fit the panel for tied copies', async () => {
    const endpoint = /[/]api[/]skills[?]scope=all(?:&body=0)?$/;
    const inventory = await (await page.request.get(base + '/api/skills?scope=all')).json();
    await page.route(endpoint, route => route.fulfill({json:inventory.filter(record => record.name === 'split-even')}));
    try {
      for (const width of [1366, 1024, 320]) {
        await page.setViewportSize({width,height:768});
        await go('map');
        await page.getByRole('button', {name:'OpenCode', exact:true}).click();
        const action = page.getByRole('link', {name:'Choose which copies to keep in Needs attention'});
        await action.scrollIntoViewIfNeeded();
        assert(await action.evaluate(el => {
          const panel = el.closest('.mpanel');
          const bounds = el.getBoundingClientRect();
          return bounds.left >= 0 && bounds.right <= innerWidth && panel.scrollWidth <= panel.clientWidth + 1;
        }), `Sync map action clips at ${width}px`);
      }
    } finally {
      await page.unrouteAll({behavior:'wait'});
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Accessible names: brand at phone width, differing copy on its square, distinct Fix and Peek names (SR-4/6/7/11)',async()=>{await page.setViewportSize({width:390,height:844});try{await go('home');assert.equal(await page.locator('a.brand').getAttribute('aria-label'),'Jackfield home');const fixes=await page.locator('.look a').evaluateAll(a=>a.map(x=>x.getAttribute('aria-label')));assert.equal(new Set(fixes).size,fixes.length);}finally{await page.setViewportSize({width:1280,height:900});}await go('skill/majority-minor');assert(await page.getByRole('button',{name:'majority-minor in Codex: Different'}).isVisible());await go('map');await page.getByRole('button',{name:'Codex',exact:true}).click();const peeks=await page.locator('.peek').evaluateAll(a=>a.map(x=>x.getAttribute('aria-label')));assert(peeks.length>0&&new Set(peeks).size===peeks.length,peeks.join(' | '));});
  await test('An Undo toast stays while focused (SR-3)',async()=>{await go('skill/same-everywhere');await turnOffCodexFromReader();const undo=page.locator('.toast button').filter({hasText:'Undo'}).last();await undo.waitFor();await undo.focus();const held=await page.evaluate(()=>!!document.activeElement.closest('.toast'));assert(held);await undo.click();await page.waitForTimeout(700);assert(fs.existsSync(file('.codex')));});
  await test('Reader replacement previews before writing and ignores a repeated confirmation', async () => {
    await go('skill/majority-minor');
    const review = page.getByRole('region', {name:'Copies differ'}).getByRole('button', {name:'Review a different copy'});
    const target = file('.codex', 'majority-minor'), before = fs.readFileSync(target);
    await review.click();
    const panel = page.locator('.jf-panel');
    await panel.getByRole('button', {name:'Compare the two versions'}).click();
    assert.deepEqual(fs.readFileSync(target), before);
    await panel.getByRole('button', {name:/Keep Claude Code/}).click();
    const confirm = panel.getByRole('button', {name:/^(Make|Replace)/});
    await confirm.evaluate(el => { el.click(); el.click(); });
    const undo = page.getByRole('button', {name:'Undo', exact:true});
    await undo.waitFor();
    assert.notDeepEqual(fs.readFileSync(target), before);
    await undo.click();
    await page.locator('.toast').getByText('Undone', {exact:true}).waitFor();
    assert.deepEqual(fs.readFileSync(target), before);
  });
  await test('Reader comparison controls stay available at laptop and narrow widths', async () => {
    try {
      for (const width of [1366, 1024, 320]) {
        await page.setViewportSize({width, height:768});
        await go('skill/split-even');
        const comparison = page.getByRole('region', {name:'Copies differ'});
        const target = comparison.getByRole('combobox', {name:'Compare with'});
        const highlight = comparison.getByRole('checkbox', {name:"Highlight what's missing"});
        assert(await target.isVisible());
        await target.selectOption({index:1});
        await highlight.check();
        assert(await highlight.isChecked());
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        await comparison.getByRole('link', {name:'Choose a version in Needs attention', exact:true}).click();
        await page.waitForURL(url => url.hash.startsWith('#/attention?') &&
          new URLSearchParams(url.hash.split('?')[1]).get('item') === 'split-even:split');
        await attentionHeading.waitFor();
        assert.match(await attentionHeading.innerText(), /split-even/);
      }
    } finally {
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Needs attention review follows the chosen version and shows affected locations', async () => {
    await openAttention('majority-minor:codex:different');
    const shared = attention.getByRole('button', {name:/^The shared version/});
    const codex = attention.getByRole('button', {name:/^Codex’s version/});
    assert.equal(await shared.getAttribute('aria-pressed'), 'false');
    assert.equal(await codex.getAttribute('aria-pressed'), 'false');
    await shared.click();
    const targets = attention.getByRole('list', {name:'Copies that will be overwritten'});
    assert.match(await targets.innerText(), /Codex/);
    assert((await targets.innerText()).includes(path.dirname(file('.codex', 'majority-minor'))));
    await codex.click();
    const comparison = attention.getByRole('region', {name:'Document comparison'});
    await comparison.locator('.compare-identities > div').last().getByText('Codex', {exact:true}).waitFor();
    const apply = attention.getByRole('button', {name:'Use Codex’s version everywhere', exact:true});
    await apply.waitFor();
    assert.equal(await targets.locator('li').count(), 3);
    assert.doesNotMatch(await targets.innerText(), /Codex/);
    const exactRead = url => url.pathname === '/api/skills/majority-minor' && url.searchParams.get('scope') === 'agents';
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    const delay = async route => { await pending; await route.continue(); };
    await page.route(exactRead, delay);
    try {
      await attention.getByLabel('Compare target').selectOption('agents');
      assert.match(await comparison.locator('.compare-identities > div').first().innerText(), /Shared skills folder/);
      assert(await apply.isDisabled());
      release();
      await attention.locator('[data-primary]:enabled').waitFor();
      await comparison.getByText(/Supporting files haven’t been compared here/).waitFor();
    } finally {
      release();
      await page.unroute(exactRead, delay);
    }
  });
  await test('Needs attention Fix stays clear of navigation after scrolling', async () => {
    try {
      for (const [width, block] of [[1280, 'start'], [390, 'end']]) {
        await page.setViewportSize({width, height:577});
        await openAttention('majority-minor:codex:different');
        await attention.getByRole('button', {name:/^The shared version/}).click();
        const visible = await attention.getByRole('button', {name:'Use the shared version in Codex', exact:true}).evaluate((button, block) => {
          button.focus({preventScroll:true});
          button.scrollIntoView({block, behavior:'instant'});
          const rect = button.getBoundingClientRect();
          const header = document.querySelector('.top').getBoundingClientRect();
          const footer = document.querySelector('.bottomnav').getBoundingClientRect();
          const hit = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
          return document.activeElement === button && button.contains(hit) &&
            rect.top >= header.bottom && rect.bottom <= (footer.height ? footer.top : innerHeight);
        }, block);
        assert(visible, `Needs attention Fix is obscured at ${width}px`);
      }
    } finally {
      await page.setViewportSize({width:1280, height:900});
    }
  });
  await test('Needs attention runs one delayed Fix and Undo restores the exact folder and count (F7)', async () => {
    const name = 'majority-minor', id = `${name}:codex:different`;
    const target = file('.codex', name), before = fs.readFileSync(target);
    const companion = path.join(path.dirname(target), 'target-only.txt');
    fs.writeFileSync(companion, 'previous copy only');
    const operations = [];
    const endpoint = '**/api/batch/execute';
    const delay = async route => {
      operations.push(route.request().postDataJSON().operation);
      await new Promise(resolve => setTimeout(resolve, 400));
      await route.continue();
    };
    await page.route(endpoint, delay);
    try {
      await openAttention(id);
      const count = Number(await attentionNav.locator('.sm-nav__count').innerText());
      await expectAttentionCount(count);
      await attention.getByRole('button', {name:/^The shared version/}).click();
      const apply = attention.getByRole('button', {name:'Use the shared version in Codex', exact:true});
      await attention.locator('[data-primary]:enabled').waitFor();
      const removed = page.waitForResponse(r => attentionWrites(r.request()) &&
        r.request().postDataJSON().operation === 'remove');
      await apply.evaluate(button => { button.click(); button.click(); });
      const response = await removed;
      assert(response.ok());
      const removedCopy = (await response.json()).results[0];
      const retained = removedCopy.trash_path;
      assert.equal(path.dirname(retained), path.join(home, '.codex', 'trash'));
      assert.equal(fs.readFileSync(path.join(retained, 'target-only.txt'), 'utf8'), 'previous copy only');
      const undo = page.locator('.toast').getByRole('button', {name:'Undo', exact:true});
      await undo.waitFor();
      assert.deepEqual(operations, ['remove', 'sync']);
      await expectAttentionCount(count - 1);
      await attention.getByRole('heading', {name:'Fixed · 1', exact:true}).waitFor();
      assert.deepEqual(fs.readFileSync(target), fs.readFileSync(file('.claude', name)));
      await undo.click();
      await page.locator('.toast').getByText(/^Undone/).waitFor();
      assert.deepEqual(fs.readFileSync(target), before);
      assert.equal(fs.readFileSync(companion, 'utf8'), 'previous copy only');
      assert(!fs.existsSync(retained));
      await expectAttentionCount(count);
      await attentionItem(id).waitFor();
      await attention.getByRole('heading', {name:/^Fixed ·/}).waitFor({state:'hidden'});
    } finally {
      await page.unroute(endpoint, delay);
      fs.mkdirSync(path.dirname(target), {recursive:true});
      fs.writeFileSync(target, before);
      fs.rmSync(companion, {force:true});
    }
  });
  await test('Stale file toggle reports error without resurrecting fixture',async()=>{await go('skill/same-everywhere');const f=file('.codex'),old=fs.readFileSync(f);fs.unlinkSync(f);try{await turnOffCodexFromReader();await page.waitForTimeout(600);assert(!fs.existsSync(f));assert(!fs.existsSync(f+'.disabled'));await page.locator('.jf-panel').getByRole('alert').waitFor();}finally{fs.writeFileSync(f,old);}});
  await test('Native setting evidence is partial and file switch Undo preserves files',async()=>{await go('skill/same-everywhere');await page.locator('.native-settings summary').click();let t=await page.locator('.native-settings').innerText();assert.match(t,/partial/i);assert.match(t,/loading is unknown/i);assert.match(t,/Declared setting: off/);assert.match(t,/Declared setting: deny/);const f=file('.codex');await turnOffCodexFromReader();await page.waitForTimeout(500);assert(fs.existsSync(f+'.disabled'));await page.locator('.toast button').filter({hasText:'Undo'}).last().click();await page.waitForTimeout(600);assert(fs.existsSync(f));assert(!fs.existsSync(f+'.disabled'));});
  await test('Native invalid and unavailable settings render without exposing values',async()=>{let config=path.join(home,'.config/opencode/opencode.json'),saved=fs.readFileSync(config),claude=path.join(home,'.claude/settings.json'),oldClaude=fs.readFileSync(claude);fs.writeFileSync(config,'{"private":"fixture-secret",');fs.writeFileSync(claude,JSON.stringify({skillOverrides:{'majority-minor':'invalid-fixture-value'}}));try{await go('skill/majority-minor');await page.locator('.native-settings summary').click();let t=await page.locator('.native-settings').innerText();assert.match(t,/invalid/);assert.match(t,/unavailable/);assert.doesNotMatch(t,/fixture-secret|invalid-fixture-value/);}finally{fs.writeFileSync(config,saved);fs.writeFileSync(claude,oldClaude);}});
  await test('Discard navigation, dialog focus trap and cancellation',async()=>{await go('skill/same-everywhere');await page.getByRole('button',{name:'Edit',exact:true}).click();assert(await page.locator('#ed-desc').evaluate(e=>e===document.activeElement));await page.locator('.ed-area').fill('Unsaved browser fixture');await page.locator('.tabs a').filter({hasText:'Skills'}).click();await page.locator('.dlg').waitFor();for(let i=0;i<10;i++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>document.querySelector('.dlg').contains(document.activeElement)));}await page.getByRole('button',{name:'Keep editing'}).click();assert(await page.locator('.ed-area').isVisible());await page.locator('.tabs a').filter({hasText:'Skills'}).click();await page.getByRole('button',{name:'Discard changes'}).click();await page.waitForTimeout(300);assert(page.url().endsWith('#/skills'));});
  await test('Trash & backups restores a library folder from the merged list', async () => {
    const target = libraryFile('library-fixture'), original = fs.readFileSync(target);
    await go('skill/library-fixture');
    await page.getByRole('button', {name:'Move to Trash', exact:true}).click();
    assert.equal(await page.locator('.pick input:checked').count(), 1);
    await page.locator('.dlg-f .btn-danger').click();
    await page.waitForURL(url => url.hash === '#/skills');
    assert(!fs.existsSync(target));
    await go('recovery');
    assert.equal(new URL(page.url()).hash, '#/trash');
    const restore = restoreButton('library-fixture', 'Your library');
    await restore.click();
    const review = page.getByRole('dialog', {name:'Restore library-fixture?', exact:true});
    assert(!fs.existsSync(target));
    await review.getByRole('button', {name:'Restore folder', exact:true}).click();
    await restore.waitFor({state:'hidden'});
    assert.deepEqual(fs.readFileSync(target), original);
    const restored = trashList.getByRole('link', {name:'Show restored copy', exact:true});
    await restored.waitFor();
    assert.match(await restored.getAttribute('href'), /scope=global/);
  });
  await test('Trash & backups restores the exact library copy of a skill named purge', async () => {
    const trashed = [];
    const installed = path.dirname(libraryFile('purge'));
    try {
      for (const [i, body] of ['Older content.', 'Newer content.'].entries()) {
        const created = await page.request.post(base+'/api/skills', {data:{name:'purge', description:'Recovery test fixture.', body}});
        assert.equal(created.status(), 201);
        const removed = await page.request.delete(base+'/api/skills/purge?scope=global');
        assert.equal(removed.status(), 200);
        trashed.push((await removed.json()).trash_path);
        fs.utimesSync(trashed[i], 1700000000 + i * 60, 1700000000 + i * 60);
      }
      await go('trash');
      await restoreButton('purge', 'Your library', 'copy 1 of 2').waitFor();
      await restoreButton('purge', 'Your library', 'copy 2 of 2').click();
      const review = page.getByRole('dialog', {name:'Restore purge?', exact:true});
      const restoring = page.waitForResponse(r => {
        const url = new URL(r.url());
        return r.request().method() === 'POST' && url.pathname === '/api/trash/purge' && url.searchParams.get('scope') === 'global';
      });
      await review.getByRole('button', {name:'Restore folder', exact:true}).click();
      const response = await restoring;
      assert(response.ok());
      assert.equal(response.request().postDataJSON().trash_path, trashed[0]);
      await review.waitFor({state:'hidden'});
      assert.match(fs.readFileSync(libraryFile('purge'), 'utf8'), /Older content\./);
      assert(!fs.existsSync(trashed[0]));
      assert(fs.existsSync(trashed[1]));
    } finally {
      for (const dir of [installed, ...trashed]) fs.rmSync(dir, {recursive:true, force:true});
    }
  });
  for (const [name,sourceDisabled,targetDisabled] of [['target-disabled',false,true],['source-disabled',true,false]]) {
    await test(`Needs attention Undo restores ${name} bytes and disabled state`, async () => {
      const target = file('.codex', name), prior = target + (targetDisabled ? '.disabled' : '');
      const installed = target + (sourceDisabled ? '.disabled' : '');
      const source = file('.claude', name) + (sourceDisabled ? '.disabled' : '');
      const old = fs.readFileSync(prior), sourceBytes = fs.readFileSync(source);
      try {
        await openAttention(name + ':split');
        await attention.getByRole('button', {name:/^Version [12]$/}).filter({hasText:'claude original text'}).click();
        await attention.locator('[data-primary]:enabled').click();
        const undo = page.locator('.toast').getByRole('button', {name:'Undo', exact:true});
        await undo.waitFor();
        assert.deepEqual(fs.readFileSync(installed), sourceBytes);
        assert(!fs.existsSync(prior), 'fix should install the chosen copy’s disabled state');
        await undo.click();
        await page.locator('.toast').getByText(/^Undone/).waitFor();
        assert(!fs.existsSync(installed));
        assert.deepEqual(fs.readFileSync(prior), old);
      } finally {
        fs.rmSync(installed, {force:true});
        fs.mkdirSync(path.dirname(prior), {recursive:true});
        fs.writeFileSync(prior, old);
      }
    });
  }
  await test('Needs attention repairs malformed text and Undo brings its problem back', async () => {
    const name = 'damaged-fm', id = `${name}:codex:unreadable`;
    const target = file('.codex', name), before = fs.readFileSync(target);
    try {
      await openAttention(id);
      await attention.getByRole('button', {name:'Replace with the readable copy', exact:true}).click();
      const undo = page.locator('.toast').getByRole('button', {name:'Undo', exact:true});
      await undo.waitFor();
      await attention.getByRole('region', {name:'Fixed · 1', exact:true}).locator('[data-attention-id]').waitFor();
      assert.deepEqual(fs.readFileSync(target), fs.readFileSync(file('.claude', name)));
      await undo.click();
      await page.locator('.toast').getByText(/^Undone/).waitFor();
      await attentionItem(id).waitFor();
      assert.deepEqual(fs.readFileSync(target), before);
      await attention.getByRole('heading', {name:/^Fixed ·/}).waitFor({state:'hidden'});
    } finally {
      fs.mkdirSync(path.dirname(target), {recursive:true});
      fs.writeFileSync(target, before);
    }
  });
  await test('Create, editor focus, safe Markdown, save and Undo',async()=>{
    await go('skills');
    await page.getByRole('link',{name:'New skill',exact:true}).first().click();
    const name=page.getByLabel('Name', {exact:true});
    assert(await name.evaluate(e=>e===document.activeElement));
    await name.fill('created-browser');

    await page.locator('#nf-desc').fill('Use this fixture to verify browser creation.');
    await page.getByRole('button',{name:'Create in 1 place',exact:true}).click();
    await page.getByRole('button',{name:'Edit',exact:true}).waitFor();
    const f=file('.claude','created-browser'), original=fs.readFileSync(f);
    await page.getByRole('button',{name:'Edit',exact:true}).click();
    assert(await page.locator('#ed-desc').evaluate(e=>e===document.activeElement));
    await page.locator('#ed-body').fill('Name | Result\n--- | ---\n*italic* | [docs](https://example.test/a)\n\n<img src=x onerror="window.fixtureAttack=1">');
    await page.getByRole('button',{name:'Preview',exact:true}).click();
    assert.equal(await page.locator('.doc th').count(),2);
    assert.equal(await page.locator('.doc em').innerText(),'italic');
    assert.equal(await page.locator('.doc a,.doc img,.doc script').count(),0);
    assert.equal(await page.evaluate(()=>window.fixtureAttack),undefined);
    await page.locator('.savebar button').filter({hasText:'Save to'}).click();
    const undo = page.locator('.toast').filter({hasText:'created-browser saved to 1 place.'})
      .getByRole('button',{name:'Undo',exact:true});
    await undo.waitFor();
    assert.notDeepEqual(fs.readFileSync(f),original);
    const restore = page.waitForResponse(response => {
      const url = new URL(response.url());
      return response.request().method() === 'POST' && url.pathname === '/api/trash/created-browser'
        && url.searchParams.has('snapshot');
    });
    await undo.click();
    assert((await restore).ok());
    assert.deepEqual(fs.readFileSync(f),original);
  });
  await test('Markdown readers render tables, nested lists and safe content',async()=>{
    try {
      for (const width of [320, 768, 1024, 1440]) {
        await page.setViewportSize({width,height:900});
        await go('skill/markdown-reader');
        const table = page.locator('.doc').getByRole('table');
        await table.waitFor();
        assert.equal(await table.getByRole('columnheader').count(),6);
        assert.equal(await table.locator('tbody td code').first().innerText(),'a|b');
        assert.equal(await table.locator('tbody td').nth(1).evaluate(e=>getComputedStyle(e).textAlign),'right');
        assert.equal(await page.locator('.doc ul li ul li').innerText(),'Nested detail');
        assert(await page.locator('.doc').getByRole('checkbox',{name:'Completed'}).isChecked());
        assert.match(await page.locator('.doc pre').innerText(),/<tag>/);
        assert.equal(await page.locator('.doc :is(a,img,script)').count(),0);
        const overflow = await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
        assert(overflow <= 1, `Page overflow of ${overflow}px at ${width}px`);
        if (width===320) {
          const wrapper = page.locator('.doc').getByRole('region',{name:'Markdown table'});
          assert(await wrapper.evaluate(e=>e.scrollWidth>e.clientWidth));
          await wrapper.focus();
          await page.keyboard.press('ArrowRight');
          await page.waitForFunction(()=>document.activeElement.scrollLeft>0);
        }
      }
    } finally {
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('One-place dialogs preselect and cancellation keeps files',async()=>{
    await go('skill/sole-copy');
    const f=file('.claude','sole-copy'),before=fs.readFileSync(f);
    await page.getByRole('button',{name:'Move to Trash',exact:true}).click();
    assert.equal(await page.locator('.pick input:checked').count(),1);
    await page.getByRole('button',{name:'Cancel',exact:true}).click();
    assert.deepEqual(fs.readFileSync(f),before);
  });
  await test('Reader diagnosis and copy locations state what will be inspected', async () => {
    await go('skill/majority-minor');
    await page.getByText('Folder locations and source updates', {exact:true}).click();
    const codex = page.locator('.folder-paths > div').filter({hasText:'Codex'});
    assert.equal(await codex.locator('code').innerText(), path.dirname(file('.codex', 'majority-minor')));
    await page.getByText('AI maintenance', {exact:true}).click();
    const trigger = page.getByRole('button', {name:'Test a prompt or trace'});
    await trigger.click();
    const dialog = page.getByRole('dialog', {name:/^Why didn.t this skill run\?$/});
    await dialog.getByRole('heading', {name:'Discovery on disk'}).waitFor();
    await dialog.getByText('Skill folder', {exact:true}).press('Enter');
    assert.match(await dialog.locator('.ai-diagnosis .paths code').innerText(), /majority-minor$/);
    await dialog.getByRole('button', {name:'Cancel'}).click();
    assert(await trigger.evaluate(element => element === document.activeElement));
  });
  await test('Why page separates observed settings from unknown runtime and rechecks disk (F6)', async () => {
    const settings = path.join(home, '.claude/settings.json'), original = fs.readFileSync(settings);
    try {
      await page.setViewportSize({width:390,height:844});
      await go('skill/same-everywhere');
      await page.getByRole('link', {name:/Why isn.t it running/}).click();
      await page.getByRole('heading', {name:/Why isn.t same-everywhere running/}).waitFor();
      await page.getByRole('heading', {name:/Claude Code.s own settings turn this skill off/}).waitFor();
      const checks = page.getByRole('region', {name:'Checks in each place'});
      const loaded = checks.getByRole('row').filter({hasText:'Actually loaded'});
      assert.equal(await loaded.getByRole('cell', {name:'Unknown', exact:true}).count(), 4);
      assert(await checks.evaluate(element => element.scrollWidth > element.clientWidth));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      fs.writeFileSync(settings, '{}');
      await page.getByRole('button', {name:'Check again', exact:true}).click();
      await page.getByRole('heading', {name:/OpenCode.s own settings turn this skill off/}).waitFor();
      await page.reload();
      await page.getByRole('heading', {name:/OpenCode.s own settings turn this skill off/}).waitFor();
      await page.getByRole('navigation', {name:'Breadcrumb'}).getByRole('link', {name:'same-everywhere'}).click();
      await page.locator('.jf-reader-heading').waitFor();
    } finally {
      fs.writeFileSync(settings, original);
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Porting notes and risk findings run with AI off', async () => {
    await go('skill/sole-copy');
    await page.getByText('AI maintenance', {exact:true}).click();
    await page.getByRole('button', {name:'Check agent compatibility'}).click();
    const skill = page.getByLabel('Skill', {exact:true});
    await page.waitForURL(url => url.hash === '#/advanced/ai-port');
    await skill.waitFor();
    assert.equal(await skill.inputValue(), 'sole-copy');
    await page.getByRole('button', {name:'Find the facts'}).click();
    await page.getByText('Nothing agent-specific found').waitFor();
    await go('tools/ai-explain');
    await skill.selectOption('sole-copy');
    await page.getByRole('button', {name:'Scan', exact:true}).click();
    await page.getByText('No findings', {exact:true}).waitFor();
  });
  await test('Add-to-agent single target is selected and creates a copy',async()=>{
    await go('skill/share-three');await page.getByRole('button',{name:'Add to agent',exact:true}).click();
    assert.equal(await page.locator('.pick input:checked').count(),1);
    await page.getByRole('button',{name:'Cancel',exact:true}).click();
    const f=file('.config/opencode','share-three');assert(!fs.existsSync(f));
    await page.getByRole('button',{name:'Add to agent',exact:true}).click();
    await page.locator('.dlg-f button').filter({hasText:/^Add$/}).click();
    await page.waitForTimeout(500);assert(fs.existsSync(f));
    await page.getByRole('button',{name:'Undo',exact:true}).click();
    await page.locator('.toast').getByText('Undone',{exact:true}).waitFor();
    assert(!fs.existsSync(f));
  });
  await test('Trash & backups records a download only after successful handoff', async () => {
    await go('trash');
    const backup = trashScreen.locator('section[aria-labelledby="rec-backup"]');
    const lastDownload = backup.getByText(/^Last download started/);
    assert.equal(await lastDownload.count(), 0);
    const full=backup.getByRole('button',{name:'Download full archive'});
    const pattern=/\/api\/export\?full=1$/;
    let release, downloads=0;
    const pending=new Promise(resolve=>{release=resolve;});
    const countDownload=()=>{downloads++;};
    page.on('download',countDownload);
    await page.route(pattern,async route=>{
      await pending;
      await route.fulfill({status:409,json:{code:'backup_source_changed',error:'/private/source changed'}});
    });
    try {
      await full.click();
      await backup.getByRole('status').getByText('Preparing backup…').waitFor();
      assert(await full.isDisabled());
      assert(await backup.getByRole('button',{name:'Download backup', exact:true}).isDisabled());
      release();
      const alert=backup.getByRole('alert');
      await alert.waitFor();
      assert.match(await alert.innerText(),/Wait for changes to finish/);
      assert.doesNotMatch(await alert.innerText(),/private|HTTP 409/);
      assert.equal(downloads,0);
      assert.equal(await lastDownload.count(), 0);
      await page.unroute(pattern);
      const success=page.waitForEvent('download');
      await full.click();
      assert.equal((await success).suggestedFilename(),'full-export.tar.gz');
      await alert.waitFor({state:'detached'});
      await lastDownload.waitFor();
      const date = await lastDownload.innerText();
      await page.reload();
      await lastDownload.waitFor();
      assert.equal(await lastDownload.innerText(), date);
    } finally {
      release();
      await page.unroute(pattern);
      page.off('download',countDownload);
    }
  });
  await test('Trash & backups previews an archive before loading and explains invalid archives', async () => {
    const name = 'phase-four-archive-load';
    const installed = libraryFile(name);
    const companion = path.join(path.dirname(installed), 'notes.txt');
    const companionBytes = Buffer.from('Archived supporting file.\r\n');
    const collision = libraryFile('library-fixture');
    const collisionBefore = fs.readFileSync(collision);
    const seeded = await page.request.post(base + '/api/skills', {
      data:{name, description:'Private archive review fixture.', body:'# A skill to restore\n'},
    });
    assert.equal(seeded.status(), 201);
    const original = fs.readFileSync(installed);
    fs.writeFileSync(companion, companionBytes);
    await go('trash');
    const download = page.waitForEvent('download');
    await trashScreen.getByRole('button', {name:'Download backup', exact:true}).click();
    const saved = path.join(root, 'fixture-backup.tar.gz');
    await (await download).saveAs(saved);
    assert(fs.statSync(saved).size > 0);
    const removed = await page.request.delete(base + '/api/skills/' + name + '?scope=global');
    assert(removed.ok());

    const section = trashScreen.locator('section[aria-labelledby="rec-backup"]');
    const input = section.locator('#imp-file');
    const preview = section.getByRole('button', {name:'Preview backup', exact:true});
    const load = section.getByRole('button', {name:'Load backup', exact:true});
    const isImport = req => req.method() === 'PUT' && new URL(req.url()).pathname === '/api/import';
    const requests = [];
    const observe = req => { if (isImport(req)) requests.push(new URL(req.url()).searchParams); };
    page.on('request', observe);
    try {
      await input.setInputFiles(saved);
      await preview.click();
      await load.waitFor();
      const plan = section.getByRole('region', {name:'Backup preview', exact:true});
      const add = plan.getByRole('listitem').filter({has:page.getByText(name, {exact:true})});
      const skip = plan.getByRole('listitem').filter({has:page.getByText('library-fixture', {exact:true})});
      assert.match(await add.innerText(), /Add.*library/i);
      assert.match(await skip.innerText(), /Skip.*library/i);
      await skip.getByText('already exists', {exact:true}).waitFor();
      assert(await plan.getByRole('heading').evaluate(heading => heading === document.activeElement));
      assert.deepEqual(requests.map(q => q.get('preview')), ['1']);
      assert(!fs.existsSync(installed));
      assert.deepEqual(fs.readFileSync(collision), collisionBefore);

      await section.getByRole('button', {name:'Cancel preview', exact:true}).click();
      await load.waitFor({state:'hidden'});
      assert(await preview.evaluate(button => button === document.activeElement));
      assert.equal(requests.length, 1);
      assert(!fs.existsSync(installed));
      await input.setInputFiles(saved);
      await preview.click();
      await load.waitFor();
      const commitResponse = () => page.waitForResponse(response => isImport(response.request()) &&
        !!new URL(response.url()).searchParams.get('plan_id'));
      const external = Buffer.concat([original, Buffer.from('\nCreated outside Jackfield after preview.\n')]);
      fs.mkdirSync(path.dirname(installed));
      fs.writeFileSync(installed, external);
      try {
        const stale = commitResponse();
        await load.click();
        assert(!(await stale).ok());
        await section.getByRole('alert').filter({hasText:/preview is stale|preview.*again/i}).waitFor();
        assert.deepEqual(fs.readFileSync(installed), external);
        assert(!fs.existsSync(companion));
        assert.deepEqual(fs.readFileSync(collision), collisionBefore);
      } finally {
        fs.unlinkSync(installed);
        fs.rmdirSync(path.dirname(installed));
      }

      await input.setInputFiles(saved);
      await preview.click();
      await load.waitFor();
      const committed = commitResponse();
      await load.click();
      assert((await committed).ok());
      assert.deepEqual(requests.map(q => q.get('preview')), ['1', '1', null, '1', null]);
      assert(requests[2].get('plan_id'));
      assert(requests[4].get('plan_id'));
      assert.deepEqual(fs.readFileSync(installed), original);
      assert.deepEqual(fs.readFileSync(companion), companionBytes);
      assert.deepEqual(fs.readFileSync(collision), collisionBefore);
      await section.getByText(/1 skill imported/).waitFor();
      await section.getByText('Skipped entries', {exact:true}).click();
      await section.getByText('library-fixture', {exact:true}).waitFor();

      const bad = path.join(root, 'bad-archive.tar.gz');
      fs.writeFileSync(bad, 'not an archive');
      await page.waitForFunction(() => !document.getElementById('imp-file').disabled);
      await input.setInputFiles(bad);
      await preview.click();
      const error = await section.getByRole('alert').innerText();
      assert.match(error, /not a backup archive/);
      assert.doesNotMatch(error, /ReadError|Traceback|[/]tmp[/]/);
      assert(!(await load.isVisible()));
    } finally { page.off('request', observe); }
    await page.route('**/api/scopes',route=>route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'Traceback /home/private/secret PermissionError'})}));
    try{await go('home');assert.doesNotMatch(await page.locator('main').innerText(),/Traceback|PermissionError|[/]home[/]private/);}finally{await page.unrouteAll({behavior:'wait'});}
  });
  await test('Sync map totals, singular grammar and top-link target size',async()=>{
    await go('skills?view=shelf');const total=Number((await page.locator('.seg button').first().innerText()).match(/\d+/)?.[0]);
    await go('map');
    assert.equal(await page.locator('.map-total').innerText(), `Open all ${total.toLocaleString()} in Skills`);
    assert.doesNotMatch(await page.locator('main').innerText(),/1 copy differ(?!s)/);
    await page.setViewportSize({width:1280,height:900});
    const box=await page.locator('.top .tabs a[href="#/advanced"]').boundingBox();assert(box.height>=24);assert(box.width>=24);
  });
  await test('Shelf density persists across reload and is scoped to Shelf', async () => {
    await go('skills?view=shelf');
    const compact = page.getByRole('button', {name:'Compact', exact:true});
    const card = page.locator('.shelf .sk').first();
    const before = await card.boundingBox();
    try {
      await compact.click();
      await go('skills?view=shelf');
      assert.equal(await compact.getAttribute('aria-pressed'), 'true');
      assert((await card.boundingBox()).height < before.height);
      await page.getByRole('button', {name:'Exact instances', exact:true}).click();
      assert.equal(await compact.count(), 0);
      await page.getByRole('button', {name:'Shelf', exact:true}).click();
      assert.equal(await compact.getAttribute('aria-pressed'), 'true');
    } finally {
      await page.evaluate(() => localStorage.removeItem('skillsmgr-v2-density'));
    }
  });
  await test('Sync map reads copy states, searches, and returns keyboard focus from details', async () => {
    await page.setViewportSize({width:320,height:760});
    try {
      await go('map');
      const table = page.getByRole('table', {name:'Skill copies by agent'});
      const codexCopy = table.getByRole('button', {name:/majority-minor, Codex:.*Different copy/});
      await table.getByRole('button', {name:/damaged-one, Codex: Can't be read/}).waitFor();
      await table.getByRole('button', {name:/target-disabled, Codex: Turned off on disk.*no majority/}).waitFor();
      await table.getByRole('button', {name:/same-everywhere, Codex:.*Document text matches the reference/}).waitFor();
      assert((await table.getByRole('row').filter({hasText:'sole-copy'}).getByText('No copy listed').count()) > 0);
      assert(await page.locator('.map-scroll').evaluate(el => el.scrollWidth > el.clientWidth));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      const search = page.getByRole('searchbox', {name:'Find a skill in Sync map'});
      await search.fill('majority-minor');
      assert.equal(await table.getByRole('row').count(), 2);
      await codexCopy.focus();
      await page.keyboard.press('Enter');
      assert(await page.getByRole('heading', {name:'Codex', exact:true}).evaluate(el => el === document.activeElement));
      const details = page.locator('#map-details');
      assert.match(await details.innerText(), /majority-minor[\s\S]*Different copy/);
      assert(await details.getByRole('button', {name:'Select skills to sync'}).isDisabled());
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      assert(await codexCopy.evaluate(el => el === document.activeElement));
      await codexCopy.click();
      await details.getByRole('link', {name:'Open this copy'}).click();
      await page.waitForURL(url => url.hash === '#/skills/majority-minor');
      await go('map');
      await search.fill('no-such-fixture');
      await page.getByText('No skills match this search.').waitFor();
      assert.equal(await table.count(), 0);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    } finally {
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Copy comparison wraps on phones, reads the selected path and recovers after a read failure', async () => {
    const target = file('.codex', 'majority-minor');
    const original = fs.readFileSync(target);
    const longLine = '# ' + 'long-unbroken-markdown-path-'.repeat(30);
    fs.appendFileSync(target, '\n'+longLine+'\n');
    let allowRead = false;
    const match = url => url.pathname==='/api/skills/majority-minor' && url.searchParams.get('scope')==='codex';
    const request = route => allowRead ? route.continue() : route.fulfill({status:503, contentType:'application/json', body:'{"error":"Fixture read unavailable"}'});
    await page.route(match, request);
    try {
      await page.setViewportSize({width:1440,height:960});
      await go('map');
      await page.getByRole('button', {name:/majority-minor, Codex:.*Different copy/}).click();
      await page.getByRole('button', {name:'Show changes in majority-minor'}).focus();
      await page.keyboard.press('Enter');
      const panel = page.getByRole('region', {name:'Document comparison'});
      assert.match(await panel.getByRole('alert').innerText(), /Codex.*Fixture read unavailable/);
      assert((await panel.innerText()).includes(path.dirname(target)));
      allowRead = true;
      await panel.getByRole('button', {name:'Retry comparison'}).focus();
      await page.keyboard.press('Enter');
      const removed = panel.locator('.compare-line.del code').filter({hasText:longLine});
      await removed.waitFor();
      assert.equal(await panel.getByRole('alert').count(), 0);
      assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()), 'Document comparison');
      const chooser = panel.getByRole('button', {name:'Unified view'});
      assert(await chooser.isVisible());
      assert.equal(await chooser.getAttribute('aria-pressed'), 'false');
      await chooser.click();
      assert.equal(await chooser.getAttribute('aria-pressed'), 'true');
      await chooser.click();
      await panel.screenshot({path:path.join(root,'copy-comparison-desktop.png')});
      for (const width of [390,320]) {
        await page.setViewportSize({width,height:844});
        assert(!(await chooser.isVisible()));
        assert(await removed.evaluate(e=>e.scrollWidth<=e.clientWidth+1));
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await panel.screenshot({path:path.join(root,'copy-comparison-'+width+'.png')});
      }
      await page.getByRole('button', {name:'Hide changes in majority-minor'}).focus();
      await page.keyboard.press('Enter');
      assert.equal(await panel.count(), 0);
      assert.equal(await page.getByRole('button',{name:'Show changes in majority-minor'}).getAttribute('aria-expanded'),'false');
    } finally {
      fs.writeFileSync(target, original);
      await page.unroute(match, request);
      await page.setViewportSize({width:1280,height:900});
    }
  });
  await test('Skills retains the search when opening Sync map', async () => {
    await go('skills?view=shelf');
    await page.getByRole('searchbox',{name:'Search skills',exact:true}).fill('majority-minor');
    await page.getByRole('button',{name:'Exact instances',exact:true}).click();
    assert.equal(await page.getByRole('searchbox',{name:'Search skills',exact:true}).inputValue(),'majority-minor');
    try {
      await page.getByRole('link',{name:'Find name in Sync map'}).focus();
      await page.keyboard.press('Enter');
      const mapSearch = page.getByRole('searchbox',{name:'Find a skill in Sync map'});
      await mapSearch.waitFor();
      assert.equal(await mapSearch.inputValue(),'majority-minor');
      assert.equal(await page.getByRole('rowheader',{name:'majority-minor',exact:true}).count(),1);
    } finally {
      await go('skills?view=shelf');
      await page.getByRole('button',{name:'Shelf',exact:true}).click();
    }
  });
  await test('Sync map bounds rows and resets pagination on search', async () => {
    const list = /[/]api[/]skills[?]scope=all(?:&body=0)?$/;
    const records = await (await page.request.get(base+'/api/skills?scope=all')).json();
    const row = records.find(record => record.scope === 'codex' && record.name === 'same-everywhere');
    const many = Array.from({length:10000}, (_, i) => ({
      ...row, name:'fixture-'+String(i).padStart(5,'0'), path:undefined, physical_path:undefined, body:undefined,
    }));
    for (const i of [0, 9999]) many[i] = {...many[i], decode_error:'not valid UTF-8'};
    try {
      await page.route(list, route => route.fulfill({json:many}));
      await go('map');
      const table = page.getByRole('table', {name:'Skill copies by agent'});
      assert.equal(await table.locator('tbody tr').count(), 48);
      await page.getByRole('button', {name:'Next', exact:true}).click();
      assert.equal(await table.locator('tbody th').first().innerText(), 'fixture-00048');
      await page.getByRole('searchbox', {name:'Find a skill in Sync map'}).fill('fixture-09999');
      assert.deepEqual(await table.locator('tbody th').allInnerTexts(), ['fixture-09999']);
      await page.getByRole('searchbox', {name:'Find a skill in Sync map'}).clear();
      await page.getByRole('button', {name:'Next', exact:true}).click();
      await page.getByRole('checkbox', {name:'Needs review only'}).check();
      assert.deepEqual(await table.locator('tbody th').allInnerTexts(), ['fixture-00000', 'fixture-09999']);
    } finally {
      await page.unrouteAll({behavior:'wait'});
    }
  });
  await test('Sync map clears scope selections when opening a copy in that scope', async () => {
    await go('map');
    const table = page.getByRole('table', {name:'Skill copies by agent'});
    const panel = page.locator('#map-details');
    const checkbox = panel.getByRole('checkbox', {name:'Make majority-minor match'});
    const select = panel.getByRole('button', {name:'Select skills to sync'});
    const scope = table.getByRole('button', {name:'Codex', exact:true});
    await scope.click();
    assert(await checkbox.isChecked());
    await table.getByRole('button', {name:/same-everywhere, Codex:/}).click();
    assert(await select.isDisabled());
    assert(!(await checkbox.isChecked()));
    await scope.click();
    assert(await checkbox.isChecked());
  });
  await test('Sync map review filter combines with search and keeps actionable rows', async () => {
    await go('map');
    const table = page.getByRole('table', {name:'Skill copies by agent'});
    const review = page.getByRole('checkbox', {name:'Needs review only'});
    const rows = table.locator('tbody th');
    const search = page.getByRole('searchbox', {name:'Find a skill in Sync map'});
    await review.check();
    const names = await rows.allInnerTexts();
    for (const name of ['damaged-one', 'majority-minor', 'split-even']) {
      assert(names.includes(name), `${name} needs review`);
    }
    for (const name of ['sole-copy', 'same-everywhere', 'library-fixture']) {
      assert(!names.includes(name), `${name} has no flagged agent copies`);
    }
    await search.fill('damaged');
    assert.deepEqual(await rows.allInnerTexts(), ['damaged-fm', 'damaged-one']);
    await search.fill('same-everywhere');
    await page.getByRole('status').filter({hasText:'No skills match the review filter.'}).waitFor();
    await review.uncheck();
    assert.deepEqual(await rows.allInnerTexts(), ['same-everywhere']);
  });
  await test('Sync map review filter includes duplicated copies and uninspected links', async () => {
    const list = '**/api/skills?scope=all&body=0';
    const records = await (await page.request.get(base+'/api/skills?scope=all&body=0')).json();
    const copy = records.find(record => record.scope === 'codex' && record.name === 'same-everywhere');
    const record = (name, suffix) => ({...copy, name, path:undefined, physical_path:`/fixture/${name}/${suffix}`});
    const fixtures = [record('repeated', 'one'), record('repeated', 'two'), {
      ...record('uninspected', 'link'), decode_error:'Link outside the managed root', content_hash:null,
    }];
    try {
      await page.route(list, route => route.fulfill({json:fixtures}));
      await go('map');
      await page.getByRole('checkbox', {name:'Needs review only'}).check();
      const table = page.getByRole('table', {name:'Skill copies by agent'});
      assert.deepEqual(await table.locator('tbody th').allInnerTexts(), ['repeated', 'uninspected']);
      assert.equal(await table.getByRole('button', {name:/Multiple copies listed/}).count(), 1);
      assert.equal(await table.getByRole('button', {name:/Link target not inspected/}).count(), 1);
    } finally {
      await page.unroute(list);
    }
  });
  await test('Sync map keeps Undo when a later copy fails to sync', async () => {
    const name = 'zz-map-failure-fixture';
    const target = file('.codex', 'majority-minor');
    const before = fs.readFileSync(target);
    const additions = ['.claude', '.codex', '.agents'].map(scope => file(scope, name));
    const syncCalls = [];
    const syncRoute = '**/api/sync';
    try {
      for (const [i, filename] of additions.entries()) {
        fs.mkdirSync(path.dirname(filename));
        fs.writeFileSync(filename, `---\nname: ${name}\ndescription: Exercise partial sync.\n---\n${i === 1 ? 'Different.' : 'Reference.'}\n`);
      }
      await page.route(syncRoute, route => {
        const requested = route.request().postDataJSON().name;
        syncCalls.push(requested);
        return requested === name ? route.fulfill({status:503, json:{error:'Fixture sync interrupted'}}) : route.continue();
      });
      await go('map');
      await page.getByRole('button', {name:'Codex', exact:true}).click();
      await page.getByRole('button', {name:'Make 2 skills match in Codex', exact:true}).click();
      const toast = page.locator('.toast').filter({hasText:'Fixture sync interrupted'});
      await toast.waitFor();
      assert.deepEqual(syncCalls, ['majority-minor', name]);
      assert.match(await toast.innerText(), /1 skill now matches in Codex/);
      assert.notDeepEqual(fs.readFileSync(target), before);
      await toast.getByRole('button', {name:'Undo', exact:true}).click();
      await page.locator('.toast').filter({hasText:'Undone'}).waitFor();
      assert.deepEqual(fs.readFileSync(target), before);
    } finally {
      await page.unroute(syncRoute);
      fs.writeFileSync(target, before);
      for (const filename of additions) fs.rmSync(path.dirname(filename), {recursive:true, force:true});
    }
  });
  await test('Responsive layouts in both themes', async () => {
    const viewport = page.viewportSize();
    try {
      for (const [label, width, height] of [['desktop', 1280, 900], ['phone', 390, 844]]) {
        for (const mode of ['light', 'dark']) {
          await page.setViewportSize({width, height});
          await go('home');
          await theme(mode);
          for (const route of ['home', 'skills', 'skill/same-everywhere', 'map', 'attention', 'trash']) {
            await go(route);
            assert.equal(await page.locator('html').getAttribute('data-theme'), mode);
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1),
              false, `${label} ${mode} ${route}`);
            await page.screenshot({path:path.join(root, `${label}-${mode}-${route.replace('/', '-')}.png`)});
          }
        }
      }
    } finally { await page.setViewportSize(viewport); }
  });
  await test('Phone dark Sync map sampled text contrast',async()=>{
    await page.setViewportSize({width:390,height:844});await go('map');await theme('dark');
    const samples=await page.locator('.map-table .map-state').evaluateAll(rows=>rows.map(row=>{
      const style=getComputedStyle(row),rgb=value=>value.match(/[0-9.]+/g).slice(0,3).map(Number);
      const lum=value=>rgb(value).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
      const foreground=style.color,background=style.backgroundColor,a=lum(foreground),b=lum(background);
      return {foreground,background,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
    }));
    assert(samples.length);for(const sample of samples)assert(sample.ratio>=4.5,JSON.stringify(sample));
    fs.writeFileSync(path.join(root,'map-contrast.json'),JSON.stringify(samples,null,2)+'\n');
  });
  await test('Empty and one-record shelves render without stale cards',async()=>{
    const response=await page.request.get(base+'/api/skills?scope=all'),records=await response.json();
    const selected=records.find(r=>r.name==='library-fixture');assert(selected);
    for(const fixture of [[],[selected]]){
      await page.route(/[/]api[/]skills[?]scope=all(?:&body=0)?$/,route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture)}));
      try {
        await go('skills?view=shelf');
        assert.equal(await page.locator('.sk').count(),fixture.length);
        if (fixture.length) assert.equal(await page.locator('.instance-filters .count').innerText(), '1 skill');
        else assert(await page.getByRole('heading', {name:'No skills yet'}).isVisible());
        await go('map');
        assert.equal(await page.locator('.map-table tbody tr').count(),fixture.length);
      } finally {
        await page.unrouteAll({behavior:'wait'});
      }
    }
  });
  await test('Forced colors focus indicator',async()=>{await page.emulateMedia({forcedColors:'active'});await go('skills');await page.keyboard.press('Tab');assert(await page.evaluate(()=>matchMedia('(forced-colors: active)').matches && document.activeElement!==document.body && getComputedStyle(document.activeElement).outlineStyle!=='none'));await page.screenshot({path:path.join(root,'forced-colors.png')});await page.emulateMedia({forcedColors:'none'});});
  if(engine==='chromium' && headed) await test('Actual Chrome zoom at 200 and 400 percent',async()=>{
    const {execFileSync}=require('node:child_process');
    await page.setViewportSize({width:1280,height:900});await go('home');
    const windows=execFileSync('xwininfo',['-root','-tree'],{encoding:'utf8'});
    fs.writeFileSync(path.join(root,'x-windows.txt'),windows);
    const windowId=execFileSync('xdotool',['search','--onlyvisible','--class','[Cc]hrome'],{encoding:'utf8'}).trim().split('\n').pop();
    execFileSync('xdotool',['windowfocus','--sync',windowId]);
    execFileSync('xdotool',['key','--clearmodifiers','ctrl+0']);
    const baseline=await page.evaluate(()=>devicePixelRatio),samples=[];
    for(const [percent,keys] of [[200,5],[400,3]]){
      for(let n=0;n<keys;n++)execFileSync('xdotool',['key','--clearmodifiers','ctrl+equal']);
      await page.waitForTimeout(350);
      const sample=await page.evaluate(()=>({dpr:devicePixelRatio,width:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
      assert(Math.abs(sample.dpr/baseline-percent/100)<0.05,JSON.stringify({percent,baseline,...sample}));
      assert(sample.scroll<=sample.client+1,JSON.stringify(sample));samples.push({percent,...sample});
      for(const route of ['home','skills','skill/same-everywhere','map','attention','trash']){
        await go(route);
        await page.screenshot({path:path.join(root,`browser-zoom-${percent}-${route.replace('/','-')}.png`)});
        const overflow=await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(e=>{const b=e.getBoundingClientRect();return b.width>0 && b.right>document.documentElement.clientWidth+1;}).map(e=>({tag:e.tagName,cls:e.className,text:e.innerText?.slice(0,80),width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})));
        fs.writeFileSync(path.join(root,`overflow-${percent}-${route.replace('/','-')}.json`),JSON.stringify(overflow,null,2));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,`browser zoom ${percent}: ${route}`);
      }
      await go('skills');await page.getByRole('link',{name:'New skill',exact:true}).first().click();
      assert(await page.locator('#nf-name').evaluate(e=>e===document.activeElement));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false);
      await page.keyboard.press('Escape');
    }
    fs.writeFileSync(path.join(root,'browser-zoom.json'),JSON.stringify(samples,null,2)+'\n');
    execFileSync('xdotool',['key','--clearmodifiers','ctrl+0']);
  });
  await test('V2 Templates creates a real stored template and a skill with metadata',async()=>{
    await go('tools/templates');
    const form=page.locator('form').filter({has:page.getByRole('heading',{name:'New template',exact:true})});
    await form.getByLabel('Name',{exact:true}).fill('v2-browser-template');
    await form.getByLabel('Document body',{exact:true}).fill('# Browser template\n\nUse this fixture for checks.');
    await form.getByRole('button',{name:'Save template',exact:true}).click();
    await page.getByRole('button',{name:'v2-browser-template',exact:true}).click();
    await page.getByRole('button',{name:'Use template',exact:true}).click();
    const create=page.locator('form').filter({has:page.getByRole('heading',{name:'Create skill from template',exact:true})});
    await create.getByLabel('Name',{exact:true}).fill('v2-browser-created');
    await create.getByLabel('Description',{exact:true}).fill('Use when running v2 browser verification.');
    await create.getByLabel('Category',{exact:true}).fill('quality');
    await create.getByRole('button',{name:'Create skill',exact:true}).click();
    await page.waitForResponse(r=>r.url().includes('/api/skills?scope=all')).catch(()=>{});
    const doc=path.join(root,'data/jackfield/skills/v2-browser-created/SKILL.md');
    assert(fs.existsSync(doc));assert.match(fs.readFileSync(doc,'utf8'),/Browser template/);assert.match(fs.readFileSync(doc,'utf8'),/category: quality/);
  });
  await test('V2 Profiles stores metadata and executes an exact enable-only plan',async()=>{
    await go('tools/profiles');const form=page.locator('form').filter({has:page.getByRole('heading',{name:'Profile details',exact:true})});
    await form.getByLabel('Name',{exact:true}).fill('v2-browser-profile');
    await form.getByLabel('Description',{exact:true}).fill('Browser fixture profile.');
    await form.getByLabel('Filter skills',{exact:true}).fill('v2-browser-created');await form.locator('.tp-pick-list label').filter({hasText:'v2-browser-created'}).locator('input').check();
    await form.getByPlaceholder('Add a name not installed yet').fill('absent-member');await form.getByRole('button',{name:'Add',exact:true}).click();
    await form.getByRole('textbox',{name:'Native off list',exact:true}).fill('same-everywhere');
    await form.getByRole('button',{name:'Save profile',exact:true}).click();
    const row=page.locator('.v2-tool-row').filter({has:page.locator('strong').filter({hasText:'v2-browser-profile'})});
    await row.waitFor();
    await page.getByRole('button',{name:'New profile',exact:true}).click();
    await form.getByLabel('Name',{exact:true}).fill('v2-browser-profile');
    await form.getByRole('button',{name:'Save profile',exact:true}).click();
    await page.getByText('A saved profile has this name. Open it with Edit to make changes.').waitFor();
    await row.getByRole('button',{name:'Edit',exact:true}).click();
    assert.equal(await page.getByRole('textbox',{name:'Native off list',exact:true}).inputValue(),'same-everywhere');
    await row.getByRole('button',{name:'Preview',exact:true}).click();
    await page.getByText('absent-member',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Review enable-only plan',exact:true}).click();
    const response=page.waitForResponse(r=>r.url().endsWith('/api/batch/execute'));
    await page.getByRole('button',{name:'Execute reviewed plan',exact:true}).click();
    assert.equal((await response).status(),200);
    assert(fs.existsSync(path.join(root,'data/jackfield/skills/v2-browser-created/SKILL.md')));
    assert(fs.existsSync(file('.codex','same-everywhere')));
    assert(!fs.existsSync(path.join(home,'.claude/settings.local.json')));
  });
  await test('V2 Workspace evidence and settings persist through navigation',async()=>{
    await go('tools/workspaces');await page.getByLabel('Project path',{exact:true}).fill(root);await page.getByRole('button',{name:'Inspect project',exact:true}).click();
    await page.getByText(/Status: Outside managed roots/).waitFor();
    await go('tools/settings');await page.getByLabel('Theme',{exact:true}).selectOption('dark');
    await page.getByLabel('Text size',{exact:true}).selectOption('large');await page.getByLabel('Regional format',{exact:true}).selectOption('en-IN');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');assert.match(await page.locator('main').innerText(),/12,34,567.89/);
    await go('tools/settings');assert.equal(await page.getByLabel('Regional format',{exact:true}).inputValue(),'en-IN');
    await page.getByLabel('Text size',{exact:true}).selectOption('standard');await page.getByLabel('Theme',{exact:true}).selectOption('light');
    await page.keyboard.press('Control+k');await page.locator('#command-q').fill('templates');await page.locator('#command-list').getByRole('option',{name:/Templates/}).click();await page.getByRole('heading',{name:'Templates',exact:true}).waitFor();
  });
  await test('Peer scope link reads through and the owner copy remains editable',async()=>{
    const name='browser-peer-owner';
    const created=await page.request.post(base+'/api/skills?scope=agents',{data:{name,description:'Peer link browser fixture.',body:'# Original owner text\n'}});
    assert(created.ok(),await created.text());
    const target=path.join(home,'.agents','skills',name),link=path.join(home,'.claude','skills',name);
    fs.symlinkSync(target,link,'dir');
    const listed=await page.request.get(base+'/api/skills?scope=claude-code&body=1');
    assert(listed.ok());const alias=(await listed.json()).find(row=>row.name===name);
    assert(alias);assert.equal(alias.body,'# Original owner text\n');assert.equal(alias.link_followed,true);assert.equal(alias.read_only,true);
    await go('skills?view=shelf');
    await page.getByRole('button',{name:'Refresh files',exact:true}).click();
    await page.waitForTimeout(350);
    await page.locator('#agent-f').selectOption('claude-code');
    const card=page.locator('.sk').filter({hasText:name});await card.waitFor();
    await page.locator('.instance-filters').getByRole('button',{name:'Exact instances',exact:true}).click();
    const instance=page.locator('.instance-row').filter({hasText:name});await instance.waitFor();
    assert.match(await instance.innerText(),/linked copy is read-only/);
    assert(await instance.locator('input[type="checkbox"]').isDisabled());
    assert(await instance.getByRole('button',{name:'Review update',exact:true}).isDisabled());
    await page.locator('.instance-filters').getByRole('button',{name:'Shelf',exact:true}).click();
    await card.click();
    const copyPicker=page.getByLabel('Read copy');
    await copyPicker.selectOption({label:'Claude Code'});
    assert(await page.getByRole('button',{name:/^Edit/}).isDisabled());
    await copyPicker.selectOption({label:'Shared skills folder'});
    await page.getByRole('button',{name:'Edit',exact:true}).click();
    const targets=page.getByRole('complementary',{name:'Save to'});
    assert.equal(await targets.getByRole('checkbox',{name:/Claude Code/}).count(),0);
    assert.equal(await targets.locator('input:checked').count(),1);
    assert(await targets.getByRole('checkbox',{name:/Shared skills folder/}).isChecked());
    await page.locator('#ed-body').fill('# Updated by the owner UI\n');
    await page.locator('.savebar button').filter({hasText:'Save'}).click();
    await page.waitForTimeout(500);
    assert.match(fs.readFileSync(path.join(target,'SKILL.md'),'utf8'),/Updated by the owner UI/);
    assert.match(fs.readFileSync(path.join(link,'SKILL.md'),'utf8'),/Updated by the owner UI/);
  });
  await test('Trash & backups restores an exact agent folder and preserves both on conflict', async () => {
    const name='browser-agent-trash';
    const created=await page.request.post(base+'/api/skills?scope=agents',{data:{name,description:'Agent trash browser fixture.',body:'# Trash fixture\n'}});
    assert(created.ok(),await created.text());
    const filePath=path.join(home,'.agents','skills',name,'SKILL.md');
    const original=fs.readFileSync(filePath);
    const companion = path.join(path.dirname(filePath), 'notes.txt');
    const originalNotes = Buffer.from('The first revision has its own notes.\r\n');
    fs.writeFileSync(companion, originalNotes);
    await go('skill/'+name);
    await page.getByRole('button',{name:'Move to Trash',exact:true}).click();
    await page.locator('.dlg-f .btn-danger').click();
    await page.getByRole('button',{name:'Undo',exact:true}).last().waitFor().catch(async error => { throw Error(error.message + ' | toast: ' + await page.locator('.toasts').innerText() + ' | route: ' + page.url()); });
    assert(!fs.existsSync(filePath));
    await page.getByRole('button',{name:'Undo',exact:true}).last().click();
    await page.waitForTimeout(500);
    assert(fs.existsSync(filePath));
    assert.deepEqual(fs.readFileSync(filePath),original);
    assert.deepEqual(fs.readFileSync(companion), originalNotes);

    await go('skill/'+name);
    await page.getByRole('button',{name:'Move to Trash',exact:true}).click();
    await page.locator('.dlg-f .btn-danger').click();
    await page.waitForTimeout(500);
    assert(!fs.existsSync(filePath));
    const replacement=await page.request.post(base+'/api/skills?scope=agents',{data:{name,description:'Second archive fixture.',body:'# Newer text\n'}});
    assert(replacement.ok(),await replacement.text());
    await go('skill/'+name);
    await page.getByRole('button',{name:'Move to Trash',exact:true}).click();
    await page.locator('.dlg-f .btn-danger').click();
    await page.waitForTimeout(500);
    assert(!fs.existsSync(filePath));
    await go('trash');
    const older = restoreButton(name, 'Shared skills folder', 'copy 2 of 2');
    await older.waitFor();
    assert.equal(await restoreButton(name, 'Shared skills folder', 'copy 1 of 2').count(), 1);
    await older.focus();
    await page.keyboard.press('Enter');
    const review=page.getByRole('dialog',{name:`Restore ${name}?`});
    assert.match(await review.innerText(), /supporting files[\s\S]*copy 2 of 2/);
    const entries=await (await page.request.get(base+'/api/trash?scope=agents')).json();
    const [newer, olderEntry] = entries.filter(row => row.name === name);
    const savedFolder = olderEntry.trash_path;
    assert.deepEqual(fs.readFileSync(path.join(savedFolder, 'notes.txt')), originalNotes);
    assert(!fs.existsSync(filePath));
    await page.keyboard.press('Escape');
    assert(await older.evaluate(b=>b===document.activeElement));
    await older.click();
    fs.mkdirSync(path.dirname(filePath));
    const occupied = Buffer.from('---\nname: browser-agent-trash\ndescription: Occupied browser fixture.\n---\n# Live copy\n');
    fs.writeFileSync(filePath, occupied);
    try {
      await review.getByRole('button',{name:'Restore folder',exact:true}).click();
      assert.match(await review.getByRole('alert').innerText(), /already exists/);
      assert.deepEqual(fs.readFileSync(filePath), occupied);
      assert.deepEqual(fs.readFileSync(path.join(savedFolder, 'SKILL.md')), original);
      assert.deepEqual(fs.readFileSync(path.join(savedFolder, 'notes.txt')), originalNotes);
      assert(fs.existsSync(newer.trash_path));
    } finally {
      fs.unlinkSync(filePath);
      fs.rmdirSync(path.dirname(filePath));
    }
    const restore=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('/api/trash/'+name+'?scope=agents'));
    await review.getByRole('button',{name:'Restore folder',exact:true}).click();
    const response=await restore;
    assert(response.ok());
    assert.equal(response.request().postDataJSON().trash_path,savedFolder);
    await review.waitFor({state:'hidden'});
    assert.deepEqual(fs.readFileSync(filePath),original);
    assert.deepEqual(fs.readFileSync(companion), originalNotes);
    assert(!fs.existsSync(savedFolder));
    assert(fs.existsSync(newer.trash_path));
    await restoreButton(name, 'Shared skills folder').waitFor();
    const restored = trashList.getByRole('link', {name:'Show restored copy', exact:true});
    await restored.waitFor();
    const route = new URLSearchParams((await restored.getAttribute('href')).split('?')[1]);
    assert.equal(route.get('scope'), 'agents');
    assert.equal(route.get('copy'), path.dirname(filePath));
  });
  await test('Trash & backups labels an unreadable agent scope and retries its listing', async () => {
    const matches = url => url.pathname==='/api/trash' && url.searchParams.get('scope')==='codex';
    const fail = route => route.fulfill({status:503, contentType:'application/json', body:'{"error":"Fixture trash unavailable"}'});
    await page.route(matches, fail);
    try {
      await go('trash');
      assert.match(await trashList.getByRole('alert').innerText(), /Codex.*Fixture trash unavailable/);
    } finally { await page.unroute(matches, fail); }
    await trashList.getByRole('button', {name:'Retry trash', exact:true}).focus();
    await page.keyboard.press('Enter');
    await trashList.getByRole('alert').waitFor({state:'hidden'});
    assert.equal(await page.evaluate(() => document.activeElement.id), 'rec-trash');
  });
  await test('V2 tool read failure stays visible and a retry recovers',async()=>{
    await page.route('**/api/catalog',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Fixture catalog unavailable'})}));
    try{await go('tools/profiles');await page.getByRole('alert').filter({hasText:'Fixture catalog unavailable'}).waitFor();assert(await page.getByRole('button',{name:'Retry profiles',exact:true}).isVisible());}
    finally{await page.unroute('**/api/catalog');}
    await page.getByRole('button',{name:'Retry profiles',exact:true}).click();await page.getByText('v2-browser-profile',{exact:true}).waitFor();
  });
  await test('V2 Quality labels APM evidence for the selected project',async()=>{
    const project=path.join(root,'data','jackfield','apm-fixture');
    fs.mkdirSync(project);
    fs.writeFileSync(path.join(project,'apm.yml'),'name: browser-fixture\nversion: 1.0.0\n');
    await go('tools/quality');
    await page.getByLabel('Project path',{exact:true}).fill(project);
    await page.getByRole('button',{name:'Inspect project',exact:true}).click();
    const evidence=page.locator('.evidence-limits');
    const manifest=evidence.getByText(/apm\.yml is present/);
    await manifest.waitFor({state:'attached'});
    await evidence.locator('summary').click();
    await manifest.waitFor();
    assert.equal(await evidence.getByText(/apm\.lock\.yaml is present/).count(),0);
    const apmAudit=evidence.getByRole('link',{name:'Audit the project with Microsoft APM'});
    assert.equal(await apmAudit.getAttribute('href'),'https://microsoft.github.io/apm/reference/cli/audit/');
    await page.getByRole('button',{name:'Clear project',exact:true}).click();
    await evidence.locator('summary').waitFor();
    assert.equal(await manifest.count(),0);
    assert.equal(await apmAudit.count(),0);
  });
  await test('Quality finding evidence uses a separate disclosure', async () => {
    await go('tools/quality');
    const finding = page.locator('.tp-findings > li > details').first();
    await finding.locator(':scope > summary').click();
    const evidence = finding.getByText('Finding evidence', {exact:true});
    assert(await evidence.evaluate(element =>
      getComputedStyle(element).display !== 'grid' && getComputedStyle(element, '::before').content !== 'none'));
    await evidence.press('Enter');
    await finding.getByRole('region', {name:/^Evidence for /}).waitFor();
  });
  await test('Tool directory filters by task and stays searchable after opening a tool',async()=>{
    await page.setViewportSize({width:390,height:844});
    await go('tools');
    const search=page.getByRole('searchbox',{name:'Find a tool',exact:true});
    await search.fill('  INDEX   maintenance  ');
    const links=page.locator('.tp-index').getByRole('link');
    assert.equal(await links.count(),1);
    assert.match(await links.innerText(),/Settings/);
    await search.press('Tab');
    assert(await links.evaluate(link=>link===document.activeElement));
    await page.keyboard.press('Enter');
    await page.getByRole('heading',{name:'Settings',exact:true}).waitFor();
    const nav=page.getByRole('navigation',{name:'Tools navigation'});
    assert.equal(await nav.getByRole('link').count(),1);
    await nav.getByRole('link',{name:'All tools',exact:true}).click();
    assert.match(await search.inputValue(),/INDEX/);
    await search.fill('<unmatched>');
    assert.equal(await links.count(),0);
    await page.getByRole('status').filter({hasText:'0 matching tools'}).waitFor();
    await search.fill('');
    assert(await links.count()>10);
  });
  await test('Quality jumps focus headings without changing the route', async () => {
    await page.setViewportSize({width:320,height:780});
    await go('tools/quality');
    const url = page.url();
    const jumps = page.getByRole('group', {name:'On this page'});
    for (const [label, id] of [['Findings', 'tp-findings'], ['Diagnostics', 'tp-diagnostics']]) {
      await jumps.getByRole('button', {name:label, exact:true}).press('Enter');
      assert.equal(page.url(), url);
      assert(await page.locator('#' + id).evaluate(heading => {
        const top = heading.getBoundingClientRect().top;
        return heading === document.activeElement && top >= document.querySelector('.top').getBoundingClientRect().bottom && top < innerHeight / 2;
      }), id);
    }
  });
  await test('All v2 tool routes fit desktop and small phone in both themes',async()=>{
    for(const width of [320,768,1280])for(const mode of ['light','dark']){
      await page.setViewportSize({width,height:900});await go('tools/settings');await page.getByLabel('Theme',{exact:true}).selectOption(mode);
      for(const route of ['tools','tools/install','tools/profiles','tools/templates','tools/quality','tools/workspaces','tools/settings','tools/source-update','tools/ai-settings','skills','trash','settings/tracking','settings/tracking/add-agent']){
        await go(route);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${route} ${width} ${mode}`);
        if (route.startsWith('tools/')) {
          const nav = page.getByRole('navigation',{name:'Tools navigation'});
          if(width<=860){
            assert(await nav.getByRole('link',{name:'All tools',exact:true}).isVisible());
            assert.equal(await nav.getByRole('link').count(),1);
          }else{
            const active = nav.locator('[aria-current="page"]');
            assert(await active.evaluate(link => {
              const tab = link.getBoundingClientRect(), nav = link.closest('nav').getBoundingClientRect();
              return tab.top >= nav.top - 1 && tab.bottom <= nav.bottom + 1 && nav.bottom <= innerHeight;
            }), `active tool is clipped on ${route} at ${width}px`);
          }
        }
      }
    }
    await page.setViewportSize({width:1280,height:900});await go('tools');await page.screenshot({path:path.join(root,'final-tools-desktop.png')});
  });
  await test('Stop tracking an agent leaves its files alone and Undo brings its column back', async () => {
    const f=file('.codex','same-everywhere'), bytes=fs.readFileSync(f);
    const heads=async()=>(await page.locator('.map-table thead th').allInnerTexts()).map(t=>t.replace(/\s+/g,' ').trim());
    await go('map');
    assert((await heads()).some(t=>t.startsWith('Codex')));
    await page.getByRole('button',{name:'Codex options',exact:true}).click();
    await page.getByRole('menuitem',{name:'Stop tracking Codex…'}).click();
    const form=page.locator('.trk-confirm');
    assert.match(await form.innerText(),/The Codex column and its counts leave the table[\s\S]*Nothing on disk changes/);
    assert.equal(await page.evaluate(()=>document.activeElement.id),'map-confirm-h');
    await form.getByRole('button',{name:'Stop tracking Codex',exact:true}).click();
    const toast=page.locator('.toast',{hasText:'Stopped tracking Codex. Nothing on disk changed.'});
    await toast.waitFor();
    assert(!(await heads()).some(t=>t.startsWith('Codex')));
    assert(!(await (await context.request.get(base+'/api/scopes')).json()).some(s=>s.id==='codex'));
    assert.deepEqual(fs.readFileSync(f),bytes);
    await toast.getByRole('button',{name:'Undo'}).click();
    await page.locator('.toast',{hasText:'Tracking Codex again.'}).waitFor();
    assert((await heads()).some(t=>t.startsWith('Codex')));
    assert((await (await context.request.get(base+'/api/scopes')).json()).some(s=>s.id==='codex'));
  });
  await test('Add other agent checks the folder live, adds a column, and Remove keeps its folder', async () => {
    const kilo=path.join(home,'.kilo','skills','kilo-only','SKILL.md'), bytes=fs.readFileSync(kilo);
    await go('settings/tracking');
    await page.getByRole('link',{name:'Add other agent'}).click();
    const folder=page.locator('#trk-folder'); await folder.waitFor();
    await folder.fill('/etc');
    await page.locator('#trk-folder-hint',{hasText:'Pick a folder inside your home folder.'}).waitFor();
    await folder.fill('~/.kilo/skills');
    await page.locator('#trk-folder-hint',{hasText:'1 skill found in ~/.kilo/skills'}).waitFor();
    assert.equal(await page.locator('#trk-name').inputValue(),'Kilo');
    await page.getByRole('button',{name:'Add Kilo',exact:true}).click();
    await page.locator('.toast',{hasText:'Added Kilo.'}).waitFor();
    assert.equal(new URL(page.url()).hash,'#/settings/tracking');
    assert.match(await page.locator('#trk-st-custom-kilo').innerText(),/Tracked · 1 skill/);
    await go('map');
    assert((await page.locator('.map-table thead th').allInnerTexts()).some(t=>t.includes('Kilo')));
    await go('settings/tracking');
    await page.locator('.trk-row',{hasText:'Kilo'}).getByRole('button',{name:'Details'}).click();
    await page.locator('.trk-row',{hasText:'Kilo'}).getByRole('button',{name:'Remove'}).click();
    assert.match(await page.locator('.dlg').innerText(),/Remove Kilo\?[\s\S]*Nothing on disk changes/);
    await page.locator('.dlg-f').getByRole('button',{name:'Remove Kilo',exact:true}).click();
    await page.locator('.toast',{hasText:'Removed Kilo. Its folder is unchanged.'}).waitFor();
    assert.equal(await page.locator('#trk-st-custom-kilo').count(),0);
    assert.deepEqual(fs.readFileSync(kilo),bytes);
  });
  await test('Review fixes: observed settings and attention count stay accurate across routes', async () => {
    await go('skills');
    const welcome = page.getByRole('button', {name:'Show my skills'});
    if (await welcome.isVisible()) await welcome.click();
    for (const agent of ['Claude Code', 'OpenCode']) {
      await page.getByRole('button', {name:`same-everywhere in ${agent}: Off in settings`, exact:true}).waitFor();
    }
    const attention = page.locator('.tabs a[href="#/attention"]');
    const label = await attention.getAttribute('aria-label');
    assert.match(label, /Needs attention, \d+ items/);
    await attention.click();
    await page.waitForURL(url => url.hash === '#/attention');
    assert.equal(await attention.getAttribute('aria-label'), label);
    await expectAttentionCount(Number(label.match(/\d+/)[0]));
  });
  await test('Review fixes: tablet sheet, split comparison and tracking confirmation', async () => {
    await page.setViewportSize({width:768, height:900});
    try {
      await go('skills');
      const welcome = page.getByRole('button', {name:'Show my skills'});
      if (await welcome.isVisible()) await welcome.click();
      const square = page.getByRole('button', {name:/^split-even in Codex: Version [12]$/});
      await square.click();
      const panel = page.getByRole('dialog', {name:'split-even'});
      const confirm = panel.getByRole('button', {name:'Make all 4 match'});
      assert(await confirm.isDisabled());
      const keepVersion = panel.getByRole('button', {name:'Keep version 1'});
      await keepVersion.focus();
      assert.equal(await page.locator('.jf-square.is-camp').count(), 2);
      assert.equal(await panel.evaluate(el => getComputedStyle(el).position), 'fixed');
      await panel.getByRole('button', {name:'Compare the two versions'}).click();
      await panel.getByRole('region', {name:'Version 1 instructions'}).waitFor();
      await panel.getByRole('region', {name:'Version 2 instructions'}).waitFor();
      assert(await confirm.isDisabled());
      await page.keyboard.press('Escape');
      await panel.waitFor({state:'hidden'});
      assert(await square.evaluate(el => el === document.activeElement));
      await page.getByRole('button', {name:'Codex options', exact:true}).click();
      await page.getByRole('button', {name:'Stop tracking Codex…'}).click();
      const stop = page.getByRole('dialog', {name:'Stop tracking Codex?'});
      await stop.getByText(/Nothing on disk changes/).waitFor();
      await stop.getByRole('button', {name:'Keep tracking', exact:true}).click();
      await stop.waitFor({state:'hidden'});
      assert(await page.getByRole('button', {name:'Codex options', exact:true}).evaluate(el => el === document.activeElement));
    } finally { await page.setViewportSize({width:1280,height:900}); }
  });
  await test('Review fixes: tracking Undo keeps another window’s changes after refresh', async () => {
    const endpoint = base + '/api/tracking';
    const read = async () => (await page.request.get(endpoint)).json();
    const write = async (settings) => {
      const response = await page.request.put(endpoint, {headers:{Origin:base}, data:settings});
      assert.equal(response.status(), 200, await response.text());
      return response.json();
    };
    const previous = (await read()).settings;
    try {
      await go('skills');
      const welcome = page.getByRole('button', {name:'Show my skills'});
      if (await welcome.isVisible()) await welcome.click();
      await page.getByRole('button', {name:'Codex options', exact:true}).click();
      await page.getByRole('button', {name:'Stop tracking Codex…'}).click();
      await page.getByRole('button', {name:'Stop tracking Codex', exact:true}).click();
      const undo = page.locator('.toast', {hasText:'Stopped tracking Codex.'}).getByRole('button', {name:'Undo', exact:true});
      await undo.waitFor();
      const later = (await read()).settings;
      later.agents.tracked = later.agents.tracked.filter(id => id !== 'opencode');
      const advanced = await write(later);
      await page.getByRole('button', {name:'Refresh files', exact:true}).click();
      await page.getByRole('button', {name:'OpenCode options', exact:true}).waitFor({state:'hidden'});
      await page.waitForLoadState('networkidle');
      await undo.click();
      await page.locator('.toast', {hasText:/Couldn.t undo:.*changed in another window/i}).waitFor();
      const after = await read();
      assert.equal(after.revision, advanced.revision);
      assert.deepEqual(after.settings, advanced.settings);
    } finally {
      await write({...previous, revision:(await read()).revision});
    }
  });
  for (const method of ['keyboard', 'mouse']) {
    await test(`Phase 2 F2 Codex-only toggle and Undo by ${method}`, async () => {
      const name = 'code-review', scopes = ['.claude', '.codex'];
      const bytes = Buffer.from('---\nname: code-review\ndescription: Browser benchmark fixture.\n---\n# Code review\n');
      for (const scope of scopes) {
        const target = file(scope, name);
        assert(!fs.existsSync(target) && !fs.existsSync(target + '.disabled'));
        fs.mkdirSync(path.dirname(target), {recursive:true}); fs.writeFileSync(target, bytes);
      }
      const codex = file('.codex', name), claude = file('.claude', name);
      try {
        for (const [width, themeName] of [[1440,'light'], [1440,'dark'], [390,'light'], [390,'dark']]) {
          await page.setViewportSize({width, height:900});
          await go('skills'); await theme(themeName);
          const showSkills = page.getByRole('button', {name:'Show my skills'});
          if (await showSkills.isVisible()) await showSkills.click();
          const filter = page.getByRole('searchbox', {name:'Filter skills'});
          const filterToggle = page.getByRole('button', {name:'Filter and sort'});
          if (!(await filter.isVisible()) && await filterToggle.isVisible()) await filterToggle.click();
          await filter.fill(name);
          const agentPicker = page.getByRole('combobox', {name:'Showing agent'});
          if (await agentPicker.isVisible()) await agentPicker.selectOption({label:'Codex'});
          const square = page.getByRole('button', {name:/code-review in Codex: On/i});
          await square.waitFor();
          if (method === 'keyboard') {
            await filter.focus();
            for (let i=0; i<20 && !(await page.evaluate(() => document.activeElement?.textContent?.trim() === 'code-review')); i++) await page.keyboard.press('Tab');
            assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), name);
            for (let i=0; i<10 && !(await square.evaluate(el => el === document.activeElement)); i++) await page.keyboard.press('ArrowRight');
            assert(await square.evaluate(el => el === document.activeElement));
            await page.keyboard.press('Enter');
            const primary = page.getByRole('button', {name:/Turn off in Codex/}); await primary.waitFor();
            await primary.focus(); await page.keyboard.press('Enter');
          } else {
            await square.click();
            const primary = page.getByRole('button', {name:/Turn off in Codex/});
            if (width === 1440 && themeName === 'light') {
              await primary.evaluate(button => button.addEventListener('click', () => {
                const start = performance.now();
                const observer = new MutationObserver(() => {
                  if (!document.querySelector('button[aria-label="code-review in Codex: Off"]')) return;
                  observer.disconnect();
                  window.fixtureToggleMs = performance.now() - start;
                });
                observer.observe(document.querySelector('main'), {subtree:true, childList:true, attributes:true});
              }, {once:true, capture:true}));
            }
            await primary.click();
          }
          await page.getByRole('button', {name:/code-review in Codex: Off/i}).waitFor();
          if (method === 'mouse' && width === 1440 && themeName === 'light') {
            const elapsed = await page.evaluate(() => window.fixtureToggleMs);
            assert(elapsed <= 300, `confirmed file toggle took ${elapsed} ms (limit 300 ms)`);
          }
          assert(!fs.existsSync(codex)); assert.deepEqual(fs.readFileSync(codex+'.disabled'), bytes);
          assert.deepEqual(fs.readFileSync(claude), bytes); assert(!fs.existsSync(claude+'.disabled'));
          const undo = page.getByRole('button', {name:'Undo', exact:true}).last(); await undo.waitFor();
          if (method === 'keyboard') { await undo.focus(); await page.keyboard.press('Enter'); } else await undo.click();
          await page.getByRole('button', {name:/code-review in Codex: On/i}).waitFor();
          assert.deepEqual(fs.readFileSync(codex), bytes); assert(!fs.existsSync(codex+'.disabled'));
          assert.deepEqual(fs.readFileSync(claude), bytes);
        }
      } finally {
        for (const scope of scopes) fs.rmSync(path.dirname(file(scope, name)), {recursive:true, force:true});
        await page.setViewportSize({width:1280,height:900});
      }
    });
  }
  await test('Phase 2 Shift+Space selects a row without writing', async () => {
    await go('skills');
    const showSkills = page.getByRole('button', {name:'Show my skills'});
    if (await showSkills.isVisible()) await showSkills.click();
    const source = file('.claude', 'sole-copy'), bytes = fs.readFileSync(source);
    let writes = 0;
    const observe = req => { if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(req.method())) writes++; };
    page.on('request', observe);
    try {
      const filter = page.getByRole('searchbox', {name:'Filter skills'}); await filter.fill('sole-copy');
      await filter.focus();
      for (let i=0; i<20 && !(await page.evaluate(() => document.activeElement?.textContent?.trim() === 'sole-copy')); i++) await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), 'sole-copy');
      await page.keyboard.press('Shift+Space');
      assert(await page.getByRole('checkbox', {name:'Select sole-copy'}).isChecked());
      assert.equal(writes, 0); assert.deepEqual(fs.readFileSync(source), bytes);
      await page.keyboard.press('Shift+Space');
      assert(!(await page.getByRole('checkbox', {name:'Select sole-copy'}).isChecked()));
      assert.equal(writes, 0);
    } finally { page.off('request', observe); }
  });
  await test('Phase 2 add a missing copy and Undo restores the filesystem', async () => {
    const name = 'phase-two-add', source = file('.claude', name), target = file('.codex', name);
    const bytes = Buffer.from('---\nname: phase-two-add\ndescription: Browser copy fixture.\n---\n# Copy fixture\n');
    assert(!fs.existsSync(source) && !fs.existsSync(target));
    fs.mkdirSync(path.dirname(source), {recursive:true}); fs.writeFileSync(source, bytes);
    try {
      await go('skills');
      const showSkills = page.getByRole('button', {name:'Show my skills'});
      if (await showSkills.isVisible()) await showSkills.click();
      await page.getByRole('searchbox', {name:'Filter skills'}).fill(name);
      await page.getByRole('button', {name:/phase-two-add in Codex: Not here/i}).click();
      await page.getByRole('button', {name:/Add to Codex/}).click();
      await page.getByRole('button', {name:/phase-two-add in Codex: On/i}).waitFor();
      assert.deepEqual(fs.readFileSync(target), bytes); assert.deepEqual(fs.readFileSync(source), bytes);
      await page.getByRole('button', {name:'Undo', exact:true}).last().click();
      await page.getByRole('button', {name:/phase-two-add in Codex: Not here/i}).waitFor();
      assert(!fs.existsSync(target)); assert.deepEqual(fs.readFileSync(source), bytes);
    } finally {
      fs.rmSync(path.dirname(source), {recursive:true, force:true});
      fs.rmSync(path.dirname(target), {recursive:true, force:true});
    }
  });
  await test('Phase 2 stale Undo preserves an edited companion file', async () => {
    const name = 'phase-two-stale', source = file('.claude', name), target = file('.codex', name);
    const bytes = Buffer.from('---\nname: phase-two-stale\ndescription: Browser stale fixture.\n---\n# Stale fixture\n');
    const companion = 'notes.txt', original = Buffer.from('Original notes\n'), edited = Buffer.from('Edited after copy\n');
    assert(!fs.existsSync(source) && !fs.existsSync(target));
    fs.mkdirSync(path.dirname(source), {recursive:true}); fs.writeFileSync(source, bytes);
    fs.writeFileSync(path.join(path.dirname(source), companion), original);
    try {
      await go('skills');
      const showSkills = page.getByRole('button', {name:'Show my skills'});
      if (await showSkills.isVisible()) await showSkills.click();
      await page.getByRole('searchbox', {name:'Filter skills'}).fill(name);
      await page.getByRole('button', {name:/phase-two-stale in Codex: Not here/i}).click();
      await page.getByRole('button', {name:/Add to Codex/}).click();
      await page.getByRole('button', {name:/phase-two-stale in Codex: On/i}).waitFor();
      const targetCompanion = path.join(path.dirname(target), companion);
      assert.deepEqual(fs.readFileSync(targetCompanion), original);
      fs.writeFileSync(targetCompanion, edited);
      await page.getByRole('button', {name:'Undo', exact:true}).last().click();
      await page.locator('.toast').filter({hasText:/Couldn't undo/i}).last().waitFor();
      assert.deepEqual(fs.readFileSync(target), bytes);
      assert.deepEqual(fs.readFileSync(targetCompanion), edited);
      assert.deepEqual(fs.readFileSync(source), bytes);
      assert.deepEqual(fs.readFileSync(path.join(path.dirname(source), companion)), original);
    } finally {
      fs.rmSync(path.dirname(source), {recursive:true, force:true});
      fs.rmSync(path.dirname(target), {recursive:true, force:true});
    }
  });
  await test('Phase 2 replace a different copy and Undo restores its bytes and disabled state', async () => {
    const target = file('.codex', 'majority-minor'), source = file('.claude', 'majority-minor');
    const disabledTarget = target + '.disabled';
    const fixture = fs.readFileSync(target), replacement = fs.readFileSync(source);
    const lateInstruction = 'Review this instruction after line forty.';
    const before = Buffer.concat([fixture, Buffer.from('\n' + 'Context line\n'.repeat(40) + lateInstruction + '\n')]);
    fs.renameSync(target, disabledTarget);
    fs.writeFileSync(disabledTarget, before);
    const previewRequest = url => url.pathname === '/api/batch/preview';
    const refuseOnce = route => route.fulfill({status:409, json:{error:'Fixture refused the first preview'}});
    try {
      await go('skills');
      const showSkills = page.getByRole('button', {name:'Show my skills'});
      if (await showSkills.isVisible()) await showSkills.click();
      await page.getByRole('searchbox', {name:'Filter skills'}).fill('majority-minor');
      await page.getByRole('button', {name:/majority-minor in Codex: Different/i}).click();
      await page.getByRole('button', {name:/Compare the two versions/}).click();
      const confirm = page.getByRole('button', {name:'Make copies match', exact:true});
      assert(await confirm.isDisabled());
      await page.locator('.jf-panel-details summary', {hasText:'Codex'}).click();
      await page.getByRole('region', {name:'Codex instructions'}).getByText(lateInstruction, {exact:false}).waitFor();
      await page.getByRole('button', {name:/Keep Claude Code’s version/}).click();
      await page.locator('.jf-panel-preview').getByText(/skill file will be switched on in Codex/).waitFor();
      await page.route(previewRequest, refuseOnce, {times:1});
      await confirm.click();
      await page.getByRole('alert').filter({hasText:'Couldn’t complete the change'}).waitFor();
      assert(!fs.existsSync(target));
      assert.deepEqual(fs.readFileSync(disabledTarget), before);
      await page.getByRole('button', {name:'Try again', exact:true}).click();
      assert(await confirm.isDisabled());
      await page.getByRole('button', {name:/Keep Claude Code’s version/}).click();
      await confirm.click();
      await page.getByRole('button', {name:/majority-minor in Codex: On/i}).waitFor();
      assert.deepEqual(fs.readFileSync(target), replacement);
      assert(!fs.existsSync(disabledTarget));
      await page.getByRole('button', {name:'Undo', exact:true}).last().click();
      await page.getByRole('button', {name:/majority-minor in Codex: Different/i}).waitFor();
      assert(!fs.existsSync(target));
      assert.deepEqual(fs.readFileSync(disabledTarget), before);
      assert.deepEqual(fs.readFileSync(source), replacement);
    } finally {
      await page.unroute(previewRequest, refuseOnce);
      fs.rmSync(disabledTarget, {force:true});
      fs.mkdirSync(path.dirname(target), {recursive:true});
      fs.writeFileSync(target, fixture);
    }
  });
  await test('Phase 2 Skills and command suggestions return focus to their search fields', async () => {
    await go('skills');
    const show = page.getByRole('button', {name:'Show my skills'});
    if (await show.isVisible()) await show.click();
    const filter = page.getByRole('searchbox', {name:'Filter skills'});
    await filter.fill('sole-copx');
    const tableIdea = page.getByRole('button', {name:'sole-copy', exact:true});
    await tableIdea.focus();
    await page.keyboard.press('Enter');
    assert.equal(await filter.inputValue(), 'sole-copy');
    assert(await filter.evaluate(el => el === document.activeElement));
    await page.keyboard.press('Control+k');
    const palette = page.getByRole('combobox', {name:'Search skills, actions and pages'});
    await palette.fill('sole-copx');
    await page.getByRole('dialog').getByRole('button', {name:'sole-copy', exact:true}).focus();
    await page.keyboard.press('Enter');
    assert.equal(await palette.inputValue(), 'sole-copy');
    assert(await palette.evaluate(el => el === document.activeElement));
    await page.keyboard.press('ArrowDown');
    assert(await palette.getAttribute('aria-activedescendant'));
    await page.keyboard.press('Escape');
  });
  await test('Phase 2 1000 skills paginate and filter in the browser', async () => {
    const list = /[/]api[/]skills[?]scope=all(?:&body=0)?$/;
    const records = await (await page.request.get(base+'/api/skills?scope=all')).json();
    const copy = records.find(record => record.scope === 'codex' && record.name === 'same-everywhere');
    assert(copy);
    const many = Array.from({length:1000}, (_, i) => ({...copy, name:'fixture-'+String(i).padStart(4,'0'), path:undefined, physical_path:undefined, body:undefined}));
    try {
      await page.route(list, route => route.fulfill({json:many}));
      await page.goto(base + '/?fixture-step=table-budget#/skills?q=fixture', {waitUntil:'commit'});
      const grid = page.getByRole('grid', {name:'Skills table'});
      const tableMs = await (await page.waitForFunction(() =>
        document.querySelector('.jf-grid tbody tr') && performance.now())).jsonValue();
      assert(tableMs <= 1500, `Skills table became interactive in ${tableMs} ms (limit 1500 ms)`);
      assert.equal(await grid.locator('tbody tr').count(), 50);
      await page.getByRole('button', {name:'Show 50 more'}).click();
      assert.equal(await grid.locator('tbody tr').count(), 100);
      const enterTimedQuery = async (input) => {
        const start = performance.now();
        input.value = 'fixture-0999';
        input.dispatchEvent(new Event('input', {bubbles:true}));
        await window.Vue.nextTick();
        return performance.now() - start;
      };
      const filterMs = await page.getByRole('searchbox', {name:'Filter skills'}).evaluate(enterTimedQuery);
      assert(filterMs <= 100, `table filter took ${filterMs} ms (limit 100 ms)`);
      assert.equal(await grid.locator('tbody tr').count(), 1);
      assert.match(await grid.locator('tbody tr').innerText(), /fixture-0999/);
      await page.keyboard.press('Control+k');
      const paletteMs = await page.getByRole('combobox', {name:'Search skills, actions and pages'}).evaluate(enterTimedQuery);
      assert(paletteMs <= 100, `palette results took ${paletteMs} ms (limit 100 ms)`);
      await page.getByRole('option', {name:/fixture-0999/}).waitFor();
      await page.keyboard.press('Escape');
    } finally { await page.unrouteAll({behavior:'wait'}); }
  });
  await test('Phase 2 status case table runs in the browser Model', async () => {
    const cases = JSON.parse(fs.readFileSync(path.join(__dirname, '../../tests/fixtures/square-status-cases.json'), 'utf8'));
    await go('skills');
    const failures = await page.evaluate(cases => {
      const M = window.SkillsV2Model;
      const scopes = ['a', 'b', 'c'].map(id => ({id, label:id, kind:'agent', exists:true}));
      return cases.flatMap(c => {
        const model = M.build(c.records, scopes), row = model.skills[0], busy = new Set(c.busy || []);
        return Object.entries(c.expected).flatMap(([id, expected]) => {
          const actual = M.squareStatus(row, model.agent(id), busy);
          return actual === expected ? [] : [`${c.name} ${id}: ${actual} != ${expected}`];
        });
      });
    }, cases);
    assert.deepEqual(failures, []);
  });
  await test('Trash & backups empties only library trash after confirmation', async () => {
    const name = 'phase-four-empty-trash';
    const trashed = [];
    for (const scope of ['global', 'codex']) {
      const created = await page.request.post(base + '/api/skills?scope=' + scope, {
        data:{name, description:'Private purge fixture.', body:`# ${scope} only\n`},
      });
      assert.equal(created.status(), 201);
      const removed = await page.request.delete(`${base}/api/skills/${name}?scope=${scope}`);
      assert(removed.ok());
      trashed.push((await removed.json()).trash_path);
    }
    const [library, agent] = trashed;
    const original = fs.readFileSync(path.join(agent, 'SKILL.md'));
    const purgeRequest = request => request.method() === 'POST' && request.url() === base + '/api/trash/purge';
    let purges = 0;
    const observe = request => { if (purgeRequest(request)) purges++; };
    page.on('request', observe);
    try {
      await go('trash');
      const libraryRestore = restoreButton(name, 'Your library');
      const agentRestore = restoreButton(name, 'Codex');
      await libraryRestore.waitFor();
      await agentRestore.waitFor();
      const empty = trashList.getByRole('button', {name:'Empty library trash…', exact:true});
      await empty.click();
      const confirm = page.getByRole('dialog', {name:/Empty.*library trash/i});
      assert.match(await confirm.innerText(), /permanent|cannot be undone/i);
      await confirm.getByRole('button', {name:'Cancel', exact:true}).click();
      await confirm.waitFor({state:'hidden'});
      assert.equal(purges, 0);
      assert(fs.existsSync(library));
      assert(fs.existsSync(agent));
      await empty.click();
      const purge = page.waitForResponse(response => purgeRequest(response.request()));
      await confirm.getByRole('button', {name:'Delete permanently', exact:true}).click();
      assert((await purge).ok());
      await libraryRestore.waitFor({state:'hidden'});
      await agentRestore.waitFor();
      assert.equal(purges, 1);
      assert(!fs.existsSync(library));
      assert.deepEqual(fs.readFileSync(path.join(agent, 'SKILL.md')), original);
      assert.equal(await page.locator('.toast').getByRole('button', {name:'Undo', exact:true}).count(), 0);
    } finally { page.off('request', observe); }
  });
  await test('No uncaught page errors',async()=>assert.deepEqual(exceptions,[]));
  record('Coverage limit','NOTE','Actual browser zoom is checked only in headed Chrome. Screen-reader and perceptual review require a person.');
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({engine,browserVersion,results,failures:failed},null,2)+'\n');await browser.close();process.exitCode=failed?1:0;
})().catch(e=>{console.error(e);process.exitCode=2}).finally(async()=>{if(browser)await browser.close();});
