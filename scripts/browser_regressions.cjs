// Synthetic static-file browser fixture; never starts the SQLite/clinical server.
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { chromium } = require('../tools/browser-tests/node_modules/playwright');
const port = Number(process.env.BROWSER_TEST_PORT || 3198);
const origin = `http://127.0.0.1:${port}`;
async function ready(server) {
  for(let i=0;i<100;i++) {
    if(server.exitCode!==null || server.signalCode!==null) throw new Error('Fixture server exited');
    try { if((await fetch(origin)).ok) return; } catch {}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('Fixture server did not become ready within ten seconds');
}
async function stop(server) {
  if(server.exitCode!==null || server.signalCode!==null) return;
  await new Promise((resolve,reject)=>{
    const force=setTimeout(()=>server.kill('SIGKILL'),3000);
    const deadline=setTimeout(()=>{clearTimeout(force);reject(new Error('Fixture server did not stop within five seconds'));},5000);
    server.once('exit',()=>{clearTimeout(force);clearTimeout(deadline);resolve();});
    server.kill('SIGTERM');
  });
}
(async()=>{
const server=spawn(process.env.PYTHON || 'python3',['-m','http.server',String(port),'--bind','127.0.0.1'],{cwd:path.resolve(__dirname,'..'),stdio:'ignore'});
let browser,context,page;
try {
  await ready(server);
  browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
  context=await browser.newContext({viewport:{width:390,height:780},reducedMotion:'reduce'});
  page=await context.newPage();const diErrors=[];page.on('pageerror',e=>diErrors.push(e.message));
  await page.route('**/*', route => { const url=new URL(route.request().url()); if(url.origin!==origin || url.pathname.startsWith('/api/')) return route.abort(); return route.continue(); });
  await page.goto(origin);
  await page.locator('[data-domain]').first().waitFor();
  await page.getByText('Display settings',{exact:true}).click();
  await page.getByLabel('Text size').selectOption('large');
  await page.getByLabel('Motion').selectOption('reduce');
  assert.equal(await page.locator('body').evaluate(el=>getComputedStyle(el).fontSize),'18px');assert.equal(await page.locator('html').evaluate(el=>getComputedStyle(el).fontSize),'18px');assert.ok(await page.locator('.lead').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))>18);
  await page.locator('#clinicianName').fill('Synthetic Reviewer');await page.locator('#caseId').fill('SYNTHETIC-UX-ONLY');
  await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new Error('Synthetic storage full')};});
  await page.getByRole('button',{name:'Save',exact:true}).click();
  await page.locator('#calculator-message').filter({hasText:/not saved/}).waitFor();
  assert.match(await page.locator('#calculator-message').textContent(),/not saved/);
  assert.equal(await page.locator('#caseId').inputValue(),'SYNTHETIC-UX-ONLY');
  await page.getByRole('link',{name:'View result',exact:true}).click();
  assert.equal(await page.locator('#calculator-result').evaluate(el=>el===document.activeElement),true);
  const before=await page.evaluate(()=>scrollY);await page.locator('[data-domain]').first().evaluate(el=>{el.value='5';el.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.waitForTimeout(350); assert.ok(Math.abs(await page.evaluate(()=>scrollY)-before)<2);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(diErrors,[]);
  console.log('Synthetic mobile display, denied-save, result focus and scroll regressions passed');await context.close();
} finally {
  if(browser) await browser.close();
  await stop(server);
}
})().catch(error=>{console.error(error);process.exitCode=1;});
