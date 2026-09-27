import { api, qs } from '../api.js';
import { errorBox, fmtDateTime, fmtDay, h, meter, pct, relTime } from '../dom.js';
import { navigate } from '../app.js';
import { barChart, heatmap, rampLegend } from '../charts.js';
import { scorePill } from './student.js';

const MODE_LABEL = { assignment: 'Séance', chapter: 'Chapitre', adaptive: 'Automatique', free: 'Libre' };
const name = (s) => s.display_name || s.username;

export async function indexPage() {
  const { classes } = await api.get('/classes');
  if (classes.length === 1) { navigate(`/stats/${classes[0].id}`); return null; }
  return h('div', {}, h('h1', {}, 'Statistiques'),
    classes.length ? h('div', { class: 'grid' }, classes.map((c) => h('a', { class: 'card', href: `#/stats/${c.id}`, style: { textDecoration: 'none', color: 'inherit' } },
      h('h3', {}, c.name), h('p', { class: 'small muted' }, `${c.students} élève(s)`))))
      : h('div', { class: 'empty' }, 'Aucune classe.'));
}

function tile(v, label) {
  return h('div', { class: 'stat-tile' }, h('div', { class: 'v' }, v), h('div', { class: 'l' }, label));
}

export async function classPage({ params, query }) {
  const tab = query.tab || 'ensemble';
  const period = { from: query.from, to: query.to };
  const { class: cls } = await api.get(`/classes/${params.id}`);
  const tabs = [['ensemble', "Vue d'ensemble"], ['competences', 'Par compétence'], ['chapitres', 'Par chapitre'],
    ['questions', 'Par question'], ['seances', 'Par séance']];
  const from = h('input', { type: 'date', value: query.from || '' });
  const to = h('input', { type: 'date', value: query.to || '' });
  const apply = () => navigate(`/stats/${cls.id}` + qs({ tab, from: from.value, to: to.value }));
  from.addEventListener('change', apply);
  to.addEventListener('change', apply);
  const content = h('div', {}, h('p', { class: 'muted' }, 'Chargement…'));
  const builders = { ensemble: overviewTab, competences: skillsTab, chapitres: chaptersTab, questions: questionsTab, seances: assignmentsTab };
  (builders[tab] || overviewTab)(cls, period).then((el) => content.replaceChildren(el)).catch((e) => content.replaceChildren(errorBox(e)));
  return h('div', {},
    h('div', { class: 'row between' }, h('h1', { style: { margin: 0 } }, `Statistiques — ${cls.name}`),
      h('a', { class: 'btn', href: `/api/stats/classes/${cls.id}/export.csv` + qs(period) }, '⬇ Export CSV des réponses')),
    h('div', { class: 'row small', style: { margin: '.8rem 0' } }, 'Période :', h('div', {}, from), '→', h('div', {}, to),
      (query.from || query.to) ? h('button', { class: 'small', onclick: () => navigate(`/stats/${cls.id}` + qs({ tab })) }, 'Tout') : null),
    h('nav', { class: 'tabs' }, tabs.map(([k, l]) => h('a', { href: `#/stats/${cls.id}` + qs({ tab: k, ...period }), class: k === tab ? 'active' : '' }, l))),
    content);
}

async function overviewTab(cls, period) {
  const d = await api.get(`/stats/classes/${cls.id}/overview` + qs(period));
  const s = d.summary;
  const days = d.days.map((x) => ({
    label: x.day.slice(8, 10) + '/' + x.day.slice(5, 7), value: x.answered,
    tip: `${fmtDay(x.day)}\n${x.answered} réponse(s) · ${x.students} élève(s)\nscore moyen ${pct(x.avg_score)}`,
  }));
  return h('div', {},
    h('div', { class: 'stat-tiles' },
      tile(s.students, 'élèves'), tile(s.active_week, 'connectés cette semaine'),
      tile(s.answered, 'réponses'), tile(pct(s.avg_score), 'score moyen')),
    days.length ? h('div', { class: 'card' }, h('h3', {}, 'Réponses par jour'), barChart(days, { yLabel: 'Réponses par jour' })) : null,
    h('h2', {}, 'Élèves'),
    h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Élève'), h('th', {}, 'Dernière connexion'), h('th', { class: 'num' }, 'Connexions (7 j)'),
        h('th', { class: 'num' }, 'Réponses'), h('th', { class: 'num' }, 'Questions diff.'), h('th', {}, 'Score moyen'),
        h('th', {}, 'Séances traitées'), h('th', {}, 'Dernière activité'))),
      h('tbody', {}, d.students.map((st) => h('tr', { class: 'clickable', onclick: () => navigate(`/eleves/${st.id}`) },
        h('td', {}, name(st)), h('td', { class: 'small' }, fmtDateTime(st.last_login_at)),
        h('td', { class: 'num' }, `${st.logins_week} (${st.logins_total})`),
        h('td', { class: 'num' }, st.answered), h('td', { class: 'num' }, st.distinct_questions),
        h('td', { style: { minWidth: '8rem' } }, meter(st.avg_score)),
        h('td', { style: { minWidth: '8rem' } }, st.assignments_done === null ? h('span', { class: 'muted' }, '—') : meter(st.assignments_done)),
        h('td', { class: 'small' }, relTime(st.last_activity))))))));
}

