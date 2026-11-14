import { cp, mkdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const publish = path.join(root, 'public');
await mkdir(publish, {recursive: true});

for (const file of ['index.html', 'detail.html', 'playground.html', 'console.html', 'styles.css', 'console.css', 'app.js', 'detail.js', 'playground.js', 'console.js', '_headers', 'README.md', 'LICENSE']) {
  await copyFile(path.join(root, file), path.join(publish, file));
}
await cp(path.join(root, 'assets'), path.join(publish, 'assets'), {recursive: true, force: true});
await cp(path.join(root, 'downloads'), path.join(publish, 'downloads'), {recursive: true, force: true});
console.log(`Prepared Netlify publish directory: ${publish}`);
