import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { commentUrl, featureUrl, issueFromHash, issueUrl, safeLink } from '../src/links.ts';

const src = fileURLToPath(new URL('../src/', import.meta.url));

describe('no HTML or code sinks (SECURITY.md)', () => {
  const SINKS = /\b(innerHTML|outerHTML|insertAdjacentHTML|document\.write|DOMParser|srcdoc|eval\s*\(|new Function|setHTML|createContextualFragment)\b/;
  for (const f of readdirSync(src).filter((f) => f.endsWith('.ts'))) {
    it(f, () => {
      expect(readFileSync(src + f, 'utf8')).not.toMatch(SINKS);
    });
  }
  it('index.html has no inline script, style or handlers', () => {
    const html = readFileSync(fileURLToPath(new URL('../index.html', import.meta.url)), 'utf8');
    expect(html).not.toMatch(/<script(?![^>]*\bsrc=)/);
    expect(html).not.toMatch(/<style|\son[a-z]+=|style="/i);
  });
});

describe('link builders', () => {
  it('build fixed-prefix links from integers only', () => {
    expect(issueUrl(1000)).toBe('https://github.com/w3ctag/design-reviews/issues/1000');
    expect(commentUrl(5, 77)).toBe('https://github.com/w3ctag/design-reviews/issues/5#issuecomment-77');
    expect(commentUrl(5, 0)).toBe('https://github.com/w3ctag/design-reviews/issues/5');
    expect(featureUrl(123456)).toBe('https://chromestatus.com/feature/123456');
    for (const bad of [-1, 0, 1.5, NaN, Infinity, '12' as unknown as number, null as unknown as number]) {
      expect(issueUrl(bad)).toBeNull();
      expect(featureUrl(bad)).toBeNull();
    }
  });

  it('keep only blink-dev / chromium.org Google Groups URLs', () => {
    expect(safeLink('https://groups.google.com/a/chromium.org/g/blink-dev/c/abc123/m/xyz'))
      .toBe('https://groups.google.com/a/chromium.org/g/blink-dev/c/abc123/m/xyz');
    for (const bad of [
      'javascript:alert(1)',
      'JAVASCRIPT:alert(1)//https://groups.google.com/a/chromium.org/',
      'http://groups.google.com/a/chromium.org/g/blink-dev',
      'https://groups.google.com.evil.example/a/chromium.org/',
      'https://groups.google.com@evil.example/a/chromium.org/',
      'https://user:pw@groups.google.com/a/chromium.org/',
      'https://groups.google.com/g/evil-group',
      'https://groups.google.com/a/chromium.org.evil/x',
      'data:text/html,<script>alert(1)</script>',
      '"><img src=x onerror=alert(1)>',
      42,
      null,
    ]) {
      expect(safeLink(bad)).toBeNull();
    }
  });

  it('accept only digits in #issue=', () => {
    expect(issueFromHash('#issue=1000')).toBe(1000);
    for (const bad of ['#issue=1e3', '#issue=1000x', '#issue=<img>', '#issue=', '#x=1']) {
      expect(issueFromHash(bad)).toBeNull();
    }
  });
});