function matrixView(d, groupLabel, emptyMsg) {
  if (!d.groups.length) return h('div', { class: 'empty' }, emptyMsg);
  return h('div', {},
    h('p', { class: 'small muted' }, 'Chaque case : maîtrise (%) — moyenne des scores où les réponses récentes comptent davantage. Survolez pour le détail. Cliquez sur un élève pour son suivi individuel.'),
    rampLegend(),
    heatmap(d.students, d.groups, (st, g) => {
      const c = d.cells[`${st.id}:${g.id}`];
      return c ? { value: c.mastery, tip: `${name(st)} — ${groupLabel(g)}\nmaîtrise ${pct(c.mastery)}\nmoyenne ${pct(c.avg)} sur ${c.n} réponse(s)` }
        : { value: null, tip: `${name(st)} — ${groupLabel(g)}\npas encore travaillé` };
    }, {
      rowLabel: name, colLabel: groupLabel, onRow: (st) => `#/eleves/${st.id}`,
      avgRow: (g) => ({ value: g.avg, tip: `${groupLabel(g)}\nmoyenne de la classe ${pct(g.avg)} (${g.n} réponses)\n${g.students_mastered} élève(s) à ≥ 80 %` }),
    }),
    h('h3', {}, 'Synthèse'),
    h('table', { class: 'data' }, h('thead', {}, h('tr', {}, h('th', {}, ''), h('th', { class: 'num' }, 'Réponses'), h('th', {}, 'Moyenne classe'), h('th', { class: 'num' }, 'Élèves ≥ 80 %'))),
      h('tbody', {}, [...d.groups].sort((a, b) => (a.avg ?? 2) - (b.avg ?? 2)).map((g) => h('tr', {},
        h('td', {}, groupLabel(g)), h('td', { class: 'num' }, g.n), h('td', { style: { minWidth: '10rem' } }, meter(g.avg)),
        h('td', { class: 'num' }, `${g.students_mastered}/${d.students.length}`))))));
}

async function skillsTab(cls, period) {
  const d = await api.get(`/stats/classes/${cls.id}/skills` + qs(period));
  return matrixView(d, (g) => g.name, 'Aucune compétence : renseignez les compétences des questions affectées à la classe.');
}

async function chaptersTab(cls, period) {
  const d = await api.get(`/stats/classes/${cls.id}/chapters` + qs(period));
  return matrixView(d, (g) => g.name, 'Aucune question affectée à cette classe.');
}

async function questionsTab(cls, period) {
  const { questions } = await api.get(`/stats/classes/${cls.id}/questions` + qs(period));
  return h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
    h('thead', {}, h('tr', {}, h('th', {}, 'Question'), h('th', {}, 'Chapitre'), h('th', { class: 'num' }, 'Élèves'),
      h('th', { class: 'num' }, 'Réponses'), h('th', { class: 'num' }, 'Réussies'), h('th', { class: 'num' }, 'Abandonnées'), h('th', {}, 'Score moyen'))),
    h('tbody', {}, questions.map((q) => h('tr', { class: 'clickable', onclick: () => navigate(`/questions/${q.id}`) },
      h('td', {}, q.uid ? h('span', { class: 'uid' }, q.uid) : null, q.title), h('td', { class: 'small' }, q.chapter || '—'), h('td', { class: 'num' }, q.students),
      h('td', { class: 'num' }, q.answered), h('td', { class: 'num' }, q.correct), h('td', { class: 'num', title: 'servies sans réponse' }, q.unanswered),
      h('td', { style: { minWidth: '9rem' } }, meter(q.avg_score)))))));
}

async function assignmentsTab(cls) {
  const d = await api.get(`/stats/classes/${cls.id}/assignments`);
  if (!d.assignments.length) return h('div', { class: 'empty' }, 'Aucune séance.');
  return h('div', {},
    h('p', { class: 'small muted' }, 'Chaque case : score de la séance (moyenne des meilleurs scores par question). Survolez pour le nombre de questions traitées.'),
    rampLegend(),
    heatmap(d.students, d.assignments, (st, a) => {
      const c = d.cells[`${st.id}:${a.id}`];
      return c.done ? { value: c.score, tip: `${name(st)} — ${a.title}\n${c.done}/${c.total} traitée(s), ${c.mastered} réussie(s)\nscore ${pct(c.score)}` }
        : { value: null, tip: `${name(st)} — ${a.title}\nrien de traité` };
    }, { rowLabel: name, colLabel: (a) => `${a.day.slice(5).split('-').reverse().join('/')} ${a.title}`, onRow: (st) => `#/eleves/${st.id}` }));
}

