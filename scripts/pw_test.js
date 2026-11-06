const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => { const loc=msg.location(); console.log('PAGE_CONSOLE', msg.type(), msg.text().substring(0,200), loc.url, loc.lineNumber); if (msg.type() === 'error') errors.push(msg.text()+' @'+loc.lineNumber); });
  page.on('pageerror', err => { console.log('PAGEERROR', err.message); console.log('STACK', err.stack); errors.push('PAGEERROR: '+err.message); });
  page.on('pageerror', err => errors.push(err.stack || err.message));
  await page.goto('http://localhost:8000/', { waitUntil: 'commit', timeout: 60000 });
  await page.waitForTimeout(15000);
  // check canvas not blank
  const canvasInfo = await page.evaluate(() => {
    const c = document.querySelector('canvas');
    return {w:c.width, h:c.height, clientW:c.clientWidth, clientH:c.clientHeight};
  });
  console.log('CANVAS_INFO:', JSON.stringify(canvasInfo));
  const blank = await page.evaluate(() => {
    const c = document.querySelector('canvas');
    const ctx = c.getContext('webgl2') || c.getContext('webgl');
    // sample center pixel via readPixels
    const data = new Uint8Array(c.width*c.height*4);
    ctx.readPixels(0,0,c.width,c.height,ctx.RGBA,ctx.UNSIGNED_BYTE,data);
    let nonBlack=0;
    for(let i=0;i<data.length;i+=4){ if(data[i]>10||data[i+1]>10||data[i+2]>10) nonBlack++; }
    console.log('NONBLACK_PIXELS', nonBlack);
    return nonBlack < 1000;
  });
  await page.screenshot({ path: 'docs/capturas/visor_ok.png', fullPage: true });
  console.log('CONSOLE_ERRORS:', JSON.stringify(errors));
  console.log('CENTER_BLANK:', blank);
  await browser.close();
})();