const { chromium } = require('playwright');
const path = require('path');

async function triggerExports() {
  const userDataDir = path.join(process.env.HOME, '.omega-browser-context');
  const headless = process.env.OMEGA_HEADLESS === 'true';
  
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless,
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  console.log("Navigating to Meta Accounts Center...");
  await page.goto('https://accountscenter.facebook.com/your_information_and_permissions');
  
  try {
    await page.click('text="Download your information"');
    console.log("Action required: Select accounts and 'All available information' in the browser.");
  } catch (e) {
    console.log("Meta export path failed or requires manual login.");
  }

  console.log("Navigating to LinkedIn Data Privacy...");
  await page.goto('https://www.linkedin.com/mypreferences/d/download-my-data');
  
  try {
    await page.check('input[value="full_archive"]');
    await page.click('button:has-text("Request archive")');
    console.log("LinkedIn archive requested.");
  } catch (e) {
    console.log("LinkedIn request button not found. Check if an export is already pending.");
  }

  console.log("Automation task complete.");
  await page.waitForTimeout(60000); 
  await context.close();
}

triggerExports();
