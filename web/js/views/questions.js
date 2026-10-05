import { api, qs } from '../api.js';
import { codeArea, confirmBox, errorBox, h, modal, mount, pct, toast } from '../dom.js';
import { navigate, render, state } from '../app.js';
import { md } from '../markdown.js';
import { questionView } from '../player.js';

export function uidBadge(uid) {
  return uid ? h('span', { class: 'uid', title: 'Identifiant de la question' }, uid) : null;
}

// ---------------------------------------------------------------------------
// Liste
// ---------------------------------------------------------------------------

export async function listPage({ query }) {
  const [{ questions }, { chapters }, { classes }] = await Promise.all([
    api.get('/questions' + qs({ chapter_id: query.chapitre, class_id: query.classe, q: query.q, archived: query.archives })),
    api.get('/chapters'), api.get('/classes')]);
  const className = Object.fromEntries(classes.map((c) => [c.id, c.name]));
  const setQuery = (k, v) => navigate('/questions' + qs({ ...query, [k]: v }));
  const search = h('input', { type: 'search', placeholder: 'Rechercher : plusieurs mots, ex. somme arbre…', value: query.q || '',
    title: SEARCH_HELP });
  search.addEventListener('change', () => setQuery('q', search.value));
  const chapterSel = h('select', { onchange: (e) => setQuery('chapitre', e.target.value) },
    h('option', { value: '' }, 'Tous les chapitres'), chapters.map((c) => h('option', { value: c.id, selected: String(c.id) === query.chapitre }, c.name)));
  const classSel = h('select', { onchange: (e) => setQuery('classe', e.target.value) },
    h('option', { value: '' }, 'Toutes les classes'), classes.map((c) => h('option', { value: c.id, selected: String(c.id) === query.classe }, c.name)));
  const checks = [];
  const selected = () => checks.filter((c) => c.checked).map((c) => Number(c.value));

  const bulk = h('div', { class: 'row' },
    h('button', { onclick: () => bulkClasses(classes, selected()) }, 'Affecter la sélection à des classes…'),
    h('button', { onclick: () => exportQuestions(selected()) }, 'Exporter (JSON)'),
    h('button', { class: 'danger', onclick: () => bulkDelete(selected()) }, 'Supprimer la sélection…'),
    h('button', { onclick: duplicatesModal }, 'Supprimer les doublons…'),
    h('label', { class: 'btn', style: { cursor: 'pointer' } }, 'Importer (JSON)',
      h('input', { type: 'file', accept: '.json,application/json', style: { display: 'none' }, onchange: (e) => importFile(e.target.files[0]) })),
    h('button', { onclick: () => chaptersModal(chapters) }, 'Chapitres…'),
    h('a', { class: 'btn', href: '#/banques' }, '📚 Banques de questions'),
    h('button', { onclick: downloadReferential, title: 'Chapitres, compétences et questions existantes, à fournir à Claude pour créer de nouvelles questions' }, 'Référentiel pour Claude'));

  const sampleBoxes = {};
  const rows = questions.map((q) => {
    const cb = h('input', { type: 'checkbox', value: q.id, 'aria-label': 'Sélectionner' });
    checks.push(cb);
    const box = h('div', { class: 'sample' });
    sampleBoxes[q.id] = box;
    fillSample(box, q.sample);
    return h('tr', {},
      h('td', {}, cb),
      h('td', {}, uidBadge(q.uid)),
      h('td', { class: 'sample-cell' },
        h('div', { class: 'small' }, h('a', { href: `#/questions/${q.id}`, title: 'Modifier' }, q.title),
          q.archived ? h('span', { class: 'pill bad', style: { marginLeft: '.3rem' } }, 'archivée') : null,
          q.skills.length ? h('span', { class: 'muted' }, ' · ' + q.skills.join(' · ')) : null),
        box),
      h('td', { class: 'small' }, q.chapter || h('span', { class: 'muted' }, '—'),
        h('div', { class: 'muted' }, q.class_ids.map((id) => className[id]).filter(Boolean).join(', ') || 'aucune classe')),
      h('td', { class: 'num small' }, q.attempts, h('div', { class: 'muted' }, pct(q.avg_score))),
      h('td', { class: 'actions' },
        h('button', { class: 'small', onclick: () => previewQuestion(q.id) }, 'Aperçu'),
        h('a', { class: 'btn small', href: `#/questions/${q.id}` }, 'Modifier'),
        h('button', { class: 'small danger', onclick: () => deleteOne(q) }, 'Supprimer')));
  });
  // exemples d'énoncés manquants : générés par lots puis mémorisés côté serveur
  const missing = questions.filter((q) => !q.sample).map((q) => q.id);
  (async () => {
    for (let i = 0; i < missing.length; i += 12) {
      const chunk = missing.slice(i, i + 12);
      try {
        const { samples } = await api.post('/questions/samples', { ids: chunk });
        chunk.forEach((id) => fillSample(sampleBoxes[id], samples[id] || { error: 'exemple indisponible' }));
      } catch { chunk.forEach((id) => fillSample(sampleBoxes[id], { error: 'exemple indisponible' })); }
    }
  })();
  const all = h('input', { type: 'checkbox', 'aria-label': 'Tout sélectionner', title: 'Tout sélectionner', onchange: (e) => checks.forEach((c) => { c.checked = e.target.checked; }) });

  return h('div', {},
    h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, 'Banque de questions'),
      h('a', { class: 'btn primary', href: '#/questions/nouvelle' }, '+ Nouvelle question')),
    h('div', { class: 'row', style: { margin: '1rem 0' } },
      h('div', { style: { flex: 2, minWidth: '14rem' } }, search), h('div', { style: { flex: 1, minWidth: '10rem' } }, chapterSel),
      h('div', { style: { flex: 1, minWidth: '10rem' } }, classSel),
      h('label', { class: 'inline small' }, h('input', { type: 'checkbox', checked: query.archives === '1', onchange: (e) => setQuery('archives', e.target.checked ? '1' : '') }), 'archivées')),
    bulk,
    questions.length ? h('div', { class: 'table-wrap', style: { marginTop: '1rem' } }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, all), h('th', {}, 'N°'), h('th', {}, 'Question (exemple d\'énoncé)'), h('th', {}, 'Chapitre · classes'), h('th', { class: 'num' }, 'Réponses'), h('th', {}, ''))),
      h('tbody', {}, rows)))
      : h('div', { class: 'empty', style: { marginTop: '1rem' } },
        h('p', {}, 'La banque de questions est vide.'),
        h('div', { class: 'row', style: { justifyContent: 'center' } },
          h('a', { class: 'btn primary', href: '#/banques' }, '📚 Parcourir les banques de questions'),
          h('a', { class: 'btn', href: '#/questions/nouvelle' }, 'Créer ma première question'))));
}

