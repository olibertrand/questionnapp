import { api } from '../api.js';
import { errorBox, h, toast } from '../dom.js';
import { state } from '../app.js';

export function page() {
  const cur = h('input', { type: 'password', autocomplete: 'current-password', id: 'cur' });
  const n1 = h('input', { type: 'password', autocomplete: 'new-password', id: 'n1' });
  const n2 = h('input', { type: 'password', autocomplete: 'new-password', id: 'n2' });
  const err = h('div');
  const form = h('form', { class: 'card', style: { maxWidth: '420px' } },
    h('h2', {}, 'Changer mon mot de passe'),
    h('div', { class: 'field' }, h('label', { for: 'cur' }, 'Mot de passe actuel'), cur),
    h('div', { class: 'field' }, h('label', { for: 'n1' }, 'Nouveau mot de passe'), n1),
    h('div', { class: 'field' }, h('label', { for: 'n2' }, 'Confirmation'), n2),
    err, h('button', { class: 'primary', type: 'submit' }, 'Enregistrer'));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.replaceChildren();
    if (n1.value !== n2.value) return err.replaceChildren(h('div', { class: 'alert error' }, 'Les deux mots de passe diffèrent.'));
    try {
      await api.post('/auth/password', { current: cur.value, new: n1.value });
      toast('Mot de passe modifié.');
      form.reset();
    } catch (ex) { err.replaceChildren(errorBox(ex)); }
  });
  return h('div', {}, h('h1', {}, 'Mon compte'),
    h('p', {}, h('strong', {}, state.user.display_name), ' — identifiant ', h('code', {}, state.user.username)),
    form);
}
