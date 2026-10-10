import { cpSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';

const DIST_DIR = resolve('dist');
const DEMO_DIST_DIR = resolve('dist-demo');

console.log('Building dist-demo for Cloudflare Pages (caja-negra-demo)...');

if (existsSync(DEMO_DIST_DIR)) {
  rmSync(DEMO_DIST_DIR, { recursive: true, force: true });
}
mkdirSync(DEMO_DIST_DIR, { recursive: true });

// Copy everything from dist to dist-demo
cpSync(DIST_DIR, DEMO_DIST_DIR, { recursive: true });

// Overwrite index.html with demo.html so the root is the interactive demo
const demoSrc = join(DEMO_DIST_DIR, 'demo.html');
const indexDest = join(DEMO_DIST_DIR, 'index.html');
if (existsSync(demoSrc)) {
  cpSync(demoSrc, indexDest);
  console.log('  ✓ Set index.html -> demo.html for caja-negra-demo root');
}

console.log('dist-demo build complete!');