// Aperçu d'une question telle que la verra un élève (données tirées au hasard, réponse testable).
export function previewModal(title, template, uid) {
  const box = h('div', {}, h('p', { class: 'muted' }, 'Génération…'));
  const show = async () => {
    const r = await api.post('/questions/preview', { template }).catch((e) => ({ ok: false, error: e.message }));
    if (!r.ok) return mount(box, h('div', { class: 'alert error' }, r.error));
    const res = r.result;
    mount(box,
      h('div', { class: 'row between small muted', style: { marginBottom: '.6rem' } },
        h('span', {}, `${res.variety.distinct} énoncé(s) différent(s) sur ${res.variety.samples} tirages`),
        h('button', { class: 'small primary', onclick: show }, '🎲 Nouvel exemple')),
      questionView(res.public, { submitLabel: 'Tester une réponse', onSubmit: async (answers) => {
        const c = await api.post('/questions/try', { template, seed: res.seed, answers });
        if (!c.ok) throw new Error(c.error);
        return c.result;
      } }),
      h('details', { class: 'help' }, h('summary', {}, 'Réponses attendues'),
        res.expected.map((e, i) => h('div', {}, h('strong', {}, `Réponse ${i + 1} : `), e ? md(e) : h('span', { class: 'muted' }, 'vérifiée par des tests cachés')))),
      res.solution ? h('details', { class: 'help' }, h('summary', {}, 'Correction'), md(res.solution)) : null);
  };
  show();
  return modal(uid ? `${uid} · ${title}` : title, box);
}

async function previewQuestion(id) {
  const { question } = await api.get(`/questions/${id}`);
  previewModal(question.title, question.template, question.uid);
}

// ---------------------------------------------------------------------------
// Banques de questions (fichiers JSON du répertoire banque/)
// ---------------------------------------------------------------------------

const BANK_STATUS = {
  archived: ['pill', 'archivée (sera restaurée)'],
  new: ['pill accent', 'nouvelle'],
  imported: ['pill good', 'déjà importée'],
  modified: ['pill bad', 'modifiée dans le fichier'],
};

// Aide de la recherche par mots-clés (voir app/search.py)
const SEARCH_HELP = 'Tous les mots doivent apparaître (titre, n°, chapitre, compétences, énoncé, correction). '
  + 'Majuscules et accents ne comptent pas ; « min » trouve aussi « minimum ». '
  + '-mot exclut les questions qui contiennent ce mot ; "des mots entre guillemets" cherchent l\'expression exacte.';

export async function banksPage({ query = {} } = {}) {
  const { dir, banks, results } = await api.get('/banks' + qs({ q: query.q }));
  const search = h('input', { type: 'search', placeholder: 'Rechercher dans toutes les banques : plusieurs mots, ex. somme arbre…',
    value: query.q || '', title: SEARCH_HELP });
  search.addEventListener('change', () => navigate('/banques' + qs({ q: search.value.trim() || undefined })));
  return h('div', {},
    h('p', {}, h('a', { href: '#/questions' }, '← Banque de questions de l\'application')),
    h('h1', {}, 'Banques de questions'),
    h('p', { class: 'muted' }, 'Chaque fichier JSON du répertoire ', h('code', {}, dir),
      " est une banque thématique. Déposez-y de nouveaux fichiers (par exemple ceux produits par votre projet Claude) : ils apparaissent ici. Importez les questions qui vous intéressent ; celles modifiées dans le fichier depuis l'import peuvent être mises à jour."),
    h('div', { class: 'field' }, search, h('div', { class: 'small muted' }, SEARCH_HELP)),
    results ? searchResults(results, query.q) : null,
    results ? null : banks.length ? h('div', { class: 'grid' }, banks.map((b) => h('div', { class: 'card' },
      h('h3', {}, b.error ? b.title : h('a', { href: `#/banques/${encodeURIComponent(b.id)}` }, b.title)),
      b.error ? h('div', { class: 'alert error' }, b.error) : [
        h('p', { class: 'small muted' }, b.description),
        h('div', { class: 'row small' }, `${b.count} question(s)`,
          b.new ? h('span', { class: BANK_STATUS.new[0] }, `${b.new} nouvelle(s)`) : null,
          b.imported ? h('span', { class: BANK_STATUS.imported[0] }, `${b.imported} importée(s)`) : null,
          b.modified ? h('span', { class: BANK_STATUS.modified[0] }, `${b.modified} modifiée(s)`) : null),
        h('div', { style: { marginTop: '.6rem' } }, h('a', { class: 'btn small', href: `#/banques/${encodeURIComponent(b.id)}` }, 'Ouvrir')),
      ])))
      : h('div', { class: 'empty' }, 'Aucun fichier dans le répertoire des banques.'));
}

// Résultats d'une recherche dans toutes les banques, avec import de la sélection
function searchResults(results, q) {
  if (!results.length) return h('div', { class: 'empty' }, `Aucune question ne contient tous les mots « ${q} ».`);
  const checks = [];
  const rows = results.map((r) => {
    const cb = h('input', { type: 'checkbox', checked: false, disabled: r.status === 'imported', 'aria-label': 'Sélectionner' });
    checks.push([cb, r]);
    const [cls, label] = BANK_STATUS[r.status];
    return h('tr', {},
      h('td', {}, cb),
      h('td', {}, uidBadge(r.uid)),
      h('td', {}, r.status !== 'new' ? h('a', { href: `#/questions/${r.question_id}` }, r.title) : r.title,
        h('div', { class: 'small muted' }, [r.chapter, ...(r.skills || [])].filter(Boolean).join(' · '))),
      h('td', { class: 'small' }, h('a', { href: `#/banques/${encodeURIComponent(r.bank_id)}` }, r.bank_title)),
      h('td', {}, h('span', { class: cls }, label)),
      h('td', { class: 'num' }, h('button', { class: 'small', onclick: () => previewModal(r.title, r.template, r.uid) }, 'Aperçu')));
  });
  const out = h('div');
  const btn = h('button', { class: 'primary' }, 'Importer / mettre à jour la sélection');
  btn.addEventListener('click', async () => {
    const sel = checks.filter(([c]) => c.checked && !c.disabled).map(([, r]) => r);
    if (!sel.length) return mount(out, h('div', { class: 'alert error' }, 'Aucune question sélectionnée.'));
    btn.disabled = true;
    mount(out, h('div', { class: 'alert info' }, `Chaque question est testée sur 20 tirages avant import (${sel.length} question(s))…`));
    // un import par fichier de banque, puis un seul compte rendu
    const total = { created: [], updated: [], restored: [], skipped: [], errors: [], warnings: [] };
    try {
      for (const bid of [...new Set(sel.map((r) => r.bank_id))]) {
        const mine = sel.filter((r) => r.bank_id === bid);
        const r = await api.post(`/banks/${encodeURIComponent(bid)}/import`, {
          titles: mine.filter((x) => x.status === 'new' || x.status === 'archived').map((x) => x.title),
          update: mine.filter((x) => x.status === 'modified').map((x) => x.title), class_ids: [] });
        for (const k of Object.keys(total)) total[k].push(...(r[k] || []));
      }
      importReport(total);
      render();
    } catch (e) { mount(out, errorBox(e)); btn.disabled = false; }
  });
  return h('div', {},
    h('p', {}, `${results.length} question(s) trouvée(s). `, h('a', { href: '#/banques' }, 'Effacer la recherche')),
    h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, ''), h('th', {}, 'N°'), h('th', {}, 'Question'), h('th', {}, 'Banque'), h('th', {}, 'État'), h('th', {}, ''))),
      h('tbody', {}, rows))),
    h('p', { class: 'small muted' }, 'Les questions importées d\'ici ne sont affectées à aucune classe : affectez-les ensuite depuis la page Questions (ou importez-les depuis la page de leur banque).'),
    out, h('div', { style: { marginTop: '.6rem' } }, btn));
}

