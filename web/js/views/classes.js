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
  const tabs = [['eleves', 'Élèves'], ['groupes', 'Groupes'], ['questions', 'Questions affectées'], ['seances', 'Séances']];
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
  const builder = { eleves: membersTab, groupes: groupsTab, questions: questionsTab, seances: assignmentsTab }[tab] || membersTab;
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
    h('p', { class: 'small muted' }, 'Une ligne par élève : identifiant ; mot de passe ; nom affiché (séparateur « ; », « , » ou tabulation — copier-coller depuis un tableur fonctionne). Les élèves déjà existants sont simplement ajoutés à la classe. Chaque élève devra choisir son propre mot de passe à sa première connexion.'),
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

// ---------------------------------------------------------------------------
// Groupes d'élèves
// ---------------------------------------------------------------------------

const studentName = (m) => m.display_name || m.username;

async function groupsTab(cls) {
  const { groups } = await api.get(`/classes/${cls.id}/groups`);
  const students = cls.members.filter((m) => m.role === 'student');
  const byId = Object.fromEntries(students.map((m) => [m.id, m]));
  return h('div', {},
    h('button', { class: 'primary', onclick: () => groupModal(cls, students) }, '+ Nouveau groupe'),
    h('p', { class: 'muted small' }, "Un groupe rassemble quelques élèves de la classe (soutien, approfondissement…). On peut ensuite donner une séance à un ou plusieurs groupes, ou à des élèves choisis un par un."),
    groups.length ? h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Groupe'), h('th', {}, 'Élèves'), h('th', {}, ''))),
      h('tbody', {}, groups.map((g) => h('tr', {},
        h('td', {}, h('strong', {}, g.name)),
        h('td', { class: 'small' }, g.user_ids.map((id) => byId[id] ? studentName(byId[id]) : '?').join(', ') || h('span', { class: 'muted' }, 'aucun élève')),
        h('td', { class: 'actions' },
          h('button', { class: 'small', onclick: () => groupModal(cls, students, g) }, 'Modifier'),
          h('button', { class: 'small danger', onclick: async () => {
            if (!confirmBox(`Supprimer le groupe « ${g.name} » ? Les séances qui ne visaient que ce groupe seront désactivées.`)) return;
            const r = await api.del(`/groups/${g.id}`);
            if (r.deactivated) toast(`${r.deactivated} séance(s) désactivée(s).`);
            render();
          } }, 'Supprimer'))))))
      : h('div', { class: 'empty' }, 'Aucun groupe dans cette classe.'));
}

function studentChecklist(students, selected) {
  const filter = h('input', { type: 'search', placeholder: 'Filtrer…', style: { marginBottom: '.4rem' } });
  const box = h('div', { class: 'checklist', style: { maxHeight: '16rem' } }, students.map((m) => h('label', { class: 'inline', 'data-s': `${studentName(m)} ${m.username}`.toLowerCase() },
    h('input', { type: 'checkbox', value: m.id, checked: selected.has(m.id) }), studentName(m), h('span', { class: 'muted small' }, ` (${m.username})`))));
  filter.addEventListener('input', () => box.querySelectorAll('label').forEach((l) => { l.style.display = l.dataset.s.includes(filter.value.toLowerCase()) ? '' : 'none'; }));
  const wrap = h('div', {}, students.length > 8 ? filter : null, box);
  wrap.selected = () => [...box.querySelectorAll('input:checked')].map((x) => Number(x.value));
  return wrap;
}

function groupModal(cls, students, existing = null) {
  const name = h('input', { type: 'text', value: existing ? existing.name : '', placeholder: 'ex. Soutien, Groupe A, Projet…' });
  const list = studentChecklist(students, new Set(existing ? existing.user_ids : []));
  const err = h('div');
  const close = modal(existing ? 'Modifier le groupe' : 'Nouveau groupe', h('div', {},
    h('div', { class: 'field' }, h('label', {}, 'Nom du groupe'), name),
    h('div', { class: 'field' }, h('label', {}, 'Élèves'), students.length ? list : h('p', { class: 'muted' }, "Aucun élève dans la classe.")),
    err,
    h('button', { class: 'primary', onclick: async () => {
      const body = { name: name.value, user_ids: list.selected() };
      try {
        if (existing) await api.put(`/groups/${existing.id}`, body);
        else await api.post(`/classes/${cls.id}/groups`, body);
        close();
        render();
      } catch (e) { err.replaceChildren(errorBox(e)); }
    } }, 'Enregistrer')));
}

