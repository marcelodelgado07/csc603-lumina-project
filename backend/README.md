# Lumina Backend (FastAPI)

The backend for the Lumina study schedule generator. Exposes a single
route that takes user preferences + class data and returns a generated
weekly schedule from the HuggingFace Inference API.

## Setup

### 1. Install dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate         # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your `.env`

Copy the example file and add your HuggingFace token:

```bash
cp .env.example .env
# then edit .env and replace hf_your_new_token_here with your real token
```

Get a token at <https://huggingface.co/settings/tokens>. **Never commit
the real `.env` file** — it's already in `.gitignore`.

### 3. Run the server

```bash
uvicorn main:app --reload --port 8000
```

The interactive API docs are available at <http://localhost:8000/docs>.

## Endpoints

### `GET /`

Health check. Confirms the server is up and reports whether the HF token
is loaded from the environment.

### `POST /generate-schedule`

Generates a weekly study schedule.

**Request body:**

```json
{
  "user": {
    "user_id": 1,
    "earliest_study_time": "08:00:00",
    "latest_study_time": "21:00:00",
    "total_weekly_hours_goal": 5,
    "break_frequency": 50,
    "break_duration": 10
  },
  "classes": [
    {
      "class_id": 101,
      "class_name": "CSC 603 - Generative AI",
      "class_start_time": "14:00:00",
      "class_end_time": "15:15:00",
      "class_days": ["Tuesday", "Thursday"],
      "priority_level": 5,
      "syllabus_url": "https://example.com/syllabi/csc603.pdf",
      "is_completed": false
    }
  ]
}
```

**Response body:**

```json
{
  "schedule": [
    {
      "id": 1,
      "type": "study",
      "class_name": "CSC 603 - Generative AI",
      "start_time": "2025-07-07T08:00:00",
      "end_time": "2025-07-07T08:50:00"
    }
  ],
  "warnings": []
}
```

`warnings` is a list of validation messages (e.g. blocks that overlap
class lectures, or total study time that's far from the user's goal).
An empty list means the schedule passed all checks.

## Quick test from the command line

```bash
curl -X POST http://localhost:8000/generate-schedule \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

A `sample_request.json` is included in this directory.

## Notes

- The route imports helper functions (`build_messages`, `call_huggingface`,
  `extract_json`, `validate_schedule`) from `Lumina AI Test.py`. The file
  has spaces in the name, so we load it via `importlib`.
- CORS is enabled for `localhost:5173` (Vite) and `localhost:3000` so the
  React frontend can call the API in dev.
- Requests can take 10–30 seconds because the HF model has to generate
  many blocks. Make sure your fetch on the frontend has a generous timeout.
