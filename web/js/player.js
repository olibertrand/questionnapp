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
  const hintBox = h('div');
  const actions = h('div', { class: 'row' });
  const resultBox = h('div');
  root.append(hintBox, actions, resultBox);
  const clearFeedback = () => {
    root.querySelectorAll('.feedback').forEach((el) => el.remove());
    root.querySelectorAll('.option.correct, .option.wrong').forEach((el) => el.classList.remove('correct', 'wrong'));
  };
  const markChoice = (i, fr) => {
    // on ne colore que les options choisies par l'élève (la bonne réponse est donnée en texte à la fin)
    root.querySelectorAll(`input[name="${name}-${i}"]`).forEach((x) => {
      if (x.checked) x.closest('.option').classList.add(fr.correct ? 'correct' : 'wrong');
    });
  };
  const lockField = (i) => fieldBoxes[i].querySelectorAll('input, textarea').forEach((el) => { el.disabled = true; });

  const showResult = (result) => {
    clearFeedback();
    hintBox.replaceChildren();
    root.querySelectorAll('input, textarea').forEach((el) => { el.disabled = true; });
    result.fields.forEach((fr, i) => {
      if (instance.fields[i].type === 'choice') markChoice(i, fr);
      const fb = h('div', { class: 'feedback ' + (fr.correct ? 'ok' : 'ko') }, verdict(fr.score),
        fr.feedback ? md(fr.feedback) : null,
        !fr.correct && fr.expected ? h('div', {}, h('div', { class: 'small muted' }, 'Réponse attendue :'), md(fr.expected)) : null);
      fieldBoxes[i].append(fb);
    });
    const tries = result.tries || 1;
    const raw = result.raw_score ?? result.score;
    let detail = null;
    if (result.gave_up) detail = `solution demandée après ${tries} essai${tries > 1 ? 's' : ''}`;
    else if (tries > 1 && raw >= 1) detail = `réussi au ${tries}e essai`;
    else if (tries > 1) detail = `${tries} essais`;
    mount(resultBox,
      h('div', { class: 'row', style: { marginTop: '1rem' } },
        h('strong', {}, 'Résultat : '), verdict(raw),
        detail ? h('span', { class: 'muted small' }, `— ${detail}, score retenu ${Math.round(result.score * 100)} %`) : null),
      result.solution ? h('div', { class: 'solution' }, h('h3', {}, 'Correction'), md(result.solution)) : null,
      options.after || null);
  };

  // essai intermédiaire : ce qui est juste est verrouillé, le reste peut être corrigé
  const showAttempt = (res) => {
    clearFeedback();
    res.result.fields.forEach((fr, i) => {
      if (instance.fields[i].type === 'choice') markChoice(i, fr);
      if (fr.correct) lockField(i);
      fieldBoxes[i].append(h('div', { class: 'feedback ' + (fr.correct ? 'ok' : 'ko') }, verdict(fr.score),
        fr.feedback ? md(fr.feedback) : null));
    });
    const left = res.max_tries - res.tries;
    mount(hintBox,
      h('div', { class: 'alert warn', style: { marginTop: '1rem' } },
        h('strong', {}, 'Pas encore tout à fait. '),
        `Corrigez ce qui est faux : il vous reste ${left} essai${left > 1 ? 's' : ''}.`,
        (res.hints || []).map((hint, k) => h('div', { class: 'hint-box' }, h('strong', {}, `💡 Indice ${k + 1} : `), md(hint)))));
  };

  if (options.answers) instance.fields.forEach((f, i) => fillAnswer(root, f, i, name, options.answers[i]));
  if (options.result) {
    showResult(options.result);
  } else if (options.onSubmit) {
    const maxTries = instance.max_tries || 1;
    const label = (n) => (n > 1 ? `Valider (essai ${n}/${maxTries})` : options.submitLabel || 'Valider');
    const btn = h('button', { class: 'primary', type: 'button' }, label(1));
    const giveUp = h('button', { type: 'button', style: { display: 'none' } }, 'Voir la solution');
    const err = h('span', { class: 'error-line' });
    let tries = 0;
    const handle = (res) => {
      // compatibilité : l'aperçu du professeur renvoie directement la correction finale
      if (res.final === undefined) res = { final: true, result: res };
      if (res.final) {
        actions.remove();
        showResult(res.result);
      } else {
        tries = res.tries;
        showAttempt(res);
        btn.disabled = false;
        btn.textContent = label(tries + 1);
        giveUp.style.display = options.onReveal ? '' : 'none';
      }
    };
    btn.addEventListener('click', async () => {
      const answers = instance.fields.map((f, i) => readAnswer(root, f, i, name));
      btn.disabled = true;
      btn.textContent = 'Correction…';
      err.textContent = '';
      try {
        handle(await options.onSubmit(answers));
      } catch (e) {
        err.textContent = e.message;
        btn.disabled = false;
        btn.textContent = label(tries + 1);
      }
    });
    giveUp.addEventListener('click', async () => {
      if (!window.confirm('Afficher la solution ? La question sera terminée avec le score de votre dernier essai.')) return;
      giveUp.disabled = true;
      try {
        handle(await options.onReveal(instance.fields.map((f, i) => readAnswer(root, f, i, name))));
      } catch (e) { err.textContent = e.message; giveUp.disabled = false; }
    });
    // Entrée dans un champ simple = valider
    root.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text') { e.preventDefault(); btn.click(); }
    });
    actions.append(btn, giveUp, err);
    if (maxTries > 1 && options.onReveal) {
      actions.append(h('span', { class: 'small muted' }, `${maxTries} essais possibles`));
    }
  }
  return root;
}
