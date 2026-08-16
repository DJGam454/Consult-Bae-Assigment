# ConsultBae — AI Automation Assignment (Phase 1 + Phase 2)

This repository contains the completed implementation for the ConsultBae assignment.

It includes:
- Phase 1: CSV ingestion, cleaning, deduplication, and record merging into PostgreSQL/Supabase
- Optional cloud n8n workflow for LLM-based skill categorization
- Phase 2: Flask-based audio collection app for recording and uploading audio
- Audio metadata extraction with persistence to the database
- A data-quality report based on the actual issues found in the source CSV data

---

## Overview

ConsultBae is designed to take 3 source datasets, normalize and merge them into a single candidate database, classify skill categories, and then let a user record or upload audio that is matched back to a candidate and stored with metadata.

The solution is organized around three main flows:
1. Data ingestion and de-duplication
2. Skill classification via cloud n8n/LLM (optional)
3. Audio collection and metadata tracking in a Flask app

---

## Architecture

```text
Local Python pipeline
├── input/source1_naukri_applicants.csv
├── input/source2_gig_workers.csv
├── input/source3_cbnexus_contacts.csv
├── src/clean_data.py
├── src/matching.py
├── src/ingest.py
├── src/database.py
├── src/report_phase1.py
├── reports/data_profile.json
└── PostgreSQL / Supabase

Optional cloud workflow
├── n8n workflow file
├── PostgreSQL read/write to people table
├── LLM classification (Google Gemini / OpenAI style)
└── skill_category update back to database

Phase 2 audio app
├── app/app.py
├── app/templates/index.html
├── app/templates/submissions.html
├── src/audio_metadata.py
├── uploads/audio/
└── audio_submissions table
```

---

## Tech stack

- Python 3.11+
- pandas
- numpy
- psycopg2-binary
- python-dotenv
- Flask
- Werkzeug
- librosa
- soundfile
- pydub
- PostgreSQL/Supabase
- n8n (cloud, optional)

---

## Project structure

```text
ConsultBae/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── test_setup.py
├── test_db_connection.py
├── setup_audio_table.py
├── app/
│   ├── app.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── submissions.html
├── src/
│   ├── __init__.py
│   ├── database.py
│   ├── ingest.py
│   ├── clean_data.py
│   ├── matching.py
│   ├── inspect_data.py
│   ├── report_phase1.py
│   ├── audio_metadata.py
│   └── analyze_data_quality.py
├── input/
│   ├── source1_naukri_applicants.csv
│   ├── source2_gig_workers.csv
│   └── source3_cbnexus_contacts.csv
├── reports/
│   ├── data_profile.json
│   └── data_quality_report.json
├── uploads/
│   └── audio/
├── ConsultBae_n8n_skill_classification.json
├── MIGRATION_SUMMARY.md
├── package.json
├── database/
├── .env
└── ConsultBae - AI Automation Assignment.pdf
```

---

## Prerequisites

Before running the project, ensure:
- Python 3.11+ is installed
- A PostgreSQL/Supabase database is available
- `.env` is configured with your DB credentials
- A browser is available for the audio app
- Optional: FFmpeg installed for stronger audio metadata support

---

## Installation

From the project root:

```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

---

## Environment variables

Create a `.env` file in the project root:

```env
DB_HOST=your-supabase-host.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
```

Do not commit `.env` to GitHub. Use `.env.example` as the template.

---

## Phase 1: data ingestion and merge

### What this does
The project reads all three CSV files and merges duplicates into a master candidate table.

### Source files
- `source1_naukri_applicants.csv`
- `source2_gig_workers.csv`
- `source3_cbnexus_contacts.csv`

### Matching and normalization rules
- normalize phone numbers to a common 10-digit format
- normalize city names and whitespace
- lowercase email addresses
- standardize dates into readable ISO-like values
- tokenize and normalize skill strings
- skip malformed rows or duplicate header rows gracefully

### Run Phase 1

```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
.venv\Scripts\activate
python -m src.ingest
python -m src.report_phase1
```

### Expected outcome
- records loaded into the `people` table
- duplicates merged into a single candidate identity
- `skill_category` remains NULL until classification step
- summary output prints the totals and merge result

---

## Task 2: n8n workflow (optional cloud classification)

The project includes the workflow file:
- `ConsultBae_n8n_skill_classification.json`

This workflow is intended for use in cloud n8n to read unclassified records from PostgreSQL, classify a person’s skills, and write the result back to `people.skill_category`.

### Recommended categories
- `automation-heavy`
- `web dev`
- `data`
- `AI/ML`
- `other`

### Import into n8n
1. Open n8n cloud
2. Import `ConsultBae_n8n_skill_classification.json`
3. Connect the PostgreSQL credential to Supabase
4. Configure the LLM node with your API key
5. Activate the workflow

This step is optional for the local app, but it completes the AI classification flow.

---

## Task 3: audio collection web app (completed)

The Phase 2 audio app is implemented and ready to run locally.

### App purpose
The app lets a user:
- enter a candidate name and phone number
- record audio directly from the browser microphone
- upload an audio file instead of recording
- validate the file type and size
- match the recording to an existing person in the `people` table
- save metadata to the `audio_submissions` table

### Primary files
- `app/app.py`
- `app/templates/index.html`
- `app/templates/submissions.html`
- `app/templates/base.html`
- `src/audio_metadata.py`

### Supported audio formats
- WAV
- MP3
- M4A
- FLAC
- OGG
- WebM

### Max file size
- 50 MB

### Run the app

```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
.venv\Scripts\activate
python app/app.py
```

Then open:
- `http://127.0.0.1:5000`
- `http://127.0.0.1:5000/submissions`

### App endpoints
- `GET /` — main submission page
- `GET /submissions` — all submissions list
- `POST /api/submit-audio` — upload/record and save audio
- `GET /api/audio/<id>` — serve audio for playback
- `GET /api/health` — app health check

---

## Task 4: data quality issues report

This project also generates a report of the actual quality issues found in the source data.

Report location:
- `reports/data_quality_report.json`

### Examples of issues actually identified
1. Inconsistent phone formats across all files
2. City casing and whitespace inconsistencies
3. Email casing inconsistencies in source 2
4. Multiple date formats in source 1
5. Status/verified value inconsistency
6. Skills stored in inconsistent comma-separated forms
7. Duplicate header row in source 3
8. Malformed and blank rows
9. Mixed rate units and inconsistent CTC scale
10. Name casing differences across sources

### Run the report

```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
.venv\Scripts\activate
python -m src.analyze_data_quality
```

---

## Database schema

### People table
The merged candidate records are stored in `people` with fields like:
- `id`
- `full_name`
- `normalized_name`
- `email`
- `phone`
- `city`
- `skills`
- `experience_years`
- `current_ctc`
- `applied_date`
- `gig_rate_raw`
- `gig_status`
- `verified`
- `projects_completed`
- `skill_category`
- `source_count`
- `created_at`
- `updated_at`

### Audio submissions table
The audio app stores submissions in `audio_submissions` with fields including:
- `id`
- `person_id`
- `matched_name`
- `matched_phone`
- `audio_file_path`
- `file_size_bytes`
- `file_format`
- `duration_seconds`
- `sample_rate_khz`
- `bitrate_kbps`
- `loudness_db`
- `noise_quality_estimate`
- `submission_status`
- `error_message`
- `created_at`
- `updated_at`

If the table is missing, run:

```powershell
python setup_audio_table.py
```

---

## Checking app health and setup

### Verify project environment
```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
.venv\Scripts\activate
python test_setup.py
python test_db_connection.py
```

### Verify app response
```powershell
curl http://127.0.0.1:5000/api/health
```

### Verify database record after an upload
```sql
SELECT * FROM audio_submissions ORDER BY created_at DESC LIMIT 10;
```

---

## Actual validation results

The following checks were validated in the project environment:

