from datetime import date
import calendar
from ortools.sat.python import cp_model


SHIFT_DAY = "D"
SHIFT_NIGHT = "N"
SHIFT_REST = "R"
SHIFT_OFF = "O"

SHIFT_TYPES = [
    SHIFT_DAY,
    SHIFT_NIGHT,
    SHIFT_REST,
    SHIFT_OFF
]


def is_weekend(work_date: date) -> bool:
    return work_date.weekday() in [4, 5, 6]


def generate_schedule(year: int, month: int, agents: list[dict]) -> dict:
    active_agents = sorted(
        [agent for agent in agents if agent.get("active") is True],
        key=lambda x: int(x["id"])
    )

    if len(active_agents) < 4:
        raise ValueError("복무중 요원이 너무 적습니다. 최소 4명 이상 필요합니다.")

    num_agents = len(active_agents)
    last_day = calendar.monthrange(year, month)[1]
    days = list(range(1, last_day + 1))

    model = cp_model.CpModel()
    penalties = []

    x = {}

    for a in range(num_agents):
        for d in days:
            for s in SHIFT_TYPES:
                x[(a, d, s)] = model.NewBoolVar(f"x_a{a}_d{d}_{s}")

    # 하루에 하나의 근무만
    for a in range(num_agents):
        for d in days:
            model.Add(
                sum(x[(a, d, s)] for s in SHIFT_TYPES) == 1
            )

    # 주간전담 / 야간전담
    for a, agent in enumerate(active_agents):
        work_type = agent.get("work_type", "general")

        for d in days:
            if work_type == "day_only":
                model.Add(x[(a, d, SHIFT_NIGHT)] == 0)
                model.Add(x[(a, d, SHIFT_REST)] == 0)

            elif work_type == "night_only":
                model.Add(x[(a, d, SHIFT_DAY)] == 0)

    # 야간 인원
    for d in days:
        work_date = date(year, month, d)

        night_count = sum(
            x[(a, d, SHIFT_NIGHT)]
            for a in range(num_agents)
        )

        if is_weekend(work_date):
            # 금토일 야간은 무조건 2명
            model.Add(night_count == 2)
        else:
            # 평일 야간은 1~2명
            model.Add(night_count >= 1)
            model.Add(night_count <= 2)

            # 되도록 2명 선호
            lack_night = model.NewBoolVar(f"lack_night_d{d}")
            model.Add(night_count == 1).OnlyEnforceIf(lack_night)
            model.Add(night_count >= 2).OnlyEnforceIf(lack_night.Not())
            penalties.append(lack_night * 30)

    # 주간 인원
    for d in days:
        work_date = date(year, month, d)

        day_count = sum(
            x[(a, d, SHIFT_DAY)]
            for a in range(num_agents)
        )

        if is_weekend(work_date):
            # 금토일은 최대 3명, 최소 1명
            model.Add(day_count >= 1)
            model.Add(day_count <= 3)

            # 되도록 2명 선호
            diff = model.NewIntVar(0, 3, f"weekend_day_diff_d{d}")
            model.AddAbsEquality(diff, day_count - 2)
            penalties.append(diff * 5)

        else:
            # 평일은 3명 이상 금지
            model.Add(day_count >= 1)
            model.Add(day_count <= 2)

            # 되도록 2명 선호
            lack_day = model.NewBoolVar(f"lack_day_d{d}")
            model.Add(day_count == 1).OnlyEnforceIf(lack_day)
            model.Add(day_count >= 2).OnlyEnforceIf(lack_day.Not())
            penalties.append(lack_day * 20)

    # 야간 다음날은 비번 강제
    for a in range(num_agents):
        for d in range(1, last_day):
            model.AddImplication(
                x[(a, d, SHIFT_NIGHT)],
                x[(a, d + 1, SHIFT_REST)]
            )

    # 비번 다음날은 휴무 선호
    for a in range(num_agents):
        for d in range(1, last_day):
            penalty = model.NewBoolVar(f"rest_not_off_a{a}_d{d}")

            # penalty = 1 when R today and not O tomorrow
            model.AddBoolAnd(
                [
                    x[(a, d, SHIFT_REST)],
                    x[(a, d + 1, SHIFT_OFF)].Not()
                ]
            ).OnlyEnforceIf(penalty)

            model.AddBoolOr(
                [
                    x[(a, d, SHIFT_REST)].Not(),
                    x[(a, d + 1, SHIFT_OFF)]
                ]
            ).OnlyEnforceIf(penalty.Not())

            penalties.append(penalty * 15)

    # 신입끼리 야간 금지
    new_agent_indexes = [
        a for a, agent in enumerate(active_agents)
        if agent.get("is_new") is True
    ]

    for d in days:
        if new_agent_indexes:
            model.Add(
                sum(x[(a, d, SHIFT_NIGHT)] for a in new_agent_indexes) <= 1
            )

    # 적응 완료자끼리 야간 붙는 것 피하기
    regular_agent_indexes = [
        a for a, agent in enumerate(active_agents)
        if agent.get("is_new") is False
    ]

    for d in days:
        regular_night_count = sum(
            x[(a, d, SHIFT_NIGHT)]
            for a in regular_agent_indexes
        )

        over_regular = model.NewIntVar(0, 2, f"regular_night_over_d{d}")
        model.AddMaxEquality(
            over_regular,
            [
                regular_night_count - 1,
                0
            ]
        )

        penalties.append(over_regular * 25)

    # 선복무 / 교육 미수료자끼리 야간 금지
    limited_agent_indexes = [
        a for a, agent in enumerate(active_agents)
        if agent.get("pre_service") is True
        or agent.get("training_completed") is False
    ]

    for d in days:
        if limited_agent_indexes:
            model.Add(
                sum(x[(a, d, SHIFT_NIGHT)] for a in limited_agent_indexes) <= 1
            )

    # 같은 사람이 너무 연속 근무하지 않게
    for a in range(num_agents):
        for d in range(1, last_day - 2):
            work_4_days = sum(
                x[(a, day, SHIFT_DAY)] + x[(a, day, SHIFT_NIGHT)]
                for day in range(d, d + 4)
            )

            model.Add(work_4_days <= 3)

    # 근무 횟수 균형
    work_counts = []

    for a in range(num_agents):
        work_count = model.NewIntVar(0, last_day, f"work_count_a{a}")

        model.Add(
            work_count ==
            sum(
                x[(a, d, SHIFT_DAY)] + x[(a, d, SHIFT_NIGHT)]
                for d in days
            )
        )

        work_counts.append(work_count)

    max_work = model.NewIntVar(0, last_day, "max_work")
    min_work = model.NewIntVar(0, last_day, "min_work")

    model.AddMaxEquality(max_work, work_counts)
    model.AddMinEquality(min_work, work_counts)

    penalties.append((max_work - min_work) * 10)

    model.Minimize(sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        raise ValueError(
            "조건을 만족하는 근무표를 찾지 못했습니다. "
            "복무중 인원 수, 주간전담/야간전담 비율, 신입 인원 수를 확인하세요."
        )

    assignments = []

    for d in days:
        work_date = date(year, month, d)

        for a, agent in enumerate(active_agents):
            selected_shift = None

            for s in SHIFT_TYPES:
                if solver.Value(x[(a, d, s)]) == 1:
                    selected_shift = s
                    break

            assignments.append(
                {
                    "date": work_date.isoformat(),
                    "day": d,
                    "agent_id": agent["id"],
                    "agent_name": agent["name"],
                    "shift": selected_shift
                }
            )

    return {
        "year": int(year),
        "month": int(month),
        "month_key": f"{year}-{month:02}",
        "assignments": assignments
    }