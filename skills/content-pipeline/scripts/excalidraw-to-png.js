#!/usr/bin/env node
/**
 * excalidraw-to-png.js — Convert Excalidraw .json to PNG
 * Uploads to excalidraw.com, screenshots with Puppeteer (headless Chrome)
 * 
 * Usage: node excalidraw-to-png.js <input.json> [output.png]
 * 
 * Prerequisites:
 *   npm install -g excalidraw-cli     (for `excalidraw export`)
 *   npm install puppeteer             (headless browser)
 * 
 * The excalidraw JSON must already exist and be valid.
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
  const out = execSync(`excalidraw export "${inputFile}"`, { encoding: 'utf8' });
  const m = out.match(/URL:\s*(\S+)/);
  if (!m) { console.error('Upload failed'); process.exit(1); }
  const url = m[1] + '?embed=1&theme=light';

  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200 });
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('canvas', { timeout: 15000 });
  await new Promise(r => setTimeout(r, 3000));

  await page.screenshot({ path: outputFile, fullPage: true });
  console.error(`Saved: ${outputFile}`);
  await browser.close();
  console.log(outputFile);
})();
