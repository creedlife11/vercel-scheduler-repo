from datetime import date, datetime, timedelta
from typing import List, Dict
import pandas as pd

def nearest_previous_sunday(d: date) -> date:
    return d - timedelta(days=(d.weekday()+1) % 7)

def build_rotation(engineers: List[str], seed: int=0) -> List[str]:
    seed = seed % len(engineers)
    return engineers[seed:] + engineers[:seed]

def is_weekday(d: date) -> bool:
    return d.weekday() < 5  # Mon=0..Sun=6

def week_index(start_sunday: date, d: date) -> int:
    return (d - start_sunday).days // 7

def weekend_worker_for_week(engineers_rotated: List[str], week_idx: int) -> str:
    n = len(engineers_rotated)
    return engineers_rotated[week_idx % n]

def works_today(engineer: str, d: date, start_sunday: date, weekend_seeded: List[str]) -> bool:
    w = week_index(start_sunday, d)
    dow = d.weekday()  # Mon=0..Sun=6
    wk_current = weekend_worker_for_week(weekend_seeded, w)
    wk_prev = weekend_worker_for_week(weekend_seeded, w-1) if w-1 >= 0 else weekend_worker_for_week(weekend_seeded, -1)

    default_work = dow <= 4  # Mon-Fri

    if engineer == wk_current:
        # Week A: Mon,Tue,Wed,Thu,Sat
        return dow in (0,1,2,3,5)
    if engineer == wk_prev:
        # Week B: Sun,Tue,Wed,Thu,Fri
        return dow in (1,2,3,4,6)

    return default_work

def generate_day_assignments(d: date, engineers: List[str], start_sunday: date, weekend_seeded: List[str],
                             leave_map: Dict[str,set], seeds: Dict[str,int],
                             assign_early_on_weekends: bool=False):
    working = [e for e in engineers if works_today(e, d, start_sunday, weekend_seeded)]
    leave_today = set([e for e, days in leave_map.items() if d in days])
    working = [e for e in working if e not in leave_today]

    roles = {"Chat":"", "OnCall":"", "Appointments":"", "Early1":"", "Early2":""}

    if is_weekday(d) or assign_early_on_weekends:
        if working:
            day_idx = (d - start_sunday).days
            order = sorted(working, key=lambda name: ((engineers.index(name) + seeds.get("early",0) + day_idx) % len(engineers)))
            roles["Early1"] = order[0] if len(order) >= 1 else ""
            roles["Early2"] = order[1] if len(order) >= 2 else ""

    if is_weekday(d):
        day_idx = (d - start_sunday).days
        available = working.copy()
        if available:
            chat_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("chat",0) + day_idx) % len(engineers)))
            roles["Chat"] = chat_order[0]
            available.remove(roles["Chat"])
        if available:
            oncall_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("oncall",0) + day_idx) % len(engineers)))
            roles["OnCall"] = oncall_order[0]
            available.remove(roles["OnCall"])
        if available:
            appt_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("appointments",0) + day_idx) % len(engineers)))
            roles["Appointments"] = appt_order[0]
    return working, leave_today, roles

def make_schedule(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], leave: pd.DataFrame,
                  assign_early_on_weekends: bool=False) -> pd.DataFrame:
    assert len(engineers) == 6, "Exactly 6 engineers are required."
    weekend_seeded = build_rotation(engineers, seeds.get("weekend",0))

    leave_map = {}
    if leave is not None and not leave.empty:
        leave = leave.copy()
        leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
        for e in leave["Engineer"].unique():
            leave_map[e] = set(leave.loc[leave["Engineer"]==e, "Date"].tolist())
    for e in engineers:
        leave_map.setdefault(e, set())

    days = weeks * 7
    dates = [start_sunday + pd.Timedelta(days=i) for i in range(days)]
    dates = [d.date() for d in dates]

    columns = ["Date","Day","WeekIndex","Early1","Early2","Chat","OnCall","Appointments"]
    for i in range(6):
        columns += [f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"]

    rows = []
    for d in dates:
        w = week_index(start_sunday, d)
        dow = pd.Timestamp(d).strftime("%a")
        working, leave_today, roles = generate_day_assignments(d, engineers, start_sunday, weekend_seeded, leave_map, seeds, assign_early_on_weekends)
        eng_cells = []
        for e in engineers:
            status = "LEAVE" if e in leave_today else ("WORK" if works_today(e, d, start_sunday, weekend_seeded) else "OFF")
            shift = ""
            if status == "WORK":
                if e in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    shift = "08:00-17:00" if pd.Timestamp(d).weekday() < 5 else "Weekend"
            eng_cells += [e, status, shift]
        row = [d, dow, w, roles["Early1"], roles["Early2"], roles["Chat"], roles["OnCall"], roles["Appointments"]] + eng_cells
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns)
    return df
