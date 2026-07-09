# Playwright Guide — Reference for Future Projects

## Project Structure

```
your-project/
├── public/                  # Static HTML files
│   └── login.html           # Example: a login page to test
├── tests/                   # All Playwright test files
│   └── login.spec.js        # Example: tests for login.html
├── test-results/            # Auto-generated test output (screenshots, traces on failure)
├── playwright.config.js     # Playwright configuration
├── package.json             # Dependencies & scripts
├── package-lock.json        # Auto-generated — locks dependency versions
└── node_modules/            # Installed packages
```

## Setup (for a new project)

```bash
npm init -y
npm install --save-dev @playwright/test
npx playwright install chromium
```

## Playwright Config (`playwright.config.js`)

```js
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',        // folder containing test files
  timeout: 30000,            // per-test timeout (ms)
  use: { headless: true },   // false to see the browser
});
```

## Writing Tests

Tests use `describe` blocks to group and `test` for individual cases.

```js
const { test, expect } = require('@playwright/test');
const path = require('path');

// For local HTML files (no server needed):
const URL = 'file:///' + path.resolve(__dirname, '..', 'public', 'file.html').replace(/\\/g, '/');

test.describe('Group Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
  });

  test('test description', async ({ page }) => {
    await page.fill('#inputId', 'value');
    await page.click('#buttonId');
    await expect(page.locator('#outputId')).toHaveText('expected');
  });
});
```

## Common Playwright Commands

| Action | Code |
|---|---|
| Navigate | `await page.goto(url)` |
| Fill input | `await page.fill('#id', 'text')` |
| Click | `await page.click('#id')` |
| Select option | `await page.selectOption('#id', 'value')` |
| Press key | `await page.press('#id', 'Enter')` |
| Check text | `await expect(locator).toHaveText('text')` |
| Check CSS | `await expect(locator).toHaveCSS('color', 'rgb(r, g, b)')` |
| Check visible | `await expect(locator).toBeVisible()` |
| Check attribute | `await expect(locator).toHaveAttribute('attr', 'value')` |
| Check attached | `await expect(locator).toBeAttached()` |
| Run JS | `await page.evaluate(() => { ... })` |

## Running Tests

```bash
npm test                         # headless mode (default)
npx playwright test --headed     # visible browser
npx playwright test --ui         # interactive UI mode
npx playwright test tests/login.spec.js   # single file
npx playwright test --grep "UI"          # tests matching "UI"
```

## Key Notes

- **No server needed** for static HTML — use `file:///` path in tests.
- **`beforeEach`** runs before every test in the `describe` block — keeps tests isolated.
- Use **`toBeAttached()`** instead of `toBeVisible()` for empty elements like `<div id="message"></div>`.
- For **server-based apps**, add a `webServer` block in `playwright.config.js`.
- Test files must end with `.spec.js` or `.spec.ts`.
