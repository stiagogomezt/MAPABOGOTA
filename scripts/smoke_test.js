const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => { if (msg.type()==='error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  await page.goto('http://localhost:8099/', { waitUntil:'networkidle', timeout:60000 });
  await page.waitForTimeout(8000);
  console.log('CONSOLE_ERRORS:', JSON.stringify(errors));
  await page.screenshot({ path: 'docs/capturas/smoke.png' });
  await browser.close();
  if (errors.length>0) process.exit(1);
})();
