#!/usr/bin/env node
/**
 * excalidraw-to-png.js — Convert Excalidraw .json to PNG via headless browser
 * 
 * Usage: node excalidraw-to-png.js <input.json> [output.png]
 * 
 * Uploads the JSON to excalidraw.com, opens in embed mode via Puppeteer,
 * and screenshots the canvas to produce a clean PNG.
 * 
 * Requires: puppeteer (npm install puppeteer)
 */
const { execSync } = require('child_process');
const puppeteer = require('puppeteer');
const fs = require('fs');

const inputFile = process.argv[2];
if (!inputFile || !fs.existsSync(inputFile)) {
  console.error('Usage: node excalidraw-to-png.js <input.json> [output.png]');
  process.exit(1);
}

const outputFile = process.argv[3] || inputFile.replace(/\.excalidraw\.json$/i, '.png').replace(/\.json$/i, '.png');

(async () => {
  // Upload to excalidraw.com
  const exportOutput = execSync(`excalidraw export "${inputFile}"`, { encoding: 'utf8' });
  const urlMatch = exportOutput.match(/URL:\s*(\S+)/);
  if (!urlMatch) { console.error('Upload failed'); process.exit(1); }

  const embedUrl = urlMatch[1] + '?embed=1&theme=light';

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200 });
  await page.goto(embedUrl, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('canvas', { timeout: 15000 });
  await new Promise(r => setTimeout(r, 3000));

  await page.screenshot({ path: outputFile, fullPage: true });
  await browser.close();
  console.log(outputFile);
})();
