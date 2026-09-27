// Petits utilitaires DOM, sans framework.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked' || k === 'selected' || k === 'disabled') el[k] = Boolean(v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function mount(target, ...children) {
  target.replaceChildren();
  append(target, children);
}

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export function toast(message, type = 'info') {
  const box = document.getElementById('toasts');
  const t = h('div', { class: 'toast ' + type, role: 'status' }, message);
  box.append(t);
  setTimeout(() => t.remove(), type === 'error' ? 6000 : 3000);
}

export function modal(title, content, { onClose } = {}) {
  const close = () => { bg.remove(); document.removeEventListener('keydown', onKey); onClose && onClose(); };
  const onKey = (e) => { if (e.key === 'Escape' && bg === [...document.querySelectorAll('.modal-bg')].pop()) close(); };
  const bg = h('div', { class: 'modal-bg', onclick: (e) => { if (e.target === bg) close(); } },
    h('div', { class: 'modal', role: 'dialog', 'aria-label': title },
      h('div', { class: 'row between' }, h('h2', { style: { margin: 0 } }, title), h('button', { class: 'small', onclick: close, 'aria-label': 'Fermer' }, '✕')),
      h('div', { style: { marginTop: '1rem' } }, content)));
  document.addEventListener('keydown', onKey);
  document.body.append(bg);
  return close;
}

export function confirmBox(message) {
  return window.confirm(message);
}

const DATE_FMT = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' });
const DAY_FMT = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

export function fmtDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : DATE_FMT.format(d);
}

export function fmtDay(day) {
  if (!day) return '—';
  const d = new Date(day + 'T12:00:00');
  return isNaN(d) ? day : DAY_FMT.format(d);
}

export function relTime(iso) {
  if (!iso) return 'jamais';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.round(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.round(diff / 3600)} h`;
  if (diff < 86400 * 30) return `il y a ${Math.round(diff / 86400)} j`;
  return fmtDateTime(iso);
}

export function pct(x, digits = 0) {
  return x === null || x === undefined ? '—' : `${(x * 100).toFixed(digits)} %`;
}

export function todayIso() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function loading() {
  return h('p', { class: 'muted' }, 'Chargement…');
}

export function errorBox(err) {
  return h('div', { class: 'alert error' }, err.message || String(err));
}

// Zone de code avec numéros de ligne : tabulation = 4 espaces, indentation automatique après « : ».
// Renvoie la zone de texte ; l'élément à insérer dans la page est `ta.container`,
// et `ta.markLine(n)` met en évidence la ligne n (null pour effacer).
export function codeArea(attrs = {}) {
  const ta = h('textarea', { class: 'code', spellcheck: 'false', autocapitalize: 'off', autocomplete: 'off', wrap: 'off', ...attrs });
  const gutter = h('div', { class: 'gutter', 'aria-hidden': 'true' });
  ta.container = h('div', { class: 'code-wrap' }, gutter, ta);
  let marked = null;
  const refresh = () => {
    const n = Math.max(1, ta.value.split('\n').length);
    if (gutter.childElementCount !== n) {
      gutter.replaceChildren(...Array.from({ length: n }, (_, i) => h('span', { class: i + 1 === marked ? 'err' : '' }, i + 1)));
    }
    gutter.scrollTop = ta.scrollTop;
  };
  ta.markLine = (line) => {
    marked = line || null;
    gutter.replaceChildren();
    refresh();
  };
  ta.addEventListener('input', refresh);
  ta.addEventListener('scroll', () => { gutter.scrollTop = ta.scrollTop; });
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
  Object.defineProperty(ta, 'value', {
    get() { return Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').get.call(this); },
    set(v) { setter.call(this, v); refresh(); },
  });
  refresh();
  ta.addEventListener('keydown', (e) => {
    const { selectionStart: s, selectionEnd: end, value } = ta;
    if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      if (e.shiftKey) {
        const lineStart = value.lastIndexOf('\n', s - 1) + 1;
        const n = value.slice(lineStart, lineStart + 4).match(/^ */)[0].length;
        ta.setRangeText('', lineStart, lineStart + n, 'preserve');
      } else {
        ta.setRangeText('    ', s, end, 'end');
      }
      ta.dispatchEvent(new Event('input'));
    } else if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      const lineStart = value.lastIndexOf('\n', s - 1) + 1;
      const line = value.slice(lineStart, s);
      let indent = line.match(/^ */)[0];
      if (/:\s*$/.test(line)) indent += '    ';
      e.preventDefault();
      ta.setRangeText('\n' + indent, s, end, 'end');
      ta.dispatchEvent(new Event('input'));
    }
  });
  return ta;
}

// Jauge (valeur 0..1) : barre + pourcentage écrit, la couleur ne porte jamais seule l'information.
export function meter(value, title) {
  const v = value === null || value === undefined ? null : Math.max(0, Math.min(1, value));
  return h('div', { class: 'meter', title: title || '' },
    h('div', { class: 'track' }, h('div', { class: 'fill', style: { width: v === null ? '0' : `${v * 100}%` } })),
    h('span', { class: 'val' }, v === null ? '—' : `${Math.round(v * 100)} %`));
}

let tipEl = null;
export function tooltip(target, textFn) {
  target.addEventListener('mouseenter', () => {
    tipEl = tipEl || document.body.appendChild(h('div', { class: 'tooltip', role: 'tooltip' }));
    tipEl.textContent = textFn();
    tipEl.style.display = 'block';
  });
  target.addEventListener('mousemove', (e) => {
    if (!tipEl) return;
    const w = tipEl.offsetWidth;
    tipEl.style.left = Math.min(e.clientX + 12, window.innerWidth - w - 8) + 'px';
    tipEl.style.top = e.clientY + 14 + 'px';
  });
  target.addEventListener('mouseleave', () => { if (tipEl) tipEl.style.display = 'none'; });
}
