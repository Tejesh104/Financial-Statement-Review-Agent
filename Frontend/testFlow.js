// testFlow.js
import puppeteer from 'puppeteer';
(async () => {
  const launchOptions = {headless: true, args: ['--no-sandbox']};
if (process.platform === 'win32') {
  launchOptions.executablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
}
const browser = await puppeteer.launch(launchOptions);
  const page = await browser.newPage();
  const base = 'http://localhost:5173';
  const waitForUrl = async (expected, timeout = 5000) => {
    await page.waitForFunction(url => location.href.includes(url), {}, expected);
    const url = page.url();
    return url.includes(expected);
  };
  // Fresh session
  await page.goto(base, {waitUntil: 'networkidle2'});
  await page.waitForSelector('canvas', {timeout: 5000});
  const toLogin = await waitForUrl('/login');
  console.log('Splash -> Login:', toLogin ? 'PASS' : 'FAIL');
  const loginForm = await page.$('form');
  console.log('Login page form present:', loginForm ? 'PASS' : 'FAIL');
  await page.type('input[type="email"]', 'test@example.com');
  await page.type('input[type="password"]', 'password');
  await page.click('button[type="submit"]');
  const toDashboard = await waitForUrl('/dashboard');
  console.log('Login -> Dashboard:', toDashboard ? 'PASS' : 'FAIL');
  const logoutBtn = await page.$x("//button[contains(., 'Logout')]");
  if (logoutBtn.length > 0) {
    await logoutBtn[0].click();
    await page.waitForNavigation({waitUntil: 'networkidle2'});
    console.log('Logout action:', 'PASS');
  } else {
    console.log('Logout button not found: SKIP');
  }
  // Authenticated reload
  await page.evaluate(() => {
    localStorage.setItem('finny_token', 'dummy');
  });
  await page.reload({waitUntil: 'networkidle2'});
  const autoDashboard = await waitForUrl('/dashboard');
  console.log('Authenticated startup -> Dashboard:', autoDashboard ? 'PASS' : 'FAIL');
  await browser.close();
})();
