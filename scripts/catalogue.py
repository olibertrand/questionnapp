#!/usr/bin/env python3
"""Catalogue des questions de la banque : une page HTML à parcourir, avec un exemple tiré
par le moteur pour chaque question (énoncé, zone de réponse, réponse attendue, solution, indices).

    python3 scripts/catalogue.py                       # écrit catalogue-questions.html
    python3 scripts/catalogue.py --sortie ~/catalogue.html
    python3 scripts/catalogue.py --graine 2            # d'autres exemples

La page est autonome : un seul fichier, qui s'ouvre sans connexion dans n'importe quel
navigateur (styles, coloration syntaxique et rendu des énoncés sont inclus, rien n'est chargé
depuis l'extérieur). Les énoncés sont affichés avec le même rendu que dans l'appli.
Les exemples sont toujours les mêmes pour une graine donnée : on peut régénérer la page après
chaque ajout de questions sans que les autres changent.
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import core  # noqa: E402

WEB = os.path.join(ROOT, "web")


def _read(*parts):
    with open(os.path.join(WEB, *parts), encoding="utf-8") as f:
        return f.read()


def example(template, uid, graine):
    """Un exemple de la question : énoncé et champs tels que vus par l'élève, réponses attendues,
    solution, indices et nombre de variantes différentes sur 20 tirages."""
    seed = zlib.crc32(f"{uid}:{graine}".encode()) & 0x7FFFFFFF
    p = core.preview(template, seed, samples=20)
    _public, priv, _ns = core._build(template, seed)
    fields = []
    for f, pub, pv, expected in zip(template["fields"], p["public"]["fields"], priv["fields"], p["expected"]):
        item = dict(pub, expected=expected)
        if pub["type"] == "choice":
            item["correct"] = pv["correct"]
        if pub["type"] == "code":
            item["tests"] = bool(f.get("tests"))
        fields.append(item)
    return {"statement": p["public"]["statement"], "fields": fields, "max_tries": p["public"]["max_tries"],
            "solution": p["solution"], "hints": p["hints"], "variety": p["variety"]}


def collect(bank_dir, graine):
    banks = []
    for path in sorted(glob.glob(os.path.join(bank_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        questions = []
        for q in data.get("questions", []):
            item = {k: q.get(k) for k in ("uid", "title", "chapter", "skills", "difficulty")}
            try:
                item["example"] = example(q["template"], q.get("uid") or q["title"], graine)
            except Exception as exc:  # une question cassée ne doit pas empêcher le reste du catalogue
                item["error"] = str(exc)
            questions.append(item)
        banks.append({"file": os.path.basename(path), "title": data.get("title") or os.path.basename(path),
                      "description": data.get("description", ""), "questions": questions})
    return banks


def _markdown_js():
    """Le rendu Markdown de l'appli (web/js/markdown.js), sans ses import/export de module."""
    src = _read("js", "markdown.js")
    src = re.sub(r"^import .*$", "", src, flags=re.M)
    esc = re.search(r"export function esc\(s\) \{.*?\n\}", _read("js", "dom.js"), re.S).group(0)
    return esc.replace("export ", "") + "\n" + src.replace("export function", "function")


def _json_for_script(data):
    # « </ » fermerait la balise <script> : on l'échappe
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


