// Render assets/failed_it/*.svg to 1200x600 JPEGs for the email.
//   node scripts/render_failed_it_images.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.join(__dirname, '..', 'assets', 'failed_it');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 600 } });
  for (const f of fs.readdirSync(dir).filter((n) => n.endsWith('.svg')).sort()) {
    const svg = fs.readFileSync(path.join(dir, f), 'utf8');
    await page.setContent(`<html><body style="margin:0">${svg}</body></html>`);
    const out = path.join(dir, f.replace(/\.svg$/, '.jpg'));
    await page.screenshot({ path: out, type: 'jpeg', quality: 82, clip: { x: 0, y: 0, width: 1200, height: 600 } });
    console.log(out);
  }
  await browser.close();
})();
