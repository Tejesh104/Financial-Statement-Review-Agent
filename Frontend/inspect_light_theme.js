import puppeteer from 'puppeteer';

(async () => {
  const launchOptions = {
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  };
  if (process.platform === 'win32') {
    launchOptions.executablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  }
  const browser = await puppeteer.launch(launchOptions);
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const issues = [];

  const pagesToTest = [
    { name: 'Landing Page', url: 'http://localhost:5173/' },
    { name: 'Login Page', url: 'http://localhost:5173/login' },
    { name: 'Signup Page', url: 'http://localhost:5173/signup' },
    { name: 'Dashboard', url: 'http://localhost:5173/dashboard', auth: true },
    { name: 'Upload', url: 'http://localhost:5173/upload', auth: true },
    { name: 'Verification', url: 'http://localhost:5173/verification', auth: true },
    { name: 'Agent Processing', url: 'http://localhost:5173/agent-processing', auth: true },
    { name: 'Analysis', url: 'http://localhost:5173/analysis', auth: true },
    { name: 'Risk', url: 'http://localhost:5173/risk', auth: true },
    { name: 'Reports', url: 'http://localhost:5173/reports', auth: true },
    { name: 'History', url: 'http://localhost:5173/history', auth: true },
    { name: 'Settings', url: 'http://localhost:5173/settings', auth: true },
  ];

  // Helper to set light theme
  const enableLightTheme = async () => {
    await page.evaluate(() => {
      localStorage.setItem('finny_theme', 'light');
      localStorage.setItem('finny-theme', 'light');
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      document.body.classList.remove('dark');
      document.body.classList.add('light');
    });
  };

  // Helper to authenticate
  const setAuth = async () => {
    await page.evaluate(() => {
      const demoUser = {
        id: 'analyst-1',
        email: 'analyst@finny.com',
        full_name: 'Alex Morgan, CPA',
        role: 'Senior Financial Analyst',
        auth_provider: 'local',
      };
      localStorage.setItem('fsra_token', 'demo_token_test');
      localStorage.setItem('fsra_user', JSON.stringify(demoUser));
      sessionStorage.setItem('fsra_token', 'demo_token_test');
      sessionStorage.setItem('fsra_user', JSON.stringify(demoUser));
    });
  };

  for (const p of pagesToTest) {
    console.log(`\nChecking ${p.name} in LIGHT THEME...`);
    await page.goto(p.url, { waitUntil: 'networkidle2' });
    if (p.auth) {
      await setAuth();
      await page.goto(p.url, { waitUntil: 'networkidle2' });
    }
    await enableLightTheme();
    await new Promise(r => setTimeout(r, 600));

    // Inspect elements on page
    const pageIssues = await page.evaluate((pageName) => {
      const detected = [];
      const allElements = Array.from(document.querySelectorAll('*'));

      for (const el of allElements) {
        // Skip hidden, scripts, styles
        if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'SVG' || el.tagName === 'PATH') continue;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

        const bg = style.backgroundColor;
        const color = style.color;

        // Check for pure white block with area > 1000px that might look like an unstyled harsh white patch
        const rect = el.getBoundingClientRect();
        const area = rect.width * rect.height;

        // Check if pure solid white (rgb(255, 255, 255)) is used on large containers
        if (area > 8000 && (bg === 'rgb(255, 255, 255)' || bg === '#ffffff' || bg === '#fff')) {
          detected.push({
            page: pageName,
            tag: el.tagName,
            class: el.className,
            issue: 'Harsh solid pure-white large container: ' + area + 'px',
            bg,
          });
        }

        // Check contrast: dark background leaking into light theme with dark text
        // or light text on light background
        function parseRgb(str) {
          const match = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
          if (!match) return null;
          return {
            r: parseInt(match[1]),
            g: parseInt(match[2]),
            b: parseInt(match[3]),
            a: match[4] !== undefined ? parseFloat(match[4]) : 1.0,
          };
        }

        const textColor = parseRgb(color);
        const bgColor = parseRgb(bg);

        // Dark leak: background is dark (r<40, g<40, b<50, a>0.7) and text is dark (r<50, g<50, b<50) -> unreadable dark-on-dark!
        if (bgColor && bgColor.a > 0.5 && bgColor.r < 30 && bgColor.g < 35 && bgColor.b < 45) {
          if (textColor && textColor.r < 70 && textColor.g < 70 && textColor.b < 80) {
            detected.push({
              page: pageName,
              tag: el.tagName,
              class: el.className,
              issue: 'Dark-on-dark text (dark leak): bg=' + bg + ' text=' + color,
              text: el.innerText?.substring(0, 40),
            });
          }
        }

        // Light leak: background is light (r>200, g>200, b>200) and text is white/light (r>230, g>230, b>230)
        if (bgColor && bgColor.a > 0.5 && bgColor.r > 190 && bgColor.g > 190 && bgColor.b > 210) {
          if (textColor && textColor.r > 230 && textColor.g > 230 && textColor.b > 230) {
            detected.push({
              page: pageName,
              tag: el.tagName,
              class: el.className,
              issue: 'White-on-light text (unreadable): bg=' + bg + ' text=' + color,
              text: el.innerText?.substring(0, 40),
            });
          }
        }
      }

      return detected;
    }, p.name);

    if (pageIssues.length > 0) {
      console.log(`Found ${pageIssues.length} issues on ${p.name}:`);
      console.log(JSON.stringify(pageIssues.slice(0, 5), null, 2));
      issues.push(...pageIssues);
    } else {
      console.log(`Clean: 0 visual issues detected on ${p.name}`);
    }
  }

  // Also check Chatbot drawer in light mode
  console.log('\nChecking Chatbot in LIGHT THEME...');
  await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle2' });
  await enableLightTheme();
  const botBtn = await page.$('.finny-assistant button');
  if (botBtn) {
    await botBtn.click();
    await new Promise(r => setTimeout(r, 600));

    const botIssues = await page.evaluate(() => {
      const panel = document.querySelector('.finny-assistant-panel');
      if (!panel) return ['Panel not found'];
      const style = window.getComputedStyle(panel);
      return {
        panelBg: style.backgroundColor,
        panelColor: style.color,
        inputs: Array.from(panel.querySelectorAll('input, button')).map(el => ({
          tag: el.tagName,
          bg: window.getComputedStyle(el).backgroundColor,
          color: window.getComputedStyle(el).color,
        }))
      };
    });
    console.log('Chatbot panel light styles:', JSON.stringify(botIssues, null, 2));
  }

  await browser.close();

  console.log(`\nTotal potential issues detected across all pages: ${issues.length}`);
})();