export async function bankPage({ params }) {
  const [{ bank }, { classes }] = await Promise.all([api.get(`/banks/${encodeURIComponent(params.id)}`), api.get('/classes')]);
  const checks = [];
  const groups = {};
  bank.questions.forEach((q) => (groups[q.chapter || 'Sans chapitre'] ||= []).push(q));
  const rows = Object.entries(groups).map(([ch, qs]) => [
    h('tr', {}, h('td', { colspan: 6, class: 'small', style: { fontWeight: 600, background: 'var(--surface-2)' } }, ch)),
    qs.map((q) => {
      const cb = h('input', { type: 'checkbox', value: q.title, checked: q.status !== 'imported', disabled: q.status === 'imported', 'aria-label': 'Sélectionner' });
      cb.dataset.status = q.status;
      checks.push(cb);
      const [cls, label] = BANK_STATUS[q.status];
      return h('tr', {},
        h('td', {}, cb),
        h('td', {}, uidBadge(q.uid)),
        h('td', {}, q.status !== 'new' ? h('a', { href: `#/questions/${q.question_id}` }, q.title) : q.title,
          h('div', { class: 'small muted' }, (q.skills || []).join(' · '))),
        h('td', { class: 'small' }, ['', 'facile', 'moyen', 'difficile'][q.difficulty || 2]),
        h('td', {}, h('span', { class: cls }, label)),
        h('td', { class: 'num' }, h('button', { class: 'small', onclick: () => previewModal(q.title, q.template, q.uid) }, 'Aperçu')));
    }),
  ]);
  const boxes = classes.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id }), c.name));
  const out = h('div');
  const btn = h('button', { class: 'primary' }, 'Importer / mettre à jour la sélection');
  btn.addEventListener('click', async () => {
    const sel = checks.filter((c) => c.checked && !c.disabled);
    const titles = sel.filter((c) => c.dataset.status === 'new' || c.dataset.status === 'archived').map((c) => c.value);
    const update = sel.filter((c) => c.dataset.status === 'modified').map((c) => c.value);
    if (!titles.length && !update.length) return mount(out, h('div', { class: 'alert error' }, 'Aucune question sélectionnée.'));
    btn.disabled = true;
    mount(out, h('div', { class: 'alert info' }, `Chaque question est testée sur 20 tirages avant import (${titles.length + update.length} question(s))…`));
    try {
      const class_ids = boxes.map((b) => b.querySelector('input')).filter((x) => x.checked).map((x) => Number(x.value));
      const r = await api.post(`/banks/${encodeURIComponent(bank.id)}/import`, { titles, update, class_ids });
      importReport(r);
      render();
    } catch (e) { mount(out, errorBox(e)); btn.disabled = false; }
  });
  const setAll = (v) => checks.forEach((c) => { if (!c.disabled) c.checked = v; });
  return h('div', {},
    h('p', {}, h('a', { href: '#/banques' }, '← Banques de questions')),
    h('h1', {}, bank.title),
    bank.description ? h('p', { class: 'muted' }, bank.description) : null,
    h('p', { class: 'small muted' }, 'Fichier ', h('code', {}, `banque/${bank.id}.json`), '. « Aperçu » permet d\'essayer une question avant de l\'importer. Une question « modifiée dans le fichier » a déjà été importée mais sa version du fichier est différente : la mettre à jour crée une nouvelle version (les réponses passées des élèves sont conservées).'),
    h('div', { class: 'row small', style: { margin: '.6rem 0' } },
      h('button', { class: 'small link', onclick: () => setAll(true) }, 'tout cocher'),
      h('button', { class: 'small link', onclick: () => setAll(false) }, 'tout décocher')),
    h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, ''), h('th', {}, 'N°'), h('th', {}, 'Question'), h('th', {}, 'Difficulté'), h('th', {}, 'État'), h('th', {}, ''))),
      h('tbody', {}, rows))),
    classes.length ? h('div', { class: 'field', style: { marginTop: '1rem' } }, h('label', {}, 'Affecter aussi aux classes (facultatif)'), h('div', { class: 'row' }, boxes)) : null,
    out, h('div', { style: { marginTop: '.6rem' } }, btn));
}

// Exemple d'énoncé dans la liste : l'énoncé et l'intitulé des champs (jamais les options d'un QCM)
function fillSample(box, sample) {
  if (!box) return;
  if (!sample) return box.replaceChildren(h('span', { class: 'muted small' }, 'génération de l\'exemple…'));
  if (sample.error) return box.replaceChildren(h('span', { class: 'error-line small' }, `⚠ ${sample.error}`));
  const labels = sample.fields.map((f) => f.label).filter((l) => l && l.trim());
  const content = h('div', { class: 'sample-body' }, md(sample.statement),
    labels.length ? h('ul', { class: 'sample-fields' }, labels.map((l) => h('li', {}, md(l, 'span')))) : null);
  const more = h('button', { class: 'link small sample-more', type: 'button' }, 'voir tout');
  more.addEventListener('click', () => {
    const open = box.classList.toggle('open');
    more.textContent = open ? 'réduire' : 'voir tout';
  });
  box.replaceChildren(content, more);
  // le bouton n'apparaît que si l'énoncé est plus long que la zone visible
  requestAnimationFrame(() => { if (content.scrollHeight <= content.clientHeight + 4) { more.remove(); box.classList.add('short'); } });
}

async function deleteOne(q) {
  if (!confirmBox(`Supprimer la question ${q.uid ? q.uid + ' ' : ''}« ${q.title} » ?\n(Si des élèves y ont déjà répondu, elle sera archivée pour garder les statistiques.)`)) return;
  const r = await api.del(`/questions/${q.id}`);
  toast(r.archived ? 'Question archivée (des élèves y avaient répondu).' : 'Question supprimée.');
  render();
}

function bulkDelete(ids) {
  if (!ids.length) return toast('Cochez les questions à supprimer.', 'error');
  const isAdmin = state.user.role === 'admin';
  const purge = h('input', { type: 'checkbox' });
  const btn = h('button', { class: 'primary danger' }, `Supprimer ${ids.length} question(s)`);
  btn.addEventListener('click', async () => {
    if (purge.checked && !confirmBox('Effacer définitivement ces questions ET toutes les réponses des élèves qui s\'y rapportent ?')) return;
    btn.disabled = true;
    const r = await api.post('/questions/bulk-delete', { ids, purge: purge.checked });
    close();
    toast(`${r.deleted} supprimée(s)` + (r.archived ? `, ${r.archived} archivée(s) (des élèves y avaient répondu)` : '') + '.');
    render();
  });
  const close = modal('Supprimer des questions', h('div', {},
    h('p', {}, `${ids.length} question(s) sélectionnée(s).`),
    h('p', { class: 'small muted' }, 'Une question à laquelle des élèves ont déjà répondu est archivée plutôt que supprimée : elle n\'est plus proposée, mais les statistiques sont conservées.'),
    isAdmin ? h('label', { class: 'inline' }, purge, 'Supprimer définitivement, y compris les réponses des élèves') : null,
    h('div', { style: { marginTop: '1rem' } }, btn)));
}

