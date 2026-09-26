import { api, qs } from '../api.js';
import { fmtDateTime, fmtDay, h, meter, pct, relTime } from '../dom.js';
import { isStaff, navigate } from '../app.js';
import { questionView } from '../player.js';

const MODE_LABEL = { assignment: 'Séance', chapter: 'Chapitre', adaptive: 'Automatique', free: 'Libre' };

function progressLine(p) {
  return h('div', { class: 'stack' },
    meter(p.total ? p.done / p.total : 0, 'Questions traitées'),
    h('div', { class: 'small muted' }, `${p.done}/${p.total} traitée(s) · ${p.mastered} réussie(s) · score ${pct(p.score)}`));
}

function assignmentCard(a, today) {
  const late = a.day < today && a.progress.done < a.progress.total;
  return h('div', { class: 'card' },
    h('div', { class: 'row between' }, h('strong', {}, a.title),
      late ? h('span', { class: 'pill bad' }, 'à terminer') : a.progress.mastered === a.progress.total ? h('span', { class: 'pill good' }, '✓ terminé') : null),
    h('div', { class: 'small muted', style: { margin: '.2rem 0 .6rem' } }, `${a.class_name} · ${fmtDay(a.day)}`),
    progressLine(a.progress),
    h('div', { class: 'row', style: { marginTop: '.8rem' } },
      h('a', { class: 'btn primary', href: `#/jouer?mode=assignment&a=${a.id}` }, a.progress.done ? 'Continuer' : 'Commencer'),
      h('a', { class: 'btn', href: `#/seance/${a.id}` }, 'Détail')));
}

export async function homePage() {
  const d = await api.get('/me/dashboard');
  const today = d.today;
  const todays = d.assignments.filter((a) => a.day === today);
  const upcoming = d.assignments.filter((a) => a.day > today);
  const past = d.assignments.filter((a) => a.day < today).reverse();
  const chapterSelect = h('select', { 'aria-label': 'Limiter à un chapitre' },
    h('option', { value: '' }, 'Tous les chapitres'), d.chapters.map((c) => h('option', { value: c.id ?? '' }, c.name)));

  return h('div', {},
    h('h1', {}, 'Bonjour !'),
    d.classes.length ? null : h('div', { class: 'alert warn' }, "Vous n'êtes inscrit·e dans aucune classe pour l'instant."),
    h('div', { class: 'stat-tiles' },
      tile(d.totals.answered || 0, 'questions traitées'),
      tile(d.totals.week || 0, 'cette semaine'),
      tile(pct(d.totals.avg), 'score moyen')),

    h('h2', {}, "Aujourd'hui"),
    todays.length ? h('div', { class: 'grid' }, todays.map((a) => assignmentCard(a, today)))
      : h('div', { class: 'empty' }, "Pas de séance prévue aujourd'hui."),

    h('h2', {}, "S'entraîner"),
    h('div', { class: 'card' },
      h('h3', {}, 'Entraînement automatique'),
      h('p', { class: 'muted small' }, 'Les questions sont choisies selon vos points faibles : plus une compétence est fragile, plus elle revient.'),
      h('div', { class: 'row' }, h('div', { style: { minWidth: '14rem' } }, chapterSelect),
        h('button', { class: 'primary', onclick: () => navigate('/jouer' + qs({ mode: 'adaptive', c: chapterSelect.value })) }, 'Démarrer'))),
    d.chapters.length ? h('div', { class: 'grid', style: { marginTop: '1rem' } }, d.chapters.map((c) => h('div', { class: 'card' },
      h('strong', {}, c.name),
      h('div', { class: 'small muted', style: { margin: '.2rem 0 .5rem' } }, `${c.seen}/${c.questions} question(s) déjà vue(s)`),
      meter(c.mastery, 'Réussite récente'),
      h('div', { style: { marginTop: '.6rem' } },
        c.id !== null ? h('a', { class: 'btn', href: `#/jouer?mode=chapter&c=${c.id}` }, 'Travailler ce chapitre') : null))))
      : h('div', { class: 'empty', style: { marginTop: '1rem' } }, 'Aucune question disponible.'),

    d.skills.length ? [h('h2', {}, 'Mes compétences'),
      h('div', { class: 'card' }, h('p', { class: 'small muted', style: { marginTop: 0 } }, 'Les moins maîtrisées en premier.'),
        h('table', { class: 'data' }, h('tbody', {}, d.skills.map((s) => h('tr', {},
          h('td', {}, s.name), h('td', { style: { width: '40%' } }, meter(s.mastery)),
          h('td', { class: 'num small muted' }, `${s.attempts} essai(s)`))))))] : null,

    upcoming.length ? [h('h2', {}, 'À venir'), h('div', { class: 'grid' }, upcoming.map((a) => assignmentCard(a, today)))] : null,
    past.length ? [h('h2', {}, 'Séances précédentes'), h('div', { class: 'grid' }, past.map((a) => assignmentCard(a, today)))] : null,

    d.recent.length ? [h('h2', {}, 'Dernières réponses'), attemptsTable(d.recent)] : null);
}

