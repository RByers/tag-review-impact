import { bars, legend, lines, stacked } from './charts.ts';
import { type Dataset, type Dimension, type Review, load, valuesOf, year } from './data.ts';
import { openDetail } from './detail.ts';
import { append, clear, h } from './dom.ts';
import { issueFromHash, safeLink } from './links.ts';

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

/** TAG-time histogram bins, in days. */
export const BINS: { label: string; lo: number; hi: number }[] = [
  { label: '< 2 wk', lo: 0, hi: 14 },
  { label: '2–4 wk', lo: 14, hi: 30 },
  { label: '1–2 mo', lo: 30, hi: 60 },
  { label: '2–3 mo', lo: 60, hi: 91 },
  { label: '3–6 mo', lo: 91, hi: 182 },
  { label: '6–12 mo', lo: 182, hi: 365 },
  { label: '> 1 yr', lo: 365, hi: Infinity },
];

type Selection =
  | { kind: 'bin'; bin: number }
  | { kind: 'value'; dim: string; value: string }
  | { kind: 'year-value'; year: number; dim: string; value: string }
  | null;

interface State {
  from: number;
  to: number;
  kind: string;
  chrome: string;
  state: string;
  q: string;
  sel: Selection;
  sort: { key: string; dir: 1 | -1 };
  shown: number;
}

let data: Dataset;
let audit: Audit | null = null;

interface Audit {
  reference_model: string;
  n: number;
  dimensions: Record<string, { metric: string; value: number | null }>;
  change_within_one_step: number | null;
  tag_credited_change_agreement: number | null;
}

function auditText(a: Audit): string {
  const p = (v: number | null | undefined) => (typeof v === 'number' ? `${Math.round(v * 100)}%` : '–');
  return `Audit against ${a.reference_model} on ${a.n} reviews: design change agrees ${p(a.dimensions.change?.value)} ` +
    `(${p(a.change_within_one_step)} within one step), credit to the TAG ${p(a.dimensions.attribution?.value)}, ` +
    `verdict ${p(a.dimensions.verdict?.value)}; "changed, TAG credited" agrees ${p(a.tag_credited_change_agreement)}.`;
}
/** Dimensions labelled but not charted: "change" counts changes whoever caused them; TAG impact covers TAG-caused ones. */
export const HIDDEN_DIMENSIONS = new Set(['change']);

let byNumber = new Map<number, Review>();
let st: State;

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const a = [...xs].sort((x, y) => x - y);
  const m = a.length >> 1;
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

const fmtDays = (d: number | null) => (d === null ? '–' : d < 1 ? '<1' : String(Math.round(d)));

const COLOR_TOKEN = /^var\(--[a-z0-9-]{1,20}\)$/;

/** The value's colour token from the data, if it is one of ours (a CSS var), else neutral. */
export function valueColor(dim: Dimension, key: string): string {
  const c = dim.values.find((v) => v.key === key)?.color;
  return typeof c === 'string' && COLOR_TOKEN.test(c) ? c : 'var(--axis)';
}

function filtered(): Review[] {
  const q = st.q.trim().toLowerCase();
  const num = /^#?(\d+)$/.exec(q);
  return data.reviews.filter((r) => {
    const y = year(r);
    if (y < st.from || y > st.to) return false;
    if (st.kind !== 'all' && r.kind !== st.kind) return false;
    if (st.state === 'closed' && r.open) return false;
    if (st.state === 'open' && !r.open) return false;
    if (st.chrome === 'linked' && !r.features.length) return false;
    if (st.chrome === 'unlinked' && r.features.length) return false;
    if (st.chrome === 'i2s' && !r.features.some((f) => safeLink(f.i2s_url))) return false;
    if (num) return r.number === Number(num[1]);
    if (q && !r.title.toLowerCase().includes(q)) return false;
    return true;
  });
}

function selected(rs: Review[]): Review[] {
  const sel = st.sel;
  if (!sel) return rs;
  if (sel.kind === 'bin') {
    const b = BINS[sel.bin];
    return rs.filter((r) => r.tag_days >= b.lo && r.tag_days < b.hi);
  }
  const dim = data.taxonomy.dimensions.find((d) => d.key === sel.dim);
  if (!dim) return rs;
  return rs.filter((r) => valuesOf(r, dim).includes(sel.value) && (sel.kind !== 'year-value' || year(r) === sel.year));
}

function selectionText(): string {
  const sel = st.sel;
  if (!sel) return '';
  if (sel.kind === 'bin') return `TAG time ${BINS[sel.bin].label}`;
  const dim = data.taxonomy.dimensions.find((d) => d.key === sel.dim);
  const v = dim?.values.find((x) => x.key === sel.value);
  return `${dim?.label ?? sel.dim}: ${v?.label ?? sel.value}${sel.kind === 'year-value' ? `, opened ${sel.year}` : ''}`;
}

