// The per-review detail dialog, for spot-checking the numbers and labels.

import { type Dataset, type Review, valuesOf } from './data.ts';
import { h, link, s } from './dom.ts';
import { commentUrl, featureUrl, issueUrl, safeLink } from './links.ts';

const DAY = 86400;
const W = 860;

function fmt(d: number | null) {
  return d === null ? '–' : `${d < 1 ? d.toFixed(1) : Math.round(d)} days`;
}

/** Opened -> closed (or now), waiting intervals shaded, comments as ticks by side. */
function timeline(r: Review): SVGSVGElement {
  const t0 = Date.parse(r.opened) / 1000;
  const t1 = r.closed ? Date.parse(r.closed) / 1000 : t0 + r.total_days * DAY;
  const span = Math.max(1, t1 - t0);
  const X = (t: number) => 10 + ((W - 20) * Math.min(Math.max(t - t0, 0), span)) / span;
  const svg = s('svg', { viewBox: `0 0 ${W} 70`, class: 'timeline-svg', role: 'img',
                         'aria-label': 'Review timeline: waiting intervals shaded, comments as ticks' });
  svg.append(s('rect', { x: 10, y: 20, width: W - 20, height: 20, class: 'span', rx: 3 }));
  for (const [a, b] of r.wait_segments) {
    const seg = s('rect', { x: X(a), y: 20, width: Math.max(1, X(b) - X(a)), height: 20, class: 'wait' });
    seg.append(s('title', {}, `Waiting on requesters: ${new Date(a * 1000).toISOString().slice(0, 10)} to ${new Date(b * 1000).toISOString().slice(0, 10)}`));
    svg.append(seg);
  }
  for (const c of r.timeline) {
    const y = c.side === 'tag' ? 8 : 44;
    const m = s('rect', { x: X(c.t) - 1, y, width: 3, height: 12, class: `c-${c.side}` });
    m.append(s('title', {}, `${c.login} (${c.side === 'tag' ? 'TAG' : 'requester side'}), ${new Date(c.t * 1000).toISOString().slice(0, 10)}`));
    svg.append(m);
  }
  svg.append(
    s('text', { x: 10, y: 68, class: 'tick' }, r.opened.slice(0, 10)),
    s('text', { x: W - 10, y: 68, class: 'tick', 'text-anchor': 'end' }, r.closed ? r.closed.slice(0, 10) : 'open'),
  );
  return svg;
}

export function openDetail(data: Dataset, r: Review) {
  const dialog = document.getElementById('detail') as HTMLDialogElement;
  const body = document.getElementById('d-body')!;
  const dims = data.taxonomy.dimensions;

  const facts = h('dl', { class: 'facts' });
  const fact = (k: string, v: Node | string) => facts.append(h('dt', {}, k), h('dd', {}, v));
  fact('Requested by', r.requester);
  fact('Opened / closed', `${r.opened.slice(0, 10)} → ${r.closed ? r.closed.slice(0, 10) : 'still open'}`);
  fact('Resolution label', r.resolution ?? '(none)');
  if (r.review_type.length) fact('Review type', r.review_type.join(', '));
  if (r.venues.length) fact('Venue', r.venues.join(', '));
  fact('Total', fmt(r.total_days));
  fact('Waiting on requesters', `${fmt(r.author_wait_days)} (labels ${fmt(r.label_wait_days)}, turns ${fmt(r.turn_wait_days)}, overlapping)`);
  fact('TAG time', fmt(r.tag_days));
  fact('First TAG comment', fmt(r.first_tag_comment_days));
  fact('Comments', `${r.comments} (${r.tag_comments} TAG, ${r.requester_comments} requester side)`);

  const impact = h('section', {}, h('h3', {}, 'Design impact (model labels)'));
  if (r.impact) {
    const il = h('dl', { class: 'facts' });
    for (const d of dims) {
      const vals = valuesOf(r, d).map((k) => d.values.find((v) => v.key === k)?.label ?? k);
      il.append(h('dt', {}, d.label), h('dd', {}, vals.length ? vals.join(', ') : '–'));
    }
    impact.append(il, h('p', { class: 'reason' }, r.impact.reason || '(no reason given)'));
    if (r.impact.evidence_ids.length) {
      const p = h('p', { class: 'note' }, 'Evidence cited: ');
      r.impact.evidence_ids.forEach((id, i) => {
        if (i) p.append(', ');
        const k = r.timeline.findIndex((c) => c.id === id);
        const c = r.timeline[k];
        const text = !id ? 'issue body'
          : c ? `#${k + 1} ${new Date(c.t * 1000).toISOString().slice(0, 10)} ${c.login}` : 'comment';
        p.append(link(commentUrl(r.number, id), text));
      });
      impact.append(p);
    }
    impact.append(h('p', { class: 'note' }, `Labelled by ${r.impact.model}, prompt ${r.impact.prompt_version}.`));
  } else {
    impact.append(h('p', { class: 'note' }, 'Not labelled.'));
  }

  const chrome = h('section', {}, h('h3', {}, 'Chrome features'));
  if (r.features.length) {
    const ul = h('ul');
    for (const f of r.features) {
      const li = h('li', {}, link(featureUrl(f.id), f.name || `feature ${f.id}`));
      const bits: (Node | string)[] = [];
      if (f.chrome_status) bits.push(` · ${f.chrome_status}`);
      if (f.ship_milestone) bits.push(` · ships M${f.ship_milestone}`);
      const i2s = safeLink(f.i2s_url);
      if (i2s) bits.push(' · ', link(i2s, 'Intent to Ship thread'));
      const i2p = safeLink(f.i2p_url);
      if (i2p) bits.push(' · ', link(i2p, 'Intent to Prototype'));
      bits.push(` · linked via ${f.link_source.replace('_', ' ')}`);
      if (f.tag_review_status) bits.push(` · chromestatus TAG status: ${f.tag_review_status}`);
      for (const b of bits) li.append(b);
      ul.append(li);
    }
    chrome.append(ul);
  } else {
    chrome.append(h('p', { class: 'note' }, 'No chromestatus feature links to this review.'));
  }

  const comments = h('section', {}, h('h3', {}, 'Comments'));
  const ol = h('ol', { class: 'comments' });
  for (const c of r.timeline) {
    ol.append(h('li', {}, link(commentUrl(r.number, c.id), new Date(c.t * 1000).toISOString().slice(0, 10)),
      ` ${c.login} `, h('span', { class: 'muted' }, c.side === 'tag' ? '(TAG)' : '(requester side)')));
  }
  comments.append(ol);

  body.replaceChildren(
    h('h2', { id: 'd-title' }, `#${r.number} ${r.title}`),
    h('p', {}, link(issueUrl(r.number), 'Open on GitHub')),
    timeline(r),
    h('ul', { class: 'legend' },
      h('li', {}, h('span', { class: 'swatch tag' }), 'TAG comment'),
      h('li', {}, h('span', { class: 'swatch req' }), 'requester-side comment'),
      h('li', {}, h('span', { class: 'swatch wait' }), 'waiting on requesters')),
    facts, impact, chrome, comments,
  );
  history.replaceState(null, '', `#issue=${r.number}`);
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
}
