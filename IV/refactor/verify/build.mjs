import { build } from 'esbuild';

await build({
  entryPoints: ['verify/live-matches.ts'],
  bundle: true,
  outfile: 'verify/dist/live-matches.mjs',
  format: 'esm',
  platform: 'node',
  target: 'node20',
  sourcemap: false,
  tsconfig: 'tsconfig.json',
  logLevel: 'info',
});
