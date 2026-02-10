-- Quiz Feature Database Schema
-- Run this migration to set up quiz tables

-- ============ Clean up existing objects (if any) ============
-- Drop tables first (CASCADE will handle triggers and constraints)
DROP TABLE IF EXISTS public.quiz_answers CASCADE;
DROP TABLE IF EXISTS public.quiz_sessions CASCADE;
DROP TABLE IF EXISTS public.quiz_performance CASCADE;
DROP TABLE IF EXISTS public.user_learning_profiles CASCADE;
DROP TABLE IF EXISTS public.quizzes CASCADE;

-- Drop functions after tables are gone
DROP FUNCTION IF EXISTS calculate_streak_days() CASCADE;
DROP FUNCTION IF EXISTS update_user_learning_profile() CASCADE;

-- ============ Quizzes Table ============
CREATE TABLE public.quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pdf_ids TEXT[] NOT NULL,
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    subject_name TEXT,
    quiz_type TEXT NOT NULL CHECK (quiz_type IN ('mcq', 'true_false', 'short_answer', 'mixed')),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard', 'adaptive')),
    num_questions INTEGER NOT NULL DEFAULT 10,
    time_limit INTEGER, -- in minutes
    adaptive_mode BOOLEAN DEFAULT FALSE,
    questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_answers JSONB DEFAULT '{}'::jsonb, -- Store all user answers
    detailed_results JSONB DEFAULT '[]'::jsonb, -- Store complete results with explanations
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    current_question_index INTEGER DEFAULT 0, -- For resume functionality
    time_spent INTEGER DEFAULT 0, -- Accumulated time in seconds
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT valid_num_questions CHECK (num_questions > 0 AND num_questions <= 50)
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_quizzes_user_id ON public.quizzes(user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_status ON public.quizzes(status);
CREATE INDEX IF NOT EXISTS idx_quizzes_created_at ON public.quizzes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quizzes_subject_id ON public.quizzes(subject_id);

-- ============ Quiz Performance Table ============
CREATE TABLE public.quiz_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_id UUID NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    accuracy DECIMAL(5,4) NOT NULL CHECK (accuracy >= 0 AND accuracy <= 1),
    percentage DECIMAL(5,2) NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    earned_points INTEGER NOT NULL DEFAULT 0,
    total_points INTEGER NOT NULL DEFAULT 0,
    time_taken INTEGER NOT NULL DEFAULT 0, -- in seconds
    weak_topics TEXT[] DEFAULT '{}',
    strong_topics TEXT[] DEFAULT '{}',
    topic_scores JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_quiz_performance_user_id ON public.quiz_performance(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_performance_quiz_id ON public.quiz_performance(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_performance_created_at ON public.quiz_performance(created_at DESC);

-- ============ Quiz Sessions Table (for adaptive mode) ============
CREATE TABLE public.quiz_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_id UUID NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    correct_count INTEGER NOT NULL DEFAULT 0,
    total_answered INTEGER NOT NULL DEFAULT 0,
    current_difficulty INTEGER NOT NULL DEFAULT 3 CHECK (current_difficulty >= 1 AND current_difficulty <= 5),
    answers JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_quiz_session UNIQUE (user_id, quiz_id)
);

-- Index for session queries
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_quiz ON public.quiz_sessions(user_id, quiz_id);

-- ============ Quiz Answers Table (detailed answer tracking) ============
CREATE TABLE public.quiz_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_id UUID NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    question_id UUID NOT NULL,
    user_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_spent INTEGER DEFAULT 0, -- seconds spent on this question
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for answer queries
CREATE INDEX IF NOT EXISTS idx_quiz_answers_user_quiz ON public.quiz_answers(user_id, quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_question ON public.quiz_answers(question_id);

-- ============ User Learning Profile Table ============
CREATE TABLE public.user_learning_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    total_quizzes_taken INTEGER DEFAULT 0,
    total_questions_answered INTEGER DEFAULT 0,
    overall_accuracy DECIMAL(5,4) DEFAULT 0,
    preferred_difficulty TEXT DEFAULT 'medium',
    learning_style JSONB DEFAULT '{}'::jsonb,
    weak_topics TEXT[] DEFAULT '{}',
    strong_topics TEXT[] DEFAULT '{}',
    streak_days INTEGER DEFAULT 0,
    last_quiz_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for user profile
CREATE INDEX IF NOT EXISTS idx_user_learning_profiles_user_id ON public.user_learning_profiles(user_id);

-- ============ Row Level Security ============

-- Enable RLS on all tables
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_learning_profiles ENABLE ROW LEVEL SECURITY;

-- Policies for quizzes
CREATE POLICY "Users can view their own quizzes"
    ON public.quizzes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own quizzes"
    ON public.quizzes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own quizzes"
    ON public.quizzes FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own quizzes"
    ON public.quizzes FOR DELETE
    USING (auth.uid() = user_id);

-- Policies for quiz_performance
CREATE POLICY "Users can view their own performance"
    ON public.quiz_performance FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own performance"
    ON public.quiz_performance FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for quiz_sessions
CREATE POLICY "Users can manage their own sessions"
    ON public.quiz_sessions FOR ALL
    USING (auth.uid() = user_id);

-- Policies for quiz_answers
CREATE POLICY "Users can manage their own answers"
    ON public.quiz_answers FOR ALL
    USING (auth.uid() = user_id);

-- Policies for user_learning_profiles
CREATE POLICY "Users can manage their own profile"
    ON public.user_learning_profiles FOR ALL
    USING (auth.uid() = user_id);

-- ============ Functions ============

-- Function to update user learning profile after quiz completion
CREATE OR REPLACE FUNCTION update_user_learning_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_learning_profiles (user_id, total_quizzes_taken, overall_accuracy, last_quiz_date, updated_at)
    VALUES (NEW.user_id, 1, NEW.accuracy, CURRENT_DATE, NOW())
    ON CONFLICT (user_id) DO UPDATE SET
        total_quizzes_taken = user_learning_profiles.total_quizzes_taken + 1,
        overall_accuracy = (user_learning_profiles.overall_accuracy * user_learning_profiles.total_quizzes_taken + NEW.accuracy) / (user_learning_profiles.total_quizzes_taken + 1),
        weak_topics = ARRAY(
            SELECT DISTINCT unnest(user_learning_profiles.weak_topics || NEW.weak_topics)
        ),
        strong_topics = ARRAY(
            SELECT DISTINCT unnest(user_learning_profiles.strong_topics || NEW.strong_topics)
        ),
        last_quiz_date = CURRENT_DATE,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update learning profile
CREATE TRIGGER on_quiz_performance_insert
    AFTER INSERT ON public.quiz_performance
    FOR EACH ROW
    EXECUTE FUNCTION update_user_learning_profile();

-- Function to calculate streak days
CREATE OR REPLACE FUNCTION calculate_streak_days()
RETURNS TRIGGER AS $$
DECLARE
    last_date DATE;
    current_streak INTEGER;
BEGIN
    SELECT last_quiz_date, streak_days INTO last_date, current_streak
    FROM public.user_learning_profiles
    WHERE user_id = NEW.user_id;
    
    IF last_date IS NULL OR last_date < CURRENT_DATE - INTERVAL '1 day' THEN
        -- Reset streak
        UPDATE public.user_learning_profiles
        SET streak_days = 1
        WHERE user_id = NEW.user_id;
    ELSIF last_date = CURRENT_DATE - INTERVAL '1 day' THEN
        -- Increment streak
        UPDATE public.user_learning_profiles
        SET streak_days = streak_days + 1
        WHERE user_id = NEW.user_id;
    END IF;
    -- If same day, streak stays the same
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for streak calculation
CREATE TRIGGER on_quiz_performance_streak
    AFTER INSERT ON public.quiz_performance
    FOR EACH ROW
    EXECUTE FUNCTION calculate_streak_days();

-- ============ Grant permissions ============
GRANT ALL ON public.quizzes TO authenticated;
GRANT ALL ON public.quiz_performance TO authenticated;
GRANT ALL ON public.quiz_sessions TO authenticated;
GRANT ALL ON public.quiz_answers TO authenticated;
GRANT ALL ON public.user_learning_profiles TO authenticated;
