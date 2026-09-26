// Point d'entrée de l'interface : session, navigation, routage par « # ».
import { api } from './api.js';
import { errorBox, h, mount, toast } from './dom.js';
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
    ? [['/classes', 'Classes'], ['/questions', 'Questions'], ['/stats', 'Statistiques'], ['/utilisateurs', 'Utilisateurs']]
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

let renderToken = 0;
export async function render() {
  const app = document.getElementById('app');
  if (!state.user) return mount(app, loginView());
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
    main);
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
  const pass = h('input', { type: 'password', id: 'password', autocomplete: 'current-password', required: true });
  const form = h('form', { class: 'card' },
    h('h1', {}, 'Connexion'),
    h('div', { class: 'field' }, h('label', { for: 'username' }, 'Identifiant'), user),
    h('div', { class: 'field' }, h('label', { for: 'password' }, 'Mot de passe'), pass),
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
