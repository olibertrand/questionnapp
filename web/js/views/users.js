import { api, qs } from '../api.js';
import { confirmBox, errorBox, h, modal, relTime, toast } from '../dom.js';
import { navigate, render, state } from '../app.js';

const ROLE = { admin: 'Administrateur', teacher: 'Professeur', student: 'Élève' };

export async function listPage({ query }) {
  const role = query.role || '';
  const [{ users }, { classes }] = await Promise.all([api.get('/users' + qs({ role })), api.get('/classes')]);
  const isAdmin = state.user.role === 'admin';
  const filter = h('input', { type: 'search', placeholder: 'Filtrer par nom, identifiant, classe…' });
  const tbody = h('tbody', {}, users.map((u) => h('tr', { 'data-s': `${u.display_name} ${u.username} ${u.classes || ''}`.toLowerCase() },
    h('td', {}, u.role === 'student' ? h('a', { href: `#/eleves/${u.id}` }, u.display_name || u.username) : (u.display_name || u.username),
      u.active ? null : h('span', { class: 'pill bad', style: { marginLeft: '.3rem' } }, 'désactivé')),
    h('td', {}, h('code', {}, u.username)), h('td', {}, ROLE[u.role]), h('td', { class: 'small' }, u.classes || h('span', { class: 'muted' }, '—')),
    h('td', { class: 'small' }, relTime(u.last_login_at)),
    h('td', { class: 'num' }, u.id === state.user.id ? null : h('button', { class: 'small', onclick: () => editModal(u, isAdmin) }, 'Modifier')))));
  filter.addEventListener('input', () => tbody.querySelectorAll('tr').forEach((tr) => { tr.style.display = tr.dataset.s.includes(filter.value.toLowerCase()) ? '' : 'none'; }));
  return h('div', {},
    h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, 'Utilisateurs'),
      h('button', { class: 'primary', onclick: () => createModal(classes, isAdmin) }, '+ Nouvel utilisateur')),
    h('nav', { class: 'tabs', style: { marginTop: '1rem' } },
      [['', 'Tous'], ['student', 'Élèves'], ['teacher', 'Professeurs'], ...(isAdmin ? [['admin', 'Administrateurs']] : [])]
        .map(([k, l]) => h('a', { href: '#/utilisateurs' + qs({ role: k }), class: k === role ? 'active' : '' }, l))),
    h('div', { style: { marginBottom: '.8rem' } }, filter),
    h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Nom'), h('th', {}, 'Identifiant'), h('th', {}, 'Rôle'), h('th', {}, 'Classes'), h('th', {}, 'Dernière connexion'), h('th', {}, ''))),
      tbody)),
    h('p', { class: 'small muted' }, "Pour inscrire toute une classe d'un coup, utilisez « Importer une liste » depuis la page de la classe."));
}

function createModal(classes, isAdmin) {
  const username = h('input', { type: 'text', autocapitalize: 'off' });
  const display = h('input', { type: 'text' });
  const password = h('input', { type: 'text', value: Math.random().toString(36).slice(2, 8) });
  const role = h('select', {}, h('option', { value: 'student' }, 'Élève'), isAdmin ? [h('option', { value: 'teacher' }, 'Professeur'), h('option', { value: 'admin' }, 'Administrateur')] : null);
  const boxes = classes.map((c) => h('label', { class: 'inline' }, h('input', { type: 'checkbox', value: c.id }), c.name));
  const err = h('div');
  const close = modal('Nouvel utilisateur', h('form', { onsubmit: async (e) => {
    e.preventDefault();
    try {
      await api.post('/users', { username: username.value, display_name: display.value, password: password.value, role: role.value,
        class_ids: boxes.map((b) => b.querySelector('input')).filter((x) => x.checked).map((x) => Number(x.value)) });
      toast(`Compte ${username.value} créé (mot de passe : ${password.value}).`);
      close();
      render();
    } catch (ex) { err.replaceChildren(errorBox(ex)); }
  } },
  h('div', { class: 'fields-2' },
    h('div', { class: 'field' }, h('label', {}, 'Nom affiché'), display),
    h('div', { class: 'field' }, h('label', {}, 'Identifiant'), username, h('div', { class: 'hint' }, 'minuscules, chiffres, . _ -'))),
  h('div', { class: 'fields-2' },
    h('div', { class: 'field' }, h('label', {}, 'Mot de passe'), password, h('div', { class: 'hint' }, 'Provisoire : il sera demandé de le changer à la première connexion.')),
    h('div', { class: 'field' }, h('label', {}, 'Rôle'), role)),
  classes.length ? h('div', { class: 'field' }, h('label', {}, 'Classes'), h('div', { class: 'row' }, boxes)) : null,
  err, h('button', { class: 'primary', type: 'submit' }, 'Créer')));
}

function editModal(u, isAdmin) {
  const display = h('input', { type: 'text', value: u.display_name });
  const username = h('input', { type: 'text', value: u.username });
  const password = h('input', { type: 'text', placeholder: 'laisser vide pour ne pas changer' });
  const role = h('select', { disabled: !isAdmin }, Object.entries(ROLE).map(([k, l]) => h('option', { value: k, selected: k === u.role }, l)));
  const active = h('input', { type: 'checkbox', checked: Boolean(u.active) });
  const err = h('div');
  const close = modal(`Modifier ${u.display_name || u.username}`, h('form', { onsubmit: async (e) => {
    e.preventDefault();
    const body = { display_name: display.value, active: active.checked };
    if (username.value !== u.username) body.username = username.value;
    if (password.value) body.password = password.value;
    if (isAdmin && role.value !== u.role) body.role = role.value;
    try {
      await api.patch(`/users/${u.id}`, body);
      toast('Modifications enregistrées.');
      close();
      render();
    } catch (ex) { err.replaceChildren(errorBox(ex)); }
  } },
  h('div', { class: 'fields-2' },
    h('div', { class: 'field' }, h('label', {}, 'Nom affiché'), display),
    h('div', { class: 'field' }, h('label', {}, 'Identifiant'), username)),
  h('div', { class: 'fields-2' },
    h('div', { class: 'field' }, h('label', {}, 'Nouveau mot de passe'), password, h('div', { class: 'hint' }, "À changer par l'utilisateur à sa prochaine connexion.")),
    h('div', { class: 'field' }, h('label', {}, 'Rôle'), role)),
  h('label', { class: 'inline' }, active, 'Compte actif'),
  err,
  h('div', { class: 'row', style: { marginTop: '1rem' } },
    h('button', { class: 'primary', type: 'submit' }, 'Enregistrer'),
    h('button', { class: 'danger', type: 'button', onclick: async () => {
      if (!confirmBox(`Supprimer définitivement ${u.username} et toutes ses réponses ?`)) return;
      await api.del(`/users/${u.id}`);
      close();
      navigate('/utilisateurs');
      render();
    } }, 'Supprimer le compte'))));
}
