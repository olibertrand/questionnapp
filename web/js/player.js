// Affichage d'une instance de question, saisie des réponses et affichage de la correction.
import { codeArea, h, mount } from './dom.js';
import { md } from './markdown.js';

function fieldInput(field, i, name) {
  switch (field.type) {
    case 'number':
      return h('div', { class: 'row' },
        h('input', { type: 'text', inputmode: 'decimal', autocomplete: 'off', id: `${name}-${i}`, 'aria-label': field.label || 'Réponse' }),
        field.suffix ? h('span', { class: 'suffix' }, field.suffix) : null);
    case 'text':
      return field.multiline
        ? h('textarea', { id: `${name}-${i}`, rows: 4, class: 'code', style: { minHeight: '5rem' }, spellcheck: 'false' })
        : h('input', { type: 'text', autocomplete: 'off', spellcheck: 'false', id: `${name}-${i}`, 'aria-label': field.label || 'Réponse' });
    case 'choice':
      return h('div', { class: 'options', role: field.multiple ? 'group' : 'radiogroup' },
        field.multiple ? h('div', { class: 'hint' }, 'Plusieurs réponses possibles.') : null,
        field.options.map((opt, j) => h('label', { class: 'option' },
          h('input', { type: field.multiple ? 'checkbox' : 'radio', name: `${name}-${i}`, value: j }),
          md(opt))));
    case 'code':
    case 'sql': {
      const ta = codeArea({ id: `${name}-${i}`, rows: Math.max(6, (field.starter || '').split('\n').length + 4) });
      ta.value = field.starter || '';
      return ta;
    }
    default:
      return h('p', { class: 'alert error' }, `Type de champ inconnu : ${field.type}`);
  }
}

function readAnswer(root, field, i, name) {
  if (field.type === 'choice') {
    const checked = [...root.querySelectorAll(`input[name="${name}-${i}"]:checked`)].map((x) => Number(x.value));
    return field.multiple ? checked : (checked.length ? checked[0] : null);
  }
  const el = root.querySelector(`#${name}-${i}`);
  return el ? el.value : null;
}

function fillAnswer(root, field, i, name, value) {
  if (value === null || value === undefined) return;
  if (field.type === 'choice') {
    const vals = Array.isArray(value) ? value : [value];
    root.querySelectorAll(`input[name="${name}-${i}"]`).forEach((x) => { x.checked = vals.includes(Number(x.value)); });
  } else {
    const el = root.querySelector(`#${name}-${i}`);
    if (el) el.value = value;
  }
}

function verdict(score) {
  if (score >= 1) return h('span', { class: 'verdict ok' }, '✓ Correct');
  if (score > 0) return h('span', { class: 'verdict ko' }, `◐ Partiellement correct (${Math.round(score * 100)} %)`);
  return h('span', { class: 'verdict ko' }, '✗ Incorrect');
}

let counter = 0;

/**
 * instance : {statement, fields}
 * options : onSubmit(answers) -> Promise<{score, fields, solution}>, answers, result (lecture seule),
 *           submitLabel, after (élément à afficher après correction)
 */
export function questionView(instance, options = {}) {
  const name = `q${++counter}`;
  const root = h('div', { class: 'question' });
  const fieldBoxes = [];
  root.append(h('div', { class: 'statement' }, md(instance.statement)));
  instance.fields.forEach((f, i) => {
    const box = h('div', { class: 'answer-field' },
      f.label ? h('label', { for: `${name}-${i}` }, md(f.label, 'span')) : null,
      fieldInput(f, i, name));
    fieldBoxes.push(box);
    root.append(box);
  });
  const actions = h('div', { class: 'row' });
  const resultBox = h('div');
  root.append(actions, resultBox);

  const showResult = (result) => {
    root.querySelectorAll('input, textarea').forEach((el) => { el.disabled = true; });
    result.fields.forEach((fr, i) => {
      const f = instance.fields[i];
      if (f.type === 'choice') {
        // on ne colore que les options choisies par l'élève (la bonne réponse est donnée en texte)
        root.querySelectorAll(`input[name="${name}-${i}"]`).forEach((x) => {
          if (x.checked) x.closest('.option').classList.add(fr.correct ? 'correct' : 'wrong');
        });
      }
      const fb = h('div', { class: 'feedback ' + (fr.correct ? 'ok' : 'ko') }, verdict(fr.score),
        fr.feedback ? md(fr.feedback) : null,
        !fr.correct && fr.expected ? h('div', {}, h('div', { class: 'small muted' }, 'Réponse attendue :'), md(fr.expected)) : null);
      fieldBoxes[i].append(fb);
    });
    mount(resultBox, 
      h('div', { class: 'row', style: { marginTop: '1rem' } },
        h('strong', {}, 'Score : '), verdict(result.score)),
      result.solution ? h('div', { class: 'solution' }, h('h3', {}, 'Correction'), md(result.solution)) : null,
      options.after || null);
  };

  if (options.answers) instance.fields.forEach((f, i) => fillAnswer(root, f, i, name, options.answers[i]));
  if (options.result) {
    showResult(options.result);
  } else if (options.onSubmit) {
    const btn = h('button', { class: 'primary', type: 'button' }, options.submitLabel || 'Valider');
    const err = h('span', { class: 'error-line' });
    btn.addEventListener('click', async () => {
      const answers = instance.fields.map((f, i) => readAnswer(root, f, i, name));
      btn.disabled = true;
      btn.textContent = 'Correction…';
      err.textContent = '';
      try {
        const result = await options.onSubmit(answers);
        actions.remove();
        showResult(result);
      } catch (e) {
        err.textContent = e.message;
        btn.disabled = false;
        btn.textContent = options.submitLabel || 'Valider';
      }
    });
    // Entrée dans un champ simple = valider
    root.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text') { e.preventDefault(); btn.click(); }
    });
    actions.append(btn, err);
  }
  return root;
}
