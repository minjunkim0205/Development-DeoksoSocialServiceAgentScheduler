import json
from pathlib import Path
from typing import Any


DATA_DIR = Path("data")
AGENT_FILE = DATA_DIR / "agents.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
SCHEDULE_DIR = DATA_DIR / "schedules"

DEFAULT_SETTINGS = {
    "weekday_day_target": 2,
    "weekend_day_target": 2,
    "weekday_night_target": 2,
    "weekend_night_target": 2,
    "max_consecutive_work_days": 3,
    "night_rest_required": True,
    "prefer_off_after_rest": True,
    "prefer_day_before_night": True,
    "senior_pair_rank_limit": 4,
    "avoid_limited_agent_pair": True,
    "avoid_regular_agent_pair": True,
    "developer_mode": False,
    "solver_time_limit_seconds": 30,
}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_agents() -> list[dict]:
    data = _read_json(AGENT_FILE, {"agents": []})
    agents = data.get("agents", []) if isinstance(data, dict) else []
    return agents if isinstance(agents, list) else []


def save_agents(agents: list[dict]) -> None:
    _write_json(AGENT_FILE, {"agents": agents})


def load_settings() -> dict:
    data = _read_json(SETTINGS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {**DEFAULT_SETTINGS, **data}


def save_settings(settings: dict) -> None:
    merged = {**DEFAULT_SETTINGS, **settings}
    _write_json(SETTINGS_FILE, merged)


def save_schedule(month_key: str, schedule: dict) -> None:
    _write_json(SCHEDULE_DIR / f"{month_key}.json", schedule)


def load_schedule(month_key: str) -> dict | None:
    schedule = _read_json(SCHEDULE_DIR / f"{month_key}.json", None)
    return schedule if isinstance(schedule, dict) else None


def previous_month_key(year: int, month: int) -> str:
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02}"


def delete_schedule(month_key: str) -> bool:
    schedule_file = SCHEDULE_DIR / f"{month_key}.json"
    if not schedule_file.exists():
        return False
    schedule_file.unlink()
    return True


def list_schedule_months() -> list[str]:
    if not SCHEDULE_DIR.exists():
        return []
    return sorted((path.stem for path in SCHEDULE_DIR.glob("*.json")), reverse=True)
