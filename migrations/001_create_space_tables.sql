-- Migration: Create Space/Library Feature Tables
-- Description: Tables for organizing user PDFs into subjects/folders
-- Date: 2026-01-22

-- ============================================
-- 1. Create subjects table
-- ============================================
CREATE TABLE IF NOT EXISTS subjects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  color TEXT DEFAULT '#6366F1',
  icon TEXT DEFAULT 'folder',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster user queries
CREATE INDEX IF NOT EXISTS idx_subjects_user_id ON subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_subjects_name ON subjects(name);

-- ============================================
-- 2. Create space_pdfs table
-- ============================================
CREATE TABLE IF NOT EXISTS space_pdfs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INTEGER DEFAULT 0,
  subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
  uploaded_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_space_pdfs_user_id ON space_pdfs(user_id);
CREATE INDEX IF NOT EXISTS idx_space_pdfs_subject_id ON space_pdfs(subject_id);
CREATE INDEX IF NOT EXISTS idx_space_pdfs_name ON space_pdfs(name);

-- ============================================
-- 3. Enable Row Level Security (RLS)
-- ============================================
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE space_pdfs ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 4. Create RLS Policies for subjects
-- ============================================

-- Users can view their own subjects
CREATE POLICY "Users can view own subjects"
  ON subjects FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own subjects
CREATE POLICY "Users can insert own subjects"
  ON subjects FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own subjects
CREATE POLICY "Users can update own subjects"
  ON subjects FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own subjects
CREATE POLICY "Users can delete own subjects"
  ON subjects FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- 5. Create RLS Policies for space_pdfs
-- ============================================

-- Users can view their own PDFs
CREATE POLICY "Users can view own pdfs"
  ON space_pdfs FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own PDFs
CREATE POLICY "Users can insert own pdfs"
  ON space_pdfs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own PDFs
CREATE POLICY "Users can update own pdfs"
  ON space_pdfs FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own PDFs
CREATE POLICY "Users can delete own pdfs"
  ON space_pdfs FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- 6. Create function to update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 7. Create triggers for updated_at
-- ============================================
CREATE TRIGGER update_subjects_updated_at
  BEFORE UPDATE ON subjects
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_space_pdfs_updated_at
  BEFORE UPDATE ON space_pdfs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
