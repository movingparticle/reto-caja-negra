const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
let m, n = 0;
while ((m = re.exec(html))) {
  const attrs = m[1];
  if (/\bsrc\s*=/.test(attrs)) continue;
  const code = m[2];
  if (!code.trim()) continue;
  n++;
  try {
    new vm.Script(code, { filename: 'inline-' + n + '.js' });
  } catch (e) {
    console.error('SYNTAX ERROR in inline script #' + n + ': ' + e.message);
    console.error(e.stack.split('\n').slice(0, 6).join('\n'));
    process.exit(1);
  }
}
console.log('OK: ' + n + ' inline script blocks parsed without syntax errors');
