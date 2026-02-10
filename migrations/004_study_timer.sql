-- Study Timer / Pomodoro Feature
-- Run this migration in Supabase SQL Editor

-- ============================================
-- Study Sessions Table (individual pomodoro sessions)
-- ============================================
CREATE TABLE IF NOT EXISTS study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Session details
    session_type VARCHAR(20) NOT NULL DEFAULT 'focus', -- 'focus', 'short_break', 'long_break'
    duration_minutes INTEGER NOT NULL DEFAULT 25,
    actual_duration_seconds INTEGER, -- Actual time spent (for incomplete sessions)
    
    -- What was being studied
    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
    deck_id UUID REFERENCES flashcard_decks(id) ON DELETE SET NULL,
    activity_type VARCHAR(50), -- 'flashcards', 'quiz', 'reading', 'notes', 'general'
    
    -- Session state
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'completed', 'paused', 'cancelled'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    total_pause_seconds INTEGER DEFAULT 0,
    
    -- Productivity tracking
    focus_rating INTEGER CHECK (focus_rating >= 1 AND focus_rating <= 5), -- User self-rating after session
    notes TEXT,
    distractions_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Daily Study Stats (aggregated daily stats)
-- ============================================
CREATE TABLE IF NOT EXISTS daily_study_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Time stats
    total_focus_minutes INTEGER DEFAULT 0,
    total_break_minutes INTEGER DEFAULT 0,
    sessions_completed INTEGER DEFAULT 0,
    sessions_cancelled INTEGER DEFAULT 0,
    
    -- Productivity
    average_focus_rating DECIMAL(3,2),
    total_distractions INTEGER DEFAULT 0,
    longest_streak_minutes INTEGER DEFAULT 0,
    
    -- Goals
    daily_goal_minutes INTEGER DEFAULT 120, -- 2 hours default
    goal_achieved BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, date)
);

-- ============================================
-- Subject Study Time (time per subject)
-- ============================================
CREATE TABLE IF NOT EXISTS subject_study_time (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    focus_minutes INTEGER DEFAULT 0,
    sessions_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, subject_id, date)
);

-- ============================================
-- User Timer Settings
-- ============================================
CREATE TABLE IF NOT EXISTS timer_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    
    -- Duration settings (in minutes)
    focus_duration INTEGER DEFAULT 25,
    short_break_duration INTEGER DEFAULT 5,
    long_break_duration INTEGER DEFAULT 15,
    sessions_until_long_break INTEGER DEFAULT 4,
    
    -- Preferences
    auto_start_breaks BOOLEAN DEFAULT TRUE,
    auto_start_focus BOOLEAN DEFAULT FALSE,
    sound_enabled BOOLEAN DEFAULT TRUE,
    vibration_enabled BOOLEAN DEFAULT TRUE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    
    -- Daily goals
    daily_goal_minutes INTEGER DEFAULT 120,
    weekly_goal_minutes INTEGER DEFAULT 600,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Study Streaks
-- ============================================
CREATE TABLE IF NOT EXISTS study_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_study_date DATE,
    streak_start_date DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Indexes for performance
-- ============================================
CREATE INDEX idx_study_sessions_user_id ON study_sessions(user_id);
CREATE INDEX idx_study_sessions_started_at ON study_sessions(started_at);
CREATE INDEX idx_study_sessions_status ON study_sessions(status);
CREATE INDEX idx_study_sessions_subject_id ON study_sessions(subject_id);
CREATE INDEX idx_daily_study_stats_user_date ON daily_study_stats(user_id, date);
CREATE INDEX idx_subject_study_time_user_subject ON subject_study_time(user_id, subject_id);

-- ============================================
-- Row Level Security Policies
-- ============================================
ALTER TABLE study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_study_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE subject_study_time ENABLE ROW LEVEL SECURITY;
ALTER TABLE timer_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_streaks ENABLE ROW LEVEL SECURITY;

-- Study Sessions policies
CREATE POLICY "Users can manage own study sessions" ON study_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Daily Study Stats policies
CREATE POLICY "Users can manage own daily stats" ON daily_study_stats
    FOR ALL USING (auth.uid() = user_id);

-- Subject Study Time policies
CREATE POLICY "Users can manage own subject time" ON subject_study_time
    FOR ALL USING (auth.uid() = user_id);

-- Timer Settings policies
CREATE POLICY "Users can manage own timer settings" ON timer_settings
    FOR ALL USING (auth.uid() = user_id);

-- Study Streaks policies
CREATE POLICY "Users can manage own streaks" ON study_streaks
    FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- Updated_at trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_study_timer_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables
CREATE TRIGGER update_study_sessions_updated_at
    BEFORE UPDATE ON study_sessions
    FOR EACH ROW EXECUTE FUNCTION update_study_timer_updated_at();

CREATE TRIGGER update_daily_study_stats_updated_at
    BEFORE UPDATE ON daily_study_stats
    FOR EACH ROW EXECUTE FUNCTION update_study_timer_updated_at();

CREATE TRIGGER update_subject_study_time_updated_at
    BEFORE UPDATE ON subject_study_time
    FOR EACH ROW EXECUTE FUNCTION update_study_timer_updated_at();

CREATE TRIGGER update_timer_settings_updated_at
    BEFORE UPDATE ON timer_settings
    FOR EACH ROW EXECUTE FUNCTION update_study_timer_updated_at();

CREATE TRIGGER update_study_streaks_updated_at
    BEFORE UPDATE ON study_streaks
    FOR EACH ROW EXECUTE FUNCTION update_study_timer_updated_at();


