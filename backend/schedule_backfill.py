from datetime import datetime, timedelta, date
from typing import List, Dict
 
 
# ─────────────────────────────────────────────
# Helpers (same as the original)
# ─────────────────────────────────────────────
 
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
    """Find an open slot of duration_min minutes on target_day.
    Returns (start_dt, end_dt) or None."""
    day_name = target_day.strftime("%A")
    earliest_h, earliest_m = int(earliest[:2]), int(earliest[3:5])
    latest_h, latest_m = int(latest[:2]), int(latest[3:5])
 
    current = datetime.combine(target_day, datetime.min.time()).replace(
        hour=earliest_h, minute=earliest_m
    )
    day_end = datetime.combine(target_day, datetime.min.time()).replace(
        hour=latest_h, minute=latest_m
    )
 
    while current + timedelta(minutes=duration_min) <= day_end:
        slot_end = current + timedelta(minutes=duration_min)
 
        # Lecture conflict?
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
 
        # Block conflict?
        block_conflict = any(
            not (slot_end <= b_start or current >= b_end)
            for b_start, b_end in occupied
        )
        if not block_conflict:
            return (current, slot_end)
 
        current += timedelta(minutes=30)
 
    return None
 
 
def _occupied_from_schedule(schedule: List[Dict]) -> List[tuple]:
    """Rebuild the occupied list from current schedule state."""
    occupied = []
    for b in schedule:
        try:
            occupied.append((_parse_dt(b["start_time"]), _parse_dt(b["end_time"])))
        except (KeyError, ValueError):
            continue
    return occupied
 
 
def _lecture_times_from_classes(classes: List[Dict]) -> List[tuple]:
    """Build the lecture conflict list from active classes."""
    lecture_times = []
    for c in classes:
        for d in c.get("class_days", []):
            lecture_times.append(
                (d, c.get("class_start_time", "00:00:00"),
                 c.get("class_end_time", "00:00:00"))
            )
    return lecture_times
 
 
# ─────────────────────────────────────────────
# Step 1: Backfill missing classes (same as before)
# ─────────────────────────────────────────────
 
def _do_backfill(
    schedule: List[Dict],
    user: Dict,
    classes: List[Dict],
    week_start: date,
    messages: List[str],
) -> None:
    """In-place: ensure every active class has at least one study block."""
    active_classes = [c for c in classes if not c.get("is_completed", False)]
 
    study_counts: Dict[str, int] = {}
    for b in schedule:
        if b.get("type") == "study":
            cn = b.get("class_name", "")
            study_counts[cn] = study_counts.get(cn, 0) + 1
 
    occupied = _occupied_from_schedule(schedule)
    lecture_times = _lecture_times_from_classes(active_classes)
 
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
 
        # Pick the day with the fewest study blocks so far
        day_loads = []
        for d in week_days:
            d_str = d.isoformat()
            load = sum(
                1 for b in schedule
                if b.get("type") == "study" and b["start_time"].startswith(d_str)
            )
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
            messages.append(f"Could not backfill '{cn}' — no open slot in the week.")
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
            f"Backfilled '{cn}' on {chosen_day.strftime('%A')} "
            f"at {study_start.strftime('%H:%M')}."
        )
 
 
# ─────────────────────────────────────────────
# Step 2: Redistribute over-clustered days (the new logic)
# ─────────────────────────────────────────────
 
