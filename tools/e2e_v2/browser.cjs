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
  async function go(route) { await page.goto(base+'/?fixture-step='+(++navigation)+'#/'+route); await page.locator('main').waitFor(); await page.waitForLoadState('networkidle'); if (route.startsWith('skill/')) await page.locator('.use').first().waitFor(); await page.waitForTimeout(200); }
  async function theme(t) { for (let i=0;i<3 && await page.locator('html').getAttribute('data-theme')!==t;i++) await page.locator('.themebtn').first().click(); assert.equal(await page.locator('html').getAttribute('data-theme'),t); }
  const file=(scope,name='same-everywhere')=>path.join(home,scope,'skills',name,'SKILL.md');
  await test('Default entry preserves query and hash and opens v2',async()=>{await page.goto(base+'/?window=claude#/skills');await page.waitForLoadState('networkidle');assert.equal(page.url(),base+'/v2/?window=claude#/skills');assert(await page.locator('.sk').count()>0);});
  await test('Home listing budgets use real evidence and recover from a failed read', async () => {
    await go('home');
    let card = page.getByRole('region', {name:'Skill listing budgets', exact:true});
    assert.equal(await card.locator('.listing-budget').count(), 2);
    assert.match(await card.innerText(), /Claude Code[\s\S]*chars[\s\S]*Codex[\s\S]*tokens/);
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
      assert(page.url().endsWith('#/tools/quality'));
    } finally { await page.unroute(matches, handler); }
  });
  await test('Slashless v2 entry keeps query and hash and loads its own app', async () => {
    await page.goto(base + '/v2?window=claude#/skills');
    await page.locator('.shelf').first().waitFor();
    assert.equal(page.url(), base + '/v2/?window=claude#/skills');
    assert.equal(await page.locator('#h1').innerText(), 'Skills');
    assert(await page.locator('.shelf').first().isVisible());
  });
  await test('Unreadable Inbox guidance preserves original bytes',async()=>{ await go('inbox');const f=file('.codex','damaged-one'), bytes=fs.readFileSync(f);if (!(await page.locator('#focus-t').innerText()).includes('damaged-one')) await page.locator('.qi').filter({hasText:'damaged-one'}).click();assert.equal(await page.locator('[data-primary]').innerText(),'Show me how');await page.locator('[data-primary]').click();assert.match(await page.locator('.dlg').innerText(),/original file/);assert.deepEqual(fs.readFileSync(f),bytes);await page.keyboard.press('Escape'); });
  await test('Home Inbox count equals queue; acknowledging a note is not a fix',async()=>{await go('home');let t=await page.locator('.side .card').first().innerText();let n=Number(t.match(/(\d+) things?/)[1]);await page.locator('.look a').first().click();let prog=await page.locator('.prog').innerText();assert.equal(Number(prog.match(/(\d+) to go/)[1]),n);await page.locator('.qi').filter({hasText:'.system'}).click();await page.locator('[data-primary]').click();assert.match(await page.locator('.prog').innerText(),/^0 fixed/);await page.locator('.tabs a').filter({hasText:'Home'}).click();assert.match(await page.locator('.side .card').first().innerText(),new RegExp(`\\b${n-1} things?`));});
  await test('Disabled Enter does not sync a tied copy',async()=>{await go('inbox');await page.locator('.qi').filter({hasText:'split-even'}).click();let f=file('.codex','split-even'), bytes=fs.readFileSync(f),posts=0;const observe=req=>{if(req.method()==='POST'&&req.url().endsWith('/api/sync'))posts++;};page.on('request',observe);assert(await page.locator('[data-primary]').isDisabled());await page.locator('#h1').focus();await page.keyboard.press('Enter');await page.waitForTimeout(300);assert.deepEqual(fs.readFileSync(f),bytes);page.off('request',observe);assert.equal(posts,0);});
  await test('Keyboard: Enter on Open skill navigates and never runs the fix (SR-1)',async()=>{await go('inbox');if(!(await page.locator('#focus-t').innerText()).includes('damaged-fm'))await page.locator('.qi').filter({hasText:'damaged-fm'}).click();const f=file('.codex','damaged-fm'),bytes=fs.readFileSync(f);let posts=0;const observe=req=>{if(req.method()==='POST'&&req.url().endsWith('/api/sync'))posts++;};page.on('request',observe);try{await page.locator('.f-acts a.link').filter({hasText:'Open skill'}).focus();await page.keyboard.press('Enter');await page.waitForTimeout(500);assert(page.url().includes('#/skill/damaged-fm'),page.url());assert.equal(posts,0);assert.deepEqual(fs.readFileSync(f),bytes);}finally{page.off('request',observe);}});
  await test('Skip link keeps the current page and focuses its heading (SR-2)',async()=>{await go('skill/same-everywhere');await page.locator('a.skip').focus();await page.keyboard.press('Enter');await page.waitForTimeout(200);assert(page.url().endsWith('#/skill/same-everywhere'),page.url());assert.equal(await page.evaluate(()=>document.activeElement&&document.activeElement.id),'h1');});
  await test('Navigation names the Inbox count and stays outside the dialog tab order', async () => {
    await go('home');
    const badge = page.locator('.tabs a[href="#/inbox"] .badge');
    const count = Number(await badge.innerText());
    assert(count > 1, 'fixture includes multiple Inbox entries');
    const inbox = page.getByRole('link', {name: `Inbox, ${count} items`, exact: true});
    const skipLink = page.getByRole('link', {name: 'Skip to content', exact: true});
    try {
      for (const width of [1280, 390]) {
        await page.setViewportSize({width, height: 900});
        await inbox.waitFor();
        assert.equal(await inbox.count(), 1);
      }
    } finally {
      await page.setViewportSize({width: 1280, height: 900});
    }
    const shortcuts = page.getByRole('button', {name: 'Keyboard shortcuts', exact: true});
    await shortcuts.click();
    await page.getByRole('dialog', {name: 'Keyboard shortcuts'}).waitFor();
    assert(await page.locator('a.skip').evaluate(element => {
      const focused = document.activeElement;
      element.focus();
      return element.inert && document.activeElement === focused;
    }));
    await page.keyboard.press('Escape');
    assert.equal(await skipLink.count(), 1);
    assert(await shortcuts.evaluate(element => document.activeElement === element));
  });
  await test('Accessible names: brand at phone width, differing copy on its switch, distinct Fix and Peek names (SR-4/6/7/11)',async()=>{await page.setViewportSize({width:390,height:844});try{await go('home');assert.equal(await page.locator('a.brand').getAttribute('aria-label'),'Skills Manager home');const fixes=await page.locator('.look a').evaluateAll(a=>a.map(x=>x.getAttribute('aria-label')));assert.equal(new Set(fixes).size,fixes.length);}finally{await page.setViewportSize({width:1280,height:900});}await go('skill/majority-minor');const names=await page.locator('.use .switch .sr-only').allInnerTexts();assert(names.some(n=>/Codex.*differs from most places/.test(n)),names.join(' | '));await go('map');await page.getByRole('button',{name:'Codex',exact:true}).click();const peeks=await page.locator('.peek').evaluateAll(a=>a.map(x=>x.getAttribute('aria-label')));assert(peeks.length>0&&new Set(peeks).size===peeks.length,peeks.join(' | '));});
  await test('An Undo toast stays while focused (SR-3)',async()=>{await go('skill/same-everywhere');await page.locator('.use').filter({hasText:'Codex'}).locator('label.switch').click();const undo=page.locator('.toast button').filter({hasText:'Undo'}).last();await undo.waitFor();await undo.focus();const held=await page.evaluate(()=>!!document.activeElement.closest('.toast'));assert(held);await undo.click();await page.waitForTimeout(700);assert(fs.existsSync(file('.codex')));});
  await test('Repeated Reader Sync clicks issue one request', async () => {
    await go('skill/majority-minor');
    const button = page.locator('.inline-note.warn button');
    const target = file('.codex', 'majority-minor'), before = fs.readFileSync(target);
    let syncs = 0;
    const observe = request => {
      if (request.method() === 'POST' && request.url() === base + '/api/sync') ++syncs;
    };
    page.on('request', observe);
    try {
      await button.evaluate(el => { el.click(); el.click(); });
      const undo = page.locator('.toast button').filter({hasText:'Undo'}).last();
      await undo.waitFor();
      await undo.click();
      await page.locator('.toast').filter({hasText:'Undone'}).waitFor();
      assert.equal(syncs, 1);
      assert.deepEqual(fs.readFileSync(target), before);
    } finally {
      page.off('request', observe);
    }
  });
  await test('Inbox Sync preview follows the selected source and shows affected locations', async () => {
    await go('inbox');
    await page.locator('.qi').filter({hasText:'majority-minor'}).click();
    const targets = page.getByRole('list', {name:'Copies that will be overwritten'});
    assert.match(await targets.innerText(), /Codex/);
    assert((await targets.innerText()).includes(path.dirname(file('.codex', 'majority-minor'))));
    await page.getByRole('radio', {name:'Codex'}).check();
    await page.locator('.vs header').last().filter({hasText:"Codex's copy"}).waitFor();
    assert.match(await page.locator('[data-primary]').innerText(), /^Sync 3 copies from Codex$/);
    assert.equal(await targets.locator('li').count(), 3);
    assert.doesNotMatch(await targets.innerText(), /Codex/);
  });
  await test('Inbox Sync stays clear of navigation after scrolling', async () => {
    try {
      for (const [width, block] of [[1280, 'start'], [390, 'end']]) {
        await page.setViewportSize({width, height:577});
        await go('inbox');
        await page.locator('.qi').filter({hasText:'majority-minor'}).click();
        const visible = await page.locator('[data-primary]').evaluate((button, block) => {
          button.focus({preventScroll:true});
          button.scrollIntoView({block, behavior:'instant'});
          const rect = button.getBoundingClientRect();
          const header = document.querySelector('.top').getBoundingClientRect();
          const footer = document.querySelector('.bottomnav').getBoundingClientRect();
          const hit = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
          return document.activeElement === button && button.contains(hit) &&
            rect.top >= header.bottom && rect.bottom <= (footer.height ? footer.top : innerHeight);
        }, block);
        assert(visible, `Inbox Sync is obscured at ${width}px`);
      }
    } finally {
      await page.setViewportSize({width:1280, height:900});
    }
  });
  await test('Delayed double click issues one sync and Undo restores bytes and queue',async()=>{
    await go('inbox');
    await page.locator('.qi').filter({hasText:'majority-minor'}).click();
    const target=file('.codex','majority-minor'), before=fs.readFileSync(target);
    const companion = path.join(path.dirname(target), 'target-only.txt');
    fs.writeFileSync(companion, 'previous copy only');
    let count=0, retained;
    await page.route('**/api/sync',async route=>{
      count++;
      await new Promise(resolve=>setTimeout(resolve,400));
      await route.continue();
    });
    try{
      const [response]=await Promise.all([
        page.waitForResponse(r=>r.url()===base+'/api/sync', {timeout:15000}),
        page.locator('[data-primary]').dblclick({delay:25}),
      ]);
      assert.equal(response.status(),200);
      const {replaced_to_trash: moved} = await response.json();
      assert.equal(fs.readFileSync(path.join(moved.codex, 'target-only.txt'), 'utf8'), 'previous copy only');
      const scopeTrash = path.join(home, '.codex', 'trash');
      assert.equal(path.dirname(moved.codex), scopeTrash);
      retained = moved.codex;
      await page.locator('.toast').filter({hasText:/Recovery/}).waitFor();
      assert.notDeepEqual(fs.readFileSync(target),before);
      await page.locator('.toast button').filter({hasText:'Undo'}).last().click();
      await page.locator('.toast').filter({hasText:'Undone'}).waitFor();
      assert.equal(count,1);
      assert.deepEqual(fs.readFileSync(target),before);
      assert.match(await page.locator('main').innerText(),/majority-minor/);
      assert.match(await page.locator('.prog').innerText(),/^0 fixed/);
    }finally{
      await page.unrouteAll({behavior:'wait'});
      fs.rmSync(companion, {force:true});
      if (retained) fs.rmSync(retained, {recursive:true, force:true});
    }
  });
  await test('Stale file toggle reports error without resurrecting fixture',async()=>{await go('skill/same-everywhere');const f=file('.codex'),old=fs.readFileSync(f);fs.unlinkSync(f);try{await page.locator('.use').filter({hasText:'Codex'}).locator('label.switch').click();await page.waitForTimeout(600);assert(!fs.existsSync(f));assert(!fs.existsSync(f+'.disabled'));assert.match((await page.locator('.toast').allInnerTexts()).join(' '),/not installed|not found/i);}finally{fs.writeFileSync(f,old);}});
  await test('Native setting evidence is partial and file switch Undo preserves files',async()=>{await go('skill/same-everywhere');await page.locator('.native-settings summary').click();let t=await page.locator('.native-settings').innerText();assert.match(t,/partial/i);assert.match(t,/loading is unknown/i);assert.match(t,/Declared setting: off/);assert.match(t,/Declared setting: deny/);const f=file('.codex');await page.locator('.use').filter({hasText:'Codex'}).locator('label.switch').click();await page.waitForTimeout(500);assert(fs.existsSync(f+'.disabled'));await page.locator('.toast button').filter({hasText:'Undo'}).last().click();await page.waitForTimeout(600);assert(fs.existsSync(f));assert(!fs.existsSync(f+'.disabled'));});
  await test('Native invalid and unavailable settings render without exposing values',async()=>{let config=path.join(home,'.config/opencode/opencode.json'),saved=fs.readFileSync(config),claude=path.join(home,'.claude/settings.json'),oldClaude=fs.readFileSync(claude);fs.writeFileSync(config,'{"private":"fixture-secret",');fs.writeFileSync(claude,JSON.stringify({skillOverrides:{'majority-minor':'invalid-fixture-value'}}));try{await go('skill/majority-minor');await page.locator('.native-settings summary').click();let t=await page.locator('.native-settings').innerText();assert.match(t,/invalid/);assert.match(t,/unavailable/);assert.doesNotMatch(t,/fixture-secret|invalid-fixture-value/);}finally{fs.writeFileSync(config,saved);fs.writeFileSync(claude,oldClaude);}});
  await test('Discard navigation, dialog focus trap and cancellation',async()=>{await go('skill/same-everywhere');await page.locator('.acts button').filter({hasText:'Edit'}).click();assert(await page.locator('#ed-desc').evaluate(e=>e===document.activeElement));await page.locator('.ed-area').fill('Unsaved browser fixture');await page.locator('.tabs a').filter({hasText:'Home'}).click();await page.locator('.dlg').waitFor();for(let i=0;i<10;i++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>document.querySelector('.dlg').contains(document.activeElement)));}await page.getByRole('button',{name:'Keep editing'}).click();assert(await page.locator('.ed-area').isVisible());await page.locator('.tabs a').filter({hasText:'Home'}).click();await page.getByRole('button',{name:'Discard changes'}).click();await page.waitForTimeout(300);assert(page.url().endsWith('#/home'));});
  await test('Global Recovery restores a trashed fixture',async()=>{await go('skill/library-fixture');await page.getByRole('button',{name:'Move to trash',exact:true}).click();assert.equal(await page.locator('.pick input:checked').count(),1);await page.locator('.dlg-f .btn-danger').click();await page.waitForTimeout(700);let f=path.join(root,'data/skills-manager/skills/library-fixture/SKILL.md');assert(!fs.existsSync(f));await go('recovery');assert.match(await page.locator('.rec-list').innerText(),/last changed/);await page.locator('.rec-list button').filter({hasText:'Restore'}).click();await page.waitForTimeout(700);assert(fs.existsSync(f));});
  await test('Global Recovery restores the selected copy of a skill named purge', async () => {
    const trashed = [];
    const installed = path.join(root, 'data', 'skills-manager', 'skills', 'purge');
    try {
      for (const [i, body] of ['Older content.', 'Newer content.'].entries()) {
        const created = await page.request.post(base+'/api/skills', {data:{name:'purge', description:'Recovery test fixture.', body}});
        assert.equal(created.status(), 201);
        const removed = await page.request.delete(base+'/api/skills/purge?scope=global');
        assert.equal(removed.status(), 200);
        trashed.push((await removed.json()).trash_path);
        fs.utimesSync(trashed[i], 1700000000 + i * 60, 1700000000 + i * 60);
      }
      await go('recovery');
      const copies = page.getByRole('region', {name:/^Trash/}).getByRole('button', {name:'Restore', exact:true});
      assert.equal(await copies.count(), 2);
      await copies.first().click();
      await page.getByText('purge restored to your library.', {exact:true}).first().waitFor();
      assert.match(fs.readFileSync(path.join(installed, 'SKILL.md'), 'utf8'), /Older content\./);
      assert(!fs.existsSync(trashed[0]));
      assert(fs.existsSync(trashed[1]));
    } finally {
      for (const dir of [installed, ...trashed]) fs.rmSync(dir, {recursive:true, force:true});
    }
  });
  await test('Classic disable and enable send bodyless POST requests',async()=>{await page.goto(base+'/classic/');await page.waitForTimeout(700);await page.getByRole('button',{name:'Library',exact:true}).first().click();await page.waitForTimeout(400);await page.locator('[data-skill-key$="/library-fixture"]').click();await page.waitForTimeout(400);let requests=[];page.on('request', req=>{if(req.method()==='POST'&&/\/api\/skills\/library-fixture\/(disable|enable)/.test(req.url())) requests.push({url:req.url(),body:req.postData()});});await page.getByRole('button',{name:'Disable',exact:true}).click();await page.waitForTimeout(600);await page.getByRole('button',{name:'Enable',exact:true}).click();await page.waitForTimeout(600);assert.equal(requests.length,2);assert(requests.every(r=>!r.body));let f=path.join(root,'data/skills-manager/skills/library-fixture/SKILL.md');assert(fs.existsSync(f));});
  for (const [name,sourceDisabled,targetDisabled] of [['target-disabled',false,true],['source-disabled',true,false]]) {
    await test(`Sync Undo restores ${name} bytes and disabled state`,async()=>{
      await go('inbox');let focus=await page.locator('#focus-t').innerText();if(!focus.includes(name))await page.locator('.qi').filter({hasText:name}).click();
      const target=file('.codex',name), prior=target+(targetDisabled?'.disabled':'');const source=file('.claude',name)+(sourceDisabled?'.disabled':'');const old=fs.readFileSync(prior),sourceBytes=fs.readFileSync(source);
      await page.locator('.srcpick label').filter({hasText:'Claude Code'}).locator('input').check();await page.locator('[data-primary]').click();await page.waitForTimeout(700);
      const current=fs.existsSync(target)?target:target+'.disabled';assert.deepEqual(fs.readFileSync(current),sourceBytes);await page.locator('.toast button').filter({hasText:'Undo'}).last().click();await page.waitForTimeout(900);
      assert(fs.existsSync(prior));assert(!fs.existsSync(target+(targetDisabled?'':'.disabled')));assert.deepEqual(fs.readFileSync(prior),old);
    });
  }
  await test('Malformed text Inbox repair and Undo reappear',async()=>{
    await go('inbox');
    if (!(await page.locator('#focus-t').innerText()).includes('damaged-fm')) await page.locator('.qi').filter({hasText:'damaged-fm'}).click();
    const f=file('.codex','damaged-fm'), before=fs.readFileSync(f);
    await page.locator('[data-primary]').click();
    await page.getByRole('button',{name:'Undo',exact:true}).last().waitFor();
    assert.notDeepEqual(fs.readFileSync(f),before);
    await page.getByRole('button',{name:'Undo',exact:true}).last().click();
    await page.waitForFunction(()=>document.querySelector('#focus-t')?.textContent.includes('damaged-fm') || [...document.querySelectorAll('.qi')].some(e=>e.textContent.includes('damaged-fm')));
    assert.deepEqual(fs.readFileSync(f),before);
    assert.match(await page.locator('.prog').innerText(),/^0 fixed/);
  });
  await test('Create, editor focus, safe Markdown, save and Undo',async()=>{
    await go('skills');
    await page.getByRole('button',{name:'New skill',exact:true}).first().click();
    const name=page.locator('.dlg input').first();
    assert(await name.evaluate(e=>e===document.activeElement));
    await name.fill('created-browser');

    await page.locator('#nf-desc').fill('Use this fixture to verify browser creation.');
    await page.getByRole('button',{name:'Create skill',exact:true}).click();
    await page.locator('.acts button').filter({hasText:'Edit'}).waitFor();
    const f=file('.claude','created-browser'), original=fs.readFileSync(f);
    await page.locator('.acts button').filter({hasText:'Edit'}).click();
    assert(await page.locator('#ed-desc').evaluate(e=>e===document.activeElement));
    await page.locator('#ed-body').fill('Read *italic* and [docs](https://example.test/a).\n\n<img src=x onerror="window.fixtureAttack=1">');
    await page.getByRole('tab',{name:'Preview',exact:true}).click();
    assert.equal(await page.locator('.doc em').innerText(),'italic');
    assert.equal(await page.locator('.doc a,.doc img,.doc script').count(),0);
    assert.equal(await page.evaluate(()=>window.fixtureAttack),undefined);
    await page.locator('.savebar button').filter({hasText:'Save to'}).click();
    await page.getByRole('button',{name:'Undo',exact:true}).last().waitFor();
    assert.notDeepEqual(fs.readFileSync(f),original);
    await page.getByRole('button',{name:'Undo',exact:true}).last().click();
    await page.waitForTimeout(400);
    assert.deepEqual(fs.readFileSync(f),original);
  });
  await test('One-place dialogs preselect and cancellation keeps files',async()=>{
    await go('skill/sole-copy');
    const f=file('.claude','sole-copy'),before=fs.readFileSync(f);
    await page.getByRole('button',{name:'Move to trash',exact:true}).click();
    assert.equal(await page.locator('.pick input:checked').count(),1);
    await page.getByRole('button',{name:'Cancel',exact:true}).click();
    assert.deepEqual(fs.readFileSync(f),before);
  });
  await test('Add-to-agent single target is selected and creates a copy',async()=>{
    await go('skill/share-three');await page.getByRole('button',{name:'Add to agent',exact:true}).click();
    assert.equal(await page.locator('.pick input:checked').count(),1);
    await page.getByRole('button',{name:'Cancel',exact:true}).click();
    const f=file('.config/opencode','share-three');assert(!fs.existsSync(f));
    await page.getByRole('button',{name:'Add to agent',exact:true}).click();
    await page.locator('.dlg-f button').filter({hasText:/^Add$/}).click();
    await page.waitForTimeout(500);assert(fs.existsSync(f));
    assert.match((await page.locator('.toast').allInnerTexts()).join(' '),/Undo is unavailable/);
  });
  await test('Backup conflict explains retry and leaves the full download available',async()=>{
    await go('recovery');
    const backup=page.getByRole('region',{name:'Backup',exact:true});
    const full=backup.getByRole('button',{name:'Include trash and templates'});
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
      assert(await backup.getByRole('button',{name:'Download a backup'}).isDisabled());
      release();
      const alert=backup.getByRole('alert');
      await alert.waitFor();
      assert.match(await alert.innerText(),/Wait for changes to finish/);
      assert.doesNotMatch(await alert.innerText(),/private|HTTP 409/);
      assert.equal(downloads,0);
      await page.unroute(pattern);
      const success=page.waitForEvent('download');
      await full.click();
      assert.equal((await success).suggestedFilename(),'full-export.tar.gz');
      await alert.waitFor({state:'detached'});
    } finally {
      release();
      await page.unroute(pattern);
      page.off('download',countDownload);
    }
  });
  await test('Backup download/import and invalid archive error',async()=>{
    await go('recovery');
    const download=page.waitForEvent('download');
    await page.getByRole('button',{name:'Download a backup',exact:true}).click();
    const saved=path.join(root,'fixture-backup.tar.gz');await (await download).saveAs(saved);
    assert(fs.statSync(saved).size>0);
    await page.locator('#imp-file').setInputFiles(saved);
    await page.getByRole('button',{name:'Load skills',exact:true}).click();
    const outcome=page.locator('.import-outcome');
    await outcome.getByRole('status').waitFor();
    assert.match(await outcome.innerText(),/0 skills imported\. \d+ skipped\./);
    await outcome.getByText('Skipped entries',{exact:true}).click();
    assert((await outcome.getByRole('listitem').count())>0);
    const bad=path.join(root,'bad-archive.tar.gz');fs.writeFileSync(bad,'not an archive');
    await page.locator('#imp-file').setInputFiles(bad);
    await page.getByRole('button',{name:'Load skills',exact:true}).click();
    await outcome.waitFor();
    const text=await outcome.innerText();
    assert.match(text,/not a backup archive/);assert.doesNotMatch(text,/ReadError|Traceback|[/]tmp[/]/);
    await page.route('**/api/scopes',route=>route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({error:'Traceback /home/private/secret PermissionError'})}));
    try{await go('home');assert.doesNotMatch(await page.locator('main').innerText(),/Traceback|PermissionError|[/]home[/]private/);}finally{await page.unrouteAll({behavior:'wait'});}
  });
  await test('Sync map totals, singular grammar and top-link target size',async()=>{
    await go('skills');const total=Number((await page.locator('.seg button').first().innerText()).match(/\d+/)?.[0]);
    await go('map');assert.equal(Number((await page.locator('.map-total').innerText()).match(/^([\d,]+)/)[1].replace(/,/g,'')),total);
    assert.doesNotMatch(await page.locator('main').innerText(),/1 copy differ(?!s)/);
    await page.setViewportSize({width:1280,height:900});
    const box=await page.locator('.top .tabs a[href="#/tools"]').boundingBox();assert(box.height>=24);assert(box.width>=24);
  });
  await test('Shelf density persists across reload and is scoped to Shelf', async () => {
    await go('skills');
    const compact = page.getByRole('button', {name:'Compact', exact:true});
    const card = page.locator('.shelf .sk').first();
    const before = await card.boundingBox();
    try {
      await compact.click();
      await go('skills');
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
      await table.getByRole('button', {name:/same-everywhere, Codex:.*Matches reference content/}).waitFor();
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
      await page.waitForURL(url => url.hash === '#/skill/majority-minor');
      await go('map');
      await search.fill('no-such-fixture');
      await page.getByText('No skills match this search.').waitFor();
      assert.equal(await table.count(), 0);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    } finally {
      await page.setViewportSize({width:1280,height:900});
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
  await test('Responsive layouts in both themes',async()=>{for(const [label,w,h] of [['desktop',1280,900],['phone',390,844]])for(const t of ['light','dark']){await page.setViewportSize({width:w,height:h});await go('home');await theme(t);for(const r of ['home','skills','skill/same-everywhere','map','inbox','recovery']){await go(r);assert.equal(await page.locator('html').getAttribute('data-theme'),t);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,`${label} ${t} ${r}`);await page.screenshot({path:path.join(root,`${label}-${t}-${r.replace('/','-')}.png`)});}}});
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
        await go('skills');
        assert.equal(await page.locator('.sk').count(),fixture.length);
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
      for(const route of ['home','skills','skill/same-everywhere','map','inbox','recovery']){
        await go(route);
        await page.screenshot({path:path.join(root,`browser-zoom-${percent}-${route.replace('/','-')}.png`)});
        const overflow=await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(e=>{const b=e.getBoundingClientRect();return b.width>0 && b.right>document.documentElement.clientWidth+1;}).map(e=>({tag:e.tagName,cls:e.className,text:e.innerText?.slice(0,80),width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})));
        fs.writeFileSync(path.join(root,`overflow-${percent}-${route.replace('/','-')}.json`),JSON.stringify(overflow,null,2));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,`browser zoom ${percent}: ${route}`);
      }
      await go('skills');await page.getByRole('button',{name:'New skill',exact:true}).first().click();
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
    const doc=path.join(root,'data/skills-manager/skills/v2-browser-created/SKILL.md');
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
    assert(fs.existsSync(path.join(root,'data/skills-manager/skills/v2-browser-created/SKILL.md')));
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
    await page.keyboard.press('Control+k');await page.locator('#command-q').fill('templates');await page.locator('.command-list').getByRole('button',{name:'Templates',exact:true}).click();await page.getByRole('heading',{name:'Templates',exact:true}).waitFor();
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
    await go('skills');
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
    await page.locator('.use').filter({hasText:'Shared skills folder'}).first().waitFor({state:'visible'});
    const claudeCopy=page.locator('.use').filter({hasText:'Claude Code'});
    assert(await claudeCopy.locator('input[type="checkbox"]').isDisabled());
    await page.locator('.acts button').filter({hasText:'Edit'}).click();
    const targets=await page.locator('.savebar label').allInnerTexts();
    assert.deepEqual(targets,['Shared skills folder']);
    await page.locator('#ed-body').fill('# Updated by the owner UI\n');
    await page.locator('.savebar button').filter({hasText:'Save'}).click();
    await page.waitForTimeout(500);
    assert.match(fs.readFileSync(path.join(target,'SKILL.md'),'utf8'),/Updated by the owner UI/);
    assert.match(fs.readFileSync(path.join(link,'SKILL.md'),'utf8'),/Updated by the owner UI/);
  });
  await test('Agent trash removal offers Undo and Recovery restore',async()=>{
    const name='browser-agent-trash';
    const created=await page.request.post(base+'/api/skills?scope=agents',{data:{name,description:'Agent trash browser fixture.',body:'# Trash fixture\n'}});
    assert(created.ok(),await created.text());
    const filePath=path.join(home,'.agents','skills',name,'SKILL.md');
    const original=fs.readFileSync(filePath);
    await go('skill/'+name);
    await page.getByRole('button',{name:'Move to trash',exact:true}).click();
    await page.locator('.dlg-f .btn-danger').click();
    await page.getByRole('button',{name:'Undo',exact:true}).last().waitFor();
    assert(!fs.existsSync(filePath));
    await page.getByRole('button',{name:'Undo',exact:true}).last().click();
    await page.waitForTimeout(500);
    assert(fs.existsSync(filePath));
    assert.deepEqual(fs.readFileSync(filePath),original);

    await go('skill/'+name);
    await page.getByRole('button',{name:'Move to trash',exact:true}).click();
    await page.locator('.dlg-f .btn-danger').click();
    await page.waitForTimeout(500);
    assert(!fs.existsSync(filePath));
    await go('recovery');
    const agentTrash=page.locator('section[aria-labelledby="rec-agent-trash"]');
    await agentTrash.getByText(name,{exact:true}).waitFor();
    const restore=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('/api/trash/'+name+'?scope=agents'));
    await agentTrash.getByRole('button',{name:'Restore',exact:true}).click();
    assert((await restore).ok());
    await page.waitForTimeout(300);
    assert(fs.existsSync(filePath));
    assert.deepEqual(fs.readFileSync(filePath),original);
    await agentTrash.getByText(name,{exact:true}).waitFor({state:'detached'});
  });
  await test('V2 tool read failure stays visible and a retry recovers',async()=>{
    await page.route('**/api/catalog',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Fixture catalog unavailable'})}));
    try{await go('tools/profiles');await page.getByRole('alert').filter({hasText:'Fixture catalog unavailable'}).waitFor();assert(await page.getByRole('button',{name:'Retry profiles',exact:true}).isVisible());}
    finally{await page.unroute('**/api/catalog');}
    await page.getByRole('button',{name:'Retry profiles',exact:true}).click();await page.getByText('v2-browser-profile',{exact:true}).waitFor();
  });
  await test('V2 Quality labels APM evidence for the selected project',async()=>{
    const project=path.join(root,'data','skills-manager','apm-fixture');
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
  await test('All v2 tool routes fit desktop and small phone in both themes',async()=>{
    for(const width of [320,768,1280])for(const mode of ['light','dark']){
      await page.setViewportSize({width,height:900});await go('tools/settings');await page.getByLabel('Theme',{exact:true}).selectOption(mode);
      for(const route of ['tools','tools/install','tools/profiles','tools/templates','tools/quality','tools/workspaces','tools/settings','tools/source-update','skills','recovery']){
        await go(route);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${route} ${width} ${mode}`);
      }
    }
    await page.setViewportSize({width:1280,height:900});await go('tools');await page.screenshot({path:path.join(root,'final-tools-desktop.png')});
  });
  await test('No uncaught page errors',async()=>assert.deepEqual(exceptions,[]));
  record('Coverage limit','NOTE','Actual browser zoom is checked only in headed Chrome. Screen-reader and perceptual review require a person.');
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({engine,browserVersion,results,failures:failed},null,2)+'\n');await browser.close();process.exitCode=failed?1:0;
})().catch(e=>{console.error(e);process.exitCode=2}).finally(async()=>{if(browser)await browser.close();});
