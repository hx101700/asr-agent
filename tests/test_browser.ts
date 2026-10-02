import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import assert from "node:assert/strict";
import test from "node:test";

const repository = path.resolve(".");
const screenshots = path.join(repository, ".runtime/ui-previews");

// 以合成输入启动真实HTTP服务，结束后清理整个测试工作区。
test("Edge页面完成双语、主题、输入校验、Key保存及配置确认", { timeout: 60_000 }, async (t) => {
  const testRoot = path.join(repository, ".runtime/browser-tests");
  await fs.mkdir(testRoot, { recursive: true });
  await fs.mkdir(screenshots, { recursive: true });
  const root = await fs.mkdtemp(path.join(testRoot, "run-"));
  const previousTemp = { TEMP: process.env.TEMP, TMP: process.env.TMP };
  process.env.TEMP = root;
  process.env.TMP = root;
  const server = spawn(path.join(repository, ".venv/Scripts/python.exe"),
    ["-B", "-X", "utf8", "-m", "tests.browser_server", "--workspace", root],
    { cwd: repository, windowsHide: true, stdio: "pipe" });
  t.after(async () => {
    if (server.exitCode === null && server.signalCode === null) {
      const ended = new Promise<void>(resolve => server.once("exit", () => resolve()));
      server.kill();
      await ended;
    }
    const actual = await fs.realpath(root);
    assert.equal(path.dirname(actual), await fs.realpath(testRoot));
    await fs.rm(actual, { recursive: true });
    for (const name of ["TEMP", "TMP"] as const) {
      if (previousTemp[name] === undefined) delete process.env[name];
      else process.env[name] = previousTemp[name];
    }
  });
  const lines = createInterface({ input: server.stdout });
  const connection = await new Promise<{ url: string }>((resolve, reject) => {
    lines.once("line", line => {
      try { resolve(JSON.parse(line) as { url: string }); }
      catch { reject(new Error("本机测试服务返回了无效的启动回执。")); }
      lines.close();
    });
    server.once("error", reject);
    server.once("exit", () => reject(new Error("本机测试服务在就绪前退出。")));
  });
  const origin = new URL(connection.url).origin;
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, locale: 'zh-CN', colorScheme: 'light' });
    const page = await context.newPage();
    const errors: string[] = [], requests: { origin: string; path: string }[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('request', request => { const url = new URL(request.url()); requests.push({ origin: url.origin, path: url.pathname }); });
    await page.goto(connection.url);
    await page.getByText('选择音频文件', { exact: true }).waitFor();
    assert.equal(await page.locator('#language_hint').getByText('自动识别', { exact: true }).isVisible(), true);
    await page.screenshot({ path: path.join(screenshots, 'zh-light.png'), animations: 'disabled' });
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForFunction(() => document.documentElement.classList.contains('dark'));
    await page.screenshot({ path: path.join(screenshots, 'zh-dark.png'), animations: 'disabled' });
    await page.locator('.language-select').click();
    await page.getByRole('option', { name: 'English', exact: true }).click();
    await page.locator('.theme-select').click();
    await page.getByRole('option', { name: 'Light', exact: true }).click();
    await page.waitForFunction(() => !document.documentElement.classList.contains('dark'));
    await page.locator('#page-title').click();
    await page.screenshot({ path: path.join(screenshots, 'en-light.png'), animations: 'disabled' });
    await page.locator('.theme-select').click();
    await page.getByRole('option', { name: 'Dark', exact: true }).click();
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    assert.equal(await page.locator('html').getAttribute('class'), 'dark');
    await page.locator('#page-title').click();
    await page.screenshot({ path: path.join(screenshots, 'en-dark.png'), animations: 'disabled' });
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.locator('#error-panel').getByText('Choose an audio file.', { exact: true }).waitFor();
    assert.equal(await page.locator('#audio_upload_id').evaluate(element => element.contains(document.activeElement)), true);
    await page.locator('#audio_upload_id input[type=file]').setInputFiles(path.join(root, 'fixtures/sample.wav'));
    await page.locator('#audio_upload_id').getByText('Added', { exact: true }).waitFor();
    await page.locator('label[for="use-api-key"]').click();
    await page.locator('#api-key-value').fill('fixture-ui-key-not-real');
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.getByRole('button', { name: 'Save settings', exact: true }).waitFor();
    assert.ok((await fs.readFile(path.join(root, '.asr-transcription/.env'), 'utf8')).includes('fixture-ui-key-not-real'));
    assert.ok((await page.locator('#review').innerText()).includes('mono'));
    await page.locator('label[for="hotwords-enabled"]').click();
    await page.locator('label[for="context-enabled"]').click();
    const input = '--terms "Kubernetes"\nC:\\voice\\😀 context';
    await page.locator('#context-text').fill(input);
    await page.locator('#hotwords_upload_id input[type=file]').setInputFiles(path.join(root, 'fixtures/invalid.xlsx'));
    await page.locator('#hotwords_upload_id').getByText('Added', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.locator('#error-panel').waitFor();
    assert.ok((await page.locator('#error-panel').innerText()).includes('The first row must contain text and weight'));
    await page.locator('#hotwords_upload_id input[type=file]').setInputFiles(path.join(root, 'fixtures/words.xlsx'));
    await page.locator('#hotwords_upload_id').getByText('Added', { exact: true }).waitFor();
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.getByRole('button', { name: 'Save settings', exact: true }).waitFor();
    assert.ok((await page.locator('#review').innerText()).includes('1 hotword'));
    await page.evaluate(() => window.scrollTo(0, 850));
    const stickyTop = await page.locator('#review').evaluate(element => element.getBoundingClientRect().top);
    assert.ok(stickyTop >= 90 && stickyTop <= 105, 'Review panel should remain visible while scrolling');
    await page.locator('.language-select').click();
    await page.getByRole('option', { name: '简体中文', exact: true }).click();
    assert.equal(await page.locator('#context-text').inputValue(), input);
    assert.equal(await page.getByRole('button', { name: '保存设置', exact: true }).count(), 0);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(screenshots, 'mobile-dark.png') });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.locator('.language-select').click();
    await page.getByRole('option', { name: 'English', exact: true }).click();
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.route(origin + '/api/confirm', route => route.fulfill({ status: 422, contentType: 'application/json',
      body: JSON.stringify({ ok: false, field: 'confirmation', error: 'Settings changed. Check and preview again.' }) }), { times: 1 });
    await page.getByRole('button', { name: 'Save settings', exact: true }).click();
    await page.locator('#error-panel').waitFor();
    assert.equal(await page.locator('#error-panel').evaluate(element => document.activeElement === element), true);
    await page.getByRole('button', { name: 'Check and preview', exact: true }).click();
    await page.getByRole('button', { name: 'Save settings', exact: true }).click();
    await page.locator('#receipt').waitFor();
    assert.equal(await page.locator('#api-key-value').count(), 0);
    const files = await fs.readdir(path.join(root, '.asr-transcription/.state/jobs'));
    assert.equal(files.length, 1);
    const configuration = await fs.readFile(path.join(root, '.asr-transcription/.state/jobs', files[0], 'config.json'), 'utf8');
    assert.equal(configuration.includes('fixture-ui-key-not-real'), false);
    const config = JSON.parse(configuration) as { execution_authorized: boolean; enhancement: { context: string } };
    assert.equal(config.execution_authorized, false);
    assert.equal(config.enhancement.context, input);
    await page.reload();
    await page.locator('#receipt').waitFor();
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    assert.equal(await page.locator('html').getAttribute('class'), 'dark');
    const storage = await page.evaluate(() => ({ ...localStorage }));
    assert.deepEqual(Object.keys(storage), ['asr-ui-preferences']);
    assert.equal(JSON.stringify(storage).includes('fixture-ui-key-not-real'), false);
    assert.ok(requests.every(request => request.origin === origin));
    assert.equal(requests.filter(request => request.path === '/api/save-api-key').length, 1);
    const actualErrors = errors.filter(message => !message.includes('status of 422'));
    assert.deepEqual(actualErrors, []);
    await context.close();
  } finally { await browser.close(); }
});
