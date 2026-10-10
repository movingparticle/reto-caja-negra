import { cpSync, mkdirSync, rmSync, existsSync, readdirSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';

const ROOT_DIR = resolve('.');
const DIST_DIR = resolve('dist');

console.log('Building dist directory for Cloudflare Pages deployment...');

// Recreate dist
if (existsSync(DIST_DIR)) {
  rmSync(DIST_DIR, { recursive: true, force: true });
}
mkdirSync(DIST_DIR, { recursive: true });

// Files to copy directly to dist
const rootFiles = [
  'index.html',
  'design-doc.html',
  'DESIGN_DOC.html',
  'architecture.html',
  'architecture.mmd',
  'LOG.html',
  '.nojekyll'
];

for (const file of rootFiles) {
  const src = join(ROOT_DIR, file);
  if (existsSync(src)) {
    cpSync(src, join(DIST_DIR, file));
    console.log(`  ✓ Copied ${file}`);
  }
}

// Copy directories
const dirsToCopy = ['assets', 'en'];

for (const dir of dirsToCopy) {
  const srcDir = join(ROOT_DIR, dir);
  if (existsSync(srcDir)) {
    const destDir = join(DIST_DIR, dir);
    cpSync(srcDir, destDir, { recursive: true });
    console.log(`  ✓ Copied directory ${dir}/`);
  }
}

// Also ensure en/design-doc.html exists in dist for clean alias
const enIndex = join(DIST_DIR, 'en', 'index.html');
const enDesignDoc = join(DIST_DIR, 'en', 'design-doc.html');
if (existsSync(enIndex) && !existsSync(enDesignDoc)) {
  cpSync(enIndex, enDesignDoc);
  console.log(`  ✓ Created en/design-doc.html alias`);
}

// Verification
function listFiles(dir, prefix = '') {
  const entries = readdirSync(dir);
  for (const entry of entries) {
    const fullPath = join(dir, entry);
    const relPath = prefix ? `${prefix}/${entry}` : entry;
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      listFiles(fullPath, relPath);
    } else {
      console.log(`    dist/${relPath} (${stat.size} bytes)`);
    }
  }
}

console.log('\nDist contents:');
listFiles(DIST_DIR);
console.log('\nBuild complete! Ready for wrangler pages deploy dist.');
