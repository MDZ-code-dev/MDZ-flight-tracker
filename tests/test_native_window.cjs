// Attach to the WebView2 inside the actual packaged native application.
// No separate browser is launched, and no app window/page is created here.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');

const url = process.env.MDZ_TEST_URL;
const cdp = process.env.MDZ_NATIVE_CDP_URL;
const version = process.env.MDZ_TEST_VERSION;
const plane = {callsign:'SKY747',hex:'abc123',registration:'N747',type:'B744',
  description:'BOEING 747-400',squawk:'1200',altitude:'12,000 FT',speed:'250 KT',
  vertical:'LEVEL',track:238,track_direction:'SW',distance_nm:4.2,bearing:173,
  bearing_direction:'S',military:false,lat:43.66,lon:-79.38};
const config = {lat:43.65,lon:-79.38,radius_nm:80,refresh_seconds:60};
const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function main() {
  assert(url && cdp && version, 'Set MDZ_TEST_URL, MDZ_NATIVE_CDP_URL and MDZ_TEST_VERSION');
  let browser;
  let lastConnectionError;
  const deadline = Date.now() + 45000;
  while (!browser && Date.now() < deadline) {
    try { browser = await chromium.connectOverCDP(cdp, {timeout:2000}); }
    catch (error) { lastConnectionError = error.message; await delay(500); }
  }
  assert(browser, 'Native WebView2 did not expose its CI-only CDP endpoint: ' + lastConnectionError);
  try {
    let page;
    while (!page && Date.now() < deadline) {
      for (const context of browser.contexts()) {
        page = context.pages().find(candidate => candidate.url().startsWith(url));
        if (page) break;
      }
      if (!page) await delay(250);
    }
    assert(page, 'Could not find the application page in the embedded WebView2');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/config', route => route.fulfill({json:config}));
    await page.route('**/api/planes', route => route.fulfill({json:{ok:true,config,nearest:plane,
      planes:[plane],total:1,updated:Math.floor(Date.now()/1000)}}));
    for (const [name,width,height] of [['native-window',1280,720],['native-window-scaled',1093,500]]) {
      await page.setViewportSize({width,height});
      await page.reload();
      await page.waitForFunction(() => document.getElementById('aircraftVisualType').textContent === 'B744');
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.locator('#appVersion').textContent(), 'v' + version);
      assert(await page.evaluate(() => Array.from(document.fonts).some(font =>
        font.family.replace(/["']/g,'') === 'SkyScan Pixel' && font.status === 'loaded')),
        name + ': bundled pixel font did not load inside WebView2');
      for (const heading of [0,45,90,180,238,315]) {
        await page.evaluate(p => renderNearest(p,1), {...plane,track:heading});
        const geometry = await page.evaluate(() => {
          const node = document.getElementById('aircraftSilhouette');
          const length = node.getTotalLength(), matrix = node.getScreenCTM();
          const points = Array.from({length:301}, (_,i) => node.getPointAtLength(length*i/300).matrixTransform(matrix));
          const rect = document.getElementById('aircraftVisual').getBoundingClientRect();
          return {left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),
            top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y)),
            visual:{left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom},
            svgHeight:document.querySelector('.aircraft-visual-svg').getBoundingClientRect().height};
        });
        assert(geometry.svgHeight >= 80, name + ': silhouette drawing collapsed');
        assert(geometry.top >= geometry.visual.top && geometry.bottom <= geometry.visual.bottom,
          name + ': silhouette clipped vertically');
        assert(geometry.left >= geometry.visual.left && geometry.right <= geometry.visual.right,
          name + ': silhouette clipped horizontally');
        assert(geometry.top >= 0 && geometry.bottom <= height, name + ': silhouette outside window viewport');
      }
      const jet = await page.locator('#aircraftSilhouette').getAttribute('d');
      await page.evaluate(p => renderNearest(p,1), {...plane,type:'B06',category:'A7',track:null});
      assert.notEqual(await page.locator('#aircraftSilhouette').getAttribute('d'), jet);
      assert((await page.locator('#aircraftVisual').getAttribute('aria-label')).includes('heading unknown'));
      await page.evaluate(() => renderNearest(null,0));
      assert.equal(await page.locator('#aircraftSilhouette').getAttribute('d'),'');
      await page.locator('#modeBtn').click();
      await page.waitForFunction(() => document.getElementById('radar').width > 100 && document.getElementById('radar').height > 100);
      assert.deepEqual(errors, [], name + ': embedded JavaScript errors');
      assert.equal(new URL(page.url()).origin, new URL(url).origin, 'Embedded page left the application origin');
      console.log('PASS:',name,'actual embedded WebView2, pixel font, silhouette headings, aircraft changes and radar');
    }
  } finally {
    // For connectOverCDP Playwright closes only its WebSocket connection. Leave
    // the app window open for PowerShell to test its real close/shutdown event.
    await browser.close();
  }
}
main().catch(error => {
  console.error(error);
  const details = String(error.message).replace(/%/g,'%25').replace(/\r/g,'%0D').replace(/\n/g,'%0A');
  console.error('::error::Embedded Windows WebView2 regression: ' + details);
  process.exitCode = 1;
});
