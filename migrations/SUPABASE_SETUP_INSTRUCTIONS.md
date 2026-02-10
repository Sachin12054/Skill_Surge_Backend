# Supabase Setup Instructions for Space Feature

## Step 1: Access Supabase SQL Editor

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Click on **SQL Editor** in the left sidebar (or press `Ctrl+K` and search "SQL Editor")

## Step 2: Run the Migration SQL

1. Click **"+ New query"** button
2. Copy the entire content from `001_create_space_tables.sql`
3. Paste it into the SQL Editor
4. Click **"Run"** (or press `Ctrl+Enter`)
5. Wait for success message: "Success. No rows returned"

**What this creates:**
- ✅ `subjects` table - For organizing PDFs into folders/categories
- ✅ `space_pdfs` table - For storing PDF metadata
- ✅ Indexes for faster queries
- ✅ Row Level Security (RLS) policies - Users can only see their own data
- ✅ Auto-updating timestamps
- ✅ Foreign key relationships

## Step 3: Configure Storage Bucket

### ✅ Using Existing Bucket: `course-materials`

The Space feature will use your existing **`course-materials`** bucket to store PDFs.

**No new bucket creation needed!** The backend is already configured to use `course-materials`.

### Verify Storage Policies

Your `course-materials` bucket should already have the necessary policies. Verify by:

1. Go to **Storage** → Click **`course-materials`**
2. Go to **Policies** tab
3. Make sure you have these policies (if not, add them):

#### Policy 1: Users can upload their own files
```sql
-- Policy name: Users can upload own files
-- Allowed operation: INSERT
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'course-materials' AND
  auth.uid()::text = (storage.foldername(name))[1]
);
```

#### Policy 2: Users can view their own files
```sql
-- Policy name: Users can view own files
-- Allowed operation: SELECT
CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'course-materials' AND
  auth.uid()::text = (storage.foldername(name))[1]
);
```

#### Policy 3: Users can delete their own files
```sql
-- Policy name: Users can delete own files
-- Allowed operation: DELETE
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'course-materials' AND
  auth.uid()::text = (storage.foldername(name))[1]
);
```

## Step 4: Verify Setup

Run these queries in SQL Editor to verify everything is set up:

```sql
-- Check if tables exist
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('subjects', 'space_pdfs');

-- Check if RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('subjects', 'space_pdfs');

-- Check policies
SELECT schemaname, tablename, policyname, cmd 
FROM pg_policies 
WHERE tablename IN ('subjects', 'space_pdfs');

-- Check indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND tablename IN ('subjects', 'space_pdfs');
```

Expected results:
- ✅ 2 tables found (subjects, space_pdfs)
- ✅ RLS enabled = true for both tables
- ✅ 8 policies (4 per table: SELECT, INSERT, UPDATE, DELETE)
- ✅ 5 indexes

## Step 5: Update Backend Configuration (if needed)

Make sure your Supabase credentials are set in `.env`:

```env
SUPABASE_URL=your_project_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
```

## Step 6: Test the Feature

1. Start the backend server:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. Start the mobile app:
   ```bash
   cd mobile-app
   npx expo start
   ```

3. In the app:
   - Navigate to **"My Space"** from the home screen
   - Try uploading a PDF
   - Create subjects/folders
   - Assign PDFs to subjects

## Troubleshooting

### Issue: "permission denied for table subjects"
**Solution:** RLS policies not created. Re-run the migration SQL.

### Issue: "Failed to upload file"
**Solution:** Check storage bucket policies. Make sure bucket name matches in code.

### Issue: "relation 'subjects' does not exist"
**Solution:** Migration didn't run. Check SQL Editor for errors and re-run.

### Issue: Files uploading but not visible
**Solution:** Check storage policies. Make sure SELECT policy exists for bucket.

## Database Schema Diagram

```
┌─────────────────────┐
│      auth.users     │
│  (Supabase built-in)│
└──────────┬──────────┘
           │
           │ user_id (FK)
           │
    ┌──────┴──────────────────────────┐
    │                                  │
    ▼                                  ▼
┌─────────────────┐          ┌──────────────────┐
│    subjects     │          │   space_pdfs     │
├─────────────────┤          ├──────────────────┤
│ id (PK)         │◄─────────│ id (PK)          │
│ user_id (FK)    │          │ user_id (FK)     │
│ name            │          │ name             │
│ color           │          │ file_path        │
│ icon            │          │ file_size        │
│ created_at      │          │ subject_id (FK)  │
│ updated_at      │          │ uploaded_at      │
└─────────────────┘          │ updated_at       │
                             └──────────────────┘
```

## API Endpoints Available

After setup, these endpoints will work:

- `GET /api/v1/space/subjects` - List user's subjects
- `POST /api/v1/space/subjects` - Create new subject
- `PUT /api/v1/space/subjects/{id}` - Update subject
- `DELETE /api/v1/space/subjects/{id}` - Delete subject
- `GET /api/v1/space/pdfs` - List user's PDFs (optional ?subject_id filter)
- `POST /api/v1/space/pdfs/upload` - Upload new PDF
- `POST /api/v1/space/pdfs/assign` - Assign PDFs to subject
- `DELETE /api/v1/space/pdfs/{id}` - Delete PDF
- `GET /api/v1/space/pdfs/{id}/content` - Get PDF file content

## Next Steps

1. Run the migration SQL in Supabase
2. Set up storage bucket and policies
3. Test uploading a PDF through the app
4. Create subjects and organize PDFs
5. Use PDFs in other features (podcasts, quizzes, hypothesis generation)