function select(sel: Selection) {
  st.sel = sel;
  st.shown = 100;
  render();
  $('list-h').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function tile(value: string, key: string, title?: string) {
  return h('div', { class: 'tile', title }, h('div', { class: 'v' }, value), h('div', { class: 'k' }, key));
}

function renderTiles(rs: Review[]) {
  const pct = (n: number, of = rs.length) => (of ? `${Math.round((100 * n) / of)}%` : '–');
  const labelled = rs.filter((r) => r.impact);
  const out = (keys: string[]) => labelled.filter((r) => keys.includes(String(r.impact?.outcome))).length;
  $('tiles').replaceChildren(
    tile(String(rs.length), 'reviews'),
    tile(fmtDays(median(rs.map((r) => r.tag_days))), 'median TAG days', 'Open-to-close time minus time waiting on the requesters'),
    tile(fmtDays(median(rs.map((r) => r.total_days))), 'median total days'),
    tile(fmtDays(median(rs.map((r) => r.author_wait_days))), 'median days waiting on requesters'),
    tile(fmtDays(median(rs.flatMap((r) => (r.first_tag_comment_days === null ? [] : [r.first_tag_comment_days])))),
      'median days to first TAG comment'),
    tile(pct(rs.filter((r) => r.features.length).length), 'linked from chromestatus'),
    tile(pct(out(['minor', 'major']), labelled.length), 'changed, TAG credited',
      'Share of labelled reviews where a change is credited to the TAG (any size)'),
    tile(pct(out(['major']), labelled.length), 'functional+ change, TAG credited',
      'Functional or significant change credited to the TAG'),
    tile(String(out(['blocked'])), 'blocked', 'Abandoned, with the TAG credited for it'),
  );
}

function renderLatency(rs: Review[]) {
  const counts = BINS.map((b) => rs.filter((r) => r.tag_days >= b.lo && r.tag_days < b.hi).length);
  $('c-hist').replaceChildren(bars(BINS.map((b, i) => ({
    label: b.label,
    value: counts[i],
    selected: st.sel?.kind === 'bin' && st.sel.bin === i,
    detail: [`TAG time ${b.label}`, `${counts[i]} reviews (${rs.length ? Math.round((100 * counts[i]) / rs.length) : 0}%)`, 'Click to list them'],
  })), { label: 'Histogram of reviews by TAG time', onSelect: (i) => select(st.sel?.kind === 'bin' && st.sel.bin === i ? null : { kind: 'bin', bin: i }) }));

  const years: number[] = [];
  for (let y = st.from; y <= st.to; y++) years.push(y);
  const by = (f: (r: Review) => number | null) => years.map((y) => median(rs.filter((r) => year(r) === y).flatMap((r) => {
    const v = f(r);
    return v === null ? [] : [v];
  })));
  const series = [
    { name: 'Total', cls: 'series-2', values: by((r) => r.total_days) },
    { name: 'TAG time', cls: 'series-1', values: by((r) => r.tag_days) },
    { name: 'First TAG comment', cls: 'series-3', values: by((r) => r.first_tag_comment_days) },
  ];
  $('c-years').replaceChildren(lines(years.map(String), series, { label: 'Median review days by year opened', unit: 'days' }));
  $('years-legend').replaceChildren(...series.map((s) => h('li', {}, h('span', { class: `swatch ${s.cls}` }), s.name)));
}

function renderImpact(rs: Review[]) {
  const box = $('impact');
  clear(box);
  const labelled = rs.filter((r) => r.impact);
  $('imp-note').textContent = labelled.length
    ? `Labels from ${labelled[0].impact!.model || 'a model'} reading each thread (taxonomy ${data.taxonomy.version}); ` +
      `${labelled.length} of ${rs.length} reviews in view are labelled. Click a value to list its reviews, then open one to see the model's reason and the comments it cited.` +
      (audit ? ` ${auditText(audit)}` : '')
    :'No impact labels yet: run `python3 -m tagimpact.classify` and rebuild.';
  if (!labelled.length) return;
  for (const dim of data.taxonomy.dimensions) {
    if (HIDDEN_DIMENSIONS.has(dim.key)) continue;
    const sec = h('div', { class: 'dim' }, h('h3', {}, dim.label), h('p', { class: 'note dim-desc' }, dim.description,
      dim.multi ? ' (several can apply)' : ''));
    const rows = h('div', { class: 'values' });
    for (const v of dim.values) {
      const n = labelled.filter((r) => valuesOf(r, dim).includes(v.key)).length;
      const meter = h('span');
      meter.style.width = `${(100 * n) / labelled.length}%`;
      meter.style.background = valueColor(dim, v.key);
      const btn = h('button', { type: 'button', title: v.definition }, v.label);
      btn.addEventListener('click', () => select({ kind: 'value', dim: dim.key, value: v.key }));
      rows.append(h('div', { class: 'value-row' }, btn, h('div', { class: 'meter', title: v.definition }, meter),
        h('span', { class: 'n' }, `${n}`)));
    }
    sec.append(rows);
    if (dim.ordinal && !dim.multi) {
      const years: number[] = [];
      for (let y = st.from; y <= st.to; y++) years.push(y);
      const cols = years.map((y) => ({
        label: String(y),
        parts: dim.values.map((v) => ({
          key: v.key, name: v.label, color: valueColor(dim, v.key),
          value: labelled.filter((r) => year(r) === y && valuesOf(r, dim).includes(v.key)).length,
        })),
      }));
      const fig = h('figure', {}, h('figcaption', {}, `${dim.label} by year opened (share of labelled reviews)`));
      fig.append(stacked(cols, {
        label: `${dim.label} by year`,
        onSelect: (i, key) => select({ kind: 'year-value', year: years[i], dim: dim.key, value: key }),
      }), legend(dim.values.map((v) => ({ name: v.label, color: valueColor(dim, v.key) }))));
      sec.append(fig);
    }
    box.append(sec);
  }
}

interface Col {
  key: string;
  label: string;
  num?: boolean;
  get: (r: Review) => number | string;
  cell: (r: Review) => Node | string;
}

function columns(): Col[] {
  const primary = data.taxonomy.dimensions.find((d) => d.ordinal && !d.multi);
  const cols: Col[] = [
    { key: 'number', label: '#', num: true, get: (r) => r.number, cell: (r) => String(r.number) },
    { key: 'title', label: 'Review', get: (r) => r.title.toLowerCase(), cell: (r) => r.title },
    { key: 'opened', label: 'Opened', get: (r) => r.opened, cell: (r) => h('span', { class: 'nowrap' }, r.opened.slice(0, 10)) },
    { key: 'tag_days', label: 'TAG days', num: true, get: (r) => r.tag_days, cell: (r) => fmtDays(r.tag_days) },
    { key: 'author_wait_days', label: 'Waiting days', num: true, get: (r) => r.author_wait_days, cell: (r) => fmtDays(r.author_wait_days) },
    { key: 'total_days', label: 'Total days', num: true, get: (r) => r.total_days, cell: (r) => fmtDays(r.total_days) },
    { key: 'resolution', label: 'Resolution', get: (r) => r.resolution ?? (r.open ? 'open' : ''), cell: (r) => r.resolution ?? (r.open ? 'open' : '') },
  ];
  if (primary) {
    cols.push({
      key: 'impact', label: primary.label,
      get: (r) => primary.values.findIndex((v) => valuesOf(r, primary).includes(v.key)),
      cell: (r) => {
        const v = primary.values.find((x) => valuesOf(r, primary).includes(x.key));
        return v ? v.label : '';
      },
    });
  }
  cols.push({
    key: 'chrome', label: 'Chrome', get: (r) => (r.features.some((f) => f.i2s_url) ? 2 : r.features.length ? 1 : 0),
    cell: (r) => {
      if (!r.features.length) return '';
      const f = r.features[0];
      const extra = r.features.length > 1 ? ` +${r.features.length - 1}` : '';
      return `${f.i2s_url ? 'I2S' : 'feature'}${f.ship_milestone ? ` M${f.ship_milestone}` : ''}${extra}`;
    },
  });
  return cols;
}

function renderTable(rs: Review[]) {
  const cols = columns();
  const head = $('thead');
  head.replaceChildren(...cols.map((c) => {
    const th = h('th', { scope: 'col' });
    if (st.sort.key === c.key) th.setAttribute('aria-sort', st.sort.dir === 1 ? 'ascending' : 'descending');
    const b = h('button', { type: 'button' }, c.label);
    b.addEventListener('click', () => {
      st.sort = { key: c.key, dir: st.sort.key === c.key ? (st.sort.dir === 1 ? -1 : 1) : c.num ? -1 : 1 };
      render();
    });
    th.append(b);
    return th;
  }));
  const col = cols.find((c) => c.key === st.sort.key) ?? cols[0];
  const sorted = [...rs].sort((a, b) => {
    const x = col.get(a);
    const y = col.get(b);
    return (x < y ? -1 : x > y ? 1 : 0) * st.sort.dir || a.number - b.number;
  });
  const body = document.querySelector('#reviews tbody')!;
  body.replaceChildren(...sorted.slice(0, st.shown).map((r) => {
    const tr = h('tr');
    cols.forEach((c, i) => {
      if (i === 1) {
        const b = h('button', { type: 'button' }, r.title || `#${r.number}`);
        b.addEventListener('click', (e) => {
          e.stopPropagation();
          openDetail(data, r);
        });
        tr.append(h('th', { scope: 'row' }, b));
      } else {
        const td = h('td', { class: c.num ? 'num' : undefined, 'data-label': c.label });
        append(td, [c.cell(r)]);
        tr.append(td);
      }
    });
    tr.addEventListener('click', () => openDetail(data, r));
    return tr;
  }));
  $('list-count').textContent = `(${rs.length})`;
  const more = $<HTMLButtonElement>('more');
  more.hidden = sorted.length <= st.shown;
  more.textContent = `Show more (${sorted.length - st.shown} left)`;
  const selText = selectionText();
  const sel = $('selection');
  sel.replaceChildren();
  if (selText) {
    const clr = h('button', { type: 'button' }, 'Clear');
    clr.addEventListener('click', () => select(null));
    sel.append(`Showing ${selText}. `, clr);
  }
}

function renderPrompt() {
  const p = data.taxonomy.prompt;
  if (!p) return;
  $('prompt-version').textContent = `(taxonomy ${data.taxonomy.version})`;
  $('prompt-system').textContent = p.system;
  $('prompt-user').textContent = p.user;
  $('prompt').hidden = false;
}

function render() {
  const rs = filtered();
  renderTiles(rs);
  renderLatency(rs);
  renderImpact(rs);
  renderTable(selected(rs));
}

function setupFilters() {
  const years = data.reviews.map(year);
  const lo = Math.min(...years);
  const hi = Math.max(...years);
  const from = $<HTMLSelectElement>('f-from');
  const to = $<HTMLSelectElement>('f-to');
  for (let y = lo; y <= hi; y++) {
    from.append(new Option(String(y), String(y)));
    to.append(new Option(String(y), String(y)));
  }
  const defaults = (): State => ({
    from: lo, to: hi, kind: 'review', chrome: 'all', state: 'closed', q: '', sel: null, sort: { key: 'number', dir: -1 }, shown: 100,
  });
  st = defaults();
  const sync = () => {
    from.value = String(st.from);
    to.value = String(st.to);
    $<HTMLSelectElement>('f-kind').value = st.kind;
    $<HTMLSelectElement>('f-chrome').value = st.chrome;
    $<HTMLSelectElement>('f-state').value = st.state;
    $<HTMLInputElement>('f-q').value = st.q;
  };
  sync();
  const read = () => {
    st.from = Number(from.value);
    st.to = Math.max(st.from, Number(to.value));
    st.kind = $<HTMLSelectElement>('f-kind').value;
    st.chrome = $<HTMLSelectElement>('f-chrome').value;
    st.state = $<HTMLSelectElement>('f-state').value;
    st.q = $<HTMLInputElement>('f-q').value;
    st.shown = 100;
    render();
  };
  for (const id of ['f-from', 'f-to', 'f-kind', 'f-chrome', 'f-state']) $(id).addEventListener('change', read);
  $('f-q').addEventListener('input', read);
  $('filters').addEventListener('submit', (e) => e.preventDefault());
  $('f-reset').addEventListener('click', () => {
    st = defaults();
    sync();
    render();
  });
  $('more').addEventListener('click', () => {
    st.shown += 200;
    render();
  });
}

function setupDialog() {
  const dialog = $<HTMLDialogElement>('detail');
  // Light dismiss where <dialog closedby> isn't supported (Safari).
  if (!('closedBy' in HTMLDialogElement.prototype)) {
    const outside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    let pressedOutside = false;
    dialog.addEventListener('pointerdown', (e) => { pressedOutside = outside(e); });
    dialog.addEventListener('pointerup', (e) => { if (pressedOutside && outside(e)) dialog.close(); });
  }
  dialog.addEventListener('close', () => {
    if (issueFromHash(location.hash) !== null) history.replaceState(null, '', location.pathname + location.search);
  });
  const fromHash = () => {
    const n = issueFromHash(location.hash);
    const r = n === null ? undefined : byNumber.get(n);
    if (r) openDetail(data, r);
  };
  window.addEventListener('hashchange', fromHash);
  fromHash();
}

async function main() {
  try {
    data = await load();
  } catch (e) {
    $('tiles').replaceChildren(h('p', {}, `Couldn't load the data: ${String(e)}`));
    return;
  }
  try {
    const r = await fetch('./audit.json');
    if (r.ok) audit = JSON.parse(await r.text()) as Audit;
  } catch {
    audit = null;
  }
  byNumber = new Map(data.reviews.map((r) => [r.number, r]));
  $('generated').textContent = ` Data as of ${data.generated.slice(0, 10)}.`;
  setupFilters();
  renderPrompt();
  render();
  setupDialog();
}

// Not in unit tests (no DOM there).
if (typeof document !== 'undefined' && document.getElementById('tiles')) void main();

