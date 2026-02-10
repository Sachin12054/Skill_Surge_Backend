-- Mock Interviews Table
-- Stores AI-powered mock interview sessions using Tavus video API

CREATE TABLE IF NOT EXISTS mock_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'behavioral', 'technical', 'system-design'
    target_role VARCHAR(255),
    conversation_id VARCHAR(255), -- Tavus conversation ID
    conversation_url TEXT, -- Tavus video URL
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'ended', 'demo'
    duration INTEGER DEFAULT 0, -- Duration in seconds
    demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mock_interviews_user_id 
    ON mock_interviews(user_id);

CREATE INDEX IF NOT EXISTS idx_mock_interviews_status 
    ON mock_interviews(status);

CREATE INDEX IF NOT EXISTS idx_mock_interviews_created_at 
    ON mock_interviews(created_at DESC);

-- Row Level Security
ALTER TABLE mock_interviews ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own interviews" 
    ON mock_interviews FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own interviews" 
    ON mock_interviews FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own interviews" 
    ON mock_interviews FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own interviews" 
    ON mock_interviews FOR DELETE 
    USING (auth.uid() = user_id);

-- Service role bypass (for backend operations)
CREATE POLICY "Service role bypass for mock_interviews" 
    ON mock_interviews FOR ALL 
    USING (auth.role() = 'service_role');

-- Updated_at trigger
CREATE TRIGGER update_mock_interviews_updated_at
    BEFORE UPDATE ON mock_interviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE mock_interviews IS 'AI-powered mock interview sessions using Tavus video API';
COMMENT ON COLUMN mock_interviews.type IS 'Interview type: behavioral, technical, or system-design';
COMMENT ON COLUMN mock_interviews.conversation_id IS 'Tavus conversation identifier';
COMMENT ON COLUMN mock_interviews.conversation_url IS 'Tavus video session URL for embedding';
COMMENT ON COLUMN mock_interviews.demo IS 'True if running in demo mode without actual Tavus connection';
