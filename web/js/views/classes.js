import { api } from '../api.js';
import { confirmBox, errorBox, fmtDay, h, meter, modal, mount, pct, relTime, toast, todayIso } from '../dom.js';
import { navigate, render, state } from '../app.js';

export async function listPage() {
  const { classes } = await api.get('/classes');
  const name = h('input', { type: 'text', placeholder: 'Nom de la nouvelle classe (ex. 1re NSI groupe A)', 'aria-label': 'Nom de la classe' });
  const add = h('form', { class: 'row', style: { marginBottom: '1rem' } }, h('div', { style: { flex: 1, minWidth: '16rem' } }, name),
    h('button', { class: 'primary', type: 'submit' }, 'Créer la classe'));
  add.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!name.value.trim()) return;
    try {
      const r = await api.post('/classes', { name: name.value });
      navigate(`/classes/${r.id}`);
    } catch (ex) { toast(ex.message, 'error'); }
  });
  return h('div', {}, h('h1', {}, 'Classes'), add,
    classes.length ? h('div', { class: 'grid' }, classes.map((c) => h('div', { class: 'card' },
      h('h3', {}, h('a', { href: `#/classes/${c.id}` }, c.name)),
      h('p', { class: 'small muted' }, `${c.students} élève(s) · ${c.questions} question(s)`, c.teachers ? ` · ${c.teachers}` : ''),
      h('div', { class: 'row' },
        h('a', { class: 'btn small', href: `#/classes/${c.id}` }, 'Gérer'),
        h('a', { class: 'btn small', href: `#/classes/${c.id}?tab=seances` }, 'Séances'),
        h('a', { class: 'btn small', href: `#/stats/${c.id}` }, 'Statistiques')))))
      : h('div', { class: 'empty' }, 'Aucune classe. Créez-en une ci-dessus.'));
}

export async function detailPage({ params, query }) {
  const tab = query.tab || 'eleves';
  const { class: cls } = await api.get(`/classes/${params.id}`);
  const tabs = [['eleves', 'Élèves'], ['questions', 'Questions affectées'], ['seances', 'Séances']];
  const content = h('div', {}, h('p', { class: 'muted' }, 'Chargement…'));
  const header = h('div', { class: 'row between' },
    h('h1', { style: { margin: 0 } }, cls.name),
    h('div', { class: 'row' },
      h('a', { class: 'btn', href: `#/stats/${cls.id}` }, 'Statistiques'),
      h('button', { onclick: () => renameClass(cls) }, 'Renommer'),
      h('button', { class: 'danger', onclick: async () => {
        if (!confirmBox(`Supprimer la classe « ${cls.name} » ? Les comptes élèves sont conservés.`)) return;
        await api.del(`/classes/${cls.id}`);
        navigate('/classes');
      } }, 'Supprimer')));
  const view = h('div', {}, h('p', {}, h('a', { href: '#/classes' }, '← Classes')), header,
    cls.description ? h('p', { class: 'muted' }, cls.description) : null,
    h('nav', { class: 'tabs', style: { marginTop: '1rem' } }, tabs.map(([k, l]) => h('a', { href: `#/classes/${cls.id}?tab=${k}`, class: k === tab ? 'active' : '' }, l))),
    content);
  const builder = { eleves: membersTab, questions: questionsTab, seances: assignmentsTab }[tab] || membersTab;
  builder(cls).then((el) => content.replaceChildren(el)).catch((e) => content.replaceChildren(errorBox(e)));
  return view;
}

function renameClass(cls) {
  const name = h('input', { type: 'text', value: cls.name });
  const desc = h('input', { type: 'text', value: cls.description || '' });
  const close = modal('Modifier la classe', h('form', { onsubmit: async (e) => {
    e.preventDefault();
    await api.patch(`/classes/${cls.id}`, { name: name.value, description: desc.value });
    close();
    render();
  } }, h('div', { class: 'field' }, h('label', {}, 'Nom'), name), h('div', { class: 'field' }, h('label', {}, 'Description'), desc),
  h('button', { class: 'primary', type: 'submit' }, 'Enregistrer')));
}

