BEGIN IMMEDIATE;

CREATE TABLE learning_attempts (
    attempt_id TEXT PRIMARY KEY NOT NULL,
    submission_id TEXT NOT NULL UNIQUE,
    visit_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    activity_kind TEXT NOT NULL CHECK (activity_kind IN ('practice', 'quiz')),
    content_version TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (typeof(score) = 'integer' AND score >= 0),
    total_questions INTEGER NOT NULL CHECK (typeof(total_questions) = 'integer'),
    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (visit_id, topic_id) REFERENCES topic_progress(visit_id, topic_id),
    CHECK (score <= total_questions),
    CHECK ((activity_kind = 'practice' AND total_questions = 1)
        OR (activity_kind = 'quiz' AND total_questions = 5))
);

CREATE INDEX attempts_by_visit_topic ON learning_attempts(visit_id, topic_id, submitted_at);

CREATE TABLE learning_answers (
    attempt_id TEXT NOT NULL REFERENCES learning_attempts(attempt_id),
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 5),
    question_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    selected_option TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    explanation TEXT NOT NULL,
    PRIMARY KEY (attempt_id, position),
    UNIQUE (attempt_id, question_id),
    CHECK (is_correct = (selected_option = correct_option))
);

PRAGMA user_version = 3;
COMMIT;
