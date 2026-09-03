#!/usr/bin/env node
// Scripted dark-mode README tour: drives the standalone-HTML scenes in
// docs/tour/ (written by emit-tour-html.py) in headless Chromium and captures
// PNG stills + WebM video + an animated GIF per the docs-tour pipeline.
//
// Run: node scripts/capture-tour.mjs   (after uv run python scripts/emit-tour-html.py)
// No build step — plain ESM, playwright resolved from the npx cache.
// Known pixel-check requirement: Chromium must run with --no-sandbox.

import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOUR = path.join(ROOT, "docs", "tour");
const WIDTH = 1264;
const HEIGHT = 640;
const SCENES = ["dark", "boxes", "bundle", "rrg"]; // README order
const STAY_MS = 5000; // time each scene is on screen

const require_ = createRequire(import.meta.url);

function loadPlaywright() {
  try {
    return require_("playwright");
  } catch {
    const npxRoot = path.join(os.homedir(), ".npm", "_npx");
    for (const dir of fs.existsSync(npxRoot) ? fs.readdirSync(npxRoot) : []) {
      const p = path.join(npxRoot, dir, "node_modules", "playwright");
      if (fs.existsSync(p)) return require_(p);
    }
  }
  throw new Error("playwright not found — run: npx -y playwright@1.62.1 install chromium");
}

const { chromium } = loadPlaywright();

// Ink gate: wait until the chart actually painted (sum of non-transparent
// canvas pixels), mirroring the smoke-check gates used for RRG.
const inkExpr = `(() => {
  let ink = 0;
  for (const c of document.querySelectorAll("canvas")) {
    const ctx = c.getContext("2d");
    if (!ctx) continue;
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 16) ink++;
  }
  return ink;
})()`;

const videoDir = fs.mkdtempSync(path.join(os.tmpdir(), "klinepy-tour-"));
const browser = await chromium.launchPersistentContext(path.join(videoDir, "profile"), {
  viewport: { width: WIDTH, height: HEIGHT },
  deviceScaleFactor: 2, // README stills are @2x
  recordVideo: { dir: videoDir, size: { width: WIDTH, height: HEIGHT } },
  args: ["--no-sandbox"],
});

const webms = [];
try {
  for (const scene of SCENES) {
    const file = path.join(TOUR, `${scene}.html`);
    if (!fs.existsSync(file)) throw new Error(`missing scene ${file} — run emit-tour-html.py`);
    const page = await browser.newPage();
    page.on("pageerror", (e) => console.warn(`[${scene}] pageerror:`, e.message));
    await page.goto(`file://${file}`);
    await page.waitForFunction(inkExpr, null, { timeout: 30_000 });
    await page.waitForTimeout(STAY_MS);
    await page.screenshot({ path: path.join(TOUR, `tour-${scene}.png`) });
    const video = page.video();
    await page.close();
    webms.push(path.join(videoDir, `${scene}.webm`));
    fs.renameSync(await video.path(), webms.at(-1));
    console.log(`captured ${scene}`);
  }
} finally {
  await browser.close();
}

// One WebM from all scenes (same codec/size → stream copy).
const list = path.join(videoDir, "list.txt");
fs.writeFileSync(list, webms.map((w) => `file '${w}'`).join("\n"));
const ffmpeg = (args) => execFileSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args]);
ffmpeg(["-f", "concat", "-safe", "0", "-i", list, "-t", String((STAY_MS * webms.length) / 1000), "-c", "copy", path.join(TOUR, "tour.webm")]);

// Animated GIF from the stills (palettegen for sane colors, half-res).
const stills = SCENES.map((s) => path.join(TOUR, `tour-${s}.png`));
const inputs = stills.flatMap((f) => ["-loop", "1", "-t", String(STAY_MS / 1000), "-i", f]);
const n = SCENES.length;
ffmpeg([
  ...inputs,
  "-filter_complex",
  `${SCENES.map((_, i) => `[${i}:v]`).join("")}concat=n=${n}:v=1,` +
    "fps=10,scale=1264:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer",
  path.join(TOUR, "tour.gif"),
]);

fs.rmSync(list);
console.log(`done — PNG stills, tour.webm (${(STAY_MS * n) / 1000}s), tour.gif in ${TOUR}`);
