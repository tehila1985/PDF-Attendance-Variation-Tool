from __future__ import annotations

import copy
import random
from dataclasses import replace as dc_replace
from datetime import datetime, timedelta

from core.entities import AttendanceRow, hhmm_to_minutes, minutes_to_hhmm, parse_time
from interfaces.strategy import BaseTransformationStrategy


def _build_shifted_row(row: AttendanceRow, rng: random.Random, max_shift: int) -> AttendanceRow:
    """Shared deterministic time-shift logic used by both concrete strategies.

    Shifts start and end independently by ±max_shift minutes. The end-after-start
    invariant is always enforced: if the shift produces end ≤ start, the end is
    snapped to start + original_duration (minimum 1 minute).
    """
    start_t = parse_time(row.start_time)
    end_t = parse_time(row.end_time)
    if not start_t or not end_t:
        return dc_replace(row)

    today = datetime.today()
    start_dt = datetime.combine(today, start_t)
    end_dt = datetime.combine(today, end_t)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    original_duration = end_dt - start_dt
    start_shift = rng.randint(-max_shift, max_shift)
    end_shift = rng.randint(-max_shift, max_shift)

    new_start = start_dt + timedelta(minutes=start_shift)
    new_end = end_dt + timedelta(minutes=end_shift)
    if new_end <= new_start:
        new_end = new_start + max(original_duration, timedelta(minutes=1))

    return dc_replace(
        row,
        start_time=new_start.strftime("%H:%M"),
        end_time=new_end.strftime("%H:%M"),
    )


class TypeATransformationStrategy(BaseTransformationStrategy):
    """Type A strategy: shift start/end, recompute total_hours."""

    MAX_SHIFT_MINUTES: int = 10

    def transform(self, row: AttendanceRow, rng: random.Random) -> AttendanceRow:
        new_row = _build_shifted_row(row, rng, self.MAX_SHIFT_MINUTES)
        new_row.recompute_total_hours()
        return new_row


class TypeBTransformationStrategy(BaseTransformationStrategy):
    """Type B strategy: shift start/end, recompute total_hours, respect break_minutes."""

    MAX_SHIFT_MINUTES: int = 10

    def transform(self, row: AttendanceRow, rng: random.Random) -> AttendanceRow:
        new_row = _build_shifted_row(row, rng, self.MAX_SHIFT_MINUTES)
        # recompute_total_hours already subtracts break_minutes when set.
        new_row.recompute_total_hours()
        # Preserve percentage_bracket: apply a slight variation on overtime hours.
        if new_row.overtime_125_hours:
            new_row.overtime_125_hours = _vary_overtime(new_row.overtime_125_hours, rng)
        if new_row.overtime_150_hours:
            new_row.overtime_150_hours = _vary_overtime(new_row.overtime_150_hours, rng)
        return new_row


def _vary_overtime(hhmm: str, rng: random.Random) -> str:
    """Slightly vary an overtime hours field by ±5 minutes."""
    minutes = hhmm_to_minutes(hhmm)
    if minutes is None:
        return hhmm
    delta = rng.randint(-5, 5)
    return minutes_to_hhmm(max(0, minutes + delta))
