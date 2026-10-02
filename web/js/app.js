// Point d'entrée de l'interface : session, navigation, routage par « # ».
import { api } from './api.js';
import { errorBox, h, mount, passwordInput, toast } from './dom.js';
import * as student from './views/student.js';
import * as classes from './views/classes.js';
import * as questions from './views/questions.js';
import * as users from './views/users.js';
import * as stats from './views/stats.js';
import * as account from './views/account.js';

export const state = { user: null };

const routes = [
  ['/', () => (isStaff() ? classes.listPage : student.homePage)],
  ['/seance/:id', () => student.assignmentPage],
  ['/jouer', () => student.playPage],
  ['/tentative/:id', () => student.attemptPage],
  ['/historique', () => student.historyPage],
  ['/classes', () => classes.listPage, true],
  ['/classes/:id', () => classes.detailPage, true],
  ['/seances/:id', () => classes.assignmentPage, true],
  ['/questions', () => questions.listPage, true],
  ['/questions/nouvelle', () => questions.editorPage, true],
  ['/questions/:id', () => questions.editorPage, true],
  ['/banques', () => questions.banksPage, true],
  ['/banques/:id', () => questions.bankPage, true],
  ['/utilisateurs', () => users.listPage, true],
  ['/stats', () => stats.indexPage, true],
  ['/stats/:id', () => stats.classPage, true],
  ['/eleves/:id', () => stats.studentPage, true],
  ['/compte', () => account.page],
];

export function isStaff() {
  return state.user && (state.user.role === 'admin' || state.user.role === 'teacher');
}

export function navigate(path) {
  if (location.hash === '#' + path) render();
  else location.hash = path;
}

function parseHash() {
  const raw = location.hash.slice(1) || '/';
  const [path, query = ''] = raw.split('?');
  return { path, query: Object.fromEntries(new URLSearchParams(query)) };
}

function match(path) {
  for (const [pattern, getView, staffOnly] of routes) {
    const names = [];
    const re = new RegExp('^' + pattern.replace(/:(\w+)/g, (_, n) => { names.push(n); return '([^/]+)'; }) + '/?$');
    const m = path.match(re);
    if (m) return { view: getView(), staffOnly, params: Object.fromEntries(names.map((n, i) => [n, decodeURIComponent(m[i + 1])])) };
  }
  return null;
}

function navLinks(path) {
  const links = isStaff()
    ? [['/classes', 'Classes'], ['/questions', 'Questions'], ['/banques', 'Banques'], ['/stats', 'Statistiques'], ['/utilisateurs', 'Utilisateurs']]
    : [['/', 'Accueil'], ['/jouer?mode=adaptive', 'Entraînement'], ['/historique', 'Historique']];
  return links.map(([href, label]) => {
    const active = href === '/' ? path === '/' : path.startsWith(href.split('?')[0]);
    return h('a', { href: '#' + href, class: active ? 'active' : '' }, label);
  });
}

const ROLE_LABEL = { admin: 'Administrateur', teacher: 'Professeur', student: 'Élève' };

async function logout() {
  await api.post('/auth/logout').catch(() => {});
  state.user = null;
  location.hash = '/';
  render();
}

let versionInfo = null;
function versionFooter() {
  const el = h('footer', { class: 'app-footer' });
  const fill = (v) => { el.textContent = v && v.commit ? `QuestionnApp · version ${v.commit}${v.branch ? ` (${v.branch})` : ''}` : 'QuestionnApp'; };
  if (versionInfo) fill(versionInfo);
  else api.get('/version').then((v) => { versionInfo = v; fill(v); }).catch(() => fill(null));
  return el;
}

