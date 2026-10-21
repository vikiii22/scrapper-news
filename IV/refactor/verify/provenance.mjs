import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import * as acorn from 'acorn';

const SITE = 'https://web.tulotero.es/';
const LOCAL = fileURLToPath(new URL('../../tulotero-chunk.js', import.meta.url));

const IGNORE = new Set(['start', 'end', 'raw', 'loc', 'range']);
const clean = (node) => {
  if (Array.isArray(node)) return node.map(clean);
  if (node && typeof node === 'object') {
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      if (!IGNORE.has(key)) out[key] = clean(value);
    }
    return out;
  }
  return node;
};

const parse = (code) =>
  clean(acorn.parse(code, { ecmaVersion: 'latest', sourceType: 'module', allowHashBang: true }));

const html = await fetch(SITE).then((response) => {
  if (!response.ok) throw new Error(`No se pudo cargar ${SITE}: HTTP ${response.status}`);
  return response.text();
});

const mainMatch = html.match(/<script[^>]+src="(main-[A-Z0-9]+\.js)"/);
if (!mainMatch) throw new Error('No se encontró el bundle main-*.js en web.tulotero.es');

const liveUrl = new URL(mainMatch[1], SITE).href;
const liveCode = await fetch(liveUrl).then((response) => {
  if (!response.ok) throw new Error(`No se pudo cargar ${liveUrl}: HTTP ${response.status}`);
  return response.text();
});
const localCode = await readFile(LOCAL, 'utf8');

const equal = isDeepStrictEqual(parse(localCode), parse(liveCode));

console.log(`local : ${LOCAL}`);
console.log(`live  : ${liveUrl}`);
console.log(`bytes : local=${localCode.length} live=${liveCode.length}`);
console.log(`AST_EQUAL ${equal}`);

for (const marker of [
  'X-Token-Expired',
  'no_verificado',
  'verificationBrowserNeeded',
  'device_verification_complete',
  'landing_play',
]) {
  console.log(`MARKER ${marker} local=${localCode.includes(marker)} live=${liveCode.includes(marker)}`);
}

if (!equal) {
  console.error('\nDRIFT: el chunk local ya no coincide con el build publicado por Tulotero.');
  process.exit(1);
}
