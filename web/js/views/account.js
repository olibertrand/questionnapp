import { api } from '../api.js';
import { errorBox, h, passwordInput, toast } from '../dom.js';
import { state } from '../app.js';

export function page() {
  const cur = passwordInput({ autocomplete: 'current-password', id: 'cur' });
  const n1 = passwordInput({ autocomplete: 'new-password', id: 'n1' });
  const n2 = passwordInput({ autocomplete: 'new-password', id: 'n2' });
  const err = h('div');
  const form = h('form', { class: 'card', style: { maxWidth: '420px' } },
    h('h2', {}, 'Changer mon mot de passe'),
    h('div', { class: 'field' }, h('label', { for: 'cur' }, 'Mot de passe actuel'), cur.container),
    h('div', { class: 'field' }, h('label', { for: 'n1' }, 'Nouveau mot de passe'), n1.container),
    h('div', { class: 'field' }, h('label', { for: 'n2' }, 'Confirmation'), n2.container),
    err, h('button', { class: 'primary', type: 'submit' }, 'Enregistrer'));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.replaceChildren();
    if (n1.value !== n2.value) return err.replaceChildren(h('div', { class: 'alert error' }, 'Les deux mots de passe diffèrent.'));
    try {
      await api.post('/auth/password', { current: cur.value, new: n1.value });
      toast('Mot de passe modifié.');
      form.reset();
      [cur, n1, n2].forEach((i) => { if (i.type === 'text') i.container.querySelector('.pw-toggle').click(); });
    } catch (ex) { err.replaceChildren(errorBox(ex)); }
  });
  return h('div', {}, h('h1', {}, 'Mon compte'),
    h('p', {}, h('strong', {}, state.user.display_name), ' — identifiant ', h('code', {}, state.user.username)),
    form);
}