let renderToken = 0;
export async function render() {
  const app = document.getElementById('app');
  if (!state.user) return mount(app, loginView());
  if (state.user.must_change_password) return mount(app, firstPasswordView());
  const { path, query } = parseHash();
  const m = match(path);
  const main = h('main');
  mount(app,
    h('header', { class: 'topbar' },
      h('a', { class: 'brand', href: '#/' }, 'Questionn', h('span', {}, 'App')),
      h('nav', { class: 'nav' }, navLinks(path)),
      h('div', { class: 'user-menu' },
        h('a', { href: '#/compte', title: 'Mon compte' }, state.user.display_name),
        h('span', { class: 'pill' }, ROLE_LABEL[state.user.role]),
        h('button', { class: 'small', onclick: logout }, 'Déconnexion'))),
    main, versionFooter());
  if (!m) return mount(main, h('div', { class: 'empty' }, 'Page introuvable. ', h('a', { href: '#/' }, "Retour à l'accueil")));
  if (m.staffOnly && !isStaff()) return mount(main, h('div', { class: 'alert error' }, 'Accès réservé aux professeurs.'));
  const token = ++renderToken;
  try {
    const content = await m.view({ params: m.params, query, main });
    if (token !== renderToken) return; // une autre page a été demandée entre-temps
    if (content) mount(main, content);
  } catch (e) {
    if (token === renderToken) mount(main, errorBox(e));
  }
  window.scrollTo(0, 0);
}

function loginView() {
  const err = h('div');
  const user = h('input', { type: 'text', id: 'username', autocomplete: 'username', autocapitalize: 'off', required: true });
  const pass = passwordInput({ id: 'password', autocomplete: 'current-password', required: true });
  const form = h('form', { class: 'card' },
    h('h1', {}, 'Connexion'),
    h('div', { class: 'field' }, h('label', { for: 'username' }, 'Identifiant'), user),
    h('div', { class: 'field' }, h('label', { for: 'password' }, 'Mot de passe'), pass.container),
    err,
    h('button', { class: 'primary', type: 'submit', style: { width: '100%', justifyContent: 'center' } }, 'Se connecter'));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.replaceChildren();
    try {
      const res = await api.post('/auth/login', { username: user.value.trim(), password: pass.value });
      state.user = res.user;
      render();
    } catch (ex) {
      err.replaceChildren(errorBox(ex));
    }
  });
  setTimeout(() => user.focus(), 0);
  return h('div', { class: 'login-wrap' },
    h('p', { class: 'brand', style: { fontSize: '1.6rem', textAlign: 'center' } }, 'Questionn', h('span', {}, 'App')),
    form);
}

// Première connexion (ou mot de passe réinitialisé par un professeur) : choix du mot de passe
function firstPasswordView() {
  const n1 = passwordInput({ id: 'n1', autocomplete: 'new-password', required: true });
  const n2 = passwordInput({ id: 'n2', autocomplete: 'new-password', required: true });
  const err = h('div');
  const form = h('form', { class: 'card' },
    h('h1', {}, 'Choisissez votre mot de passe'),
    h('p', { class: 'muted' }, `Bonjour ${state.user.display_name} ! Pour cette première connexion, choisissez le mot de passe que vous utiliserez désormais (vous pouvez garder celui qu'on vous a donné).`),
    h('div', { class: 'field' }, h('label', { for: 'n1' }, 'Nouveau mot de passe'), n1.container, h('div', { class: 'hint' }, 'Au moins 4 caractères.')),
    h('div', { class: 'field' }, h('label', { for: 'n2' }, 'Confirmation'), n2.container),
    err,
    h('div', { class: 'row between' },
      h('button', { class: 'primary', type: 'submit' }, 'Enregistrer et continuer'),
      h('button', { class: 'link', type: 'button', onclick: logout }, 'Se déconnecter')));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.replaceChildren();
    if (n1.value !== n2.value) return err.replaceChildren(h('div', { class: 'alert error' }, 'Les deux mots de passe diffèrent.'));
    try {
      await api.post('/auth/password', { new: n1.value });
      state.user.must_change_password = false;
      toast('Mot de passe enregistré.');
      render();
    } catch (ex) { err.replaceChildren(errorBox(ex)); }
  });
  setTimeout(() => n1.focus(), 0);
  return h('div', { class: 'login-wrap' },
    h('p', { class: 'brand', style: { fontSize: '1.6rem', textAlign: 'center' } }, 'Questionn', h('span', {}, 'App')), form);
}

window.addEventListener('qa:must-change-password', () => {
  if (state.user && !state.user.must_change_password) { state.user.must_change_password = true; render(); }
});
window.addEventListener('hashchange', render);
window.addEventListener('qa:logout', () => {
  if (state.user) { state.user = null; toast('Session expirée, reconnectez-vous.', 'error'); render(); }
});

(async function boot() {
  try {
    state.user = (await api.get('/auth/me')).user;
  } catch { state.user = null; }
  render();
})();