async function membersTab(cls) {
  const students = cls.members.filter((m) => m.role === 'student');
  const teachers = cls.members.filter((m) => m.role !== 'student');
  const remove = async (m) => {
    if (!confirmBox(`Retirer ${m.display_name || m.username} de la classe ?`)) return;
    await api.del(`/classes/${cls.id}/members/${m.id}`);
    render();
  };
  return h('div', {},
    h('div', { class: 'row' },
      h('button', { class: 'primary', onclick: () => addStudentsModal(cls) }, '+ Ajouter des élèves'),
      h('button', { onclick: () => importModal(cls) }, 'Importer une liste (CSV)'),
      state.user.role === 'admin' ? h('button', { onclick: () => addTeacherModal(cls) }, '+ Ajouter un professeur') : null),
    h('h2', {}, `Élèves (${students.length})`),
    students.length ? h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Nom'), h('th', {}, 'Identifiant'), h('th', {}, 'Dernière connexion'), h('th', {}, ''))),
      h('tbody', {}, students.map((m) => h('tr', {},
        h('td', {}, h('a', { href: `#/eleves/${m.id}` }, m.display_name || m.username), m.active ? null : h('span', { class: 'pill bad' }, 'désactivé')),
        h('td', {}, h('code', {}, m.username)), h('td', {}, relTime(m.last_login_at)),
        h('td', { class: 'num' }, h('button', { class: 'small danger', onclick: () => remove(m) }, 'Retirer')))))))
      : h('div', { class: 'empty' }, 'Aucun élève dans cette classe.'),
    h('h2', {}, 'Professeurs'),
    teachers.length ? h('ul', {}, teachers.map((m) => h('li', {}, m.display_name || m.username, ' ',
      state.user.role === 'admin' ? h('button', { class: 'small link', onclick: () => remove(m) }, 'retirer') : null)))
      : h('p', { class: 'muted' }, 'Aucun professeur rattaché.'));
}

async function addStudentsModal(cls) {
  const { users } = await api.get('/users?role=student');
  const inClass = new Set(cls.members.map((m) => m.id));
  const candidates = users.filter((u) => !inClass.has(u.id));
  const filter = h('input', { type: 'search', placeholder: 'Filtrer…' });
  const list = h('div', { class: 'checklist' }, candidates.map((u) => h('label', { class: 'inline', 'data-name': `${u.display_name} ${u.username}`.toLowerCase() },
    h('input', { type: 'checkbox', value: u.id }), `${u.display_name || u.username} (${u.username})`, u.classes ? h('span', { class: 'muted small' }, ` — ${u.classes}`) : null)));
  filter.addEventListener('input', () => list.querySelectorAll('label').forEach((l) => { l.style.display = l.dataset.name.includes(filter.value.toLowerCase()) ? '' : 'none'; }));
  const uname = h('input', { type: 'text', placeholder: 'identifiant' });
  const dname = h('input', { type: 'text', placeholder: 'Prénom Nom' });
  const pwd = h('input', { type: 'text', placeholder: 'mot de passe' });
  const err = h('div');
  const close = modal('Ajouter des élèves', h('div', {},
    h('h3', {}, 'Élèves existants'),
    candidates.length ? [filter, list, h('button', { class: 'primary', style: { marginTop: '.6rem' }, onclick: async () => {
      const ids = [...list.querySelectorAll('input:checked')].map((x) => Number(x.value));
      if (!ids.length) return;
      await api.post(`/classes/${cls.id}/members`, { user_ids: ids });
      close();
      render();
    } }, 'Ajouter la sélection')] : h('p', { class: 'muted' }, 'Tous les élèves existants sont déjà dans la classe.'),
    h('h3', {}, 'Nouvel élève'),
    h('div', { class: 'fields-3' }, dname, uname, pwd), err,
    h('button', { style: { marginTop: '.6rem' }, onclick: async () => {
      try {
        await api.post('/users', { username: uname.value, display_name: dname.value, password: pwd.value, role: 'student', class_ids: [cls.id] });
        close();
        render();
      } catch (e) { err.replaceChildren(errorBox(e)); }
    } }, 'Créer et ajouter')));
}

function importModal(cls) {
  const ta = h('textarea', { rows: 10, class: 'code', placeholder: 'identifiant;mot de passe;Prénom Nom\nadupont;soleil42;Alice Dupont\nbmartin;lune17;Bilal Martin' });
  const out = h('div');
  modal('Importer des élèves', h('div', {},
    h('p', { class: 'small muted' }, 'Une ligne par élève : identifiant ; mot de passe ; nom affiché (séparateur « ; », « , » ou tabulation — copier-coller depuis un tableur fonctionne). Les élèves déjà existants sont simplement ajoutés à la classe.'),
    ta, out,
    h('button', { class: 'primary', style: { marginTop: '.6rem' }, onclick: async () => {
      const r = await api.post('/users/import', { csv: ta.value, class_id: cls.id, role: 'student' });
      mount(out, h('div', { class: 'alert info' }, `${r.created.length} compte(s) créé(s).`),
        r.errors.length ? h('div', { class: 'alert error' }, h('ul', {}, r.errors.map((e) => h('li', {}, e)))) : null);
      if (!r.errors.length) toast('Import terminé.');
    } }, 'Importer')), { onClose: render });
}

