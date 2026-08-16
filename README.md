# ConsultBae — Phase 1 (Task 1 + Task 2 Option B)

This repo completes **Phase 1** of the assignment:
- **Task 1:** CSV ingestion + cleaning + entity resolution into **Supabase PostgreSQL**
- **Task 2 (Option B):** **Cloud n8n** workflow for LLM-based skill categorization and DB update

---

## 1) Project structure

- `input/` → original CSVs (unchanged)
- `src/inspect_data.py` → schema/data-quality profiling
- `src/clean_data.py` → normalization helpers
- `src/matching.py` → conservative entity-resolution logic
- `src/database.py` → PostgreSQL connection and schema management
- `src/ingest.py` → end-to-end ingestion pipeline
- `src/report_phase1.py` → quick verification report
- `reports/data_profile.json` → inspection report
- `.env` → Supabase connection credentials (not committed)
- `.gitignore` → ignores `.env`, caches, venv, reports

---

## 2) CSV schema discovered

## `source1_naukri_applicants.csv`
- Rows: 42
- Columns:
  - `Full Name`
  - `Email`
  - `Phone`
  - `City`
  - `Experience (Years)`
  - `Current CTC`
  - `Applied Date`
  - `Skills`

## `source2_gig_workers.csv`
- Rows: 32
- Columns:
  - `email_id`
  - `worker_name`
  - `rate`
  - `location`
  - `status`
  - `skill_tags`

## `source3_cbnexus_contacts.csv`
- Rows: 31
- Columns:
  - `Name`
  - `Phone Number`
  - `City`
  - `Verified`
  - `Projects Completed`

---

## 3) Data quality problems found

From actual profiling + ingestion logs:

1. **Inconsistent city formats**
   - Examples: `GURGAON`, `gurugram `, `Delhi NCR`, `new delhi`, `bangalore`
   - Handling: normalized to canonical values (e.g. `gurugram`, `delhi`, `bengaluru`)

2. **Inconsistent email casing**
   - Examples: uppercase emails in source2
   - Handling: lowercased during normalization

3. **Inconsistent phone formats**
   - Examples: `+91...`, `091...`, `919...`, hyphenated numbers
   - Handling: stripped to 10-digit normalized phone

4. **Repeated header row inside CSV data**
   - In `source3_cbnexus_contacts.csv`
   - Handling: detected and skipped as invalid row

5. **Malformed/shifted row in source2**
   - One blank row and one shifted row pattern observed by profile
   - Handling: malformed rows skipped with warning logs

6. **Possible duplicate identities across sources**
   - Same person across CSVs with casing/format differences
   - Handling: merged via deterministic matching rules

7. **Skill field inconsistencies**
   - Mixed casing/token formats
   - Handling: tokenized, lowercased, deduplicated, merged

8. **Mixed date formats**
   - Examples: `24-07-2026`, `2026-08-08`, `7 Jul 2026`, `07/13/2026`
   - Handling: parsed into ISO `YYYY-MM-DD` where possible

9. **Mixed status/verified values**
   - `ACTIVE`, `active`, `Y`, `yes`, `No`, etc.
   - Handling: normalized status + boolean verified mapping

---

## 4) Canonical database schema (PostgreSQL via Supabase)

Primary merged table: `people`

Important fields:
- Identity: `full_name`, `normalized_name`, `email`, `phone`, `city`
- Skills: `skills`
- Source attributes: `experience_years`, `current_ctc`, `applied_date`, `gig_rate_raw`, `gig_status`, `verified`, `projects_completed`
- Assignment field: `skill_category` (NULL initially)
- Traceability: `source_count`

Audit tables:
- `person_sources` → every source row mapped to `new/matched/ambiguous`
- `ambiguous_matches` → uncertain matches preserved for review
- `classification_failures` → invalid LLM category outputs logged by cloud n8n

Constraints:
- Unique index on normalized `email` (when not NULL)
- Unique index on normalized `phone` (when not NULL)
- `skill_category` CHECK in (`automation-heavy`, `web dev`, `data`) or NULL

Connection (Supabase):
- Host: `db.iwvcyhwgpxsoteovkcrc.supabase.co`
- Port: `5432`
- Database: `postgres`
- Credentials: configured in `.env` (no local PostgreSQL needed)

---

## 5) Matching logic (Task 1)

Matching priority (conservative):
1. **Exact normalized email**
2. **Exact normalized phone**
3. If only partial contact data available: limited name-based matching with strict guards
   - Exact name + compatible city
   - Very high fuzzy name similarity (>=96) + same city
4. If conflicting evidence or multiple candidates:
   - mark **ambiguous** and preserve in `ambiguous_matches` (no unsafe merge)

This avoids aggressive fuzzy merges.

---

## 6) Ingestion result (actual run)

