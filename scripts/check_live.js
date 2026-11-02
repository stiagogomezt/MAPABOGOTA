const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  const URL = 'https://stiagogomezt.github.io/MAPABOGOTA/';
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 120000 });
  await page.waitForTimeout(8000);
  // click texture selector
  try { await page.selectOption('#tex', 'relief'); await page.waitForTimeout(1000); } catch(e){ errors.push('select: '+e.message); }
  // click video
  try { await page.click('#videoBtn'); await page.waitForTimeout(2000); await page.click('#closeVideo'); } catch(e){ errors.push('video: '+e.message); }
  // check resources
  const res = ['terrain/texture_satellite_4096.jpg','terrain/camera_path.json','media/bogota_flyover.mp4'];
  for (const r of res) {
    const resp = await page.request.get(URL + r, { timeout: 60000 });
    console.log(r, resp.status());
    if (resp.status() !== 200) errors.push(r + ' -> ' + resp.status());
  }
  // GLB via HEAD
  const glbStatus = await page.evaluate(async (u) => { const r = await fetch(u, {method:'HEAD'}); return r.status; }, URL+'terrain/terrain.glb');
  console.log('terrain/terrain.glb', glbStatus);
  if (glbStatus !== 200) errors.push('terrain/terrain.glb -> ' + glbStatus);
  await page.screenshot({ path: 'docs/capturas/publicado.png', fullPage: true });
  console.log('CONSOLE_ERRORS:', JSON.stringify(errors));
  await browser.close();
})();