CSS = """
.cat { display: grid; grid-template-columns: 17rem minmax(0, 1fr); gap: 1.5rem; max-width: 1200px; margin: 0 auto; padding: 1.2rem 16px 3rem; }
.cat main { max-width: none; margin: 0; padding: 0; }
.cat nav { position: sticky; top: 1rem; align-self: start; max-height: calc(100vh - 2rem); overflow-y: auto; font-size: .9rem; }
.cat nav ul { list-style: none; padding: 0; margin: .3rem 0 0; }
.cat nav li { margin: .15rem 0; }
.cat nav a { text-decoration: none; display: flex; justify-content: space-between; gap: .5rem; padding: .2rem .4rem; border-radius: 6px; }
.cat nav a:hover { background: var(--surface-2); }
.cat nav .n { color: var(--muted); font-variant-numeric: tabular-nums; }
.tools { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin: 0 0 1rem; }
.tools input { flex: 1; min-width: 12rem; font: inherit; padding: .5rem .7rem; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); color: var(--text); }
.tools button { font: inherit; padding: .45rem .8rem; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); color: var(--text); cursor: pointer; }
.bank-head { margin: 2rem 0 .3rem; }
.bank-head p { margin: 0 0 .8rem; color: var(--text-2); }
.q { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 1rem 1.2rem; margin: 0 0 1rem; }
.q .md, .q .code-block, .q pre { max-width: 100%; }
.q :not(pre) > code { overflow-wrap: anywhere; }
.q-head { display: flex; flex-wrap: wrap; gap: .5rem; align-items: baseline; }
.q-head h3 { margin: 0; font-size: 1.05rem; }
.meta { color: var(--muted); font-size: .85rem; margin: .2rem 0 .6rem; }
.field { margin: .7rem 0 0; padding-top: .6rem; border-top: 1px dashed var(--border); }
.field .label { font-weight: 600; margin-bottom: .3rem; }
.field .label .md p { margin: 0; display: inline; }
.answer-box { display: inline-block; min-width: 9rem; padding: .35rem .6rem; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--muted); font-size: .9rem; }
.opts { list-style: none; padding: 0; margin: .3rem 0; }
.opts li { display: flex; gap: .5rem; align-items: baseline; padding: .25rem .5rem; border: 1px solid var(--border); border-radius: 6px; margin: .3rem 0; }
.opts li .md p { margin: 0; }
.reveal .opts li.ok::after { content: "✓ bonne réponse"; margin-left: auto; color: var(--good-ink); font-size: .8rem; font-weight: 600; white-space: nowrap; }
.reveal .opts li.ok { border-color: var(--good); background: var(--good-soft); }
details.sol { margin-top: .8rem; }
details.sol summary { cursor: pointer; color: var(--accent-ink); font-weight: 600; }
details.sol .box { margin-top: .5rem; padding: .6rem .9rem; border-left: 3px solid var(--good); background: var(--surface-2); border-radius: 6px; }
details.sol h4 { margin: .6rem 0 .2rem; font-size: .9rem; }
.err { color: var(--bad-ink); background: var(--bad-soft); padding: .5rem .8rem; border-radius: 6px; }
.empty-search { color: var(--muted); }
@media (max-width: 800px) {
  .cat { grid-template-columns: minmax(0, 1fr); }
  .cat nav { position: static; max-height: none; }
}
@media print {
  .cat { display: block; }
  .cat nav, .tools { display: none; }
  .q { box-shadow: none; break-inside: avoid; }
}
"""

APP_JS = r"""
const data = JSON.parse(document.getElementById('data').textContent);
const $ = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const KIND = { number: 'Nombre', text: 'Texte', choice: 'Choix', code: 'Code Python', sql: 'Requête SQL' };

function fieldView(f) {
  const box = $('div', 'field');
  const label = $('div', 'label');
  label.append(f.label ? md(f.label) : document.createTextNode(KIND[f.type] || f.type));
  box.append(label);
  if (f.type === 'choice') {
    const ul = $('ul', 'opts');
    f.options.forEach((o, i) => {
      const li = $('li', f.correct.includes(i) ? 'ok' : '');
      li.append($('span', '', f.multiple ? '☐' : '○'), md(o));
      ul.append(li);
    });
    box.append(ul);
    if (f.multiple) box.append($('div', 'small muted', 'Plusieurs réponses possibles.'));
  } else if (f.type === 'code' || f.type === 'sql') {
    box.append(f.starter && f.starter.trim() ? md('```' + (f.type === 'sql' ? 'sql' : 'python') + '\n' + f.starter.replace(/\n$/, '') + '\n```')
      : $('div', 'answer-box', f.type === 'sql' ? 'zone de requête vide' : 'zone de code vide'));
  } else {
    box.append($('span', 'answer-box', f.type === 'number' ? 'nombre' : f.multiline ? 'texte sur plusieurs lignes' : 'texte'));
    if (f.suffix) box.append(document.createTextNode(' ' + f.suffix));
  }
  return box;
}

function solutionView(ex) {
  const det = $('details', 'sol');
  det.append($('summary', '', 'Réponse attendue et solution'));
  const box = $('div', 'box');
  const exp = ex.fields.map((f, i) => {
    const num = ex.fields.length > 1 ? `Champ ${i + 1} : ` : '';
    if (f.type === 'choice') return null;  // bonnes options surlignées dans la liste
    if (f.type === 'code') return f.tests ? num + 'vérifié par des tests (voir la solution).' : null;
    return f.expected ? num + f.expected : null;
  }).filter(Boolean);
  if (exp.length) { box.append($('h4', '', 'Réponse attendue')); exp.forEach((e) => box.append(md(e))); }
  if (ex.solution) { box.append($('h4', '', 'Solution affichée à l’élève')); box.append(md(ex.solution)); }
  if (ex.hints.length) {
    box.append($('h4', '', `Indices (un de plus à chaque essai, ${ex.max_tries} essai(s))`));
    const ol = $('ol');
    ex.hints.forEach((h) => { const li = $('li'); li.append(md(h)); ol.append(li); });
    box.append(ol);
  }
  det.append(box);
  det.addEventListener('toggle', () => det.closest('.q').classList.toggle('reveal', det.open));
  return det;
}

function questionView(q) {
  const card = $('article', 'q');
  card.id = q.uid || '';
  const head = $('div', 'q-head');
  if (q.uid) head.append($('span', 'uid', q.uid));
  head.append($('h3', '', '')); head.lastChild.textContent = q.title;
  card.append(head);
  const ex = q.example;
  const meta = [q.chapter, q.difficulty ? '★'.repeat(q.difficulty) : '', (q.skills || []).join(' · ')];
  if (ex) meta.push(`${ex.variety.distinct}/${ex.variety.samples} tirages différents`);
  card.append($('div', 'meta', '')); card.lastChild.textContent = meta.filter(Boolean).join(' — ');
  if (!ex) { card.append($('div', 'err', '')); card.lastChild.textContent = 'Erreur du moteur : ' + q.error; }
  else {
    card.append(md(ex.statement));
    ex.fields.forEach((f) => card.append(fieldView(f)));
    card.append(solutionView(ex));
  }
  card.dataset.s = norm([q.uid, q.title, q.chapter, (q.skills || []).join(' '), ex ? ex.statement : ''].join(' '));
  return card;
}

const main = document.getElementById('main');
const nav = document.getElementById('toc');
const sections = data.banks.map((b, k) => {
  const sec = $('section');
  sec.id = 'banque-' + k;
  const head = $('div', 'bank-head');
  head.append($('h2', '', '')); head.firstChild.textContent = `${b.title} (${b.questions.length})`;
  if (b.description) { head.append($('p', '', '')); head.lastChild.textContent = b.description; }
  sec.append(head);
  b.questions.forEach((q) => sec.append(questionView(q)));
  main.append(sec);
  const li = $('li'); const a = $('a'); a.href = '#banque-' + k;
  a.append($('span', '', '')); a.firstChild.textContent = b.title;
  const n = $('span', 'n', String(b.questions.length)); a.append(n);
  li.append(a); nav.append(li);
  return { sec, n, total: b.questions.length };
});
const none = $('p', 'empty-search', 'Aucune question ne correspond.'); none.hidden = true; main.append(none);

const search = document.getElementById('search');
search.addEventListener('input', () => {
  const words = norm(search.value).split(/\s+/).filter(Boolean);
  let shown = 0;
  sections.forEach((s) => {
    let n = 0;
    s.sec.querySelectorAll('.q').forEach((c) => { const ok = words.every((w) => c.dataset.s.includes(w)); c.hidden = !ok; n += ok; });
    s.sec.hidden = n === 0; s.n.textContent = words.length ? `${n}/${s.total}` : String(s.total); shown += n;
  });
  none.hidden = shown > 0;
});
let open = false;
document.getElementById('toggle').addEventListener('click', (e) => {
  open = !open;
  document.querySelectorAll('details.sol').forEach((d) => { d.open = open; });
  e.target.textContent = open ? 'Masquer les solutions' : 'Afficher toutes les solutions';
});
"""