async function duplicatesModal() {
  const { groups } = await api.get('/questions/duplicates');
  if (!groups.length) return modal('Doublons', h('p', {}, 'Aucune question en double (même titre). 👍'));
  const n = groups.reduce((acc, g) => acc + g.remove.length, 0);
  const btn = h('button', { class: 'primary' }, `Supprimer ${n} doublon(s)`);
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    const r = await api.post('/questions/remove-duplicates');
    close();
    toast(`${r.deleted + r.archived} doublon(s) retiré(s).`);
    render();
  });
  const close = modal('Questions en double', h('div', {},
    h('p', { class: 'small muted' }, 'Pour chaque titre, on garde la question qui a le plus de réponses d\'élèves (sinon celle de la banque, sinon la plus ancienne). Ses affectations aux classes et aux séances reprennent celles des doublons.'),
    h('table', { class: 'data' }, h('thead', {}, h('tr', {}, h('th', {}, 'Question'), h('th', {}, 'Gardée'), h('th', {}, 'Retirées'))),
      h('tbody', {}, groups.map((g) => h('tr', {}, h('td', {}, g.keep.title), h('td', {}, uidBadge(g.keep.uid)),
        h('td', {}, g.remove.map((d) => uidBadge(d.uid))))))),
    h('div', { style: { marginTop: '1rem' } }, btn)));
}

function bulkClasses(classes, ids) {
  if (!ids.length) return toast('Sélectionnez des questions.', 'error');
  const boxes = classes.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id }), c.name));
  const go = async (add) => {
    const cids = boxes.map((b) => b.querySelector('input')).filter((x) => x.checked).map((x) => Number(x.value));
    await api.post('/questions/bulk-classes', { question_ids: ids, class_ids: cids, add });
    close();
    render();
  };
  const close = modal(`${ids.length} question(s) sélectionnée(s)`, h('div', {},
    h('div', { class: 'stack' }, boxes),
    h('div', { class: 'row', style: { marginTop: '1rem' } },
      h('button', { class: 'primary', onclick: () => go(true) }, 'Ajouter à ces classes'),
      h('button', { onclick: () => go(false) }, 'Retirer de ces classes'))));
}

async function exportQuestions(ids) {
  const data = await api.get('/questions/export' + qs({ ids: ids.join(',') }));
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = h('a', { href: URL.createObjectURL(blob), download: 'questions.json' });
  document.body.append(a);
  a.click();
  a.remove();
}

async function importFile(file) {
  if (!file) return;
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch (e) {
    return modal('Fichier illisible', h('div', { class: 'alert error' }, `Ce fichier n'est pas un JSON valide : ${e.message}`));
  }
  const close = modal('Import en cours', h('p', {}, 'Chaque question est testée sur 20 tirages (génération, variété, correction)… cela peut prendre une minute.'));
  try {
    const r = await api.post('/questions/import', data);
    close();
    importReport(r);
    render();
  } catch (e) { close(); toast(e.message, 'error'); }
}

function importReport(r) {
  modal("Résultat de l'import", h('div', {},
    h('div', { class: 'alert info' }, `${r.created.length} question(s) importée(s)` + (r.updated && r.updated.length ? `, ${r.updated.length} mise(s) à jour` : '')
      + (r.restored && r.restored.length ? `, ${r.restored.length} restaurée(s)` : '') + '.'),
    r.skipped && r.skipped.length ? h('details', { class: 'help' },
      h('summary', {}, `${r.skipped.length} question(s) déjà présente(s), non réimportée(s)`),
      h('ul', { class: 'small' }, r.skipped.map((t) => h('li', {}, t)))) : null,
    r.warnings && r.warnings.length ? [h('h3', {}, 'À vérifier'),
      h('p', { class: 'small muted' }, "Ces questions ont été importées mais l'auto-test a relevé des points à contrôler. Ouvrez-les dans l'éditeur pour les corriger."),
      h('ul', {}, r.warnings.map((w) => h('li', {}, h('a', { href: `#/questions/${w.id}` }, w.title), h('ul', { class: 'small' }, w.messages.map((m) => h('li', {}, m))))))] : null,
    r.errors.length ? [h('h3', {}, 'Non importées'), h('div', { class: 'alert error' }, h('ul', {}, r.errors.map((e) => h('li', {}, e))))] : null));
}

async function downloadReferential() {
  const res = await fetch('/api/questions/referential', { credentials: 'same-origin' });
  if (!res.ok) return toast('Export impossible', 'error');
  const a = h('a', { href: URL.createObjectURL(await res.blob()), download: 'referentiel-questionnapp.md' });
  document.body.append(a);
  a.click();
  a.remove();
}

function chaptersModal(chapters) {
  const name = h('input', { type: 'text', placeholder: 'Nouveau chapitre' });
  const list = h('table', { class: 'data' }, h('tbody', {}, chapters.map((c, i) => h('tr', {},
    h('td', {}, c.name), h('td', { class: 'num small muted' }, `${c.questions} q.`),
    h('td', { class: 'num' },
      h('button', { class: 'small', disabled: i === 0, onclick: () => move(i, -1) }, '↑'),
      h('button', { class: 'small', disabled: i === chapters.length - 1, onclick: () => move(i, 1) }, '↓'),
      h('button', { class: 'small', onclick: async () => {
        const n = prompt('Nouveau nom', c.name);
        if (n) { await api.patch(`/chapters/${c.id}`, { name: n }); close(); render(); }
      } }, 'Renommer'),
      h('button', { class: 'small danger', onclick: async () => {
        if (!confirmBox(`Supprimer le chapitre « ${c.name} » ? Ses questions deviennent « sans chapitre ».`)) return;
        await api.del(`/chapters/${c.id}`);
        close();
        render();
      } }, '✕'))))));
  async function move(i, d) {
    const order = [...chapters];
    [order[i], order[i + d]] = [order[i + d], order[i]];
    await Promise.all(order.map((c, pos) => api.patch(`/chapters/${c.id}`, { position: pos + 1 })));
    close();
    render();
  }
  const close = modal('Chapitres', h('div', {}, list,
    h('form', { class: 'row', style: { marginTop: '1rem' }, onsubmit: async (e) => {
      e.preventDefault();
      if (!name.value.trim()) return;
      await api.post('/chapters', { name: name.value });
      close();
      render();
    } }, h('div', { style: { flex: 1 } }, name), h('button', { class: 'primary', type: 'submit' }, 'Ajouter'))));
}

// ---------------------------------------------------------------------------
// Modèles de départ
// ---------------------------------------------------------------------------