function tile(v, label) {
  return h('div', { class: 'stat-tile' }, h('div', { class: 'v' }, v), h('div', { class: 'l' }, label));
}

function scorePill(score) {
  if (score === null || score === undefined) return h('span', { class: 'pill' }, 'non répondu');
  return h('span', { class: 'pill ' + (score >= 1 ? 'good' : 'bad') }, (score >= 1 ? '✓ ' : '✗ ') + pct(score));
}

function attemptsTable(rows) {
  return h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
    h('thead', {}, h('tr', {}, h('th', {}, 'Question'), h('th', {}, 'Mode'), h('th', {}, 'Date'), h('th', {}, 'Score'))),
    h('tbody', {}, rows.map((r) => h('tr', { class: 'clickable', onclick: () => navigate(`/tentative/${r.id}`) },
      h('td', {}, r.title), h('td', {}, MODE_LABEL[r.mode] || r.mode), h('td', {}, relTime(r.answered_at)),
      h('td', {}, scorePill(r.score)))))));
}

export async function assignmentPage({ params }) {
  const { assignment: a } = await api.get(`/me/assignments/${params.id}`);
  const byQ = Object.fromEntries(a.progress.questions.map((p) => [p.question_id, p]));
  return h('div', {},
    h('p', {}, h('a', { href: '#/' }, '← Accueil')),
    h('h1', {}, a.title),
    h('p', { class: 'muted' }, fmtDay(a.day)),
    h('div', { class: 'card', style: { maxWidth: '720px' } },
      progressLine(a.progress),
      h('table', { class: 'data', style: { marginTop: '1rem' } }, h('tbody', {}, a.questions.map((q, i) => {
        const p = byQ[q.id] || {};
        return h('tr', {},
          h('td', {}, `${i + 1}. ${q.title}`), h('td', { class: 'small muted' }, q.chapter || ''),
          h('td', {}, p.tries ? scorePill(p.best) : h('span', { class: 'pill' }, 'à faire')),
          h('td', {}, h('a', { class: 'btn small', href: `#/jouer?mode=assignment&a=${a.id}&q=${q.id}` }, p.tries ? 'Refaire' : 'Faire')));
      }))),
      h('div', { style: { marginTop: '1rem' } }, h('a', { class: 'btn primary', href: `#/jouer?mode=assignment&a=${a.id}` }, 'Continuer la séance'))));
}

