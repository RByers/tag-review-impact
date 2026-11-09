import type { Plugin } from 'vite';
import { defineConfig } from 'vitest/config';
import { lowerTestPriority } from './test-priority.ts';

// Tests run at nice +5 relative to the caller (~/.claude/CLAUDE.md). VITEST is set before vitest
// loads this file; workers that re-import it have VITEST_WORKER_ID and must not lower it again.
if (process.env.VITEST && !process.env.VITEST_WORKER_ID) lowerTestPriority();

// Ports: see argus-config/ports.md. USER_PORT is forwarded to the user's laptop over SSH, and
// only `vite preview` (`npm run serve`) uses it. The dev server always gets a random port in
// 20000-39999. Preview started by Claude Code (CLAUDECODE=1) gets a random port too, unless
// DEV_PORT=user. Never use port 0: Vite treats it as unset and falls back to 5173.
const USER_PORT = 5184;
const forUser = !process.env.CLAUDECODE || process.env.DEV_PORT === 'user';
const randomPort = () => ({ port: 20000 + Math.floor(Math.random() * 20000), strictPort: false });

/** The Content Security Policy every built page carries (SECURITY.md). */
export const CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "connect-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "require-trusted-types-for 'script'",
  "trusted-types 'none'",
].join('; ');

const csp = (): Plugin => ({
  name: 'tag-review-impact-csp',
  apply: 'build',
  transformIndexHtml(html, { filename }) {
    const charset = '<meta charset="utf-8" />';
    if (!html.includes(charset)) throw new Error(`${filename}: no ${charset} to put the CSP after`);
    return html.replace(charset, `${charset}\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`);
  },
});

export default defineConfig({
  plugins: [csp()],
  base: './',
  // data/public/ holds only what the dashboard shows; it is copied into dist/ as-is.
  publicDir: '../data/public',
  server: {
    host: 'localhost',
    ...randomPort(),
    fs: {
      allow: ['.', '../data/public'],
      deny: ['.env', '.env.*', '*.{crt,pem,key,p12,pfx,cer,der}', '.npmrc', '**/.git/**', 'secrets*',
             '**/data/private/**'],
    },
  },
  preview: { host: 'localhost', ...(forUser ? { port: USER_PORT, strictPort: true } : randomPort()) },
  build: { outDir: 'dist', emptyOutDir: true, assetsInlineLimit: 0 },
  test: {
    include: ['test/**/*.test.ts'],
    environment: 'node',
    // Shared machine: never more than 4 test workers (~/.claude/CLAUDE.md).
    maxWorkers: 4,
  },
});
