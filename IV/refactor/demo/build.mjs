import { build, context } from 'esbuild';
import { copyFile, mkdir } from 'node:fs/promises';

const serve = process.argv.includes('--serve');

await mkdir('demo/dist', { recursive: true });
await copyFile('demo/index.html', 'demo/dist/index.html');

const options = {
  entryPoints: ['demo/main.ts'],
  bundle: true,
  outfile: 'demo/dist/bundle.js',
  format: 'esm',
  platform: 'browser',
  target: 'es2022',
  sourcemap: true,
  tsconfig: 'tsconfig.json',
  define: { 'process.env.NODE_ENV': '"development"' },
  logLevel: 'info',
};

if (serve) {
  const ctx = await context(options);
  await ctx.watch();
  const server = await ctx.serve({ servedir: 'demo/dist', port: 4200 });
  console.log(`Demo: http://localhost:${server.port}`);
} else {
  await build(options);
}
