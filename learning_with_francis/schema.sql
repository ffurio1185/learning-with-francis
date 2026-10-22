-- P2.1 curriculum metadata only. No visits, questions, answers, or progress yet.
BEGIN IMMEDIATE;

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    display_order INTEGER NOT NULL UNIQUE CHECK (display_order > 0)
);

CREATE TABLE topics (
    topic_id TEXT PRIMARY KEY NOT NULL,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    UNIQUE (subject_id, title)
);

INSERT INTO subjects (subject_id, name, display_order) VALUES
    ('sql', 'SQL', 1),
    ('python', 'Python', 2),
    ('javascript', 'JavaScript', 3),
    ('sap', 'SAP', 4);

INSERT INTO topics (topic_id, subject_id, title) VALUES
    ('sql-select-basics', 'sql', 'Reading tables with SELECT and WHERE'),
    ('python-basics', 'python', 'Variables and simple functions'),
    ('javascript-basics', 'javascript', 'Values, DOM elements, and events'),
    ('sap-basics', 'sap', 'Basic ERP concepts and business-process scenarios');

PRAGMA application_id = 0x4C574631;
PRAGMA user_version = 1;
COMMIT;
