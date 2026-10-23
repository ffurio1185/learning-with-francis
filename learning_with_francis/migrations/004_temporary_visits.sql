BEGIN IMMEDIATE;

-- Existing dates stay unchanged. Older visits start from their actual creation
-- time; only a subsequent valid request can renew a still-active visit.
ALTER TABLE visits ADD COLUMN last_activity_at TEXT;
UPDATE visits SET last_activity_at = started_at;
CREATE INDEX visits_by_activity ON visits(COALESCE(last_activity_at, started_at));

PRAGMA user_version = 4;
COMMIT;
