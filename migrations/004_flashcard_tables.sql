-- Flashcard Tables Migration
-- Syllabus.ai - Spaced Repetition Flashcard System

-- Flashcard decks (collections of cards)
CREATE TABLE IF NOT EXISTS flashcard_decks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    card_count INTEGER DEFAULT 0,
    mastered_count INTEGER DEFAULT 0,
    color TEXT DEFAULT '#6366F1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual flashcards
CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    front TEXT NOT NULL,  -- Question/term side
    back TEXT NOT NULL,   -- Answer/definition side
    hint TEXT,            -- Optional hint
    source_pdf_id UUID REFERENCES space_pdfs(id) ON DELETE SET NULL,
    tags TEXT[] DEFAULT '{}',
    
    -- Spaced Repetition (SM-2 Algorithm) fields
    ease_factor FLOAT DEFAULT 2.5,        -- Difficulty multiplier (1.3 - 2.5+)
    interval_days INTEGER DEFAULT 0,       -- Days until next review
    repetitions INTEGER DEFAULT 0,         -- Number of successful reviews
    next_review_date TIMESTAMPTZ DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    
    -- Status
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'learning', 'reviewing', 'mastered')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review history for analytics
CREATE TABLE IF NOT EXISTS flashcard_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Review result (0-5 scale like SM-2)
    -- 0: Complete blackout, 1: Wrong but recognized, 2: Wrong but easy recall
    -- 3: Correct with difficulty, 4: Correct with hesitation, 5: Perfect recall
    quality INTEGER NOT NULL CHECK (quality >= 0 AND quality <= 5),
    
    -- Time tracking
    response_time_ms INTEGER,  -- How long user took to answer
    
    -- State before review (for analytics)
    previous_interval INTEGER,
    previous_ease_factor FLOAT,
    
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Study sessions for tracking
CREATE TABLE IF NOT EXISTS flashcard_study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    deck_id UUID REFERENCES flashcard_decks(id) ON DELETE SET NULL,
    
    cards_studied INTEGER DEFAULT 0,
    cards_correct INTEGER DEFAULT 0,
    total_time_seconds INTEGER DEFAULT 0,
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_flashcards_deck_id ON flashcards(deck_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_user_id ON flashcards(user_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_next_review ON flashcards(user_id, next_review_date);
CREATE INDEX IF NOT EXISTS idx_flashcards_status ON flashcards(status);
CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_card ON flashcard_reviews(flashcard_id);
CREATE INDEX IF NOT EXISTS idx_flashcard_decks_user ON flashcard_decks(user_id);

-- Row Level Security
ALTER TABLE flashcard_decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcards ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcard_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcard_study_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for flashcard_decks
CREATE POLICY "Users can view own decks" ON flashcard_decks
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create decks" ON flashcard_decks
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own decks" ON flashcard_decks
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own decks" ON flashcard_decks
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for flashcards
CREATE POLICY "Users can view own flashcards" ON flashcards
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create flashcards" ON flashcards
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own flashcards" ON flashcards
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own flashcards" ON flashcards
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for flashcard_reviews
CREATE POLICY "Users can view own reviews" ON flashcard_reviews
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create reviews" ON flashcard_reviews
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS Policies for study sessions
CREATE POLICY "Users can view own sessions" ON flashcard_study_sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create sessions" ON flashcard_study_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sessions" ON flashcard_study_sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- Function to update deck card counts
CREATE OR REPLACE FUNCTION update_deck_card_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE flashcard_decks 
        SET card_count = card_count + 1,
            updated_at = NOW()
        WHERE id = NEW.deck_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE flashcard_decks 
        SET card_count = GREATEST(0, card_count - 1),
            mastered_count = CASE 
                WHEN OLD.status = 'mastered' THEN GREATEST(0, mastered_count - 1)
                ELSE mastered_count
            END,
            updated_at = NOW()
        WHERE id = OLD.deck_id;
    ELSIF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
        IF NEW.status = 'mastered' THEN
            UPDATE flashcard_decks 
            SET mastered_count = mastered_count + 1,
                updated_at = NOW()
            WHERE id = NEW.deck_id;
        ELSIF OLD.status = 'mastered' THEN
            UPDATE flashcard_decks 
            SET mastered_count = GREATEST(0, mastered_count - 1),
                updated_at = NOW()
            WHERE id = OLD.deck_id;
        END IF;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger for card count updates
DROP TRIGGER IF EXISTS trigger_update_deck_card_count ON flashcards;
CREATE TRIGGER trigger_update_deck_card_count
    AFTER INSERT OR UPDATE OR DELETE ON flashcards
    FOR EACH ROW EXECUTE FUNCTION update_deck_card_count();
