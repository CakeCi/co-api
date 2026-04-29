const { chromium } = require('playwright');

(async () => {
  console.log('Starting browser test via backend proxy...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  
  try {
    // Test 1: Login Page (via backend)
    console.log('[1/6] Testing Login page...');
    await page.goto('http://127.0.0.1:3000/static/#/login', { timeout: 10000, waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '../../screenshots/01-login.png' });
    
    const loginInputs = await page.$$('input');
    const loginBtn = await page.$('button');
    results.push({
      page: 'Login',
      status: loginInputs.length >= 2 && loginBtn ? 'OK' : 'ERROR',
      inputs: loginInputs.length,
      hasButton: !!loginBtn
    });
    console.log(`    ${results[results.length-1].status} - Inputs: ${loginInputs.length}`);
    
    // Test 2: Login and Dashboard
    console.log('[2/6] Testing Login + Dashboard...');
    if (loginInputs.length >= 2) {
      await loginInputs[0].fill('admin');
      await loginInputs[1].fill('Admin@1234');
      await loginBtn.click();
      await page.waitForTimeout(3000);
    }
    
    await page.screenshot({ path: '../../screenshots/02-dashboard.png' });
    const sidebar = await page.$('aside');
    const title = await page.title().catch(() => 'Unknown');
    
    results.push({
      page: 'Dashboard',
      status: sidebar ? 'OK' : 'ERROR',
      title: title,
      hasSidebar: !!sidebar
    });
    console.log(`    ${results[results.length-1].status} - Title: ${title}`);
    
    // Test 3: Channels
    console.log('[3/6] Testing Channels...');
    await page.goto('http://127.0.0.1:3000/static/#/channels', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '../../screenshots/03-channels.png' });
    
    const table = await page.$('table');
    results.push({
      page: 'Channels',
      status: table ? 'OK' : 'ERROR',
      hasTable: !!table
    });
    console.log(`    ${results[results.length-1].status} - Has table: ${!!table}`);
    
    // Test 4: Tokens
    console.log('[4/6] Testing Tokens...');
    await page.goto('http://127.0.0.1:3000/static/#/tokens', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '../../screenshots/04-tokens.png' });
    
    const tokensTable = await page.$('table');
    results.push({
      page: 'Tokens',
      status: tokensTable ? 'OK' : 'ERROR',
      hasTable: !!tokensTable
    });
    console.log(`    ${results[results.length-1].status}`);
    
    // Test 5: Pools
    console.log('[5/6] Testing Pools...');
    await page.goto('http://127.0.0.1:3000/static/#/pools', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '../../screenshots/05-pools.png' });
    
    const poolsTable = await page.$('table');
    results.push({
      page: 'Pools',
      status: poolsTable ? 'OK' : 'ERROR',
      hasTable: !!poolsTable
    });
    console.log(`    ${results[results.length-1].status}`);
    
    // Test 6: Logs
    console.log('[6/6] Testing Logs...');
    await page.goto('http://127.0.0.1:3000/static/#/logs', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '../../screenshots/06-logs.png' });
    
    const logsTable = await page.$('table');
    const pagination = await page.$('text=上一页') || await page.$('text=下一页');
    results.push({
      page: 'Logs',
      status: logsTable ? 'OK' : 'ERROR',
      hasTable: !!logsTable,
      hasPagination: !!pagination
    });
    console.log(`    ${results[results.length-1].status} - Pagination: ${!!pagination}`);
    
  } catch (error) {
    console.error('\nTest error:', error.message);
    results.push({ page: 'General', status: 'ERROR', error: error.message });
  } finally {
    await browser.close();
  }
  
  // Summary
  console.log('\n=== Frontend Verification Results ===');
  const allOK = results.every(r => r.status === 'OK');
  results.forEach(r => {
    const icon = r.status === 'OK' ? 'v' : 'x';
    console.log(`[${icon}] ${r.page}: ${r.status}`);
  });
  
  if (allOK) {
    console.log('\nAll tests PASSED');
  } else {
    console.log('\nSome tests FAILED');
    process.exit(1);
  }
})();
