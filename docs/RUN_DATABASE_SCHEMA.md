# Running the Database Schema in Supabase

## Method 1: Using Supabase SQL Editor (Easiest)

### Steps:

1. **Open SQL Editor:**
   - In your Supabase dashboard
   - Click **"SQL Editor"** in the left sidebar (looks like </> icon)

2. **Create New Query:**
   - Click **"New query"** button (top right)

3. **Copy the Schema:**
   - Open the file: `server/database/supabase_schema.sql`
   - Select all (Ctrl+A / Cmd+A)
   - Copy (Ctrl+C / Cmd+C)

4. **Paste and Run:**
   - Paste into the SQL Editor
   - Click **"Run"** button (or press Ctrl+Enter / Cmd+Enter)

5. **Verify Success:**
   - You should see: "Success. No rows returned"
   - This is normal - we're creating tables, not selecting data

6. **Check Tables Were Created:**
   - Click **"Table Editor"** in left sidebar
   - You should see 7 tables:
     - ✅ users
     - ✅ user_sessions
     - ✅ conversations
     - ✅ messages
     - ✅ events
     - ✅ agent_actions
     - ✅ desktop_screenshots

---

## Method 2: Using psql (Advanced)

If you prefer command line:

```bash
# Get your connection string from Supabase Settings → Database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres" -f server/database/supabase_schema.sql
```

---

## Troubleshooting:

### Error: "relation already exists"
- **Solution:** Tables already exist, you're good to go!
- Or drop tables first: `DROP TABLE IF EXISTS [table_name] CASCADE;`

### Error: "permission denied"
- **Solution:** Make sure you're using the correct connection string
- Try running queries individually if the full script fails

### Error: "syntax error"
- **Solution:** Make sure you copied the ENTIRE file
- Check that no characters were corrupted during copy/paste

---

## What Gets Created:

### Tables (7):
1. **users** - User accounts
2. **user_sessions** - JWT sessions
3. **conversations** - Telegram groups + desktop sessions
4. **messages** - Rolling 1-hour message window
5. **events** - Created calendar events
6. **agent_actions** - Audit log
7. **desktop_screenshots** - Screenshot metadata

### Functions (1):
- **cleanup_old_messages()** - Removes messages older than 1 hour

### Indexes (12):
- Optimized for fast queries on common operations

---

## Verification Query:

After running the schema, verify with this query:

```sql
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Expected output:
```
table_name            | column_count
---------------------+-------------
agent_actions        | 10
conversations        | 7
desktop_screenshots  | 8
events              | 13
messages            | 11
user_sessions       | 8
users               | 12
```

✅ **Ready!** Once you see these tables, your database is set up correctly.
