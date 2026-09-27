-- Schéma QuestionnApp (SQL standard, testé sous SQLite ; portable vers PostgreSQL/MySQL
-- en remplaçant INTEGER PRIMARY KEY par SERIAL/AUTO_INCREMENT). Dates : texte ISO 8601 UTC.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name  TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- Journal des connexions (statistiques « quand l'élève s'est-il connecté »)
CREATE TABLE IF NOT EXISTS logins (
    id      INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    at      TEXT NOT NULL,
    ip      TEXT
);
CREATE INDEX IF NOT EXISTS idx_logins_user ON logins(user_id, at);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL
);

-- Élèves et professeurs d'une classe
CREATE TABLE IF NOT EXISTS class_members (
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (class_id, user_id)
);

CREATE TABLE IF NOT EXISTS chapters (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skills (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY,
    uid         TEXT,                      -- identifiant lisible et unique (DICO-07, Q-0042) ; index unique créé par db.init
    title       TEXT NOT NULL,
    chapter_id  INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    difficulty  INTEGER NOT NULL DEFAULT 2 CHECK (difficulty BETWEEN 1 AND 3),
    version_id  INTEGER,                   -- version courante (question_versions.id)
    author_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Chaque modification du modèle crée une version : les tentatives passées restent
-- corrigeables et consultables telles que l'élève les a vues.
CREATE TABLE IF NOT EXISTS question_versions (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    template    TEXT NOT NULL,             -- JSON, voir docs/QUESTION_FORMAT.md
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_skills (
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    skill_id    INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (question_id, skill_id)
);

-- Affectation d'une question à 0, 1 ou plusieurs classes
CREATE TABLE IF NOT EXISTS class_questions (
    class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    PRIMARY KEY (class_id, question_id)
);

-- Séances / devoirs : une liste de questions à traiter pour un jour donné
CREATE TABLE IF NOT EXISTS assignments (
    id         INTEGER PRIMARY KEY,
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    day        TEXT NOT NULL,              -- AAAA-MM-JJ
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assignments_class ON assignments(class_id, day);

CREATE TABLE IF NOT EXISTS assignment_questions (
    assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    question_id   INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (assignment_id, question_id)
);

-- Une tentative = une instance servie à un élève (graine) puis, éventuellement, sa réponse.
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id   INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    version_id    INTEGER NOT NULL REFERENCES question_versions(id),
    assignment_id INTEGER REFERENCES assignments(id) ON DELETE SET NULL,
    mode          TEXT NOT NULL CHECK (mode IN ('assignment', 'chapter', 'adaptive', 'free')),
    seed          INTEGER NOT NULL,
    fingerprint   TEXT NOT NULL,
    instance      TEXT NOT NULL,           -- JSON : énoncé et champs tels que vus par l'élève
    answers       TEXT,                    -- JSON
    result        TEXT,                    -- JSON : correction détaillée
    score         REAL,                    -- 0..1 (pondéré par le nombre d'essais), NULL tant que non terminé
    tries         INTEGER NOT NULL DEFAULT 0, -- nombre d'essais utilisés
    history       TEXT,                    -- JSON : [{answers, score, at}] pour chaque essai
    created_at    TEXT NOT NULL,
    answered_at   TEXT                     -- date de fin (bonne réponse, essais épuisés ou solution demandée)
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_attempts_question ON attempts(question_id, user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_assignment ON attempts(assignment_id, user_id);
