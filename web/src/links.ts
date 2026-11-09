// Every link the dashboard builds from data goes through here (SECURITY.md,
// "Script injection in the dashboard"). Fixed prefixes plus integers, or a URL
// from the data checked against an allowed origin and path.

const REVIEWS = 'https://github.com/w3ctag/design-reviews/issues/';
const CHROMESTATUS = 'https://chromestatus.com/feature/';
const GROUPS = 'https://groups.google.com/a/chromium.org/';

const isId = (n: unknown): n is number => typeof n === 'number' && Number.isSafeInteger(n) && n > 0;

export function issueUrl(n: number): string | null {
  return isId(n) ? `${REVIEWS}${n}` : null;
}

export function commentUrl(n: number, commentId: number): string | null {
  if (!isId(n)) return null;
  return isId(commentId) ? `${REVIEWS}${n}#issuecomment-${commentId}` : `${REVIEWS}${n}`;
}

export function featureUrl(id: number | null): string | null {
  return id !== null && isId(id) ? `${CHROMESTATUS}${id}` : null;
}

/** A blink-dev (Google Groups, chromium.org) URL from the data, or null. */
export function safeLink(url: unknown): string | null {
  if (typeof url !== 'string') return null;
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  if (u.protocol !== 'https:' || u.origin !== 'https://groups.google.com' || u.username || u.password) return null;
  const href = u.href;
  return href.startsWith(GROUPS) ? href : null;
}

/** `#issue=<digits>` -> the issue number, else null. */
export function issueFromHash(hash: string): number | null {
  const m = /^#issue=(\d{1,7})$/.exec(hash);
  return m ? Number(m[1]) : null;
}
