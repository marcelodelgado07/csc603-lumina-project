"""
Lumina AI Schedule Generator - HuggingFace API Test Script
===========================================================
Author: Joe Bowen
Project: Lumina - A Study Buddy that Listens (CSC 603/803 Capstone)

This script calls the HuggingFace Inference API using Meta Llama 3.1 8B Instruct
to generate a structured JSON study schedule from user preferences and class data.

Schemas defined by Marcelo Delgado (see project API/JSON spec).

Usage:
    1. Replace HF_API_TOKEN below with your token (or use env var)
    2. Run: python lumina_ai_test.py

Dependencies:
    pip install requests
"""

import json
import re
import requests
import time
import os

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

# Replace with your token (get one at https://huggingface.co/settings/tokens)
# IMPORTANT: Remove your token before pushing to GitHub!
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# Using Llama 3.1 8B Instruct — available on HuggingFace's free tier
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

# New HuggingFace router API (OpenAI-compatible)
API_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds


# ─────────────────────────────────────────────
# Test Data — Schema 1: User Preferences
# ─────────────────────────────────────────────

TEST_USER = {
    "user_id": 1,
    "earliest_study_time": "08:00:00",
    "latest_study_time": "21:00:00",
    "total_weekly_hours_goal": 5,
    "break_frequency": 50,      # minutes of study before a break
    "break_duration": 10,       # minutes per break
}


# ─────────────────────────────────────────────
# Test Data — Schema 2: Class Data
# ─────────────────────────────────────────────

TEST_CLASSES = [
    {
        "class_id": 101,
        "class_name": "CSC 603 - Generative AI",
        "class_start_time": "14:00:00",
        "class_end_time": "15:15:00",
        "class_days": ["Tuesday", "Thursday"],
        "priority_level": 5,
        "syllabus_url": "https://example.com/syllabi/csc603.pdf",
        "is_completed": False,
    },
    {
        "class_id": 102,
        "class_name": "CSC 510 - Analysis of Algorithms",
        "class_start_time": "10:00:00",
        "class_end_time": "11:15:00",
        "class_days": ["Monday", "Wednesday"],
        "priority_level": 4,
        "syllabus_url": "https://example.com/syllabi/csc510.pdf",
        "is_completed": False,
    },
    {
        "class_id": 103,
        "class_name": "CSC 648 - Software Engineering",
        "class_start_time": "16:00:00",
        "class_end_time": "17:15:00",
        "class_days": ["Monday", "Wednesday"],
        "priority_level": 3,
        "syllabus_url": "https://example.com/syllabi/csc648.pdf",
        "is_completed": False,
    },
]


# ─────────────────────────────────────────────
# Schema 3: Expected Output Format
# ─────────────────────────────────────────────

EXAMPLE_OUTPUT = [
    {
        "id": 1,
        "type": "study",
        "class_name": "CSC 603 - Generative AI",
        "start_time": "2025-07-07T08:00:00",
        "end_time": "2025-07-07T08:50:00",
    },
    {
        "id": 2,
        "type": "break",
        "class_name": "Rest",
        "start_time": "2025-07-07T08:50:00",
        "end_time": "2025-07-07T09:00:00",
    },
]


# ─────────────────────────────────────────────
# Build the Messages (OpenAI chat format)
# ─────────────────────────────────────────────