async function addTeacherModal(cls) {
  const { users } = await api.get('/users?role=teacher');
  const sel = h('select', {}, users.map((u) => h('option', { value: u.id }, `${u.display_name || u.username} (${u.username})`)));
  const close = modal('Ajouter un professeur', users.length ? h('div', {}, sel, h('button', { class: 'primary', style: { marginTop: '.6rem' }, onclick: async () => {
    await api.post(`/classes/${cls.id}/members`, { user_ids: [Number(sel.value)] });
    close();
    render();
  } }, 'Ajouter')) : h('p', {}, "Aucun compte professeur. Créez-en un dans « Utilisateurs »."));
}

export function questionChecklist(questions, selected, { groupBy = 'chapter' } = {}) {
  const groups = {};
  for (const q of questions) (groups[q[groupBy] || 'Sans chapitre'] ||= []).push(q);
  const filter = h('input', { type: 'search', placeholder: 'Filtrer par titre ou compétence…', style: { marginBottom: '.4rem' } });
  const box = h('div', { class: 'checklist', style: { maxHeight: '30rem' } }, Object.entries(groups).map(([g, qs]) => [
    h('div', { class: 'group' }, g),
    qs.map((q) => h('label', { class: 'inline', 'data-s': `${q.uid || ''} ${q.title} ${(q.skills || []).join(' ')}`.toLowerCase() },
      h('input', { type: 'checkbox', value: q.id, checked: selected.has(q.id) }), q.uid ? h('span', { class: 'uid' }, q.uid) : null, q.title,
      q.skills && q.skills.length ? h('span', { class: 'muted small' }, ` — ${q.skills.join(', ')}`) : null)),
  ]));
  filter.addEventListener('input', () => box.querySelectorAll('label').forEach((l) => { l.style.display = l.dataset.s.includes(filter.value.toLowerCase()) ? '' : 'none'; }));
  const wrap = h('div', {}, filter, box);
  wrap.selected = () => [...box.querySelectorAll('input:checked')].map((x) => Number(x.value));
  return wrap;
}

async function questionsTab(cls) {
  const { questions } = await api.get('/questions');
  const list = questionChecklist(questions, new Set(cls.question_ids));
  return h('div', {},
    h('p', { class: 'muted' }, "Les questions cochées sont accessibles aux élèves de la classe pour l'entraînement (par chapitre et automatique). Une question peut être affectée à plusieurs classes."),
    questions.length ? [list, h('div', { class: 'row', style: { marginTop: '.8rem' } },
      h('button', { class: 'primary', onclick: async () => {
        await api.put(`/classes/${cls.id}/questions`, { question_ids: list.selected() });
        toast('Questions de la classe enregistrées.');
      } }, 'Enregistrer'),
      h('a', { class: 'btn', href: '#/questions/nouvelle' }, 'Créer une question'))]
      : h('div', { class: 'empty' }, 'La banque de questions est vide. ', h('a', { href: '#/questions' }, 'Créer ou importer des questions')));
}

async function assignmentsTab(cls) {
  const { assignments } = await api.get(`/classes/${cls.id}/assignments`);
  const today = todayIso();
  return h('div', {},
    h('button', { class: 'primary', onclick: () => assignmentModal(cls) }, '+ Nouvelle séance'),
    h('p', { class: 'muted small' }, "Une séance est une liste de questions à traiter pour un jour donné. Les élèves la voient sur leur page d'accueil."),
    assignments.length ? h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Jour'), h('th', {}, 'Titre'), h('th', { class: 'num' }, 'Questions'), h('th', {}, ''))),
      h('tbody', {}, assignments.map((a) => h('tr', { class: 'clickable', onclick: () => navigate(`/seances/${a.id}`) },
        h('td', {}, fmtDay(a.day), a.day === today ? h('span', { class: 'pill accent', style: { marginLeft: '.4rem' } }, "aujourd'hui") : null),
        h('td', {}, a.title), h('td', { class: 'num' }, a.questions), h('td', { class: 'num' }, '›')))))
      : h('div', { class: 'empty' }, 'Aucune séance.'));
}