// ---------------------------------------------------------------------------
// Séances
// ---------------------------------------------------------------------------

function kindLabel(a) {
  return a.kind === 'theme' ? h('span', { class: 'pill accent' }, 'thématique') : fmtDay(a.day);
}

async function toggleActive(a) {
  await api.put(`/assignments/${a.id}`, { active: !a.active });
  toast(a.active ? 'Séance désactivée : les élèves ne la voient plus.' : 'Séance réactivée.');
  render();
}

async function assignmentsTab(cls) {
  const { assignments } = await api.get(`/classes/${cls.id}/assignments`);
  const today = todayIso();
  return h('div', {},
    h('button', { class: 'primary', onclick: () => assignmentModal(cls) }, '+ Nouvelle séance'),
    h('p', { class: 'muted small' }, "Une séance est une liste de questions choisies pour la classe ou pour certains élèves. Séance datée : à faire pour un jour donné. Séance thématique : sans date, elle reste proposée aux élèves (en haut de leur page d'accueil) jusqu'à ce que vous la désactiviez."),
    assignments.length ? h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Jour'), h('th', {}, 'Titre'), h('th', {}, 'Pour'), h('th', { class: 'num' }, 'Questions'), h('th', {}, 'État'), h('th', {}, ''))),
      h('tbody', {}, assignments.map((a) => h('tr', { style: a.active ? {} : { opacity: '.6' } },
        h('td', {}, kindLabel(a), a.kind !== 'theme' && a.day === today ? h('span', { class: 'pill accent', style: { marginLeft: '.4rem' } }, "aujourd'hui") : null),
        h('td', {}, h('a', { href: `#/seances/${a.id}` }, a.title)),
        h('td', { class: 'small' }, a.audience),
        h('td', { class: 'num' }, a.questions),
        h('td', {}, a.active ? h('span', { class: 'pill good' }, 'active') : h('span', { class: 'pill' }, 'désactivée')),
        h('td', { class: 'actions' },
          h('button', { class: 'small', onclick: () => toggleActive(a) }, a.active ? 'Désactiver' : 'Réactiver'),
          h('a', { class: 'btn small', href: `#/seances/${a.id}` }, 'Suivi')))))))
      : h('div', { class: 'empty' }, 'Aucune séance.'));
}