def _redistribute(
    schedule: List[Dict],
    user: Dict,
    classes: List[Dict],
    week_start: date,
    messages: List[str],
    max_iterations: int = 25,
) -> None:
    """In-place: lift study blocks (+ trailing breaks) off overloaded days
    onto under-used days. Stops when no day is overloaded or no moves help.
    """
    active_classes = [c for c in classes if not c.get("is_completed", False)]
    lecture_times = _lecture_times_from_classes(active_classes)
    week_days = [week_start + timedelta(days=i) for i in range(5)]
    block_len = user.get("break_frequency", 50)
    earliest = user.get("earliest_study_time", "08:00:00")
    latest = user.get("latest_study_time", "21:00:00")
 
    iterations = 0
    moves_made = 0
 
    while iterations < max_iterations:
        iterations += 1
 
        # Count STUDY blocks per day (we redistribute studies, not breaks)
        study_per_day: Dict[str, int] = {}
        for d in week_days:
            study_per_day[d.isoformat()] = 0
        for b in schedule:
            if b.get("type") == "study":
                d = b["start_time"][:10]
                if d in study_per_day:
                    study_per_day[d] += 1
 
        total_studies = sum(study_per_day.values())
        if total_studies == 0:
            return  # nothing to redistribute
 
        avg = total_studies / 5.0
        # A day is "overloaded" if it has > avg * 1.5 blocks
        # AND it has at least 2 more than the most empty day.
        threshold = max(avg * 1.5, 2.0)
        max_load = max(study_per_day.values())
        min_load = min(study_per_day.values())
 
        if max_load <= threshold or (max_load - min_load) < 2:
            # Balanced enough, or moving wouldn't help (need a 2+ gap)
            break
 
        # Find the most overloaded day and the most underused day
        overloaded_day_str = max(study_per_day, key=study_per_day.get)
        underused_day_str = min(study_per_day, key=study_per_day.get)
        overloaded_day = date.fromisoformat(overloaded_day_str)
        underused_day = date.fromisoformat(underused_day_str)
 
        # Find the LAST study block on the overloaded day
        overloaded_studies = sorted(
            [b for b in schedule
             if b.get("type") == "study"
             and b["start_time"].startswith(overloaded_day_str)],
            key=lambda b: b["start_time"],
        )
        if not overloaded_studies:
            break
 
        # Build "occupied excluding this block + its trailing break" so we
        # don't see our own positions as taken when looking for the new slot
        to_move = overloaded_studies[-1]
        to_move_start = _parse_dt(to_move["start_time"])
        to_move_end = _parse_dt(to_move["end_time"])
 
        # Find a trailing break (a "break" block on the same day starting
        # exactly when this study block ends)
        trailing_break = None
        for b in schedule:
            if (b.get("type") == "break"
                    and b["start_time"].startswith(overloaded_day_str)
                    and _parse_dt(b["start_time"]) == to_move_end):
                trailing_break = b
                break
 
        # Build occupied list excluding the block(s) we're about to move
        occupied = []
        for b in schedule:
            if b is to_move or b is trailing_break:
                continue
            try:
                occupied.append((_parse_dt(b["start_time"]), _parse_dt(b["end_time"])))
            except (KeyError, ValueError):
                continue
 
        # Try to find a slot on the underused day for the study block
        # (use the same duration as the original block, not the user's
        # configured block_len, in case they differ)
        duration = int((to_move_end - to_move_start).total_seconds() / 60)
        slot = _find_open_slot(
            underused_day, duration, earliest, latest, occupied, lecture_times
        )
 
        if not slot:
            # Try other underused days in order of load
            ranked_days = sorted(week_days, key=lambda d: study_per_day[d.isoformat()])
            slot = None
            for d in ranked_days:
                if d.isoformat() == overloaded_day_str:
                    continue
                if study_per_day[d.isoformat()] >= max_load - 1:
                    continue  # not actually underused enough
                slot = _find_open_slot(
                    d, duration, earliest, latest, occupied, lecture_times
                )
                if slot:
                    underused_day = d
                    break
 
        if not slot:
            # No move possible — give up to avoid infinite loop
            break
 
        # Move the study block
        new_study_start, new_study_end = slot
        old_start_str = to_move["start_time"]
        to_move["start_time"] = _format_dt(new_study_start)
        to_move["end_time"] = _format_dt(new_study_end)
 
        # Move the trailing break, if any (preserve its original duration)
        if trailing_break:
            br_start = _parse_dt(trailing_break["start_time"])
            br_end = _parse_dt(trailing_break["end_time"])
            br_duration = int((br_end - br_start).total_seconds() / 60)
            new_br_start = new_study_end
            new_br_end = new_br_start + timedelta(minutes=br_duration)
 
            # Make sure the new break also fits (no lecture conflict, no
            # other-block conflict)
            day_name = underused_day.strftime("%A")
            br_lecture_conflict = False
            for lec_day, lec_start, lec_end in lecture_times:
                if lec_day != day_name:
                    continue
                ls = datetime.combine(underused_day, datetime.min.time()).replace(
                    hour=int(lec_start[:2]), minute=int(lec_start[3:5])
                )
                le = datetime.combine(underused_day, datetime.min.time()).replace(
                    hour=int(lec_end[:2]), minute=int(lec_end[3:5])
                )
                if not (new_br_end <= ls or new_br_start >= le):
                    br_lecture_conflict = True
                    break
 
            br_block_conflict = any(
                not (new_br_end <= b_start or new_br_start >= b_end)
                for b_start, b_end in occupied
            )
 
            if br_lecture_conflict or br_block_conflict:
                # Drop the trailing break rather than leave it in a bad spot.
                # The redistributed study block lives on without it.
                schedule.remove(trailing_break)
            else:
                trailing_break["start_time"] = _format_dt(new_br_start)
                trailing_break["end_time"] = _format_dt(new_br_end)
 
        moves_made += 1
        messages.append(
            f"Moved a {to_move.get('class_name', 'study')} block off "
            f"{date.fromisoformat(old_start_str[:10]).strftime('%A')} "
            f"to {underused_day.strftime('%A')} {new_study_start.strftime('%H:%M')}."
        )
 
    if moves_made > 0:
        messages.append(f"Redistribution complete ({moves_made} moves).")
 
 
# ─────────────────────────────────────────────
# Public entry point — drop-in replacement
# ─────────────────────────────────────────────
 
def backfill_missing_classes(
    schedule: List[Dict],
    user: Dict,
    classes: List[Dict],
    week_start: date,
) -> tuple[List[Dict], List[str]]:
    """
    Same signature as the original. Runs:
      1. Backfill any class the LLM dropped.
      2. Redistribute over-clustered days.
      3. Sort and renumber IDs.
 
    Returns (updated_schedule, list_of_human_readable_messages).
    """
    messages: List[str] = []
 
    _do_backfill(schedule, user, classes, week_start, messages)
    _redistribute(schedule, user, classes, week_start, messages)
 
    # Sort by start_time and renumber IDs
    schedule.sort(key=lambda b: b["start_time"])
    for i, b in enumerate(schedule, start=1):
        b["id"] = i
 
    return schedule, messages
