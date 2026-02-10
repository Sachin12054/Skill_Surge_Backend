-- Hypothesis Lab Database Schema
-- Run this migration in Supabase SQL Editor

-- =====================================================
-- Hypothesis Sessions Table
-- Stores the main hypothesis generation sessions
-- =====================================================
CREATE TABLE IF NOT EXISTS hypothesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    focus_area TEXT,
    status VARCHAR(50) DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    
    -- Input data
    paper_ids UUID[] DEFAULT '{}',
    
    -- Generated data stored as JSONB
    concepts JSONB DEFAULT '[]',
    claims JSONB DEFAULT '[]',
    hypotheses JSONB DEFAULT '[]',
    research_gaps JSONB DEFAULT '[]',
    citations JSONB DEFAULT '[]',
    
    -- Metadata
    error_message TEXT,
    processing_time_ms INTEGER,
    model_used VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- Saved Hypotheses Table
-- User's saved/bookmarked hypotheses from sessions
-- =====================================================
CREATE TABLE IF NOT EXISTS saved_hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES hypothesis_sessions(id) ON DELETE CASCADE,
    
    -- The hypothesis data (copied from session for persistence)
    hypothesis_id VARCHAR(100) NOT NULL,
    hypothesis_data JSONB NOT NULL,
    
    -- User notes/annotations
    notes TEXT,
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    saved_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- Indexes for Performance
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_hypothesis_sessions_user_id 
    ON hypothesis_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_hypothesis_sessions_status 
    ON hypothesis_sessions(status);

CREATE INDEX IF NOT EXISTS idx_hypothesis_sessions_created_at 
    ON hypothesis_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_saved_hypotheses_user_id 
    ON saved_hypotheses(user_id);

CREATE INDEX IF NOT EXISTS idx_saved_hypotheses_session_id 
    ON saved_hypotheses(session_id);

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================
ALTER TABLE hypothesis_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_hypotheses ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sessions
CREATE POLICY "Users can view own hypothesis sessions" 
    ON hypothesis_sessions FOR SELECT 
    USING (auth.uid() = user_id);

-- Users can insert their own sessions
CREATE POLICY "Users can create hypothesis sessions" 
    ON hypothesis_sessions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own sessions
CREATE POLICY "Users can update own hypothesis sessions" 
    ON hypothesis_sessions FOR UPDATE 
    USING (auth.uid() = user_id);

-- Users can delete their own sessions
CREATE POLICY "Users can delete own hypothesis sessions" 
    ON hypothesis_sessions FOR DELETE 
    USING (auth.uid() = user_id);

-- Saved hypotheses policies
CREATE POLICY "Users can view own saved hypotheses" 
    ON saved_hypotheses FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can save hypotheses" 
    ON saved_hypotheses FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own saved hypotheses" 
    ON saved_hypotheses FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own saved hypotheses" 
    ON saved_hypotheses FOR DELETE 
    USING (auth.uid() = user_id);

-- =====================================================
-- Service Role Bypass (for backend operations)
-- =====================================================
-- Allow service role to perform all operations
CREATE POLICY "Service role bypass for hypothesis_sessions" 
    ON hypothesis_sessions FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role bypass for saved_hypotheses" 
    ON saved_hypotheses FOR ALL 
    USING (auth.jwt() ->> 'role' = 'service_role');

-- =====================================================
-- Updated At Trigger
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_hypothesis_sessions_updated_at
    BEFORE UPDATE ON hypothesis_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Helper View for Session Statistics
-- =====================================================
CREATE OR REPLACE VIEW hypothesis_session_stats AS
SELECT 
    user_id,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_sessions,
    AVG(jsonb_array_length(hypotheses)) as avg_hypotheses_per_session,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM hypothesis_sessions
GROUP BY user_id;

-- Grant access to the view
GRANT SELECT ON hypothesis_session_stats TO authenticated;