export async function assignmentModal(cls, existing = null) {
  const [{ questions }, { classes }, { class: full }, { groups }] = await Promise.all([
    api.get('/questions'), api.get('/classes'), api.get(`/classes/${cls.id}`), api.get(`/classes/${cls.id}/groups`)]);
  const students = full.members.filter((m) => m.role === 'student');
  const title = h('input', { type: 'text', value: existing ? existing.title : '', placeholder: 'ex. Boucles — séance du mardi, ou Révisions : dictionnaires' });

  // type de séance
  const kind = existing ? existing.kind : 'dated';
  const kindDated = h('input', { type: 'radio', name: 'kind', value: 'dated', checked: kind === 'dated' });
  const kindTheme = h('input', { type: 'radio', name: 'kind', value: 'theme', checked: kind === 'theme' });
  const day = h('input', { type: 'date', value: existing && existing.kind === 'dated' ? existing.day : todayIso(), style: { width: 'auto' } });
  const syncKind = () => { day.disabled = !kindDated.checked; };
  kindDated.addEventListener('change', syncKind);
  kindTheme.addEventListener('change', syncKind);
  syncKind();

  // destinataires
  const t = existing ? existing.targets : { group_ids: [], user_ids: [] };
  const someone = t.group_ids.length > 0 || t.user_ids.length > 0;
  const allClass = h('input', { type: 'radio', name: 'aud', checked: !someone });
  const some = h('input', { type: 'radio', name: 'aud', checked: someone });
  const groupBoxes = groups.map((g) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: g.id, checked: t.group_ids.includes(g.id) }),
    g.name, h('span', { class: 'muted small' }, ` (${g.user_ids.length})`)));
  const studentList = studentChecklist(students, new Set(t.user_ids));
  const audienceBox = h('div', { style: { marginTop: '.4rem' } },
    groups.length ? [h('div', { class: 'small muted' }, 'Groupes :'), h('div', { class: 'row', style: { marginBottom: '.5rem' } }, groupBoxes)]
      : h('p', { class: 'small muted' }, "Pas encore de groupe (onglet « Groupes » de la classe) : choisissez les élèves un par un."),
    h('div', { class: 'small muted' }, 'Élèves :'), studentList);

  const selected = new Set(existing ? existing.questions.map((q) => q.id) : []);
  const onlyClass = h('input', { type: 'checkbox', checked: !existing });
  const listBox = h('div');
  const classQ = new Set(full.question_ids);
  const refresh = () => {
    const qs = onlyClass.checked && classQ.size ? questions.filter((q) => classQ.has(q.id) || selected.has(q.id)) : questions;
    const list = questionChecklist(qs, selected);
    list.addEventListener('change', (e) => { if (e.target.type !== 'checkbox') return; const id = Number(e.target.value); if (e.target.checked) selected.add(id); else selected.delete(id); });
    listBox.replaceChildren(list);
  };
  onlyClass.addEventListener('change', refresh);
  refresh();
  const others = classes.filter((c) => c.id !== cls.id);
  const alsoBox = !existing && others.length ? h('div', { class: 'field' }, h('label', {}, 'Créer aussi pour les classes'),
    h('div', { class: 'row' }, others.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id }), c.name)))) : null;
  const syncAudience = () => {
    audienceBox.style.display = some.checked ? '' : 'none';
    if (alsoBox) alsoBox.style.display = some.checked ? 'none' : '';
  };
  allClass.addEventListener('change', syncAudience);
  some.addEventListener('change', syncAudience);
  syncAudience();

  const err = h('div');
  const close = modal(existing ? 'Modifier la séance' : 'Nouvelle séance', h('div', {},
    h('div', { class: 'field' }, h('label', {}, 'Titre'), title),
    h('div', { class: 'field' }, h('label', {}, 'Type de séance'),
      h('label', { class: 'inline' }, kindDated, 'Séance datée, pour le ', day),
      h('label', { class: 'inline', style: { marginTop: '.3rem' } }, kindTheme, 'Séance thématique : sans date, active jusqu\'à ce que vous la désactiviez')),
    h('div', { class: 'field' }, h('label', {}, 'Pour qui ?'),
      h('label', { class: 'inline' }, allClass, 'Toute la classe'),
      h('label', { class: 'inline' }, some, 'Certains élèves ou groupes'),
      audienceBox),
    h('div', { class: 'field' }, h('div', { class: 'row between' }, h('label', {}, 'Questions (dans l\'ordre de la liste)'),
      classQ.size ? h('label', { class: 'inline small' }, onlyClass, 'seulement celles de la classe') : null), listBox,
    h('div', { class: 'hint' }, "Séance pour toute la classe : ses questions sont aussi affectées à la classe (entraînement). Séance pour certains élèves : seuls ces élèves y ont accès.")),
    alsoBox, err,
    h('button', { class: 'primary', onclick: async () => {
      const qids = questions.map((q) => q.id).filter((id) => selected.has(id));
      const body = { title: title.value, kind: kindTheme.checked ? 'theme' : 'dated', question_ids: qids,
        group_ids: some.checked ? groupBoxes.map((b) => b.querySelector('input')).filter((x) => x.checked).map((x) => Number(x.value)) : [],
        user_ids: some.checked ? studentList.selected() : [] };
      if (kindDated.checked) body.day = day.value;
      if (some.checked && !body.group_ids.length && !body.user_ids.length) {
        return err.replaceChildren(h('div', { class: 'alert error' }, 'Choisissez au moins un groupe ou un élève.'));
      }
      try {
        if (existing) {
          await api.put(`/assignments/${existing.id}`, body);
        } else {
          const extra = alsoBox && !some.checked ? [...alsoBox.querySelectorAll('input:checked')].map((x) => Number(x.value)) : [];
          await api.post('/assignments', { ...body, class_ids: [cls.id, ...extra] });
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
        h('button', { onclick: () => toggleActive(a) }, a.active ? 'Désactiver' : 'Réactiver'),
        h('button', { onclick: () => assignmentModal(cls, a) }, 'Modifier'),
        h('button', { class: 'danger', onclick: async () => {
          if (!confirmBox('Supprimer cette séance ? Les réponses des élèves restent dans les statistiques.')) return;
          await api.del(`/assignments/${a.id}`);
          navigate(`/classes/${cls.id}?tab=seances`);
        } }, 'Supprimer'))),
    h('p', { class: 'row muted' }, kindLabel(a), h('span', {}, `· pour : ${a.audience}`),
      a.active ? h('span', { class: 'pill good' }, 'active') : h('span', { class: 'pill' }, 'désactivée (invisible pour les élèves)')),
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