def build_messages(user: dict, classes: list[dict]) -> list[dict]:
    """
    Constructs the chat messages for the OpenAI-compatible API.
    """

    active_classes = [c for c in classes if not c.get("is_completed", False)]
    active_classes_sorted = sorted(
        active_classes, key=lambda c: c["priority_level"], reverse=True
    )

    # Calculate exact block counts so the LLM doesn't have to do math
    goal_minutes = user["total_weekly_hours_goal"] * 60
    block_len = user["break_frequency"]
    total_study_blocks = goal_minutes // block_len

    # Distribute blocks by priority
    total_priority = sum(c["priority_level"] for c in active_classes_sorted)
    block_distribution = {}
    assigned = 0
    for i, c in enumerate(active_classes_sorted):
        if i == len(active_classes_sorted) - 1:
            blocks = total_study_blocks - assigned
        else:
            blocks = round(total_study_blocks * c["priority_level"] / total_priority)
        block_distribution[c["class_name"]] = blocks
        assigned += blocks

    dist_str = "\n".join(
        f"   - {name}: exactly {count} study blocks"
        for name, count in block_distribution.items()
    )

    system_prompt = f"""You are Lumina, an AI study schedule planner.
Generate a weekly study schedule as a JSON array.

CRITICAL CONSTRAINTS:
1. Generate EXACTLY {total_study_blocks} study blocks total for the entire week (not per day).
2. After each study block, add 1 break block. So {total_study_blocks} study + {total_study_blocks} break = {total_study_blocks * 2} blocks total.
3. Each study block is exactly {block_len} minutes. Each break is exactly {user['break_duration']} minutes.
4. Only schedule between {user['earliest_study_time']} and {user['latest_study_time']}.
5. NEVER overlap with class lecture times.
6. Spread blocks across Mon-Fri (2025-07-07 to 2025-07-11).

BLOCK DISTRIBUTION (by priority):
{dist_str}

OUTPUT: Respond with ONLY a JSON array. No markdown, no explanation, no extra text.
Each element:
{{"id": int, "type": "study"|"break", "class_name": "ClassName"|"Rest", "start_time": "ISO8601", "end_time": "ISO8601"}}"""

    user_prompt = (
        f"CLASSES:\n{json.dumps(active_classes_sorted, indent=2)}\n\n"
        f"EXAMPLE (first 2 blocks):\n{json.dumps(EXAMPLE_OUTPUT, indent=2)}\n\n"
        f"Generate exactly {total_study_blocks * 2} blocks total. JSON array only."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ─────────────────────────────────────────────
# Call the HuggingFace API
# ─────────────────────────────────────────────

def call_huggingface(messages: list[dict]) -> str:
    """
    Sends chat messages to HuggingFace's OpenAI-compatible API.
    """

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "max_tokens": 8000,
        "temperature": 0.2,
        "top_p": 0.9,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔄 Attempt {attempt}/{MAX_RETRIES} — Calling HuggingFace API...")

        try:
            response = requests.post(
                API_URL, headers=HEADERS, json=payload, timeout=120
            )
        except requests.exceptions.Timeout:
            print("⏳ Request timed out. Retrying...")
            time.sleep(RETRY_DELAY)
            continue

        if response.status_code == 200:
            result = response.json()
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                print(f"⚠️  Unexpected response: {json.dumps(result, indent=2)}")
                return str(result)

        elif response.status_code == 503:
            body = response.json()
            wait_time = body.get("estimated_time", RETRY_DELAY)
            print(f"⏳ Model loading. Waiting {wait_time:.0f}s...")
            time.sleep(wait_time)

        elif response.status_code == 429:
            print(f"⚠️  Rate limited. Waiting {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            if attempt == MAX_RETRIES:
                response.raise_for_status()
            time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts.")


# ─────────────────────────────────────────────
# Parse and Validate the JSON Response
# ─────────────────────────────────────────────

def extract_json(raw_text: str) -> list | dict:
    """
    Extracts valid JSON from the model's response.
    If the JSON array was truncated (token limit), recovers
    by closing off the last complete object.
    """

    cleaned = raw_text.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try markdown code blocks
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding a complete JSON array
    bracket_match = re.search(r"\[[\s\S]*\]", cleaned)
    if bracket_match:
        try:
            return json.loads(bracket_match.group(0))
        except json.JSONDecodeError:
            pass

    # ── TRUNCATION RECOVERY ──
    # If we got here, the JSON was likely cut off mid-stream.
    # Find the start of the array and the last complete object.
    array_start = cleaned.find("[")
    if array_start != -1:
        json_text = cleaned[array_start:]

        # Find the last complete "}" in the text
        last_brace = json_text.rfind("}")
        if last_brace != -1:
            # Cut after the last complete object and close the array
            truncated = json_text[: last_brace + 1]

            # Remove any trailing comma before we close the array
            truncated = truncated.rstrip().rstrip(",")
            truncated += "\n]"

            try:
                result = json.loads(truncated)
                print(
                    f"⚠️  Response was truncated — recovered "
                    f"{len(result)} complete blocks."
                )
                return result
            except json.JSONDecodeError:
                pass

    raise ValueError(
        "Could not extract valid JSON from model response.\n"
        f"Raw response (first 500 chars):\n{raw_text[:500]}"
    )


def validate_schedule(
    schedule: list[dict], user: dict, classes: list[dict]
) -> list[str]:
    """
    Validates the generated schedule against user preferences and class data.
    """

    warnings = []

    if not isinstance(schedule, list):
        warnings.append("Response is not a JSON array.")
        return warnings

    if len(schedule) == 0:
        warnings.append("Schedule is empty — no blocks generated.")
        return warnings

    earliest = user["earliest_study_time"]
    latest = user["latest_study_time"]

    lecture_slots = []
    for cls in classes:
        for day in cls.get("class_days", []):
            lecture_slots.append(
                (day, cls["class_start_time"], cls["class_end_time"], cls["class_name"])
            )

    study_minutes = 0
    seen_ids = set()
    valid_types = {"study", "break"}
    day_map = {
        "2025-07-07": "Monday",
        "2025-07-08": "Tuesday",
        "2025-07-09": "Wednesday",
        "2025-07-10": "Thursday",
        "2025-07-11": "Friday",
    }

    for block in schedule:
        for field in ["id", "type", "class_name", "start_time", "end_time"]:
            if field not in block:
                warnings.append(f"Block missing '{field}': {block}")
                continue

        block_id = block.get("id")
        if block_id in seen_ids:
            warnings.append(f"Duplicate block id: {block_id}")
        seen_ids.add(block_id)

        block_type = block.get("type", "")
        if block_type not in valid_types:
            warnings.append(f"Block {block_id}: invalid type '{block_type}'.")

        if block_type == "break":
            cn = block.get("class_name")
            if cn not in (None, "Rest", "rest", "null"):
                warnings.append(
                    f"Block {block_id}: break has class_name='{cn}' "
                    f"instead of 'Rest'."
                )

        start_str = block.get("start_time", "")
        end_str = block.get("end_time", "")

        try:
            start_time = start_str.split("T")[1] if "T" in start_str else start_str
            end_time = end_str.split("T")[1] if "T" in end_str else end_str
            date_part = start_str.split("T")[0] if "T" in start_str else ""

            if block_type == "study":
                if start_time < earliest:
                    warnings.append(
                        f"Block {block_id}: starts at {start_time}, "
                        f"before {earliest}."
                    )
                if end_time > latest:
                    warnings.append(
                        f"Block {block_id}: ends at {end_time}, "
                        f"after {latest}."
                    )

                day_name = day_map.get(date_part, "")
                for lec_day, lec_start, lec_end, lec_name in lecture_slots:
                    if day_name == lec_day:
                        if start_time < lec_end and end_time > lec_start:
                            warnings.append(
                                f"Block {block_id}: overlaps {lec_name} "
                                f"on {day_name}."
                            )

                sh, sm = int(start_time[:2]), int(start_time[3:5])
                eh, em = int(end_time[:2]), int(end_time[3:5])
                study_minutes += (eh * 60 + em) - (sh * 60 + sm)

        except (IndexError, ValueError) as e:
            warnings.append(f"Block {block_id}: time parse error — {e}")

    actual_hours = study_minutes / 60
    goal = user["total_weekly_hours_goal"]
    print(f"   📊 Total study time: {actual_hours:.1f}h (goal: {goal}h)")
    if actual_hours < goal * 0.7:
        warnings.append(
            f"Study time ({actual_hours:.1f}h) significantly below goal ({goal}h)."
        )
    elif actual_hours > goal * 1.3:
        warnings.append(
            f"Study time ({actual_hours:.1f}h) significantly exceeds goal ({goal}h)."
        )

    return warnings


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    if not HF_API_TOKEN:
        print("❌ Error: HF_API_TOKEN not set.")
        return

    print("=" * 60)
    print("  Lumina AI Schedule Generator — HuggingFace Test Script")
    print("=" * 60)
    print(f"\n📡 Model:    {MODEL_ID}")
    print(f"👤 User ID:  {TEST_USER['user_id']}")
    print(f"🕐 Study window: {TEST_USER['earliest_study_time']} – "
          f"{TEST_USER['latest_study_time']}")
    print(f"🎯 Weekly goal:  {TEST_USER['total_weekly_hours_goal']}h")
    print(f"📚 Classes:  {len(TEST_CLASSES)}")

    active = [c for c in TEST_CLASSES if not c["is_completed"]]
    print(f"   Active:   {len(active)}")
    for c in sorted(active, key=lambda x: x["priority_level"], reverse=True):
        print(f"   - [{c['priority_level']}] {c['class_name']}")

    # Calculate expected blocks
    goal_min = TEST_USER["total_weekly_hours_goal"] * 60
    blocks_expected = goal_min // TEST_USER["break_frequency"]
    print(f"\n📐 Expected: {blocks_expected} study blocks + "
          f"{blocks_expected} breaks = {blocks_expected * 2} total")

    messages = build_messages(TEST_USER, TEST_CLASSES)
    print(f"📨 System prompt: {len(messages[0]['content'])} chars")
    print(f"📨 User prompt:   {len(messages[1]['content'])} chars")

    # Call API
    start_time = time.time()
    raw_response = call_huggingface(messages)
    elapsed = time.time() - start_time
    print(f"\n✅ Response received in {elapsed:.1f}s")

    # Parse
    print("\n🔍 Parsing JSON response...")
    try:
        schedule = extract_json(raw_response)
        if isinstance(schedule, list):
            print(f"✅ JSON extracted — {len(schedule)} blocks")
        else:
            print("✅ JSON extracted")
    except ValueError as e:
        print(f"❌ {e}")
        return

    # Validate
    print("\n🧪 Validating schedule...")
    warnings = validate_schedule(schedule, TEST_USER, TEST_CLASSES)
    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("✅ All checks passed!")

    # Output
    print("\n" + "=" * 60)
    print("  Generated Schedule (Schema 3 format)")
    print("=" * 60)
    print(json.dumps(schedule, indent=2))

    # Save
    output_file = "generated_schedule.json"
    with open(output_file, "w") as f:
        json.dump(schedule, f, indent=2)
    print(f"\n💾 Saved to {output_file}")

    # Summary
    print("\n📋 Summary:")
    if isinstance(schedule, list):
        study_blocks = [b for b in schedule if b.get("type") == "study"]
        break_blocks = [b for b in schedule if b.get("type") == "break"]
        print(f"   Study blocks: {len(study_blocks)}")
        print(f"   Break blocks: {len(break_blocks)}")

        class_counts = {}
        for b in study_blocks:
            name = b.get("class_name", "Unknown")
            class_counts[name] = class_counts.get(name, 0) + 1
        if class_counts:
            print("   Per class:")
            for name, count in sorted(class_counts.items(), key=lambda x: -x[1]):
                print(f"     {name}: {count}")


if __name__ == "__main__":
    main()