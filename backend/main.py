"""
Lumina FastAPI Server
=====================
Author: Muzaffarbek Muratov (Backend)
Project: Lumina - A Study Buddy that Listens (CSC 603 Capstone)

Exposes one route: POST /generate-schedule
- Accepts Schema 1 (User Preferences) and a list of Schema 2 (Class Data)
- Calls the AI script's helper functions to build the prompt, hit the
  HuggingFace router API, parse JSON, and validate the result
- Returns Schema 3 (a list of study/break blocks)

Run locally:
    cd backend
    pip install -r requirements.txt
    # Make sure .env contains HF_API_TOKEN (see .env.example)
    uvicorn main:app --reload --port 8000

Docs available at: http://localhost:8000/docs
"""

import importlib.util
import os
from datetime import date
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env BEFORE we import the AI script — the script reads
# os.getenv("HF_API_TOKEN") at module load time.
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Import the AI script (filename has a space, so use importlib)
# ─────────────────────────────────────────────

_THIS_DIR = Path(__file__).parent
_AI_SCRIPT_PATH = _THIS_DIR / "Lumina AI Test.py"

if not _AI_SCRIPT_PATH.exists():
    raise FileNotFoundError(
        f"Could not find AI script at {_AI_SCRIPT_PATH}. "
        "Make sure 'Lumina AI Test.py' is in the same directory as main.py."
    )

_spec = importlib.util.spec_from_file_location("lumina_ai", _AI_SCRIPT_PATH)
lumina_ai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lumina_ai)
# Post-LLM safety net (Fix 1)
from schedule_backfill import backfill_missing_classes


# ─────────────────────────────────────────────
# Pydantic Models (mirror the schemas in our project doc)
# ─────────────────────────────────────────────


class UserPreferences(BaseModel):
    """
    Schema 1: User Preferences

    Only `total_weekly_hours_goal` is required from the client.
    Everything else has a sensible default so the frontend can send a
    minimal payload and the server fills in the rest.
    """

    total_weekly_hours_goal: int
    user_id: int = 1
    earliest_study_time: str = Field(
        "08:00:00", description="ISO 8601 time string, e.g. '08:00:00'"
    )
    latest_study_time: str = Field(
        "22:00:00", description="ISO 8601 time string, e.g. '22:00:00'"
    )
    break_frequency: int = Field(
        50, description="Minutes of study before a break is needed"
    )
    break_duration: int = Field(10, description="Length of each break in minutes")


class ClassData(BaseModel):
    """
    Schema 2: Class Data

    Only `class_name` is required. `class_id` is auto-assigned in the
    route if the client omits it (see generate_schedule below).
    """

    class_name: str
    class_id: Optional[int] = None
    class_start_time: str = Field(
        "", description="ISO 8601 time, e.g. '14:00:00'"
    )
    class_end_time: str = Field(
        "", description="ISO 8601 time, e.g. '15:15:00'"
    )
    class_days: List[str] = Field(
        default_factory=list, description="e.g. ['Monday', 'Wednesday']"
    )
    priority_level: int = Field(3, ge=1, le=5)
    syllabus_url: Optional[str] = ""
    is_completed: bool = False


class ScheduleBlock(BaseModel):
    """Schema 3: Output block"""

    id: int
    type: str = Field(..., description="'study' or 'break'")
    class_name: Optional[str] = None
    start_time: str
    end_time: str


class GenerateScheduleRequest(BaseModel):
    user: UserPreferences
    classes: List[ClassData]


class GenerateScheduleResponse(BaseModel):
    schedule: List[ScheduleBlock]
    warnings: List[str] = []


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="Lumina API",
    description="Backend for the Lumina study schedule generator (CSC 603).",
    version="0.1.0",
)

# CORS — let the Vite dev server (and a typical CRA fallback) hit the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    """Simple health check."""
    return {
        "status": "ok",
        "service": "Lumina API",
        "hf_token_configured": bool(os.getenv("HF_API_TOKEN")),
    }


@app.post("/generate-schedule", response_model=GenerateScheduleResponse)
def generate_schedule(req: GenerateScheduleRequest) -> GenerateScheduleResponse:
    """
    Generate a weekly study schedule.

    Pipeline:
      1. Build the chat messages from user prefs + class data
      2. Call HuggingFace's chat completions endpoint (Llama 3.1 8B)
      3. Parse the JSON response (with truncation recovery)
      4. Validate the schedule against the user's constraints
    """

    if not os.getenv("HF_API_TOKEN"):
        raise HTTPException(
            status_code=500,
            detail=(
                "HF_API_TOKEN is not set. Add it to backend/.env "
                "(see .env.example)."
            ),
        )

    # The AI script's helpers expect plain dicts, not Pydantic objects.
    user_dict = req.user.model_dump()
    classes_dict = [c.model_dump() for c in req.classes]

    # Auto-assign sequential class_ids when the client omits them.
    # Lets the frontend send {"class_name": "..."} only.
    next_id = 1
    for c in classes_dict:
        if c.get("class_id") is None:
            c["class_id"] = next_id
            next_id += 1

    # Anchor the schedule on the upcoming Monday so dates aren't stuck
    # in the AI script's original 2025-07-07 hardcoded week.
    week_start = lumina_ai.next_monday_on_or_after(date.today())

    try:
        messages = lumina_ai.build_messages(
            user_dict, classes_dict, week_start=week_start
        )
        raw = lumina_ai.call_huggingface(messages)
        schedule = lumina_ai.extract_json(raw)
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"AI generation failed: {e}"
        )

    if not isinstance(schedule, list):
        raise HTTPException(
            status_code=502,
            detail=(
                "Model did not return a JSON array. "
                f"Got type: {type(schedule).__name__}"
            ),
        )

    # Post-LLM safety net: backfill any classes the model dropped (Fix 1).\
    # This guarantees every active class gets at least one study block,
    # which is the bug Joe surfaced during testing with 6 classes.
    schedule, backfill_msgs = backfill_missing_classes(
        schedule, user_dict, classes_dict, week_start
    )
    warnings = lumina_ai.validate_schedule(
        schedule, user_dict, classes_dict, week_start=week_start
    )

    warnings.extend(backfill_msgs)

    return GenerateScheduleResponse(schedule=schedule, warnings=warnings)


    return GenerateScheduleResponse(schedule=schedule, warnings=warnings)
