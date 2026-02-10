-- Migration: Create scanned_notes table for Handwritten Notes Scanner feature
-- This table stores notes scanned using Google Vision API

-- Create scanned_notes table
CREATE TABLE IF NOT EXISTS scanned_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
    confidence FLOAT DEFAULT 0.0,
    language VARCHAR(10) DEFAULT 'en',
    image_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_scanned_notes_user_id ON scanned_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_scanned_notes_subject_id ON scanned_notes(subject_id);
CREATE INDEX IF NOT EXISTS idx_scanned_notes_created_at ON scanned_notes(created_at DESC);

-- Enable full-text search on text and title
CREATE INDEX IF NOT EXISTS idx_scanned_notes_text_search 
ON scanned_notes USING gin(to_tsvector('english', title || ' ' || text));

-- Create GIN index for keyword array search
CREATE INDEX IF NOT EXISTS idx_scanned_notes_keywords ON scanned_notes USING gin(keywords);

-- Enable RLS (Row Level Security)
ALTER TABLE scanned_notes ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own scanned notes
CREATE POLICY "Users can view own scanned notes"
    ON scanned_notes FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own scanned notes
CREATE POLICY "Users can insert own scanned notes"
    ON scanned_notes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own scanned notes
CREATE POLICY "Users can update own scanned notes"
    ON scanned_notes FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own scanned notes
CREATE POLICY "Users can delete own scanned notes"
    ON scanned_notes FOR DELETE
    USING (auth.uid() = user_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_scanned_notes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_scanned_notes_updated_at
    BEFORE UPDATE ON scanned_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_scanned_notes_updated_at();
