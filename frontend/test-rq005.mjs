import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

try {
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '产品库', exact: true }).click();
  await page.locator('.catalog-panel').waitFor();

  if (await page.locator('.catalog-cost-value').count()) throw new Error('cost values must be hidden on first open');
  if (await page.getByText('显示进货价', { exact: true }).count()) throw new Error('visible cost toggle must not exist');
  if (await page.locator('.catalog-cost-secret').count() !== 1) throw new Error('hidden corner trigger is missing');

  await page.locator('.catalog-cost-secret').dblclick();
  const values = await page.locator('.catalog-cost-value').allTextContents();
  if (!values.length) throw new Error('double-click did not reveal numeric cost values');
  if (values.some(value => value !== '—' && !/^\d{1,3}(,\d{3})*\.\d{2}$/.test(value))) throw new Error(`non-numeric cost display: ${values.join(', ')}`);
  if (await page.getByText('进货价', { exact: true }).count()) throw new Error('cost wording must not be shown while values are visible');

  await page.reload({ waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '产品库', exact: true }).click();
  await page.locator('.catalog-panel').waitFor();
  if (await page.locator('.catalog-cost-value').count()) throw new Error('cost visibility must reset after reopening');

  console.log('RQ-005 passed: hidden by default, secret double-click, numeric-only display, and reopen reset.');
} finally {
  await browser.close();
}