export async function studentPage({ params, query }) {
  const period = { from: query.from, to: query.to };
  const d = await api.get(`/stats/students/${params.id}` + qs(period));
  const p = d.profile;
  const answered = d.attempts.filter((a) => a.score !== null);
  const loginDays = new Set(d.logins.map((l) => l.at.slice(0, 10))).size;
  return h('div', {},
    h('p', {}, h('button', { class: 'link', onclick: () => history.back() }, '← Retour')),
    h('h1', {}, name(p), ' ', h('span', { class: 'muted small' }, p.username)),
    h('p', { class: 'muted' }, p.classes.map((c) => c.name).join(', ') || 'Aucune classe'),
    h('div', { class: 'stat-tiles' },
      tile(relTime(p.last_login_at), 'dernière connexion'),
      tile(d.logins.length, `connexions (${loginDays} jour(s) distincts)`),
      tile(answered.length, 'réponses'),
      tile(pct(answered.length ? answered.reduce((s, a) => s + a.score, 0) / answered.length : null), 'score moyen')),
    h('div', { class: 'split' },
      h('div', { class: 'card' }, h('h3', {}, 'Compétences (les plus fragiles d\'abord)'),
        d.skills.length ? h('table', { class: 'data' }, h('tbody', {}, d.skills.map((s) => h('tr', {},
          h('td', {}, s.name, s.chapter ? h('div', { class: 'small muted' }, s.chapter) : null),
          h('td', { style: { width: '45%' } }, meter(s.mastery)), h('td', { class: 'num small muted' }, `${s.attempts}`)))))
          : h('p', { class: 'muted' }, 'Aucune donnée.')),
      h('div', { class: 'card' }, h('h3', {}, 'Chapitres'),
        d.chapters.length ? h('table', { class: 'data' }, h('thead', {}, h('tr', {}, h('th', {}, 'Chapitre'), h('th', {}, 'Moyenne'), h('th', { class: 'num' }, 'Réponses'), h('th', { class: 'num' }, 'Questions'))),
          h('tbody', {}, d.chapters.map((c) => h('tr', {}, h('td', {}, c.name), h('td', { style: { width: '40%' } }, meter(c.avg)),
            h('td', { class: 'num' }, c.n), h('td', { class: 'num' }, c.questions))))) : h('p', { class: 'muted' }, 'Aucune donnée.'),
        h('h3', {}, 'Connexions récentes'),
        d.logins.length ? h('ul', { class: 'small', style: { maxHeight: '12rem', overflow: 'auto' } }, d.logins.slice(0, 50).map((l) => h('li', {}, fmtDateTime(l.at))))
          : h('p', { class: 'muted' }, 'Jamais connecté.'))),
    h('h2', {}, 'Questions traitées'),
    h('p', { class: 'small muted' }, "Cliquez sur une ligne pour voir l'énoncé exact reçu par l'élève, ses réponses et la correction."),
    d.attempts.length ? h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
      h('thead', {}, h('tr', {}, h('th', {}, 'Servie le'), h('th', {}, 'Question'), h('th', {}, 'Chapitre'), h('th', {}, 'Mode'), h('th', {}, 'Durée'), h('th', { class: 'num' }, 'Essais'), h('th', {}, 'Score'))),
      h('tbody', {}, d.attempts.map((a) => h('tr', { class: 'clickable', onclick: () => navigate(`/tentative/${a.id}`) },
        h('td', { class: 'small' }, fmtDateTime(a.created_at)), h('td', {}, a.uid ? h('span', { class: 'uid' }, a.uid) : null, a.title), h('td', { class: 'small' }, a.chapter || '—'),
        h('td', { class: 'small' }, MODE_LABEL[a.mode], a.assignment ? ` — ${a.assignment}` : ''),
        h('td', { class: 'small num' }, duration(a.created_at, a.answered_at)),
        h('td', { class: 'num' }, a.tries || '—'),
        h('td', {}, a.score === null ? h('span', { class: 'pill' }, a.tries ? 'non terminé' : 'sans réponse') : scorePill(a.score)))))))
      : h('div', { class: 'empty' }, 'Aucune question traitée.'));
}

function duration(a, b) {
  if (!b) return '—';
  const s = Math.round((new Date(b) - new Date(a)) / 1000);
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')}`;
  return '> 1 h';
}
