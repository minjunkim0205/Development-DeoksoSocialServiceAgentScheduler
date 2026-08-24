from __future__ import annotations

import calendar
from collections import Counter
from datetime import date

from ortools.sat.python import cp_model

from core.holidays import get_month_off_dates, weekday_label
from core.storage import DEFAULT_SETTINGS, load_schedule, previous_month_key


SHIFT_DAY = "D"
SHIFT_NIGHT = "N"
SHIFT_REST = "R"
SHIFT_OFF = "O"
SHIFT_INACTIVE = "X"

SHIFT_TYPES = [SHIFT_DAY, SHIFT_NIGHT, SHIFT_REST, SHIFT_OFF]

SHIFT_LABELS = {
    SHIFT_DAY: "주간",
    SHIFT_NIGHT: "야간",
    SHIFT_REST: "비번",
    SHIFT_OFF: "휴무",
    SHIFT_INACTIVE: "###",
}

WORK_TYPE_LABELS = {
    "general": "일반",
    "day_only": "주간 전담",
    "night_only": "야간 전담",
}


def normalize_settings(settings: dict | None) -> dict:
    return {**DEFAULT_SETTINGS, **(settings or {})}


def is_heavy_day(work_date: date, off_days: set[int] | None = None) -> bool:
    return work_date.weekday() in [4, 5, 6] or (off_days is not None and work_date.day in off_days)


def _id_sort_key(agent: dict) -> tuple[int, str]:
    agent_id = str(agent.get("id", ""))
    return (int(agent_id) if agent_id.isdigit() else 999999999, agent_id)


def _active_agents(agents: list[dict]) -> list[dict]:
    active_agents = sorted(
        [agent for agent in agents if agent.get("active") is True],
        key=_id_sort_key,
    )
    normalized = []
    for index, agent in enumerate(active_agents, start=1):
        copied = {**agent}
        copied["id"] = str(copied.get("id") or index)
        copied["name"] = str(copied.get("name") or copied["id"])
        copied["seniority_rank"] = index
        copied["work_type"] = copied.get("work_type") or "general"
        copied["pre_service"] = bool(copied.get("pre_service", False))
        copied["training_completed"] = bool(copied.get("training_completed", True))
        normalized.append(copied)
    return normalized


def _validate_inputs(active_agents: list[dict], settings: dict) -> None:
    if len(active_agents) < 4:
        raise ValueError("근무표를 만들려면 복무 중인 요원이 최소 4명 필요합니다.")

    for key in [
        "weekday_day_target",
        "weekend_day_target",
        "weekday_night_target",
        "weekend_night_target",
    ]:
        if int(settings[key]) < 0:
            raise ValueError("필요 인원은 0명 이상이어야 합니다.")

    day_capable = sum(1 for agent in active_agents if agent.get("work_type") != "night_only")
    night_capable = sum(1 for agent in active_agents if agent.get("work_type") != "day_only")

    max_day_target = max(2, int(settings["weekday_day_target"]), int(settings["weekend_day_target"]))
    if day_capable < max_day_target:
        raise ValueError("주간 근무 가능 인원이 설정된 주간 필요 인원보다 적습니다.")
    if night_capable < 2:
        raise ValueError("야간 근무 가능 인원이 최소 2명 필요합니다.")


def _target_for_day(work_date: date, settings: dict, off_days: set[int]) -> tuple[int, int]:
    if is_heavy_day(work_date, off_days):
        return int(settings["weekend_day_target"]), int(settings["weekend_night_target"])
    return int(settings["weekday_day_target"]), int(settings["weekday_night_target"])


def _previous_month_carryover(year: int, month: int) -> tuple[set[str], set[str]]:
    previous_schedule = load_schedule(previous_month_key(year, month))
    if not previous_schedule:
        return set(), set()

    assignments = previous_schedule.get("assignments", [])
    if not assignments:
        return set(), set()

    last_day = max(int(item["day"]) for item in assignments)
    rest_day1_ids = {
        str(item["agent_id"])
        for item in assignments
        if int(item["day"]) == last_day and item.get("shift") == SHIFT_NIGHT
    }
    off_day1_ids = {
        str(item["agent_id"])
        for item in assignments
        if int(item["day"]) == last_day - 1 and item.get("shift") == SHIFT_NIGHT
    }
    return rest_day1_ids, off_day1_ids


