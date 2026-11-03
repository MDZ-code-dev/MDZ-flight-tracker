// Run against a source server or the packaged Windows executable.
// npm install playwright-core@1.56.1; set MDZ_TEST_URL and a browser path/channel.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const url = process.env.MDZ_TEST_URL || 'http://127.0.0.1:18767';
const plane = {callsign:'SKY747',hex:'abc123',registration:'N747',type:'B744',
  description:'BOEING 747-400',squawk:'1200',altitude:'12,000 FT',speed:'250 KT',
  vertical:'LEVEL',track:238,track_direction:'SW',distance_nm:4.2,bearing:173,
  bearing_direction:'S',military:false,lat:43.66,lon:-79.38};
const config = {lat:43.65,lon:-79.38,radius_nm:80,refresh_seconds:60};

async function geometry(page) {
  return page.evaluate(() => {
    const node = document.getElementById('aircraftSilhouette');
    const length = node.getTotalLength(), matrix = node.getScreenCTM();
    const points = Array.from({length:301}, (_,i) => node.getPointAtLength(length*i/300).matrixTransform(matrix));
    const rect = document.getElementById('aircraftVisual').getBoundingClientRect();
    return {left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),
      top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y)),
      visual:{left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom},
      svgHeight:document.querySelector('.aircraft-visual-svg').getBoundingClientRect().height};
  });
}

async function main() {
  const launch = {headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
  if (process.env.MDZ_BROWSER_EXECUTABLE) launch.executablePath = process.env.MDZ_BROWSER_EXECUTABLE;
  else launch.channel = process.env.MDZ_BROWSER_CHANNEL || 'msedge';
  const browser = await chromium.launch(launch);
  try {
    for (const [name,width,height] of [['switch',1280,720],['windows-laptop',1366,600],
      ['windows-scaled',1093,500],['landscape',960,540],['phone',390,844],['desktop',1440,900]]) {
      const page = await browser.newPage({viewport:{width,height}});
      const errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => requests.push(request.url()));
      await page.route('**/api/config', route => route.fulfill({json:config}));
      await page.route('**/api/planes', route => route.fulfill({json:{ok:true,config,nearest:plane,
        planes:[plane],total:1,updated:Math.floor(Date.now()/1000)}}));
      await page.goto(url);
      await page.waitForFunction(() => document.getElementById('aircraftVisualType').textContent === 'B744');
      await page.evaluate(() => document.fonts.ready);
      assert(await page.evaluate(() => Array.from(document.fonts).some(font =>
        font.family.replace(/["']/g,'') === 'SkyScan Pixel' && font.status === 'loaded')), 'Bundled pixel font did not load');
      assert.equal(await page.locator('#appVersion').textContent(), 'v1.0.9');
      if (width <= 850) await page.locator('#aircraftVisual').scrollIntoViewIfNeeded();
      for (const heading of [0,45,90,180,238,315]) {
        await page.evaluate(p => renderNearest(p,1), {...plane,track:heading});
        const box = await geometry(page);
        assert(box.svgHeight >= 80, name + ': drawing collapsed');
        assert(box.top >= box.visual.top && box.bottom <= box.visual.bottom, name + ': silhouette clipped vertically');
        assert(box.left >= box.visual.left && box.right <= box.visual.right, name + ': silhouette clipped horizontally');
        assert(box.top >= 0 && box.bottom <= height, name + ': silhouette outside visible viewport');
      }
      await page.evaluate(p => renderNearest(p,1), plane);
      if (process.env.MDZ_SCREENSHOT_DIR) {
        fs.mkdirSync(process.env.MDZ_SCREENSHOT_DIR,{recursive:true});
        await page.screenshot({path:path.join(process.env.MDZ_SCREENSHOT_DIR,name+'.png'),fullPage:true});
      }
      // Exact reported types keep their own models even when feed text conflicts.
      const typeCases = [
        ['B738','Bombardier Challenger 350','Boeing 737-800',true],
        ['CL35','Boeing 737-800','Bombardier Challenger 350/3500',true],
        ['CRJ9','Bombardier CRJ900','Bombardier CRJ900',false],
        ['B722','Boeing 727-200','Boeing 727-200',false],
        ['MD11','McDonnell Douglas MD-11','McDonnell Douglas MD-11',false],
        ['C130','Lockheed C-130 Hercules','Lockheed C-130 Hercules',false]
      ];
      const aircraftPaths = new Map();
      for (const [type,description,model,conflict] of typeCases) {
        await page.evaluate(p => renderNearest(p,1), {...plane,type,description,track:45});
        assert((await page.locator('#typeLine').textContent()).includes(model), name + ': wrong model name for ' + type);
        assert.equal(await page.locator('#description').textContent(), type);
        assert.equal(await page.locator('#identityNote').isVisible(), conflict, name + ': model conflict flag for ' + type);
        aircraftPaths.set(type, await page.locator('#aircraftSilhouette').getAttribute('d'));
      }
      assert.notEqual(aircraftPaths.get('B738'), aircraftPaths.get('CL35'));
      assert.notEqual(aircraftPaths.get('CRJ9'), aircraftPaths.get('B738'));
      assert.notEqual(aircraftPaths.get('B722'), aircraftPaths.get('MD11'));
      await page.evaluate(p => renderNearest(p,1), plane);
      const jet = await page.locator('#aircraftSilhouette').getAttribute('d');
      await page.evaluate(p => renderNearest(p,1), {...plane,type:'B06',category:'A7',track:null});
      assert.notEqual(await page.locator('#aircraftSilhouette').getAttribute('d'), jet);
      assert((await page.locator('#aircraftVisual').getAttribute('aria-label')).includes('heading unknown'));
      await page.evaluate(() => renderNearest(null,0));
      assert.equal(await page.locator('#aircraftSilhouette').getAttribute('d'),'');
      await page.locator('#modeBtn').click();
      await page.waitForFunction(() => document.getElementById('radar').width > 100 && document.getElementById('radar').height > 100);
      assert.deepEqual(errors, [], name + ': JavaScript errors');
      assert(requests.some(request => request.includes('/Silkscreen-Regular.ttf')), 'Font was not requested from local bundle');
      assert(requests.every(request => new URL(request).origin === new URL(url).origin), 'Unexpected external UI dependency');
      console.log('PASS:',name,'pixel font, visible silhouette at six headings, model changes, empty state, radar');
      await page.close();
    }
  } finally { await browser.close(); }
}
main().catch(error => {console.error(error);process.exitCode=1;});
