// Rendu Markdown minimal et sûr (tout le texte est échappé) pour les énoncés :
// titres, paragraphes, **gras**, *italique*, `code`, blocs ```lang, listes, citations, tableaux, liens.
import { esc } from './dom.js';

function inline(text) {
  const codes = [];
  let s = text.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>')
    .replace(/(^|[^_\w])__([^_]+?)__(?!\w)/g, '$1<u>$2</u>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/ {2}$/gm, '<br>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[+i])}</code>`);
}

// Langages dont les blocs de 3 lignes ou plus sont numérotés
const NUMBERED = new Set(['python', 'py', 'sql']);

function highlight(code, lang) {
  const hl = window.hljs;
  if (hl && lang && lang !== 'text' && hl.getLanguage(lang)) {
    try { return hl.highlight(code, { language: lang, ignoreIllegals: true }).value; } catch { /* texte brut */ }
  }
  return esc(code);
}

function splitRow(line) {
  let l = line.trim();
  if (l.startsWith('|')) l = l.slice(1);
  if (l.endsWith('|') && !l.endsWith('\\|')) l = l.slice(0, -1);
  return l.split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, '|'));
}

export function renderMarkdown(src) {
  const lines = String(src ?? '').replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^\s*(```+|~~~+)\s*([\w+-]*)\s*$/);
    if (fence) {
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence[1])) body.push(lines[i++]);
      i++;
      const lang = fence[2] || '';
      const code = `<pre><code class="language-${esc(lang)}">${highlight(body.join('\n'), lang)}</code></pre>`;
      if (NUMBERED.has(lang) && body.length >= 3) {
        // numéros de ligne dans une colonne séparée (compatible avec la coloration syntaxique)
        const nums = body.map((_, k) => k + 1).join('\n');
        out.push(`<div class="code-block"><pre class="gutter" aria-hidden="true">${nums}</pre>${code}</div>`);
      } else {
        out.push(code);
      }
      continue;
    }
    if (!line.trim()) { i++; continue; }
    const head = line.match(/^(#{1,4})\s+(.*)$/);
    if (head) {
      const n = Math.min(head[1].length + 2, 6);
      out.push(`<h${n}>${inline(head[2])}</h${n}>`);
      i++;
      continue;
    }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const headers = splitRow(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(splitRow(lines[i++]));
      out.push('<div class="table-wrap"><table><thead><tr>' + headers.map((c) => `<th>${inline(c)}</th>`).join('') +
        '</tr></thead><tbody>' + rows.map((r) => '<tr>' + r.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') +
        '</tbody></table></div>');
      continue;
    }
    if (/^\s*>/.test(line)) {
      const body = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ''));
      out.push(`<blockquote>${renderMarkdown(body.join('\n'))}</blockquote>`);
      continue;
    }
    const li = line.match(/^\s*([-*]|\d+[.)])\s+/);
    if (li) {
      const ordered = /\d/.test(li[1]);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+[.)])\s+/.test(lines[i])) {
        let item = lines[i++].replace(/^\s*([-*]|\d+[.)])\s+/, '');
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+[.)])\s+/.test(lines[i])) item += ' ' + lines[i++].trim();
        items.push(`<li>${inline(item)}</li>`);
      }
      out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`);
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^\s*(```|~~~|#{1,4}\s|>|[-*]\s|\d+[.)]\s)/.test(lines[i]) &&
           !(/^\s*\|/.test(lines[i]) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1]))) {
      para.push(lines[i++]);
    }
    out.push(`<p>${inline(para.join('\n'))}</p>`);
  }
  return out.join('\n');
}

export function md(src, tag = 'div') {
  const el = document.createElement(tag);
  el.className = 'md';
  el.innerHTML = renderMarkdown(src);
  return el;
}