export async function playPage({ query }) {
  const mode = query.mode || 'adaptive';
  const body = { mode };
  if (query.a) body.assignment_id = Number(query.a);
  if (query.q) body.question_id = Number(query.q);
  if (query.c) body.chapter_id = Number(query.c);
  const res = await api.post('/practice/next', body);

  if (res.done) {
    return h('div', { class: 'card', style: { maxWidth: '640px' } },
      h('h1', {}, '🎉 Séance terminée'),
      h('p', {}, 'Toutes les questions de cette séance sont réussies.'), progressLine(res.progress),
      h('div', { class: 'row', style: { marginTop: '1rem' } },
        h('a', { class: 'btn', href: `#/seance/${query.a}` }, 'Voir le détail'),
        h('a', { class: 'btn primary', href: '#/jouer?mode=adaptive' }, "S'entraîner encore"),
        h('a', { class: 'btn', href: '#/' }, 'Accueil')));
  }
  const at = res.attempt;
  const ctx = at.context || {};
  const nextHash = mode === 'assignment' ? `/jouer?mode=assignment&a=${query.a}` : '/jouer' + qs({ mode, c: query.c });
  const retryHash = mode === 'assignment' ? `/jouer?mode=assignment&a=${query.a}&q=${at.question.id}` : `/jouer?mode=free&q=${at.question.id}`;
  const side = h('div', { class: 'stack' });
  const after = h('div', { class: 'row', style: { marginTop: '1rem' } },
    h('button', { class: 'primary', onclick: () => navigate(nextHash) }, 'Question suivante →'),
    h('button', { onclick: () => navigate(retryHash) }, '↻ Même exercice, autres données'),
    isStaff() ? null : h('a', { class: 'btn', href: '#/' }, 'Accueil'));

  const renderSide = (progress) => {
    side.replaceChildren();
    if (ctx.assignment) {
      const p = progress || ctx.progress;
      side.append(h('div', { class: 'card' }, h('h3', {}, ctx.assignment.title), progressLine(p),
        h('div', { class: 'qnav', style: { marginTop: '.8rem' } }, p.questions.map((q, i) => h('a', {
          href: `#/jouer?mode=assignment&a=${ctx.assignment.id}&q=${q.question_id}`,
          class: q.question_id === at.question.id ? 'current' : '',
        }, h('span', {}, `Question ${i + 1}`), q.tries ? scorePill(q.best) : h('span', { class: 'pill' }, 'à faire'))))));
    } else {
      side.append(h('div', { class: 'card' },
        h('h3', {}, mode === 'adaptive' ? 'Entraînement automatique' : mode === 'chapter' ? 'Entraînement par chapitre' : 'Entraînement libre'),
        ctx.chapter ? h('p', {}, 'Chapitre : ', h('strong', {}, ctx.chapter.name)) : null,
        h('p', { class: 'small muted' }, mode === 'adaptive'
          ? 'Les notions où vous avez le plus de difficultés reviennent plus souvent.'
          : 'Les données changent à chaque fois : vous pouvez refaire un exercice autant que vous voulez.')));
    }
  };
  renderSide();

  const view = questionView(at.instance, {
    onSubmit: async (answers) => {
      const r = await api.post(`/attempts/${at.id}/answer`, { answers });
      if (r.progress) renderSide(r.progress);
      return r.result;
    },
    after,
  });
  return h('div', {},
    h('div', { class: 'split', style: { gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 1fr)' } },
      h('div', { class: 'card' },
        h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, at.question.title),
          at.question.chapter ? h('span', { class: 'pill accent' }, at.question.chapter) : null),
        h('hr'), view),
      side));
}

export async function attemptPage({ params }) {
  const { attempt: a } = await api.get(`/attempts/${params.id}`);
  return h('div', {},
    h('p', {}, h('button', { class: 'link', onclick: () => history.back() }, '← Retour')),
    h('div', { class: 'card' },
      h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, a.title), scorePill(a.score)),
      h('p', { class: 'small muted' }, `${MODE_LABEL[a.mode]} · servie ${fmtDateTime(a.created_at)}`,
        a.answered_at ? ` · répondue ${fmtDateTime(a.answered_at)}` : ''),
      h('hr'),
      a.result ? questionView(a.instance, { answers: a.answers, result: a.result })
        : [questionView(a.instance, {}), h('div', { class: 'alert info' }, "Cette question n'a pas reçu de réponse.")]));
}

export async function historyPage() {
  const { attempts } = await api.get('/me/history?limit=200');
  return h('div', {}, h('h1', {}, 'Historique'),
    attempts.length ? attemptsTable(attempts) : h('div', { class: 'empty' }, 'Aucune réponse pour le moment.'));
}

