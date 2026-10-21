import { chromium } from 'playwright';

const baseUrl = process.env.POINT_QUOTE_TEST_URL || 'http://127.0.0.1:5173';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.getByText('业务数据已写入当前知识库', { exact: false }).waitFor();
  const status = await page.evaluate(async () => (await fetch('/api/knowledge-sync/status')).json());
  if (status.brand_notes !== 14) throw new Error(`expected 14 brand notes, got ${status.brand_notes}`);
  if (status.project_notes !== 4) throw new Error(`expected 4 project notes, got ${status.project_notes}`);
  if (status.conflicts.length) throw new Error(`unexpected sync conflicts: ${status.conflicts.length}`);
  const projectCards = await page.locator('.project-card').count();
  if (projectCards !== 4) throw new Error(`expected 4 restored project cards, got ${projectCards}`);
  console.log('RQ-012 passed: live vault source, 14 brands, 4 projects, no conflicts, project list intact.');
} finally {
  await browser.close();
}