def build_html(banks, graine):
    total = sum(len(b["questions"]) for b in banks)
    errors = sum(1 for b in banks for q in b["questions"] if "error" in q)
    today = datetime.date.today().strftime("%d/%m/%Y")
    hl_light = _read("vendor", "highlight", "github.min.css")
    hl_dark = _read("vendor", "highlight", "github-dark.min.css")
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalogue des questions</title>
<style>
{_read("css", "style.css")}
@media (prefers-color-scheme: light) {{ {hl_light} }}
@media (prefers-color-scheme: dark) {{ {hl_dark} }}
{CSS}
</style>
<script>
{_read("vendor", "highlight", "highlight.min.js")}
</script>
</head>
<body>
<div class="cat">
  <nav><strong>Banques</strong><ul id="toc"></ul></nav>
  <div>
    <h1>Catalogue des questions</h1>
    <p class="muted">{total} questions de la banque, chacune avec un exemple tiré par le moteur
      (graine {graine}, le {today}). Chaque élève, à chaque essai, reçoit d'autres valeurs.{
        f" <strong>{errors} question(s) en erreur.</strong>" if errors else ""}</p>
    <div class="tools">
      <input id="search" type="search" placeholder="Rechercher (identifiant, titre, chapitre, compétence, énoncé)…" aria-label="Rechercher">
      <button id="toggle" type="button">Afficher toutes les solutions</button>
    </div>
    <main id="main"></main>
  </div>
</div>
<script type="application/json" id="data">{_json_for_script({"banks": banks})}</script>
<script>
{_markdown_js()}
{APP_JS}
</script>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Catalogue HTML des questions de la banque, avec un exemple par question.")
    parser.add_argument("--banque", default=os.path.join(ROOT, "banque"), help="dossier des fichiers de questions")
    parser.add_argument("--sortie", default="catalogue-questions.html", help="fichier HTML à écrire")
    parser.add_argument("--graine", type=int, default=1, help="change les exemples tirés")
    args = parser.parse_args(argv)
    banks = collect(args.banque, args.graine)
    with open(args.sortie, "w", encoding="utf-8") as f:
        f.write(build_html(banks, args.graine))
    total = sum(len(b["questions"]) for b in banks)
    errors = [f"{q.get('uid')} : {q['error']}" for b in banks for q in b["questions"] if "error" in q]
    print(f"{total} questions, {len(banks)} banques → {args.sortie}")
    for e in errors:
        print("  erreur", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
