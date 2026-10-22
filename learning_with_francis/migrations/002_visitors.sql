BEGIN IMMEDIATE;

CREATE TABLE visits (
    visit_id TEXT PRIMARY KEY NOT NULL,
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 50),
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT
);

CREATE TABLE topic_progress (
    visit_id TEXT NOT NULL REFERENCES visits(visit_id),
    topic_id TEXT NOT NULL REFERENCES topics(topic_id),
    learning_status TEXT NOT NULL DEFAULT 'Still Learning'
        CHECK (learning_status IN ('Still Learning', 'Needs Review', 'Completed')),
    understanding_confirmed_at TEXT,
    PRIMARY KEY (visit_id, topic_id),
    CHECK (
        (learning_status = 'Completed' AND understanding_confirmed_at IS NOT NULL)
        OR (learning_status != 'Completed' AND understanding_confirmed_at IS NULL)
    )
);

CREATE TABLE topic_status_history (
    history_id INTEGER PRIMARY KEY,
    visit_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    previous_status TEXT CHECK (previous_status IN ('Still Learning', 'Needs Review', 'Completed')),
    new_status TEXT NOT NULL CHECK (new_status IN ('Still Learning', 'Needs Review', 'Completed')),
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    user_confirmed INTEGER NOT NULL CHECK (user_confirmed IN (0, 1)),
    FOREIGN KEY (visit_id, topic_id) REFERENCES topic_progress(visit_id, topic_id),
    CHECK ((new_status = 'Completed' AND user_confirmed = 1)
        OR (new_status != 'Completed' AND user_confirmed = 0))
);

PRAGMA user_version = 2;
COMMIT;
