import { chromium } from 'playwright';

const baseUrl = process.env.POINT_QUOTE_TEST_URL || 'http://127.0.0.1:5173';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '帮助', exact: true }).click();
  await page.getByRole('heading', { name: '需求与问题状态中心' }).waitFor();

  if (await page.locator('.status-stat-card').count() !== 5) throw new Error('five status cards are required');
  if (!await page.getByText('数据源：docs/REQUIREMENTS.md · docs/ISSUES.md', { exact: true }).isVisible()) throw new Error('Markdown source note is missing');
  if (!await page.getByText('RQ-007', { exact: true }).first().isVisible()) throw new Error('RQ-007 requirement card is missing');
  if (!await page.getByText('ISSUE-006', { exact: true }).isVisible()) throw new Error('ISSUE-006 issue card is missing');

  await page.getByRole('button', { name: '问题', exact: true }).click();
  if (await page.locator('.requirement-card').count()) throw new Error('requirement cards must be hidden by issue filter');
  if (!await page.locator('.issue-card').count()) throw new Error('issue filter must show issue cards');

  await page.locator('.status-stat-card[data-status="resolved"]').click();
  if (await page.locator('.issue-card:not([data-status="resolved"])').count()) throw new Error('status filter returned a mismatched issue');

  await page.getByRole('button', { name: '版本记录', exact: true }).click();
  if (!await page.getByRole('heading', { name: '项目变更记录' }).isVisible()) throw new Error('document changelog is missing');
  if (!await page.getByRole('heading', { name: '历史正式版本' }).isVisible()) throw new Error('legacy release history is missing');

  await page.getByRole('button', { name: '问题反馈', exact: true }).click();
  if (!await page.getByRole('button', { name: '提交反馈', exact: true }).isVisible()) throw new Error('feedback form is missing');

  await page.getByRole('button', { name: '使用帮助', exact: true }).click();
  if (!await page.getByRole('heading', { name: '快速使用' }).isVisible()) throw new Error('quick guide is missing');

  console.log('RQ-007 passed: document source, five statuses, filters, separate versions, guide and feedback.');
} finally {
  await browser.close();
}
