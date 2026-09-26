// Visualisations : barres d'activité (une série) et carte de chaleur de maîtrise
// (rampe séquentielle bleue, valeur écrite dans chaque case, infobulle au survol).
import { h, tooltip } from './dom.js';

const SVG = 'http://www.w3.org/2000/svg';
function s(tag, attrs = {}) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// Barres verticales ; data = [{label, value, tip}]
export function barChart(data, { height = 180, yLabel = '' } = {}) {
  const width = Math.max(560, data.length * 34 + 50);
  const pad = { l: 36, r: 8, t: 12, b: 26 };
  const max = Math.max(1, ...data.map((d) => d.value));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;
  const svg = s('svg', { viewBox: `0 0 ${width} ${height}`, width, height, class: 'chart', role: 'img', 'aria-label': yLabel });
  const ih = height - pad.t - pad.b;
  const iw = width - pad.l - pad.r;
  for (let v = 0; v <= top; v += step) {
    const y = pad.t + ih - (v / top) * ih;
    svg.append(s('line', { x1: pad.l, x2: width - pad.r, y1: y, y2: y, class: 'grid-line' }));
    const t = s('text', { x: pad.l - 6, y: y + 4, 'text-anchor': 'end' });
    t.textContent = v;
    svg.append(t);
  }
  const bw = iw / Math.max(1, data.length);
  const barW = Math.max(4, Math.min(28, bw - 4));
  data.forEach((d, i) => {
    const x = pad.l + i * bw + (bw - barW) / 2;
    const bh = (d.value / top) * ih;
    const y = pad.t + ih - bh;
    const r = Math.min(4, barW / 2, bh);
    // extrémité arrondie en haut, ancrée à la ligne de base
    const path = bh > 0
      ? `M${x},${pad.t + ih} V${y + r} Q${x},${y} ${x + r},${y} H${x + barW - r} Q${x + barW},${y} ${x + barW},${y + r} V${pad.t + ih} Z`
      : '';
    const g = s('g');
    const hit = s('rect', { x: pad.l + i * bw, y: pad.t, width: bw, height: ih, fill: 'transparent', class: 'hit' });
    g.append(hit);
    if (path) g.append(s('path', { d: path, class: 'bar' }));
    tooltip(g, () => d.tip || `${d.label} : ${d.value}`);
    svg.append(g);
    const every = Math.ceil(data.length / 12);
    if (i % every === 0) {
      const t = s('text', { x: pad.l + i * bw + bw / 2, y: height - 8, 'text-anchor': 'middle' });
      t.textContent = d.label;
      svg.append(t);
    }
  });
  return h('div', { class: 'table-wrap' }, svg);
}

function niceStep(max) {
  const raw = max / 4;
  const p = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((m) => m * p).find((m) => m >= raw) || p;
}

const RAMP = ['--seq-100', '--seq-200', '--seq-300', '--seq-400', '--seq-500', '--seq-600', '--seq-700'];
export function rampColor(v) {
  const idx = Math.min(RAMP.length - 1, Math.floor(v * RAMP.length));
  return { bg: `var(${RAMP[idx]})`, fg: idx >= 3 ? '#fff' : '#0b0b0b' };
}

export function rampLegend() {
  return h('div', { class: 'legend' }, h('span', {}, '0 %'),
    RAMP.map((c) => h('span', { class: 'sw', style: { background: `var(${c})` } })), h('span', {}, '100 %'),
    h('span', { class: 'muted', style: { marginLeft: '1rem' } }, '— : pas encore travaillé'));
}

// Carte de chaleur : lignes = élèves, colonnes = groupes ; cell(row, col) -> {value, n, tip} | null
export function heatmap(rows, cols, cell, { rowLabel, colLabel, onRow, avgRow } = {}) {
  const head = h('tr', {}, h('th', {}, ''), cols.map((c) => h('th', { class: 'col', title: colLabel(c) }, colLabel(c))));
  const body = rows.map((r) => h('tr', {},
    h('td', { class: 'name' }, onRow ? h('a', { href: onRow(r) }, rowLabel(r)) : rowLabel(r)),
    cols.map((c) => cellTd(cell(r, c)))));
  if (avgRow) body.push(h('tr', { class: 'avg' }, h('td', { class: 'name' }, 'Moyenne'), cols.map((c) => cellTd(avgRow(c)))));
  return h('div', { class: 'table-wrap' }, h('table', { class: 'heat' }, h('thead', {}, head), h('tbody', {}, body)));
}

function cellTd(v) {
  if (!v || v.value === null || v.value === undefined) {
    const td = h('td', { class: 'cell none' }, '—');
    if (v && v.tip) tooltip(td, () => v.tip);
    return td;
  }
  const { bg, fg } = rampColor(v.value);
  const td = h('td', { class: 'cell', style: { background: bg, color: fg } }, v.text ?? Math.round(v.value * 100));
  if (v.tip) tooltip(td, () => v.tip);
  return td;
}
