import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const css = await readFile(new URL('./src/style.css', import.meta.url), 'utf8');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

const marker = (id, classes, style, inner = '') =>
  `<div data-point="${id}" class="point-marker ${classes}" style="${style}">${inner}</div>`;

async function hitAt(scale, order, x, y) {
  const elements = order.map(id => {
    if (id === 'point') {
      return marker('point', 'point-symbol', 'left:180px;top:140px;--point-size:32px;--point-color:#2856a8', '<span class="point-circle"></span>');
    }
    if (id === 'area-a') {
      return marker('area-a', 'shape-marker area-shape', 'left:40px;top:40px;width:320px;height:220px;--point-color:#d59a18');
    }
    return marker('area-b', 'shape-marker area-shape', 'left:80px;top:70px;width:300px;height:210px;--point-color:#6b7280');
  }).join('');

  await page.setContent(`
    <style>${css}</style>
    <div id="stage" style="position:absolute;left:60px;top:50px;width:500px;height:350px;transform:scale(${scale});transform-origin:0 0">
      ${elements}
    </div>
  `);
  return page.evaluate(({ scale, x, y }) => {
    const target = document.elementFromPoint(60 + x * scale, 50 + y * scale);
    return target?.closest('.point-marker')?.getAttribute('data-point') ?? null;
  }, { scale, x, y });
}

async function rightClickAt(scale, order, x, y) {
  await hitAt(scale, order, x, y);
  await page.evaluate(() => {
    window.__contextTarget = null;
    document.addEventListener('contextmenu', event => {
      event.preventDefault();
      window.__contextTarget = event.target?.closest('.point-marker')?.getAttribute('data-point') ?? null;
    }, { once: true });
  });
  await page.mouse.click(60 + x * scale, 50 + y * scale, { button: 'right' });
  return page.evaluate(() => window.__contextTarget);
}

try {
  for (const scale of [0.5, 1, 2]) {
    for (const order of [
      ['point', 'area-a'],
      ['area-a', 'point'],
      ['point', 'area-a', 'area-b'],
      ['area-a', 'area-b', 'point'],
    ]) {
      const hit = await hitAt(scale, order, 180, 140);
      if (hit !== 'point') throw new Error(`scale=${scale}, order=${order.join(',')}: expected point, got ${hit}`);
    }

    const singleAreaHit = await hitAt(scale, ['area-a', 'point'], 70, 60);
    if (singleAreaHit !== 'area-a') throw new Error(`scale=${scale}: expected area-a blank space, got ${singleAreaHit}`);

    const overlappingAreaHit = await hitAt(scale, ['area-a', 'area-b'], 100, 90);
    if (overlappingAreaHit !== 'area-b') throw new Error(`scale=${scale}: expected top overlapping area-b, got ${overlappingAreaHit}`);

    const pointContextHit = await rightClickAt(scale, ['point', 'area-a', 'area-b'], 180, 140);
    if (pointContextHit !== 'point') throw new Error(`scale=${scale}: expected point right-click target, got ${pointContextHit}`);

    const areaContextHit = await rightClickAt(scale, ['area-a', 'point'], 70, 60);
    if (areaContextHit !== 'area-a') throw new Error(`scale=${scale}: expected area right-click target, got ${areaContextHit}`);
  }

  console.log('RQ-003B hit-test passed: left/right click priority, area blank space, overlapping areas, zoom 50%/100%/200%.');
} finally {
  await browser.close();
}
