const { test, expect } = require('@playwright/test');
const path = require('path');

const LOGIN_URL = 'file:///' + path.resolve(__dirname, '..', 'public', 'login.html').replace(/\\/g, '/');

test.describe('Login Page - UI & Layout', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL);
  });

  test('page has correct title', async ({ page }) => {
    await expect(page).toHaveTitle('Login Page');
  });

  test('heading is displayed', async ({ page }) => {
    await expect(page.locator('h2')).toHaveText('Login');
    await expect(page.locator('h2')).toBeVisible();
  });

  test('all form elements are present', async ({ page }) => {
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('#loginBtn')).toBeVisible();
    await expect(page.locator('#message')).toBeAttached();
  });

  test('labels are associated with inputs', async ({ page }) => {
    const usernameLabel = page.locator('label[for="username"]');
    const passwordLabel = page.locator('label[for="password"]');
    await expect(usernameLabel).toHaveText('Username');
    await expect(passwordLabel).toHaveText('Password');
    await expect(usernameLabel).toBeVisible();
    await expect(passwordLabel).toBeVisible();
  });

  test('message area is empty on initial load', async ({ page }) => {
    await expect(page.locator('#message')).toHaveText('');
  });

  test('password field masks input', async ({ page }) => {
    await expect(page.locator('#password')).toHaveAttribute('type', 'password');
  });

  test('username field is text type', async ({ page }) => {
    await expect(page.locator('#username')).toHaveAttribute('type', 'text');
  });

  test('both fields are required', async ({ page }) => {
    await expect(page.locator('#username')).toHaveAttribute('required', '');
    await expect(page.locator('#password')).toHaveAttribute('required', '');
  });

  test('login button has correct text and type', async ({ page }) => {
    await expect(page.locator('#loginBtn')).toHaveText('Login');
    await expect(page.locator('#loginBtn')).toHaveAttribute('type', 'submit');
  });

  test('form has correct id', async ({ page }) => {
    await expect(page.locator('#loginForm')).toBeAttached();
  });

  test('tab order is username -> password -> button', async ({ page }) => {
    await page.locator('#username').focus();
    await expect(page.locator('#username')).toBeFocused();
    await page.press('#username', 'Tab');
    await expect(page.locator('#password')).toBeFocused();
    await page.press('#password', 'Tab');
    await expect(page.locator('#loginBtn')).toBeFocused();
  });

});

test.describe('Login Page - Valid Credentials', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL);
  });

  test('shows success message for correct username and password', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Login successful!');
  });

  test('success message is green', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveCSS('color', 'rgb(0, 128, 0)');
  });

  test('success message appears immediately after click', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toBeVisible();
  });

  test('can login by pressing Enter on password field', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    await page.press('#password', 'Enter');
    await expect(page.locator('#message')).toHaveText('Login successful!');
  });

});

test.describe('Login Page - Invalid Credentials', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL);
  });

  test('shows error for wrong username', async ({ page }) => {
    await page.fill('#username', 'wronguser');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('shows error for wrong password', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'wrongpass');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('shows error for both wrong', async ({ page }) => {
    await page.fill('#username', 'foo');
    await page.fill('#password', 'bar');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('error message is red', async ({ page }) => {
    await page.fill('#username', 'user');
    await page.fill('#password', 'wrong');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveCSS('color', 'rgb(255, 0, 0)');
  });

  test('is case-sensitive (Admin not admin)', async ({ page }) => {
    await page.fill('#username', 'Admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('leading space in username fails', async ({ page }) => {
    await page.fill('#username', ' admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('trailing space in password fails', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123 ');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('empty fields blocked by HTML5 validation (no message)', async ({ page }) => {
    const valid = await page.evaluate(() => document.getElementById('loginForm').checkValidity());
    expect(valid).toBe(false);
    await expect(page.locator('#message')).toHaveText('');
  });

  test('empty username only is blocked', async ({ page }) => {
    await page.fill('#username', '');
    await page.fill('#password', 'password123');
    const valid = await page.evaluate(() => document.getElementById('loginForm').checkValidity());
    expect(valid).toBe(false);
  });

  test('empty password only is blocked', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', '');
    const valid = await page.evaluate(() => document.getElementById('loginForm').checkValidity());
    expect(valid).toBe(false);
  });

});

test.describe('Login Page - Edge Cases & Security', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL);
  });

  test('handles very long username', async ({ page }) => {
    await page.fill('#username', 'a'.repeat(1000));
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('handles special characters', async ({ page }) => {
    await page.fill('#username', '!@#$%^&*()_+={}[]|\\:;"\'<>,.?/~`');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('handles SQL injection-like input harmlessly', async ({ page }) => {
    await page.fill('#username', "' OR 1=1 --");
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('handles XSS-like input harmlessly', async ({ page }) => {
    await page.fill('#username', '<script>alert("xss")</script>');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
    const html = await page.locator('#message').innerHTML();
    expect(html).not.toContain('<script>');
  });

  test('handles unicode characters', async ({ page }) => {
    await page.fill('#username', 'admin中文');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('handles whitespace-only input', async ({ page }) => {
    await page.fill('#username', '   ');
    await page.fill('#password', '   ');
    const valid = await page.evaluate(() => document.getElementById('loginForm').checkValidity());
    expect(valid).toBe(true);
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

});

test.describe('Login Page - Behavioral', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(LOGIN_URL);
  });

  test('preventDefault works - no page navigation on submit', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    const urlBefore = page.url();
    await page.click('#loginBtn');
    const urlAfter = page.url();
    expect(urlAfter).toBe(urlBefore);
  });

  test('subsequent submissions overwrite previous message', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'password123');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Login successful!');

    await page.fill('#username', 'bad');
    await page.fill('#password', 'bad');
    await page.click('#loginBtn');
    await expect(page.locator('#message')).toHaveText('Invalid username or password');
  });

  test('message is not displayed before first submission', async ({ page }) => {
    await expect(page.locator('#message')).toHaveText('');
    const count = await page.locator('#message').evaluate(el => el.childNodes.length);
    expect(count).toBe(0);
  });

  test('form can be submitted multiple times', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await page.fill('#username', 'admin');
      await page.fill('#password', 'password123');
      await page.click('#loginBtn');
      await expect(page.locator('#message')).toHaveText('Login successful!');
    }
  });

});