const STARTERS = {
  sortie: {
    label: "Qu'affiche ce programme ?",
    template: {
      code: 'a = randint(2, 9)\nn = randint(3, 6)\nsrc = f"""s = 0\nfor i in range({n}):\n    s = s + {a}\nprint(s)"""\nsortie = run(src)',
      statement: "Qu'affiche le programme suivant ?\n\n{{ code_block(src) }}",
      fields: [{ type: 'text', label: 'Affichage', answer: 'sortie' }],
      solution: 'La boucle ajoute {{ a }} à `s`, {{ n }} fois : le programme affiche **{{ sortie }}**.',
    },
  },
  fonction: {
    label: 'Écrire une fonction (tests aléatoires)',
    template: {
      code: 'k = randint(2, 5)\ncases = []\nfor _ in range(6):\n    L = randlist(randint(0, 8), -20, 20)\n    cases.append(((L,), [x * k for x in L]))',
      statement: 'Écrire une fonction `multiplie(L)` qui renvoie une nouvelle liste où chaque élément de `L` est multiplié par {{ k }}.',
      fields: [{ type: 'code', label: 'Votre code', function: 'multiplie', cases: 'cases', forbid: [], starter: 'def multiplie(L):\n    ' }],
      solution: '```python\ndef multiplie(L):\n    return [x * {{ k }} for x in L]\n```',
    },
  },
  qcm: {
    label: 'QCM (options générées)',
    template: {
      code: "a, b = randint(10, 30), randint(2, 5)\nexpr = f'{a} // {b}'\nbonne = a // b\nmauvaises = sample(sorted({round(a / b, 2), a % b, bonne + 1, bonne - 1} - {bonne}), 3)",
      statement: 'Que vaut `{{ expr }}` ?',
      fields: [{ type: 'choice', label: '', options: '[(str(bonne), True)] + [(str(m), False) for m in mauvaises]' }],
      solution: '`//` est la division entière : `{{ expr }}` vaut {{ bonne }}.',
    },
  },
  sql: {
    label: 'Requête SQL',
    template: {
      code: "rows = [(i, choice(PRENOMS), randint(8, 20)) for i in range(1, 9)]\nsetup = 'CREATE TABLE Note(id INTEGER PRIMARY KEY, prenom TEXT, note INTEGER);\\n' + sql_insert('Note', rows)\nseuil = randint(10, 15)",
      statement: "Table **Note** :\n\n{{ sql_table(setup, 'Note') }}\n\nÉcrire une requête donnant le prénom des élèves ayant une note supérieure ou égale à {{ seuil }}.",
      fields: [{ type: 'sql', label: 'Requête', setup: 'setup', answer: "f'SELECT prenom FROM Note WHERE note >= {seuil}'" }],
      solution: '```sql\nSELECT prenom FROM Note WHERE note >= {{ seuil }}\n```',
    },
  },
  nombre: {
    label: 'Réponse numérique (conversion)',
    template: {
      code: 'n = randint(16, 255)',
      statement: "Quelle est l'écriture décimale du nombre binaire `{{ tobase(n, 2) }}` ?",
      fields: [{ type: 'number', label: '', answer: 'n' }],
      solution: '`{{ tobase(n, 2) }}` = {{ n }}',
    },
  },
};

const FIELD_TYPES = { number: 'Nombre', text: 'Texte / sortie de programme', choice: 'QCM', code: 'Code Python', sql: 'Requête SQL' };

function defaultField(type) {
  return {
    number: { type, label: '', answer: '', tolerance: 0 },
    text: { type, label: '', answer: '' },
    choice: { type, label: '', options: [{ text: '', correct: true }, { text: '', correct: false }] },
    code: { type, label: '', starter: '', function: '', cases: '', tests: '', forbid: [] },
    sql: { type, label: '', setup: 'setup', answer: '' },
  }[type];
}

// ---------------------------------------------------------------------------
// Éditeur
// ---------------------------------------------------------------------------

