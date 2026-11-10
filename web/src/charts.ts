// Small SVG charts built with DOM calls (no chart library, no markup parsing).
// Marks follow the dataviz skill's specs: thin bars with 4px rounded data
// ends, 2px gaps, 2px lines, >=8px markers, recessive axes, a hover tooltip on
// every mark, and colours by role from style.css custom properties.

import { h, s } from './dom.ts';

const W = 640;
const PAD = { top: 12, right: 12, bottom: 40, left: 44 };

let tip: HTMLElement | null = null;

function tooltip(): HTMLElement {
  if (!tip) {
    tip = h('div', { class: 'tooltip', role: 'status', hidden: true });
    document.body.append(tip);
  }
  return tip;
}

function showTip(ev: PointerEvent | FocusEvent, lines: string[]) {
  const t = tooltip();
  t.replaceChildren(...lines.map((l, i) => h(i ? 'div' : 'strong', {}, l)));
  t.hidden = false;
  let x: number, y: number;
  if (ev instanceof PointerEvent) {
    x = ev.clientX;
    y = ev.clientY;
  } else {
    const r = (ev.target as Element).getBoundingClientRect();
    x = r.left + r.width / 2;
    y = r.top;
  }
  const tw = t.offsetWidth;
  t.style.left = `${Math.min(window.innerWidth - tw - 8, Math.max(8, x + 12))}px`;
  t.style.top = `${Math.max(8, y - t.offsetHeight - 12)}px`;
}

function hideTip() {
  if (tip) tip.hidden = true;
}

function hover(el: SVGElement, lines: () => string[]) {
  el.addEventListener('pointermove', (e) => showTip(e, lines()));
  el.addEventListener('pointerleave', hideTip);
  el.addEventListener('focus', (e) => showTip(e, lines()));
  el.addEventListener('blur', hideTip);
}

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

function yAxis(svg: SVGSVGElement, max: number, height: number, fmt: (v: number) => string, right = PAD.right, width = W) {
  const plotH = height - PAD.top - PAD.bottom;
  for (let i = 0; i <= 4; i++) {
    const v = (max * i) / 4;
    const y = PAD.top + plotH - (plotH * i) / 4;
    svg.append(
      s('line', { x1: PAD.left, x2: width - right, y1: y, y2: y, class: i ? 'grid' : 'baseline' }),
      s('text', { x: PAD.left - 6, y: y + 4, class: 'tick', 'text-anchor': 'end' }, fmt(v)),
    );
  }
}

function frame(height: number, label: string, width = W): SVGSVGElement {
  return s('svg', { viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'img', 'aria-label': label });
}

/** A rect with rounded top corners only (data end), anchored at the baseline. */
function bar(x: number, y: number, w: number, hgt: number, cls: string, fill?: string): SVGPathElement {
  const r = Math.min(4, w / 2, hgt);
  const d = hgt <= 0 ? '' :
    `M${x},${y + hgt}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + hgt}Z`;
  const p = s('path', { d, class: cls });
  if (fill) p.style.fill = fill;
  return p;
}

export interface BarDatum {
  label: string;
  value: number;
  detail: string[];
  selected?: boolean;
}

/** Vertical bars, one per category; click selects. */
export function bars(data: BarDatum[], opts: { label: string; height?: number; onSelect?: (i: number) => void }) {
  const height = opts.height ?? 240;
  const svg = frame(height, opts.label);
  const max = niceMax(Math.max(...data.map((d) => d.value), 1));
  yAxis(svg, max, height, (v) => String(Math.round(v)));
  const plotW = W - PAD.left - PAD.right;
  const plotH = height - PAD.top - PAD.bottom;
  const slot = plotW / data.length;
  const bw = Math.max(6, Math.min(48, slot - 2 - slot * 0.3));
  data.forEach((d, i) => {
    const x = PAD.left + i * slot + (slot - bw) / 2;
    const bh = (plotH * d.value) / max;
    const y = PAD.top + plotH - bh;
    const g = s('g', { class: `bar${d.selected ? ' selected' : ''}`, tabindex: 0, role: 'button',
                       'aria-label': `${d.label}: ${d.value}` });
    g.append(
      s('rect', { x: PAD.left + i * slot, y: PAD.top, width: slot, height: plotH, class: 'hit' }),
      bar(x, y, bw, bh, 'mark'),
      s('text', { x: x + bw / 2, y: height - PAD.bottom + 16, class: 'tick', 'text-anchor': 'middle' }, d.label),
    );
    if (d.value) g.append(s('text', { x: x + bw / 2, y: y - 4, class: 'value', 'text-anchor': 'middle' }, String(d.value)));
    hover(g, () => d.detail);
    if (opts.onSelect) {
      g.addEventListener('click', () => opts.onSelect!(i));
      g.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          opts.onSelect!(i);
        }
      });
    }
    svg.append(g);
  });
  return svg;
}

export interface Series {
  name: string;
  cls: string;        // CSS class giving the stroke colour (series-1, series-2...)
  values: (number | null)[];
}