export async function assignmentModal(cls, existing = null) {
  const [{ questions }, { classes }] = await Promise.all([api.get('/questions'), api.get('/classes')]);
  const title = h('input', { type: 'text', value: existing ? existing.title : '', placeholder: 'ex. Boucles — séance du mardi' });
  const day = h('input', { type: 'date', value: existing ? existing.day : todayIso() });
  const selected = new Set(existing ? existing.questions.map((q) => q.id) : []);
  const onlyClass = h('input', { type: 'checkbox', checked: !existing });
  const listBox = h('div');
  const classQ = new Set();
  if (!existing) (await api.get(`/classes/${cls.id}`)).class.question_ids.forEach((id) => classQ.add(id));
  let list;
  const refresh = () => {
    const qs = onlyClass.checked && classQ.size ? questions.filter((q) => classQ.has(q.id) || selected.has(q.id)) : questions;
    list = questionChecklist(qs, selected);
    list.addEventListener('change', (e) => { if (e.target.type !== 'checkbox') return; const id = Number(e.target.value); if (e.target.checked) selected.add(id); else selected.delete(id); });
    listBox.replaceChildren(list);
  };
  onlyClass.addEventListener('change', refresh);
  refresh();
  const others = classes.filter((c) => c.id !== cls.id);
  const alsoBox = !existing && others.length ? h('div', { class: 'field' }, h('label', {}, 'Créer aussi pour les classes'),
    h('div', { class: 'row' }, others.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id }), c.name)))) : null;
  const err = h('div');
  const close = modal(existing ? 'Modifier la séance' : 'Nouvelle séance', h('div', {},
    h('div', { class: 'fields-2' }, h('div', { class: 'field' }, h('label', {}, 'Titre'), title), h('div', { class: 'field' }, h('label', {}, 'Jour'), day)),
    h('div', { class: 'field' }, h('div', { class: 'row between' }, h('label', {}, 'Questions (dans l\'ordre de la liste)'),
      !existing && classQ.size ? h('label', { class: 'inline small' }, onlyClass, 'seulement celles de la classe') : null), listBox,
    h('div', { class: 'hint' }, 'Les questions choisies sont automatiquement affectées à la classe.')),
    alsoBox, err,
    h('button', { class: 'primary', onclick: async () => {
      const qids = questions.map((q) => q.id).filter((id) => selected.has(id));
      try {
        if (existing) {
          await api.put(`/assignments/${existing.id}`, { title: title.value, day: day.value, question_ids: qids });
        } else {
          const extra = alsoBox ? [...alsoBox.querySelectorAll('input:checked')].map((x) => Number(x.value)) : [];
          await api.post('/assignments', { title: title.value, day: day.value, question_ids: qids, class_ids: [cls.id, ...extra] });
        }
        close();
        render();
      } catch (e) { err.replaceChildren(errorBox(e)); }
    } }, 'Enregistrer')));
}

export async function assignmentPage({ params }) {
  const { assignment: a } = await api.get(`/assignments/${params.id}`);
  const { class: cls } = await api.get(`/classes/${a.class_id}`);
  const qCols = a.questions;
  return h('div', {},
    h('p', {}, h('a', { href: `#/classes/${cls.id}?tab=seances` }, `← ${cls.name}`)),
    h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, a.title),
      h('div', { class: 'row' },
        h('button', { onclick: () => assignmentModal(cls, a) }, 'Modifier'),
        h('button', { class: 'danger', onclick: async () => {
          if (!confirmBox('Supprimer cette séance ? Les réponses des élèves restent dans les statistiques.')) return;
          await api.del(`/assignments/${a.id}`);
          navigate(`/classes/${cls.id}?tab=seances`);
        } }, 'Supprimer'))),
    h('p', { class: 'muted' }, fmtDay(a.day)),
    h('h2', {}, 'Avancement des élèves'),
    h('p', { class: 'small muted' }, 'Pour chaque question : meilleur score obtenu (nombre d\'essais).'),
    h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Élève'), qCols.map((q, i) => h('th', { title: q.title }, q.uid || `Q${i + 1}`)), h('th', {}, 'Traitées'), h('th', {}, 'Score'))),
      h('tbody', {}, a.students.map((s) => {
        const byQ = Object.fromEntries(s.progress.questions.map((p) => [p.question_id, p]));
        return h('tr', {},
          h('td', {}, h('a', { href: `#/eleves/${s.id}` }, s.display_name || s.username)),
          qCols.map((q) => {
            const p = byQ[q.id];
            return h('td', {}, p && p.tries ? h('span', { class: 'pill ' + (p.best >= 1 ? 'good' : 'bad') }, `${pct(p.best)} (${p.tries})`) : h('span', { class: 'muted' }, '—'));
          }),
          h('td', {}, `${s.progress.done}/${s.progress.total}`), h('td', { style: { minWidth: '8rem' } }, meter(s.progress.score)));
      })))),
    h('h2', {}, 'Questions'),
    h('ol', {}, qCols.map((q) => h('li', {}, q.uid ? h('span', { class: 'uid' }, q.uid) : null, h('a', { href: `#/questions/${q.id}` }, q.title), q.chapter ? h('span', { class: 'muted small' }, ` — ${q.chapter}`) : null))));
}