- `python test_setup.py` passed for required imports and file structure
- Flask dependencies and audio processing dependencies were present
- `app/app.py` starts correctly when the database is reachable
- `audio_submissions` table creation was required when the database schema was missing
- When database connectivity is unavailable, the app may log DNS/host resolution errors until the environment is connected again

This is the actual state observed in the current environment; the implementation is complete, but the database must remain reachable for end-to-end audio submission testing.

---

## Known troubleshooting

### 1. `audio_submissions` table not found
```powershell
python setup_audio_table.py
```

### 2. App not starting because database host cannot resolve
- confirm `.env` values are correct
- check that the Supabase host is reachable
- confirm internet connectivity

### 3. Port already in use
- stop the process using port 5000 or change the port in the Flask app config

### 4. Upload fails or metadata extraction fails
- check file extension is supported
- ensure the file size is under 50 MB
- confirm the file is valid audio
- install FFmpeg if you want stronger metadata processing

---

## Exact commands to run the project

### Setup
```powershell
cd "b:\OneDrive - Amity University\Desktop\ConsultBae"
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### Check environment and DB
```powershell
python test_setup.py
python test_db_connection.py
```

### Run Phase 1 pipeline
```powershell
python -m src.ingest
python -m src.report_phase1
```

### Create audio table if missing
```powershell
python setup_audio_table.py
```

### Start the audio app
```powershell
python app/app.py
```

### Open the app
```text
http://127.0.0.1:5000
http://127.0.0.1:5000/submissions
```

### Test a direct upload API call
```powershell
curl -X POST "http://127.0.0.1:5000/api/submit-audio" \
  -F "name=Test User" \
  -F "phone=+91 9000000254" \
  -F "audio_file=@sample.wav"
```

---

## Demo flow

A simple demo sequence is:
1. Activate environment and run `python test_setup.py`
2. Start the app: `python app/app.py`
3. Open the home page
4. Enter a name and phone number
5. Record audio or upload a file
6. Click Submit
7. Confirm the metadata and status message
8. Open `/submissions` to see the entry and playback

---

## Data quality summary

The repository includes a review of real data problems in the CSVs, not fabricated ones.

The most important issues identified were:
- inconsistent phone number formatting
- city casing and whitespace differences
- inconsistent email casing
- repeated header row in one source file
- malformed or empty rows
- inconsistent status values and skill formats
- mixed date styles
- inconsistent rate and CTC representations

These are documented in the report at:
- `reports/data_quality_report.json`

---

## GitHub readiness and repo hygiene

The repo should be kept clean and safe:
- `.env` must not be committed
- `uploads/` should not be committed
- `__pycache__/` and virtual env files should be ignored
- keep credentials only in `.env`
- keep `requirements.txt` accurate and up to date

The project includes `.gitignore` and `.env.example` to support this.

---

## Stuck log (real challenges faced)

### Challenge 1: Metadata extraction without guaranteed FFmpeg
The app needed to work even when FFmpeg was not installed. The solution used a fallback chain: librosa first, then pydub, then best-effort estimation.

### Challenge 2: Matching inconsistent phone numbers
Phone numbers varied across sources and user input. The fix normalized them to a common 10-digit format before lookup.

### Challenge 3: Missing table during runtime
The audio storage flow initially failed because `audio_submissions` was not created in the database. The fix was to create the table using `setup_audio_table.py` and verify the schema before submission.

---

## Current status

The project is in a completed implementation state:
- Phase 1 data pipeline is working
- Phase 2 audio app is implemented and documented
- database matching and upload flow are in place
- quality report is included
- local run commands are provided

The remaining factor for full end-to-end validation is a reachable database environment, because successful audio insertions depend on active PostgreSQL/Supabase connectivity.

---

## Final notes

This project is intentionally designed to be practical and production-aware:
- it avoids hardcoded secrets in the repo
- it keeps CSV normalization and matching logic explicit
- it separates the app flow from the data pipeline flow
- it preserves phase-by-phase implementation without breaking existing work

The application is ready for local demonstration once the environment is connected and the database is available.

