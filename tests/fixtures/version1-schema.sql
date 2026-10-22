-- Version 1 schema only; no original records or demonstration data.
PRAGMA foreign_keys = ON;

CREATE TABLE Categories (
category_id INTEGER PRIMARY KEY,
category_name TEXT NOT NULL UNIQUE,
learning_status TEXT NOT NULL DEFAULT 'Still Learning'
CHECK (learning_status IN ('Still Learning', 'Needs Review', 'Completed')),
understanding_confirmed_at TEXT,
CHECK (
(learning_status = 'Completed' AND understanding_confirmed_at IS NOT NULL)
OR
(learning_status IN ('Still Learning', 'Needs Review') AND understanding_confirmed_at IS NULL)
)
);

CREATE TABLE QuizAttempts (
attempt_id INTEGER PRIMARY KEY,
category_id INTEGER NOT NULL,
quiz_name TEXT NOT NULL,
correct_answers INTEGER NOT NULL,
total_questions INTEGER NOT NULL,
attempted_at TEXT NOT NULL DEFAULT (datetime('now')),
FOREIGN KEY (category_id) REFERENCES Categories(category_id),
CHECK (
typeof(correct_answers) = 'integer'
AND typeof(total_questions) = 'integer'
AND total_questions > 0
AND correct_answers >= 0
AND correct_answers <= total_questions
)
);

CREATE TABLE Tasks (
task_id INTEGER PRIMARY KEY,
title TEXT NOT NULL,
status INTEGER NOT NULL DEFAULT 0 CHECK (status IN (0, 1)),
category_id INTEGER NOT NULL,
created_at TEXT NOT NULL DEFAULT (datetime('now')),
completed_at TEXT,
FOREIGN KEY (category_id) REFERENCES Categories(category_id),
CHECK (
(status = 0 AND completed_at IS NULL)
OR
(status = 1 AND completed_at IS NOT NULL)
)
);

CREATE TABLE TopicStatusHistory (
history_id INTEGER PRIMARY KEY,
category_id INTEGER NOT NULL,
previous_status TEXT,
new_status TEXT NOT NULL
CHECK (new_status IN ('Still Learning', 'Needs Review', 'Completed')),
changed_at TEXT NOT NULL DEFAULT (datetime('now')),
user_confirmed INTEGER NOT NULL DEFAULT 0
CHECK (user_confirmed IN (0, 1)),
FOREIGN KEY (category_id) REFERENCES Categories(category_id),
CHECK (new_status != 'Completed' OR user_confirmed = 1)
);