From `python -m src.ingest`:
- Rows read total: 105
- Usable rows before dedup: 103
- Final unique people: **56**
- Duplicates merged: **47**
- Ambiguous matches: **0**
- Skipped invalid/malformed: **2**

---

## 7) Task 2 Option B — n8n Cloud Workflow

**Status**: Ready for cloud n8n configuration

Workflow structure (to build in n8n cloud):
1. `Manual Trigger` or `Schedule Trigger`
2. `Get Unclassified People` (PostgreSQL query: `skill_category IS NULL`)
3. `LLM Classifier` (HTTP request to OpenAI API)
4. `Validate Category` (Code node, strict whitelist)
5. `If Valid Category`
   - True → `Update Supabase Category` (PostgreSQL UPDATE)
   - False → `Log Invalid Category` (PostgreSQL INSERT)

Allowed categories are strictly:
- `automation-heavy`
- `web dev`
- `data`

LLM prompt enforces: return **only one token** from allowed labels.

Validation step rejects anything else and logs failure in `classification_failures` instead of corrupting `people.skill_category`.

---

## 8) Exact commands to run

> Run from workspace root: `b:\OneDrive - Amity University\Desktop\ConsultBae`

### Prerequisites

1. **Supabase Project** should be active and accessible
2. Verify `.env` has correct Supabase credentials:
   ```
   DB_HOST=db.iwvcyhwgpxsoteovkcrc.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=Sanyam@1198
   ```
3. Test connection: `python test_db_connection.py`

### Python setup + Task 1

```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Profile source data
python -m src.inspect_data

# Ingest and merge CSV files into PostgreSQL
python -m src.ingest

# View report
python -m src.report_phase1
```

### Cloud n8n setup (Task 2)

1. Go to [n8n cloud](https://app.n8n.cloud)
2. Create a new workflow
3. Add a PostgreSQL connector with **Supabase** credentials:
   - Host: `db.iwvcyhwgpxsoteovkcrc.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: `Sanyam@1198`
   - ✅ Enable **SSL** (required for Supabase)
4. Build workflow:
   - Trigger: Manual or schedule
   - Query: `SELECT * FROM people WHERE skill_category IS NULL`
   - LLM node: Call OpenAI with person's skills → category
   - Update: Write `skill_category` back to Supabase PostgreSQL
5. Set environment variable: `OPENAI_API_KEY`

---

## 9) Supabase PostgreSQL connection setup (n8n Cloud)

In cloud n8n, when creating PostgreSQL nodes with Supabase:

1. Click **Credentials** button
2. Select or create new PostgreSQL credential:
   - Host: `db.iwvcyhwgpxsoteovkcrc.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: `Sanyam@1198`
   - ✅ **SSL Mode**: `require` (Supabase requires SSL)
3. Test connection
4. Save credentials
5. Use in workflow nodes for reading/writing people and classification data

---

## 10) Verification queries (Supabase PostgreSQL)

### Before n8n (after ingestion)

```sql
SELECT COUNT(*) FROM people WHERE skill_category IS NULL;
-- expected: total people from ingest
```

### After running n8n workflow

```sql
SELECT skill_category, COUNT(*)
FROM people
GROUP BY skill_category;

SELECT COUNT(*) AS failures
FROM classification_failures;
```

Expected after successful run:
- `people.skill_category` populated with values from {`automation-heavy`, `web dev`, `data`}
- categories distributed across all people
- invalid model outputs (if any) captured in `classification_failures`

### Access Supabase PostgreSQL database

```powershell
# Using psql (if installed)
psql -h db.iwvcyhwgpxsoteovkcrc.supabase.co -U postgres -d postgres

# Or use pgAdmin/DBeaver with:
# Host: db.iwvcyhwgpxsoteovkcrc.supabase.co
# Port: 5432
# Database: postgres
# User: postgres
# Password: Sanyam@1198
```

---

## 11) Phase 1 test/report fields

`python -m src.report_phase1` prints:
- total people
- unclassified people
- ambiguous matches
- classification failures
- processed/success/failure counts
- category distribution
- sample merged records

---

## 12) Current status

- ✅ Task 1: CSV ingestion + cleaning + entity resolution ready
- ✅ Database: Migrated to **Supabase PostgreSQL** (no local DB needed)
- ✅ Code updated: all Python modules use Supabase connection
- ✅ Cloud n8n ready: Configure PostgreSQL connector with Supabase credentials
- ✅ Local n8n removed: using cloud n8n only
- ✅ `.env` configured: Supabase connection parameters

**Next steps:**
1. ✅ Verify `.env` has correct Supabase credentials
2. Test connection: `python test_db_connection.py`
3. Run ingestion: `python -m src.ingest`
4. Build cloud n8n workflow with Supabase PostgreSQL connector
5. Deploy LLM skill classification
6. Verify with: `python -m src.report_phase1`