def generate_schedule(year: int, month: int, agents: list[dict], settings: dict | None = None) -> dict:
    settings = normalize_settings(settings)
    active_agents = _active_agents(agents)
    _validate_inputs(active_agents, settings)

    last_day = calendar.monthrange(year, month)[1]
    days = list(range(1, last_day + 1))
    off_dates = get_month_off_dates(year, month)
    off_days = {work_date.day for work_date in off_dates}
    off_target = len(off_days)
    num_agents = len(active_agents)
    previous_month_rest_day1_ids, previous_month_off_day1_ids = _previous_month_carryover(year, month)

    model = cp_model.CpModel()
    penalties = []
    x = {}

    for agent_index in range(num_agents):
        for day in days:
            for shift in SHIFT_TYPES:
                x[(agent_index, day, shift)] = model.NewBoolVar(f"x_a{agent_index}_d{day}_{shift}")

    for agent_index in range(num_agents):
        for day in days:
            model.Add(sum(x[(agent_index, day, shift)] for shift in SHIFT_TYPES) == 1)

    for agent_index, agent in enumerate(active_agents):
        work_type = agent.get("work_type", "general")
        for day in days:
            if work_type == "day_only":
                model.Add(x[(agent_index, day, SHIFT_NIGHT)] == 0)
                model.Add(x[(agent_index, day, SHIFT_REST)] == 0)
            elif work_type == "night_only":
                model.Add(x[(agent_index, day, SHIFT_DAY)] == 0)

    for agent_index, agent in enumerate(active_agents):
        if agent.get("work_type") != "day_only":
            continue

        for week_start in range(1, last_day + 1):
            work_date = date(year, month, week_start)
            if work_date.weekday() != 4:
                continue
            weekend_days = [day for day in [week_start, week_start + 1, week_start + 2] if day <= last_day]
            if len(weekend_days) == 3:
                model.Add(sum(x[(agent_index, day, SHIFT_OFF)] for day in weekend_days) >= 2)

        for day in days:
            work_date = date(year, month, day)
            if day in off_days or work_date.weekday() in [4, 5, 6]:
                penalties.append(x[(agent_index, day, SHIFT_DAY)] * 8)
            else:
                penalties.append(x[(agent_index, day, SHIFT_OFF)] * 8)

        for day in range(2, last_day):
            isolated_off = model.NewBoolVar(f"day_only_isolated_off_a{agent_index}_d{day}")
            model.AddBoolAnd(
                [
                    x[(agent_index, day - 1, SHIFT_OFF)].Not(),
                    x[(agent_index, day, SHIFT_OFF)],
                    x[(agent_index, day + 1, SHIFT_OFF)].Not(),
                ]
            ).OnlyEnforceIf(isolated_off)
            model.AddBoolOr(
                [
                    x[(agent_index, day - 1, SHIFT_OFF)],
                    x[(agent_index, day, SHIFT_OFF)].Not(),
                    x[(agent_index, day + 1, SHIFT_OFF)],
                ]
            ).OnlyEnforceIf(isolated_off.Not())
            penalties.append(isolated_off * 220)

        if last_day >= 2:
            first_day_isolated_off = model.NewBoolVar(f"day_only_first_day_isolated_off_a{agent_index}")
            model.AddBoolAnd(
                [
                    x[(agent_index, 1, SHIFT_OFF)],
                    x[(agent_index, 2, SHIFT_OFF)].Not(),
                ]
            ).OnlyEnforceIf(first_day_isolated_off)
            model.AddBoolOr(
                [
                    x[(agent_index, 1, SHIFT_OFF)].Not(),
                    x[(agent_index, 2, SHIFT_OFF)],
                ]
            ).OnlyEnforceIf(first_day_isolated_off.Not())
            penalties.append(first_day_isolated_off * 100)

            last_day_isolated_off = model.NewBoolVar(f"day_only_last_day_isolated_off_a{agent_index}")
            model.AddBoolAnd(
                [
                    x[(agent_index, last_day - 1, SHIFT_OFF)].Not(),
                    x[(agent_index, last_day, SHIFT_OFF)],
                ]
            ).OnlyEnforceIf(last_day_isolated_off)
            model.AddBoolOr(
                [
                    x[(agent_index, last_day - 1, SHIFT_OFF)],
                    x[(agent_index, last_day, SHIFT_OFF)].Not(),
                ]
            ).OnlyEnforceIf(last_day_isolated_off.Not())
            penalties.append(last_day_isolated_off * 100)

    for agent_index, agent in enumerate(active_agents):
        agent_id = str(agent["id"])
        if agent_id in previous_month_rest_day1_ids:
            model.Add(x[(agent_index, 1, SHIFT_REST)] == 1)
            if last_day >= 2:
                model.Add(x[(agent_index, 2, SHIFT_OFF)] == 1)
        else:
            model.Add(x[(agent_index, 1, SHIFT_REST)] == 0)
        if agent_id in previous_month_off_day1_ids:
            model.Add(x[(agent_index, 1, SHIFT_OFF)] == 1)

    single_night_days = []
    extra_day_staffing_days = []
    overstaffed_day_days = []
    daily_off_counts = []
    for day in days:
        work_date = date(year, month, day)
        day_target, night_target = _target_for_day(work_date, settings, off_days)
        day_count = sum(x[(agent_index, day, SHIFT_DAY)] for agent_index in range(num_agents))
        night_count = sum(x[(agent_index, day, SHIFT_NIGHT)] for agent_index in range(num_agents))
        off_count = sum(x[(agent_index, day, SHIFT_OFF)] for agent_index in range(num_agents))
        daily_off_counts.append(off_count)

        model.Add(night_count >= 1)
        model.Add(night_count <= 2)
        model.Add(day_count <= num_agents)

        if is_heavy_day(work_date, off_days):
            model.Add(day_count >= 1)
        else:
            model.Add(day_count >= 1)

        day_diff = model.NewIntVar(0, num_agents, f"day_target_diff_d{day}")
        night_diff = model.NewIntVar(0, num_agents, f"night_target_diff_d{day}")
        model.AddAbsEquality(day_diff, day_count - day_target)
        model.AddAbsEquality(night_diff, night_count - night_target)
        penalties.append(day_diff * 320)
        penalties.append(night_diff * 750)

        low_day_staffing = model.NewBoolVar(f"low_day_staffing_d{day}")
        model.Add(day_count <= 1).OnlyEnforceIf(low_day_staffing)
        model.Add(day_count >= 2).OnlyEnforceIf(low_day_staffing.Not())
        penalties.append(low_day_staffing * 800)

        day_over_three = model.NewIntVar(0, num_agents, f"day_over_three_d{day}")
        model.AddMaxEquality(day_over_three, [day_count - 3, 0])
        penalties.append(day_over_three * 50000)

        overstaffed_day = model.NewBoolVar(f"overstaffed_day_d{day}")
        model.Add(day_count >= 4).OnlyEnforceIf(overstaffed_day)
        model.Add(day_count <= 3).OnlyEnforceIf(overstaffed_day.Not())
        penalties.append(overstaffed_day * 50000)
        overstaffed_day_days.append(overstaffed_day)

        severely_overstaffed_day = model.NewBoolVar(f"severely_overstaffed_day_d{day}")
        model.Add(day_count >= 5).OnlyEnforceIf(severely_overstaffed_day)
        model.Add(day_count <= 4).OnlyEnforceIf(severely_overstaffed_day.Not())
        penalties.append(severely_overstaffed_day * 500000)

        extra_day_staffing_day = model.NewBoolVar(f"extra_day_staffing_day_d{day}")
        model.Add(day_count > day_target).OnlyEnforceIf(extra_day_staffing_day)
        model.Add(day_count <= day_target).OnlyEnforceIf(extra_day_staffing_day.Not())
        penalties.append(extra_day_staffing_day * (40 if is_heavy_day(work_date, off_days) else 400))
        extra_day_staffing_days.append(extra_day_staffing_day)

        single_night_day = model.NewBoolVar(f"single_night_day_d{day}")
        model.Add(night_count == 1).OnlyEnforceIf(single_night_day)
        model.Add(night_count != 1).OnlyEnforceIf(single_night_day.Not())
        penalties.append(single_night_day * 1200)
        single_night_days.append(single_night_day)

    single_night_over_limit = model.NewIntVar(0, last_day, "single_night_over_limit")
    model.AddMaxEquality(single_night_over_limit, [sum(single_night_days) - 2, 0])
    penalties.append(single_night_over_limit * 1800)

    overstaffed_day_over_limit = model.NewIntVar(0, last_day, "overstaffed_day_over_limit")
    model.AddMaxEquality(overstaffed_day_over_limit, [sum(overstaffed_day_days) - 4, 0])
    penalties.append(overstaffed_day_over_limit * 220)

    extra_day_staffing_over_limit = model.NewIntVar(0, last_day, "extra_day_staffing_over_limit")
    model.AddMaxEquality(extra_day_staffing_over_limit, [sum(extra_day_staffing_days) - 3, 0])
    penalties.append(extra_day_staffing_over_limit * 4000)

    for agent_index in range(num_agents):
        for day in range(1, last_day):
            model.Add(x[(agent_index, day + 1, SHIFT_REST)] == x[(agent_index, day, SHIFT_NIGHT)])
        for day in range(1, last_day - 1):
            model.AddImplication(
                x[(agent_index, day, SHIFT_NIGHT)],
                x[(agent_index, day + 2, SHIFT_OFF)],
            )

    if settings.get("prefer_day_before_night", True):
        for agent_index, agent in enumerate(active_agents):
            if agent.get("work_type") == "day_only":
                continue

            for day in range(2, last_day + 1):
                night_without_day_before = model.NewBoolVar(
                    f"night_without_day_before_a{agent_index}_d{day}"
                )
                model.AddBoolAnd(
                    [
                        x[(agent_index, day, SHIFT_NIGHT)],
                        x[(agent_index, day - 1, SHIFT_DAY)].Not(),
                    ]
                ).OnlyEnforceIf(night_without_day_before)
                model.AddBoolOr(
                    [
                        x[(agent_index, day, SHIFT_NIGHT)].Not(),
                        x[(agent_index, day - 1, SHIFT_DAY)],
                    ]
                ).OnlyEnforceIf(night_without_day_before.Not())
                penalties.append(night_without_day_before * 75)

    for agent_index, agent in enumerate(active_agents):
        for day in range(2, last_day):
            isolated_off = model.NewBoolVar(f"isolated_off_a{agent_index}_d{day}")
            model.AddBoolAnd(
                [
                    x[(agent_index, day - 1, SHIFT_OFF)].Not(),
                    x[(agent_index, day, SHIFT_OFF)],
                    x[(agent_index, day + 1, SHIFT_OFF)].Not(),
                ]
            ).OnlyEnforceIf(isolated_off)
            model.AddBoolOr(
                [
                    x[(agent_index, day - 1, SHIFT_OFF)],
                    x[(agent_index, day, SHIFT_OFF)].Not(),
                    x[(agent_index, day + 1, SHIFT_OFF)],
                ]
            ).OnlyEnforceIf(isolated_off.Not())
            penalties.append(isolated_off * (90 if agent.get("work_type") == "day_only" else 35))

    limited_agent_indexes = [
        index
        for index, agent in enumerate(active_agents)
        if agent.get("pre_service") is True or agent.get("training_completed") is False
    ]
    if settings["avoid_limited_agent_pair"] and limited_agent_indexes:
        for day in days:
            model.Add(sum(x[(index, day, SHIFT_NIGHT)] for index in limited_agent_indexes) <= 1)
            model.Add(sum(x[(index, day, SHIFT_DAY)] for index in limited_agent_indexes) <= 1)

    for day in days:
        for left in range(num_agents):
            for right in range(left + 1, num_agents):
                same_night = model.NewBoolVar(f"same_night_a{left}_a{right}_d{day}")
                model.AddBoolAnd([x[(left, day, SHIFT_NIGHT)], x[(right, day, SHIFT_NIGHT)]]).OnlyEnforceIf(same_night)
                model.AddBoolOr([x[(left, day, SHIFT_NIGHT)].Not(), x[(right, day, SHIFT_NIGHT)].Not()]).OnlyEnforceIf(same_night.Not())

                rank_gap = abs(int(active_agents[left]["seniority_rank"]) - int(active_agents[right]["seniority_rank"]))
                if rank_gap <= 2:
                    penalties.append(same_night * (12 - rank_gap * 3))

    work_counts = []
    night_counts = []
    off_counts = []
    for agent_index in range(num_agents):
        day_count = model.NewIntVar(0, last_day, f"day_count_a{agent_index}")
        night_count = model.NewIntVar(0, last_day, f"night_count_a{agent_index}")
        work_count = model.NewIntVar(0, last_day, f"work_count_a{agent_index}")
        off_count = model.NewIntVar(0, last_day, f"off_count_a{agent_index}")
        rest_count = model.NewIntVar(0, last_day, f"rest_count_a{agent_index}")

        model.Add(day_count == sum(x[(agent_index, day, SHIFT_DAY)] for day in days))
        model.Add(night_count == sum(x[(agent_index, day, SHIFT_NIGHT)] for day in days))
        model.Add(work_count == day_count + night_count)
        model.Add(rest_count == sum(x[(agent_index, day, SHIFT_REST)] for day in days))
        model.Add(off_count == sum(x[(agent_index, day, SHIFT_OFF)] for day in days))
        model.Add(off_count == off_target)

        work_counts.append(work_count)
        night_counts.append(night_count)
        off_counts.append(off_count)

    max_work = model.NewIntVar(0, last_day, "max_work")
    min_work = model.NewIntVar(0, last_day, "min_work")
    max_night = model.NewIntVar(0, last_day, "max_night")
    min_night = model.NewIntVar(0, last_day, "min_night")
    max_off = model.NewIntVar(0, last_day, "max_off")
    min_off = model.NewIntVar(0, last_day, "min_off")

    model.AddMaxEquality(max_work, work_counts)
    model.AddMinEquality(min_work, work_counts)
    model.AddMaxEquality(max_night, night_counts)
    model.AddMinEquality(min_night, night_counts)
    model.AddMaxEquality(max_off, off_counts)
    model.AddMinEquality(min_off, off_counts)
    model.Add(max_off == min_off)

    max_daily_off = model.NewIntVar(0, num_agents, "max_daily_off")
    min_daily_off = model.NewIntVar(0, num_agents, "min_daily_off")
    model.AddMaxEquality(max_daily_off, daily_off_counts)
    model.AddMinEquality(min_daily_off, daily_off_counts)

    penalties.append((max_work - min_work) * 20)
    penalties.append((max_night - min_night) * 10)
    penalties.append((max_daily_off - min_daily_off) * 200)

    model.Minimize(sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = int(settings["solver_time_limit_seconds"])
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        raise ValueError(
            "조건을 만족하는 근무표를 찾지 못했습니다. 야비 세트, 개인별 휴무 동일, 일별 필요 인원 조건이 충돌할 수 있습니다."
        )

    assignments = []
    for day in days:
        work_date = date(year, month, day)
        for agent_index, agent in enumerate(active_agents):
            selected_shift = next(
                shift for shift in SHIFT_TYPES if solver.Value(x[(agent_index, day, shift)]) == 1
            )
            assignments.append(
                {
                    "date": work_date.isoformat(),
                    "day": day,
                    "weekday": weekday_label(work_date),
                    "is_off_day": day in off_days,
                    "agent_id": str(agent["id"]),
                    "agent_name": agent["name"],
                    "shift": selected_shift,
                }
            )

    validation = validate_assignments(
        assignments,
        off_target,
        previous_month_rest_day1_ids,
        previous_month_off_day1_ids,
    )
    if validation["hard_error_count"] > 0:
        raise ValueError("생성 후 검증 실패: " + "; ".join(validation["hard_errors"][:3]))

    return {
        "year": int(year),
        "month": int(month),
        "month_key": f"{year}-{month:02}",
        "settings": settings,
        "off_days": sorted(off_days),
        "off_target": off_target,
        "previous_month_rest_day1_agent_ids": sorted(previous_month_rest_day1_ids),
        "previous_month_off_day1_agent_ids": sorted(previous_month_off_day1_ids),
        "validation": validation,
        "summary": summarize_assignments(assignments),
        "assignments": assignments,
    }


def validate_assignments(
    assignments: list[dict],
    off_target: int,
    previous_month_rest_day1_ids: set[str],
    previous_month_off_day1_ids: set[str],
) -> dict:
    hard_errors = []
    by_agent_day: dict[tuple[str, int], str] = {}
    by_agent_name: dict[str, str] = {}
    by_agent: dict[str, Counter] = {}
    by_day: dict[int, Counter] = {}

    for assignment in assignments:
        agent_id = str(assignment["agent_id"])
        agent_name = str(assignment["agent_name"])
        day = int(assignment["day"])
        shift = str(assignment["shift"])
        key = (agent_id, day)
        by_agent_name[agent_id] = agent_name
        if key in by_agent_day:
            hard_errors.append(f"{agent_name} {day}일 중복 배정")
        if shift not in [*SHIFT_TYPES, SHIFT_INACTIVE]:
            hard_errors.append(f"{agent_name} {day}일 알 수 없는 근무 코드 {shift}")
        by_agent_day[key] = shift
        by_agent.setdefault(agent_id, Counter())[shift] += 1
        by_day.setdefault(day, Counter())[shift] += 1

    last_day = max(by_day.keys(), default=0)
    for agent_id, counts in by_agent.items():
        agent_name = by_agent_name.get(agent_id, agent_id)
        actual_off = counts.get(SHIFT_OFF, 0)
        if counts.get(SHIFT_INACTIVE, 0) > 0:
            continue
        if actual_off != off_target:
            hard_errors.append(f"{agent_name} 휴무 {actual_off}개, 목표 {off_target}개")

    for (agent_id, day), shift in by_agent_day.items():
        agent_name = by_agent_name.get(agent_id, agent_id)
        if shift == SHIFT_NIGHT and day < last_day:
            if by_agent_day.get((agent_id, day + 1)) != SHIFT_REST:
                hard_errors.append(f"{agent_name} {day}일 야간 후 {day + 1}일 비번 없음")
            if day + 2 <= last_day and by_agent_day.get((agent_id, day + 2)) != SHIFT_OFF:
                hard_errors.append(f"{agent_name} {day}일 야간 후 {day + 2}일 휴무 없음")
        if shift == SHIFT_REST:
            if day == 1:
                if agent_id not in previous_month_rest_day1_ids:
                    hard_errors.append(f"{agent_name} 1일 비번의 전월 야간 없음")
            elif by_agent_day.get((agent_id, day - 1)) != SHIFT_NIGHT:
                hard_errors.append(f"{agent_name} {day}일 비번의 전날 야간 없음")

    for agent_id in previous_month_rest_day1_ids:
        agent_name = by_agent_name.get(agent_id, agent_id)
        if by_agent_day.get((agent_id, 1)) != SHIFT_REST:
            hard_errors.append(f"{agent_name} 전월 말 야간 이월 1일 비번 없음")
        if last_day >= 2 and by_agent_day.get((agent_id, 2)) != SHIFT_OFF:
            hard_errors.append(f"{agent_name} 전월 말 야간 이월 2일 휴무 없음")
    for agent_id in previous_month_off_day1_ids:
        agent_name = by_agent_name.get(agent_id, agent_id)
        if by_agent_day.get((agent_id, 1)) != SHIFT_OFF:
            hard_errors.append(f"{agent_name} 전월 마지막 전날 야간 이월 1일 휴무 없음")

    daily_totals = {
        str(day): {
            SHIFT_DAY: int(counter.get(SHIFT_DAY, 0)),
            SHIFT_NIGHT: int(counter.get(SHIFT_NIGHT, 0)),
            SHIFT_REST: int(counter.get(SHIFT_REST, 0)),
            SHIFT_OFF: int(counter.get(SHIFT_OFF, 0)),
            SHIFT_INACTIVE: int(counter.get(SHIFT_INACTIVE, 0)),
            "total": int(
                counter.get(SHIFT_DAY, 0)
                + counter.get(SHIFT_NIGHT, 0)
                + counter.get(SHIFT_REST, 0)
                + counter.get(SHIFT_OFF, 0)
            ),
        }
        for day, counter in sorted(by_day.items())
    }

    return {
        "hard_error_count": len(hard_errors),
        "hard_errors": hard_errors,
        "daily_totals": daily_totals,
    }


def summarize_assignments(assignments: list[dict]) -> dict:
    by_agent: dict[str, Counter] = {}
    by_day: dict[str, Counter] = {}

    for assignment in assignments:
        agent_name = assignment["agent_name"]
        day = str(assignment["day"])
        shift = assignment["shift"]
        by_agent.setdefault(agent_name, Counter())[shift] += 1
        by_day.setdefault(day, Counter())[shift] += 1

    return {
        "by_agent": {name: dict(counter) for name, counter in by_agent.items()},
        "by_day": {day: dict(counter) for day, counter in by_day.items()},
    }
