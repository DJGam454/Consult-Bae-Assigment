# ConsultBae Quick Start Commands

## Setup (One-time)

```bash
# 1. Navigate to project
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
copy .env.example .env
# Edit .env with your Supabase credentials in Notepad

# 6. Verify setup
python test_setup.py
```

## Running the Full Pipeline

### Step 1: Test Database
```bash
python test_db_connection.py
```

### Step 2: Ingest CSV Files
```bash
python -m src.ingest
```

### Step 3: Analyze Data Quality
```bash
python -m src.analyze_data_quality
```
(Output: `reports/data_quality_report.json`)

### Step 4: Verify Ingestion
```bash
python -m src.report_phase1
```

### Step 5: Create Audio Table (One-time)
```bash
python setup_audio_table.py
```

### Step 6: Start Flask Audio App
```bash
python app/app.py
```
Opens: `http://localhost:5000`

### Step 7: Submit Audio
- Enter name and phone
- Record from microphone OR upload file
- Click Submit

### Step 8: View Submissions
Visit: `http://localhost:5000/submissions`

---

## Common Tasks

### Just Test Everything Works
```bash
.venv\Scripts\activate
python test_setup.py
python test_db_connection.py
```

### Just Start Audio App
```bash
.venv\Scripts\activate
python app/app.py
```

### Just Run CSV Pipeline
```bash
.venv\Scripts\activate
python -m src.ingest
python -m src.report_phase1
```

### Just Generate Data Quality Report
```bash
.venv\Scripts\activate
python -m src.analyze_data_quality
```

---

## Optional: Cloud n8n Skill Classification

**MANUAL CLOUD STEP**

1. Open your n8n cloud instance
2. Click "+ New workflow"
3. Click "Import from file"
4. Select: `n8n/ConsultBae_n8n_skill_classification.json`
5. Configure Supabase credential (if not already done)
6. Configure Google Gemini credential (if not already done)
7. Click "Test workflow" or activate for scheduled runs
8. Monitor execution in dashboard

---

## Troubleshooting

### Port 5000 Already in Use
```bash
python app/app.py --port 5001
```

### Virtual Environment Not Working
```bash
# Recreate it
rmdir /s .venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Database Connection Fails
- Check `.env` has correct credentials
- Verify Supabase host and port
- Ensure database password is correct
- Check internet connectivity

### Missing Module
```bash
pip install librosa soundfile pydub psycopg2-binary flask
```

### FFmpeg Not Found
- Optional (app works without it)
- See README.md for installation instructions
- Windows: `choco install ffmpeg` or download from ffmpeg.org

---

## File Locations

- **Code:** `src/` and `app/`
- **Data:** `input/` (CSVs), `reports/` (outputs)
- **Config:** `.env` (credentials, not committed)
- **Docs:** `README.md`, `COMPLETION_SUMMARY.md`
- **Audio Files:** `uploads/audio/` (created at runtime)

---

## What Each File Does

| File | Purpose |
|------|---------|
| `app/app.py` | Flask web server |
| `src/ingest.py` | CSV ingestion pipeline |
| `src/database.py` | Database operations |
| `src/audio_metadata.py` | Audio analysis |
| `src/analyze_data_quality.py` | Data quality report |
| `test_setup.py` | Verify all prerequisites |
| `test_db_connection.py` | Test database connection |
| `setup_audio_table.py` | Create audio submissions table |

---

## Expected Output Examples

### After CSV Ingestion
```
Processing source1_naukri_applicants.csv...
Processing source2_gig_workers.csv...
Processing source3_cbnexus_contacts.csv...
✓ Merged X duplicate records
✓ Inserted Y unique records into database
```

### After Flask Startup
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### After Audio Submission
```
✓ Audio received
✓ Metadata extracted:
  - Duration: 15.3 seconds
  - Sample rate: 44100 kHz
  - Bitrate: 320 kbps
  - Loudness: -5.2 dB
  - Quality: high
✓ Matched to: [Person Name]
✓ Stored in database
```

---

## Environment Variables Needed

Create `.env` with:
```env
DB_HOST=your-supabase-host.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
```

See `.env.example` for template.

---

**For detailed documentation, see README.md**