export async function editorPage({ params }) {
  const isNew = !params.id;
  const [{ chapters }, { skills }, { classes }, existing] = await Promise.all([
    api.get('/chapters'), api.get('/skills'), api.get('/classes'),
    isNew ? Promise.resolve(null) : api.get(`/questions/${params.id}`).then((r) => r.question)]);
  const model = existing
    ? { title: existing.title, chapter_id: existing.chapter_id, difficulty: existing.difficulty, skills: existing.skills, class_ids: existing.class_ids, template: existing.template }
    : { title: '', chapter_id: null, difficulty: 2, skills: [], class_ids: [], template: structuredClone(STARTERS.sortie.template) };
  const t = model.template;
  t.fields = t.fields || [];

  let seed = null;
  let previewTimer = null;
  const schedulePreview = () => {
    if (!autoPreview.checked) return;
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => doPreview(false), 900);
  };

  // --- métadonnées
  const title = h('input', { type: 'text', value: model.title, placeholder: 'ex. Boucle for et range' });
  const uidInput = h('input', { type: 'text', value: existing ? existing.uid || '' : '', placeholder: 'ex. DICO-21', style: { textTransform: 'uppercase' } });
  const chapterSel = h('select', {}, h('option', { value: '' }, '— aucun —'),
    chapters.map((c) => h('option', { value: c.id, selected: c.id === model.chapter_id }, c.name)),
    h('option', { value: '__new' }, '+ Nouveau chapitre…'));
  const newChapter = h('input', { type: 'text', placeholder: 'Nom du nouveau chapitre', style: { display: 'none', marginTop: '.3rem' } });
  chapterSel.addEventListener('change', () => { newChapter.style.display = chapterSel.value === '__new' ? '' : 'none'; });
  const difficulty = h('select', {}, [[1, 'Facile'], [2, 'Moyen'], [3, 'Difficile']].map(([v, l]) => h('option', { value: v, selected: v === model.difficulty }, l)));
  const skillsInput = h('input', { type: 'text', value: model.skills.join(' ; '), list: 'skills-list', placeholder: 'ex. Boucle for ; Tracer un programme' });
  const skillsList = h('datalist', { id: 'skills-list' }, skills.map((s) => h('option', { value: s.name })));
  const classBoxes = classes.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id, checked: model.class_ids.includes(c.id) }), c.name));

  // --- modèle
  const code = codeArea({ rows: 12, 'aria-label': 'Code générateur' });
  code.value = t.code || '';
  code.addEventListener('input', () => { t.code = code.value; schedulePreview(); });
  const statement = h('textarea', { rows: 6, class: 'code', style: { whiteSpace: 'pre-wrap' }, 'aria-label': 'Énoncé' });
  statement.value = t.statement || '';
  statement.addEventListener('input', () => { t.statement = statement.value; schedulePreview(); });
  const solution = h('textarea', { rows: 4, class: 'code', style: { whiteSpace: 'pre-wrap', minHeight: '5rem' }, 'aria-label': 'Correction' });
  solution.value = t.solution || '';
  solution.addEventListener('input', () => { t.solution = solution.value; schedulePreview(); });
  const fieldsBox = h('div');
  const hintsArea = h('textarea', { rows: 4, class: 'code', style: { whiteSpace: 'pre-wrap', minHeight: '5rem' }, 'aria-label': 'Indices',
    placeholder: "Indice 1 (après la 1re erreur)\n---\nIndice 2 (après la 2e erreur)" });
  hintsArea.value = (t.hints || []).join('\n---\n');
  hintsArea.addEventListener('input', () => {
    const hints = hintsArea.value.split(/^---\s*$/m).map((x) => x.trim()).filter(Boolean);
    if (hints.length) t.hints = hints; else delete t.hints;
    schedulePreview();
  });
  const triesSel = h('select', { style: { width: 'auto' } }, h('option', { value: '' }, 'automatique (3, ou 1 pour un vrai/faux)'),
    [1, 2, 3, 4, 5].map((n) => h('option', { value: n, selected: t.max_tries === n }, `${n} essai${n > 1 ? 's' : ''}`)));
  triesSel.addEventListener('change', () => { if (triesSel.value) t.max_tries = Number(triesSel.value); else delete t.max_tries; schedulePreview(); });

  const renderFields = () => {
    fieldsBox.replaceChildren(...t.fields.map((f, i) => fieldEditor(f, i)),
      h('div', { class: 'row' }, h('span', { class: 'small muted' }, 'Ajouter une réponse :'),
        Object.entries(FIELD_TYPES).map(([k, l]) => h('button', { class: 'small', type: 'button', onclick: () => { t.fields.push(defaultField(k)); renderFields(); schedulePreview(); } }, '+ ' + l))));
  };

  const input = (obj, key, attrs = {}, parse = (v) => v) => {
    const el = h('input', { type: 'text', value: obj[key] ?? '', ...attrs });
    el.addEventListener('input', () => { obj[key] = parse(el.value); schedulePreview(); });
    return el;
  };
  const check = (obj, key, label) => {
    const el = h('input', { type: 'checkbox', checked: Boolean(obj[key]) });
    el.addEventListener('change', () => { obj[key] = el.checked; schedulePreview(); });
    return h('label', { class: 'inline small' }, el, label);
  };
  const area = (obj, key, rows = 4, isCode = true) => {
    const el = isCode ? codeArea({ rows }) : h('textarea', { rows });
    el.value = obj[key] ?? '';
    el.addEventListener('input', () => { obj[key] = el.value; schedulePreview(); });
    return isCode ? el.container : el;
  };
  const labelled = (label, el, hint) => h('div', { class: 'field' }, h('label', {}, label), el, hint ? h('div', { class: 'hint' }, hint) : null);

  function fieldEditor(f, i) {
    const typeSel = h('select', { style: { width: 'auto' } }, Object.entries(FIELD_TYPES).map(([k, l]) => h('option', { value: k, selected: k === f.type }, l)));
    typeSel.addEventListener('change', () => { t.fields[i] = { ...defaultField(typeSel.value), label: f.label }; renderFields(); schedulePreview(); });
    const body = [];
    body.push(labelled('Intitulé (facultatif, Markdown, {{ }} autorisés)', input(f, 'label')));
    if (f.type === 'number') {
      body.push(h('div', { class: 'fields-3' },
        labelled('Réponse (expression Python)', input(f, 'answer', { class: 'code', placeholder: 'ex. a * b' })),
        labelled('Tolérance', input(f, 'tolerance', { type: 'number', step: 'any' }, (v) => Number(v) || 0)),
        labelled('Unité affichée', input(f, 'suffix', { placeholder: 'ex. octets' }))));
    } else if (f.type === 'text') {
      body.push(labelled('Réponse (expression Python : une chaîne, ou une liste de chaînes acceptées)', input(f, 'answer', { placeholder: 'ex. run(src)  ou  [str(n), hex(n)]' })));
      body.push(h('div', { class: 'row' }, check(f, 'multiline', 'réponse sur plusieurs lignes'), check(f, 'ignore_case', 'ignorer la casse'),
        check(f, 'ignore_spaces', 'ignorer les espaces'), check(f, 'ignore_accents', 'ignorer les accents')));
    } else if (f.type === 'choice') {
      const exprMode = typeof f.options === 'string';
      const modeSel = h('select', { style: { width: 'auto' } }, h('option', { value: 'list', selected: !exprMode }, 'Liste d\'options'), h('option', { value: 'expr', selected: exprMode }, 'Options générées (expression Python)'));
      modeSel.addEventListener('change', () => {
        f.options = modeSel.value === 'expr' ? "[('bonne réponse', True), ('mauvaise', False)]" : [{ text: '', correct: true }, { text: '', correct: false }];
        renderFields(); schedulePreview();
      });
      body.push(h('div', { class: 'row', style: { marginBottom: '.5rem' } }, modeSel, check(f, 'multiple', 'plusieurs réponses correctes'),
        h('label', { class: 'inline small' }, (() => { const el = h('input', { type: 'checkbox', checked: f.shuffle !== false }); el.addEventListener('change', () => { f.shuffle = el.checked; schedulePreview(); }); return el; })(), 'mélanger les options')));
      if (exprMode) {
        body.push(labelled('Expression donnant une liste de couples (texte, correct)', input(f, 'options', { placeholder: "[(str(bonne), True)] + [(str(x), False) for x in pieges]" }),
          'Deux options identiques déclenchent un nouveau tirage des valeurs.'));
      } else {
        f.options.forEach((o, j) => {
          const corrSel = h('select', {}, h('option', { value: 'true', selected: o.correct === true }, '✓ correcte'), h('option', { value: 'false', selected: o.correct === false || o.correct === undefined }, '✗ incorrecte'),
            h('option', { value: 'expr', selected: typeof o.correct === 'string' }, 'si condition…'));
          const cond = h('input', { type: 'text', value: typeof o.correct === 'string' ? o.correct : '', placeholder: 'condition Python, ex. a % 2 == 0', style: { display: typeof o.correct === 'string' ? '' : 'none', gridColumn: '1 / -1' } });
          corrSel.addEventListener('change', () => { o.correct = corrSel.value === 'expr' ? (cond.value || 'True') : corrSel.value === 'true'; cond.style.display = corrSel.value === 'expr' ? '' : 'none'; schedulePreview(); });
          cond.addEventListener('input', () => { o.correct = cond.value; schedulePreview(); });
          body.push(h('div', { class: 'opt-row' }, input(o, 'text', { placeholder: `Option ${j + 1} (Markdown, {{ }} autorisés)` }), corrSel,
            h('button', { class: 'small', type: 'button', title: 'Supprimer', onclick: () => { f.options.splice(j, 1); renderFields(); schedulePreview(); } }, '✕'), cond));
        });
        body.push(h('button', { class: 'small', type: 'button', onclick: () => { f.options.push({ text: '', correct: false }); renderFields(); } }, '+ option'));
      }
    } else if (f.type === 'code') {
      body.push(labelled('Code de départ proposé à l\'élève', area(f, 'starter', 3)));
      body.push(h('div', { class: 'fields-2' },
        labelled('Nom de la fonction à tester', input(f, 'function', { placeholder: 'ex. somme' })),
        labelled('Cas de test (expression Python)', input(f, 'cases', { placeholder: 'ex. cases' }), 'Liste de couples ((arguments,), résultat attendu), générée dans le code.')));
      body.push(labelled('Tests supplémentaires (Python, facultatif)', area(f, 'tests', 3),
        "Utilisez check(condition, message) ou check_equal(obtenu, attendu). Les fonctions de l'élève et les variables du générateur sont accessibles."));
      const forbid = h('input', { type: 'text', value: (f.forbid || []).join(', '), placeholder: 'ex. sum, sorted, import, while' });
      forbid.addEventListener('input', () => { f.forbid = forbid.value.split(',').map((s) => s.trim()).filter(Boolean); });
      body.push(h('div', { class: 'fields-2' }, labelled('Noms interdits', forbid),
        labelled('Temps max (s)', input(f, 'time_limit', { type: 'number', step: '0.5', placeholder: '2' }, (v) => Number(v) || undefined))));
      body.push(h('div', { class: 'row' }, check(f, 'all_or_nothing', 'tout ou rien (sinon score = proportion de tests réussis)')));
    } else if (f.type === 'sql') {
      body.push(h('div', { class: 'fields-2' },
        labelled('Script de création de la base (expression)', input(f, 'setup', { placeholder: 'setup' }), 'Variable du générateur contenant CREATE TABLE / INSERT.'),
        labelled('Requête de référence (expression)', input(f, 'answer', { placeholder: "f'SELECT ... WHERE x > {seuil}'" }))));
      body.push(labelled('Requête de départ', area(f, 'starter', 2)));
      body.push(check(f, 'ordered', "l'ordre des lignes compte (ORDER BY)"));
    }
    return h('div', { class: 'field-card' },
      h('div', { class: 'head' }, h('strong', {}, `Réponse ${i + 1}`), typeSel, h('span', { style: { flex: 1 } }),
        h('button', { class: 'small', type: 'button', disabled: i === 0, onclick: () => { [t.fields[i - 1], t.fields[i]] = [t.fields[i], t.fields[i - 1]]; renderFields(); schedulePreview(); } }, '↑'),
        h('button', { class: 'small danger', type: 'button', onclick: () => { t.fields.splice(i, 1); renderFields(); schedulePreview(); } }, 'Supprimer')),
      body);
  }
  renderFields();

  // --- aperçu
  const previewBox = h('div', {}, h('p', { class: 'muted' }, "Cliquez sur « Nouvel exemple » pour générer l'énoncé."));
  const autoPreview = h('input', { type: 'checkbox', checked: true });
  async function doPreview(newSeed) {
    if (newSeed) seed = null;
    const body = { template: t };
    if (seed !== null) body.seed = seed;
    const r = await api.post('/questions/preview', body).catch((e) => ({ ok: false, error: e.message }));
    code.markLine(!r.ok && r.where === 'code' ? r.line : null);
    if (!r.ok) {
      mount(previewBox, h('div', { class: 'alert error' },
        h('strong', {}, 'Erreur'), r.where ? ` (${r.where}${r.line ? `, ligne ${r.line}` : ''})` : '', ' : ', r.error));
      return;
    }
    const res = r.result;
    seed = res.seed;
    const v = res.variety;
    mount(previewBox, 
      h('div', { class: 'row small muted', style: { marginBottom: '.6rem' } }, `Graine ${res.seed}`,
        h('span', { class: 'pill ' + (v.distinct >= Math.min(10, v.samples) ? 'good' : 'bad') }, `${v.distinct} énoncé(s) différent(s) sur ${v.samples} tirages`)),
      res.deterministic ? null : h('div', { class: 'alert warn' }, "Attention : le générateur ne donne pas le même résultat pour une même graine. N'utilisez que les fonctions aléatoires fournies (randint, choice…)."),
      v.distinct < Math.min(5, v.samples) ? h('div', { class: 'alert warn' }, "Peu de variété : les élèves risquent de retomber sur les mêmes données. (C'est normal si seuls les tests cachés varient.)") : null,
      questionView(res.public, { submitLabel: 'Tester ma réponse', onSubmit: async (answers) => {
        const c = await api.post('/questions/try', { template: t, seed: res.seed, answers });
        if (!c.ok) throw new Error(c.error);
        return c.result;
      } }),
      h('details', { class: 'help' }, h('summary', {}, 'Réponses attendues'),
        res.expected.map((e, i) => h('div', {}, h('strong', {}, `Réponse ${i + 1} : `), e ? md(e) : h('span', { class: 'muted' }, 'vérifiée par les tests')))),
      res.solution ? h('details', { class: 'help' }, h('summary', {}, 'Correction'), md(res.solution)) : null,
      res.hints && res.hints.length ? h('details', { class: 'help' }, h('summary', {}, `Indices (${res.hints.length})`),
        res.hints.map((x, i) => h('div', {}, h('strong', {}, `Indice ${i + 1} : `), md(x)))) : null);
  }

  // --- enregistrement
  const err = h('div');
  async function save() {
    err.replaceChildren();
    const payload = {
      title: title.value, uid: uidInput.value.trim() || undefined, difficulty: Number(difficulty.value), template: t,
      skills: skillsInput.value.split(/[;\n]/).map((s) => s.trim()).filter(Boolean),
      class_ids: classBoxes.map((b) => b.querySelector('input')).filter((x) => x.checked).map((x) => Number(x.value)),
    };
    if (chapterSel.value === '__new') payload.chapter_name = newChapter.value;
    else payload.chapter_id = chapterSel.value ? Number(chapterSel.value) : null;
    try {
      if (isNew) {
        const r = await api.post('/questions', payload);
        toast('Question créée.');
        navigate(`/questions/${r.id}`);
      } else {
        await api.put(`/questions/${params.id}`, payload);
        toast('Question enregistrée.');
      }
    } catch (e) {
      err.replaceChildren(h('div', { class: 'alert error' }, e.message, e.data.where ? ` (${e.data.where}${e.data.line ? `, ligne ${e.data.line}` : ''})` : ''));
    }
  }

  const starterSel = h('select', { style: { width: 'auto' } }, h('option', { value: '' }, 'Partir d\'un modèle…'),
    Object.entries(STARTERS).map(([k, s]) => h('option', { value: k }, s.label)));
  starterSel.addEventListener('change', () => {
    const s = STARTERS[starterSel.value];
    if (!s || !confirmBox('Remplacer le contenu actuel par ce modèle ?')) { starterSel.value = ''; return; }
    model.template = structuredClone(s.template);
    editorReplace();
  });
  function editorReplace() {
    Object.assign(t, model.template);
    code.value = t.code; statement.value = t.statement; solution.value = t.solution || '';
    hintsArea.value = (t.hints || []).join('\n---\n'); triesSel.value = t.max_tries || '';
    renderFields();
    doPreview(true);
  }
  const jsonBtn = h('button', { type: 'button', onclick: () => {
    const ta = h('textarea', { class: 'code', rows: 20 });
    ta.value = JSON.stringify(t, null, 2);
    const e2 = h('div');
    const close = modal('Modèle au format JSON', h('div', {}, ta, e2, h('button', { class: 'primary', style: { marginTop: '.6rem' }, onclick: () => {
      try { model.template = JSON.parse(ta.value); for (const k of Object.keys(t)) delete t[k]; editorReplace(); close(); } catch (ex) { e2.replaceChildren(errorBox(ex)); }
    } }, 'Appliquer')));
  } }, 'JSON');

  const actions = h('div', { class: 'row' },
    h('button', { class: 'primary', onclick: save }, 'Enregistrer'),
    isNew ? null : h('button', { onclick: async () => { const r = await api.post(`/questions/${params.id}/duplicate`); navigate(`/questions/${r.id}`); } }, 'Dupliquer'),
    isNew ? null : h('button', { class: 'danger', onclick: async () => {
      if (!confirmBox('Supprimer cette question ? (Elle sera archivée si des élèves y ont déjà répondu.)')) return;
      await api.del(`/questions/${params.id}`);
      navigate('/questions');
    } }, 'Supprimer'),
    h('button', { onclick: runSelftest, title: 'Teste le modèle sur 20 tirages' }, 'Vérifier'),
    jsonBtn, starterSel);

  async function runSelftest() {
    const close = modal('Vérification', h('p', {}, 'Test sur 20 tirages…'));
    try {
      const r = await api.post('/questions/selftest', { template: t });
      close();
      modal('Vérification', h('div', {},
        h('div', { class: 'alert ' + (r.status === 'ok' ? 'info' : r.status === 'warning' ? 'warn' : 'error') },
          r.status === 'ok' ? `✓ Tout va bien : ${r.samples} tirages, ${r.distinct} énoncé(s) différent(s), la correction est acceptée à chaque fois.`
            : `${r.samples} tirage(s) réussi(s), ${r.distinct} énoncé(s) différent(s).`),
        r.messages.length ? h('ul', {}, r.messages.map((m) => h('li', {}, m))) : null));
    } catch (e) { close(); toast(e.message, 'error'); }
  }

  setTimeout(() => doPreview(true), 0);
  return h('div', {},
    h('p', {}, h('a', { href: '#/questions' }, '← Banque de questions')),
    h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, isNew ? 'Nouvelle question' : ['Modifier la question ', uidBadge(existing.uid)]), actions),
    err,
    h('div', { class: 'split', style: { marginTop: '1rem' } },
      h('div', {},
        h('div', { class: 'card' },
          h('div', { class: 'fields-2', style: { gridTemplateColumns: '9rem 1fr' } },
            labelled('Identifiant', uidInput, isNew ? 'Automatique si vide' : null), labelled('Titre', title)),
          h('div', { class: 'fields-2' }, h('div', { class: 'field' }, h('label', {}, 'Chapitre'), chapterSel, newChapter), labelled('Difficulté', difficulty)),
          labelled('Compétences travaillées (séparées par « ; »)', h('div', {}, skillsInput, skillsList), 'Elles servent aux statistiques par compétence et au mode automatique.'),
          classes.length ? labelled('Classes', h('div', { class: 'row' }, classBoxes)) : null),
        h('div', { class: 'card', style: { marginTop: '1rem' } },
          h('h3', {}, '1. Générateur (Python)'),
          h('p', { class: 'small muted', style: { marginTop: 0 } }, 'Tire les données au hasard et calcule les réponses. Toutes les variables sont utilisables dans l\'énoncé avec {{ variable }}.'),
          code.container, helpPanel(),
          h('h3', {}, '2. Énoncé (Markdown)'), statement,
          h('div', { class: 'hint' }, '**gras**, `code`, blocs ```python, tableaux | a | b |, et {{ expression }} pour insérer une valeur.'),
          h('h3', {}, '3. Réponses attendues'), fieldsBox,
          h('h3', {}, '4. Correction affichée à la fin (facultatif)'), solution,
          h('h3', {}, '5. Indices et nombre d\'essais'),
          h('p', { class: 'small muted', style: { marginTop: 0 } }, "Après une erreur, l'élève peut se corriger : la solution n'est montrée qu'à la fin. Un indice de plus est donné à chaque erreur (Markdown, {{ }} autorisés ; séparer les indices par une ligne ---). Sans indice, un conseil générique adapté au type de question est affiché. Score : 100 % au 1er essai, 75 % au 2e, 50 % au 3e."),
          hintsArea,
          h('div', { class: 'row', style: { marginTop: '.6rem' } }, h('label', { style: { margin: 0 } }, "Nombre d'essais"), triesSel))),
      h('div', { class: 'card sticky' },
        h('div', { class: 'row between' }, h('h3', { style: { margin: 0 } }, 'Aperçu élève'),
          h('div', { class: 'row' }, h('label', { class: 'inline small' }, autoPreview, 'auto'),
            h('button', { class: 'small', onclick: () => doPreview(false) }, 'Rafraîchir'),
            h('button', { class: 'small primary', onclick: () => doPreview(true) }, '🎲 Nouvel exemple'))),
        h('hr'), previewBox)));
}

