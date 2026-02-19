-- Add task_id column to hypothesis_sessions to link in-memory task tracking
-- to persisted sessions, enabling status recovery after server restarts.

ALTER TABLE hypothesis_sessions
    ADD COLUMN IF NOT EXISTS task_id TEXT;

-- Index for fast lookup by task_id
CREATE INDEX IF NOT EXISTS idx_hypothesis_sessions_task_id
    ON hypothesis_sessions (task_id)
    WHERE task_id IS NOT NULL;
