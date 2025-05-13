/**
 * Code Story GUI Automated Demo
 * This script uses Playwright to run an automated demonstration of the Code Story GUI
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuration
const demoConfig = {
  baseUrl: 'http://localhost:5173',
  slowMo: 1000, // Slow down actions for better visibility
  demoRepo: '/path/to/demo/repo', // Path to demo repository
  narrativesPath: path.join(__dirname, 'narratives'),
  screenshotsPath: path.join(__dirname, 'screenshots'),
};

// Create directories if they don't exist
if (!fs.existsSync(demoConfig.screenshotsPath)) {
  fs.mkdirSync(demoConfig.screenshotsPath, { recursive: true });
}

// Load narratives
const narratives = {
  welcome: fs.readFileSync(path.join(demoConfig.narrativesPath, 'welcome.txt'), 'utf8'),
  configuration: fs.readFileSync(path.join(demoConfig.narrativesPath, 'configuration.txt'), 'utf8'),
  ingestion: fs.readFileSync(path.join(demoConfig.narrativesPath, 'ingestion.txt'), 'utf8'),
  graph: fs.readFileSync(path.join(demoConfig.narrativesPath, 'graph.txt'), 'utf8'),
  ask: fs.readFileSync(path.join(demoConfig.narrativesPath, 'ask.txt'), 'utf8'),
  mcp: fs.readFileSync(path.join(demoConfig.narrativesPath, 'mcp.txt'), 'utf8'),
};

// Function to display narrative and take screenshot
async function showNarrativeAndScreenshot(page, narrativeText, screenshotName) {
  // Add narrative overlay
  await page.evaluate((text) => {
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.bottom = '20px';
    overlay.style.left = '20px';
    overlay.style.right = '20px';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    overlay.style.color = 'white';
    overlay.style.padding = '20px';
    overlay.style.borderRadius = '10px';
    overlay.style.zIndex = '10000';
    overlay.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    overlay.style.maxHeight = '30%';
    overlay.style.overflow = 'auto';
    overlay.style.fontFamily = 'Arial, sans-serif';
    overlay.style.fontSize = '16px';
    overlay.style.lineHeight = '1.5';
    overlay.innerHTML = `<p>${text.replace(/\n/g, '<br>')}</p>`;
    
    // Add to body
    document.body.appendChild(overlay);
    
    // Store reference for later removal
    window._narrativeOverlay = overlay;
  }, narrativeText);
  
  // Wait a moment for the overlay to be visible
  await page.waitForTimeout(1000);
  
  // Take screenshot
  await page.screenshot({ 
    path: path.join(demoConfig.screenshotsPath, `${screenshotName}.png`),
    fullPage: false 
  });
  
  // Wait for user to press any key to continue
  await page.waitForTimeout(5000);
  
  // Remove narrative overlay
  await page.evaluate(() => {
    if (window._narrativeOverlay) {
      window._narrativeOverlay.remove();
      delete window._narrativeOverlay;
    }
  });
}

// Main demo function
async function runDemo() {
  console.log('Starting Code Story GUI Demo...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: demoConfig.slowMo
  });
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // 1. Welcome screen
    await page.goto(demoConfig.baseUrl);
    await showNarrativeAndScreenshot(
      page, 
      narratives.welcome,
      '01-welcome'
    );
    
    // 2. Configuration
    await page.goto(`${demoConfig.baseUrl}/config`);
    await showNarrativeAndScreenshot(
      page, 
      narratives.configuration,
      '02-configuration'
    );
    
    // Fill configuration form
    await page.fill('input[name="neo4j.uri"]', 'bolt://localhost:7687');
    await page.fill('input[name="neo4j.username"]', 'neo4j');
    await page.fill('input[name="neo4j.password"]', 'password');
    await page.fill('input[name="neo4j.database"]', 'codestory');
    
    await page.screenshot({ 
      path: path.join(demoConfig.screenshotsPath, '02b-configuration-filled.png'),
      fullPage: false 
    });
    
    // 3. Ingestion
    await page.goto(`${demoConfig.baseUrl}/ingest`);
    await showNarrativeAndScreenshot(
      page, 
      narratives.ingestion,
      '03-ingestion'
    );
    
    // Fill ingestion form
    await page.fill('input[name="repositoryPath"]', demoConfig.demoRepo);
    
    await page.screenshot({ 
      path: path.join(demoConfig.screenshotsPath, '03b-ingestion-filled.png'),
      fullPage: false 
    });
    
    // 4. Graph visualization
    await page.goto(`${demoConfig.baseUrl}/graph`);
    await showNarrativeAndScreenshot(
      page, 
      narratives.graph,
      '04-graph'
    );
    
    // 5. Ask questions
    await page.goto(`${demoConfig.baseUrl}/ask`);
    await showNarrativeAndScreenshot(
      page, 
      narratives.ask,
      '05-ask'
    );
    
    // Fill query input
    await page.fill('textarea[placeholder="Ask a question about your code..."]', 'What are the main components of the system?');
    
    await page.screenshot({ 
      path: path.join(demoConfig.screenshotsPath, '05b-ask-question.png'),
      fullPage: false 
    });
    
    // 6. MCP playground
    await page.goto(`${demoConfig.baseUrl}/mcp`);
    await showNarrativeAndScreenshot(
      page, 
      narratives.mcp,
      '06-mcp'
    );
    
    // Demo complete
    await showNarrativeAndScreenshot(
      page, 
      "Demo complete! Thank you for exploring Code Story.",
      '07-complete'
    );
    
  } catch (error) {
    console.error('Error during demo:', error);
  } finally {
    await browser.close();
    console.log('Demo completed.');
    console.log(`Screenshots saved to: ${demoConfig.screenshotsPath}`);
  }
}

// Run the demo if script is executed directly
if (require.main === module) {
  runDemo().catch(console.error);
}

module.exports = { runDemo };