function helpPanel() {
  const items = [
    ['randint(a, b)', 'entier aléatoire entre a et b inclus'],
    ['randnz(a, b)', 'entier aléatoire non nul'],
    ['choice(seq), sample(seq, k), shuffled(seq)', 'un élément, k éléments distincts, copie mélangée'],
    ['randlist(n, a, b, distinct=False)', 'liste de n entiers aléatoires'],
    ['randname(pool=None, k=None)', 'nom(s) de variable aléatoire(s) ; aussi PRENOMS, FRUITS, VILLES, NOMS_FONCTIONS, NOMS_LISTES'],
    ['coin(p=0.5)', 'booléen aléatoire'],
    ['require(condition) / reject()', 'refaire le tirage si la condition est fausse'],
    ['run(code, inputs=None)', "exécute du code Python et renvoie ce qu'il affiche (inputs : valeurs données à input())"],
    ['run_error(code)', "nom de l'exception levée (ou None)"],
    ['evaluate(code, expr)', 'exécute le code puis renvoie la valeur de expr'],
    ['dedent(code), code_block(code, lang)', 'nettoie l\'indentation ; bloc de code Markdown'],
    ['sql_insert(table, lignes), sql_table(setup, table), sql_schema(setup)', 'fabriquer une base et l\'afficher'],
    ['sql_run(setup, requête), sql_value(setup, requête)', 'résultat d\'une requête'],
    ['md_table(lignes, entêtes)', 'tableau Markdown'],
    ['tobase(n, b, largeur), frombase(s, b), twos(n, bits), from_twos(s), group(s, 4)', 'bases, complément à deux, groupement de chiffres'],
    ['fr(x, décimales)', 'nombre avec virgule décimale'],
  ];
  return h('details', { class: 'help' }, h('summary', {}, 'Fonctions disponibles'),
    h('dl', {}, items.map(([k, v]) => [h('dt', {}, k), h('dd', {}, v)])),
    h('p', { class: 'small' }, 'Modules : math, string, textwrap (déjà importés), et import possible de random, itertools, collections… Documentation complète : docs/QUESTION_FORMAT.md.'));
}