/** Lines over a shared x axis (years), one y axis, crosshair + tooltip per x. */
export function lines(xs: string[], series: Series[], opts: { label: string; unit: string; height?: number }) {
  const height = opts.height ?? 240;
  const svg = frame(height, opts.label);
  const all = series.flatMap((x) => x.values.filter((v): v is number => v !== null));
  const max = niceMax(Math.max(...all, 1));
  const right = 116;   // room for direct labels
  yAxis(svg, max, height, (v) => String(Math.round(v)), right);
  const plotW = W - PAD.left - right;
  const plotH = height - PAD.top - PAD.bottom;
  const step = plotW / Math.max(1, xs.length - 1);
  const X = (i: number) => PAD.left + i * step;
  const Y = (v: number) => PAD.top + plotH - (plotH * v) / max;
  xs.forEach((x, i) => {
    if (xs.length <= 16 || i % 2 === 0)
      svg.append(s('text', { x: X(i), y: height - PAD.bottom + 16, class: 'tick', 'text-anchor': 'middle' }, x));
  });
  const ends: { name: string; y: number }[] = [];
  for (const se of series) {
    let d = '';
    se.values.forEach((v, i) => {
      if (v === null) return;
      d += `${d ? 'L' : 'M'}${X(i)},${Y(v)}`;
    });
    svg.append(s('path', { d, class: `line ${se.cls}` }));
    const last = se.values.length - 1 - [...se.values].reverse().findIndex((v) => v !== null);
    const lv = se.values[last];
    if (lv !== null && lv !== undefined) ends.push({ name: se.name, y: Y(lv) });
  }
  // Direct labels right of the plot, pushed apart so they never collide.
  ends.sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 13);
  for (const e of ends) svg.append(s('text', { x: W - right + 6, y: e.y + 4, class: 'label' }, e.name));
  const cross = s('line', { y1: PAD.top, y2: PAD.top + plotH, class: 'crosshair', visibility: 'hidden' });
  const dots = series.map((se) => s('circle', { r: 4, class: `dot ${se.cls}`, visibility: 'hidden' }));
  svg.append(cross, ...dots);
  xs.forEach((x, i) => {
    const hit = s('rect', { x: X(i) - step / 2, y: PAD.top, width: step, height: plotH, class: 'hit', tabindex: 0 });
    const show = () => {
      cross.setAttribute('x1', String(X(i)));
      cross.setAttribute('x2', String(X(i)));
      cross.setAttribute('visibility', 'visible');
      series.forEach((se, k) => {
        const v = se.values[i];
        dots[k].setAttribute('visibility', v === null ? 'hidden' : 'visible');
        if (v !== null) {
          dots[k].setAttribute('cx', String(X(i)));
          dots[k].setAttribute('cy', String(Y(v)));
        }
      });
    };
    const lines = () => [x, ...series.map((se) => `${se.name}: ${se.values[i] === null ? '–' : `${Math.round(se.values[i]!)} ${opts.unit}`}`)];
    hit.addEventListener('pointerenter', show);
    hit.addEventListener('focus', show);
    hit.addEventListener('pointerleave', () => cross.setAttribute('visibility', 'hidden'));
    hover(hit, lines);
    svg.append(hit);
  });
  return svg;
}

export interface Stack {
  label: string;
  parts: { key: string; name: string; value: number; color: string }[];
}

/** 100% stacked columns (shares of each column), 2px gaps between segments. */
export function stacked(cols: Stack[], opts: { label: string; height?: number; onSelect?: (col: number, key: string) => void }) {
  // Wide and short: these sit full-width under their meters.
  const width = 1100;
  const height = opts.height ?? 280;
  const top = 26;   // room for the n= labels
  const svg = frame(height, opts.label, width);
  const plotH = height - top - PAD.bottom;
  for (let i = 0; i <= 4; i++) {
    const y = top + plotH - (plotH * i) / 4;
    svg.append(
      s('line', { x1: PAD.left, x2: width - PAD.right, y1: y, y2: y, class: i ? 'grid' : 'baseline' }),
      s('text', { x: PAD.left - 6, y: y + 4, class: 'tick', 'text-anchor': 'end' }, `${25 * i}%`),
    );
  }
  const plotW = width - PAD.left - PAD.right;
  const slot = plotW / cols.length;
  const bw = Math.max(6, Math.min(44, slot * 0.6));
  cols.forEach((c, i) => {
    const total = c.parts.reduce((a, p) => a + p.value, 0);
    const x = PAD.left + i * slot + (slot - bw) / 2;
    svg.append(s('text', { x: x + bw / 2, y: height - PAD.bottom + 16, class: 'tick', 'text-anchor': 'middle' }, c.label));
    // n per column: small columns swing wildly, so say how small.
    svg.append(s('text', { x: x + bw / 2, y: top - 8, class: 'tick', 'text-anchor': 'middle' }, `n=${total}`));
    if (!total) return;
    let y = top + plotH;
    c.parts.forEach((p, k) => {
      if (!p.value) return;
      const hgt = (plotH * p.value) / total;
      const isTop = k === c.parts.length - 1 || c.parts.slice(k + 1).every((q) => !q.value);
      const gap = y < top + plotH ? 2 : 0;
      const seg = isTop ? bar(x, y - hgt, bw, hgt - gap, 'segment', p.color)
                      : s('rect', { x, y: y - hgt, width: bw, height: Math.max(0, hgt - gap), class: 'segment' });
      if (!isTop) (seg as SVGElement).style.fill = p.color;
      seg.setAttribute('tabindex', '0');
      seg.setAttribute('aria-label', `${c.label} ${p.name}: ${p.value}`);
      hover(seg, () => [`${c.label}: ${p.name}`, `${p.value} of ${total} (${Math.round((100 * p.value) / total)}%)`]);
      if (opts.onSelect) seg.addEventListener('click', () => opts.onSelect!(i, p.key));
      svg.append(seg);
      y -= hgt;
    });
  });
  return svg;
}

export function legend(items: { name: string; color: string }[]): HTMLElement {
  return h('ul', { class: 'legend' }, ...items.map((it) => {
    const sw = h('span', { class: 'swatch' });
    sw.style.background = it.color;
    return h('li', {}, sw, it.name);
  }));
}
