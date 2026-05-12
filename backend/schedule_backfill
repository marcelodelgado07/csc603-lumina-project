from datetime import datetime, timedelta, date
from typing import List, Dict


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _find_open_slot(
    target_day: date,
    duration_min: int,
    earliest: str,
    latest: str,
    occupied: List[tuple],
    lecture_times: List[tuple],
) -> tuple | None:
    """
    Find an open time slot on target_day of duration_min minutes.
    Returns (start_dt, end_dt) or None if no slot fits.
    occupied: list of (start_dt, end_dt) already-scheduled blocks
    lecture_times: list of (day_name, "HH:MM:SS", "HH:MM:SS") lecture slots
    """
    day_name = target_day.strftime("%A")
    earliest_h, earliest_m = int(earliest[:2]), int(earliest[3:5])
    latest_h, latest_m = int(latest[:2]), int(latest[3:5])

    # Try slots in 30-min increments starting at the earliest study time
    current = datetime.combine(target_day, datetime.min.time()).replace(
        hour=earliest_h, minute=earliest_m
    )
    day_end = datetime.combine(target_day, datetime.min.time()).replace(
        hour=latest_h, minute=latest_m
    )

    while current + timedelta(minutes=duration_min) <= day_end:
        slot_end = current + timedelta(minutes=duration_min)

        # Check against lectures on this day
        lecture_conflict = False
        for lec_day, lec_start, lec_end in lecture_times:
            if lec_day != day_name:
                continue
            ls = datetime.combine(target_day, datetime.min.time()).replace(
                hour=int(lec_start[:2]), minute=int(lec_start[3:5])
            )
            le = datetime.combine(target_day, datetime.min.time()).replace(
                hour=int(lec_end[:2]), minute=int(lec_end[3:5])
            )
            if not (slot_end <= ls or current >= le):
                lecture_conflict = True
                break

        if lecture_conflict:
            current += timedelta(minutes=30)
            continue

        # Check against existing blocks
        block_conflict = any(
            not (slot_end <= b_start or current >= b_end)
            for b_start, b_end in occupied
        )

        if not block_conflict:
            return (current, slot_end)

        current += timedelta(minutes=30)

    return None


def backfill_missing_classes(
    schedule: List[Dict],
    user: Dict,
    classes: List[Dict],
    week_start: date,
) -> tuple[List[Dict], List[str]]:
    """
    Ensures every active class has at least one study block.
    Returns (updated_schedule, list_of_messages).

    Called from main.py's generate_schedule() AFTER extract_json() and
    BEFORE validate_schedule().
    """
    messages = []
    active_classes = [c for c in classes if not c.get("is_completed", False)]

    # Count study blocks per class
    study_counts: Dict[str, int] = {}
    for b in schedule:
        if b.get("type") == "study":
            cn = b.get("class_name", "")
            study_counts[cn] = study_counts.get(cn, 0) + 1

    # Build occupied list for collision checks
    occupied = []
    for b in schedule:
        try:
            occupied.append((_parse_dt(b["start_time"]), _parse_dt(b["end_time"])))
        except (KeyError, ValueError):
            continue

    # Lecture times for collision checks
    lecture_times = []
    for c in active_classes:
        for d in c.get("class_days", []):
            lecture_times.append(
                (d, c.get("class_start_time", "00:00:00"),
                 c.get("class_end_time", "00:00:00"))
            )

    # Days available (Mon-Fri)
    week_days = [week_start + timedelta(days=i) for i in range(5)]
    block_len = user.get("break_frequency", 50)
    break_len = user.get("break_duration", 10)
    earliest = user.get("earliest_study_time", "08:00:00")
    latest = user.get("latest_study_time", "21:00:00")

    next_id = max((b.get("id", 0) for b in schedule), default=0) + 1

    for cls in active_classes:
        cn = cls["class_name"]
        if study_counts.get(cn, 0) > 0:
            continue

        # This class was dropped — backfill at least one study block.
        # Try each day in order; prefer days with fewest existing blocks.
        day_loads = []
        for d in week_days:
            d_str = d.isoformat()
            load = sum(1 for b in schedule if b["start_time"].startswith(d_str))
            day_loads.append((load, d))
        day_loads.sort(key=lambda x: x[0])

        slot = None
        chosen_day = None
        for _, d in day_loads:
            slot = _find_open_slot(
                d, block_len, earliest, latest, occupied, lecture_times
            )
            if slot:
                chosen_day = d
                break

        if not slot:
            messages.append(
                f"Could not backfill '{cn}' — no open slot in the week."
            )
            continue

        study_start, study_end = slot
        schedule.append({
            "id": next_id,
            "type": "study",
            "class_name": cn,
            "start_time": _format_dt(study_start),
            "end_time": _format_dt(study_end),
        })
        next_id += 1
        occupied.append((study_start, study_end))

        # Add a break right after
        break_start = study_end
        break_end = break_start + timedelta(minutes=break_len)
        schedule.append({
            "id": next_id,
            "type": "break",
            "class_name": "Rest",
            "start_time": _format_dt(break_start),
            "end_time": _format_dt(break_end),
        })
        next_id += 1
        occupied.append((break_start, break_end))

        messages.append(
            f"Backfilled '{cn}' with a study block on "
            f"{chosen_day.strftime('%A')} at {study_start.strftime('%H:%M')}."
        )

    # Sort by start_time and renumber IDs sequentially
    schedule.sort(key=lambda b: b["start_time"])
    for i, b in enumerate(schedule, start=1):
        b["id"] = i

    return schedule, messages
