import json
from pathlib import Path

DATA_DIR = Path("data")

# Agent json
AGENT_FILE = DATA_DIR / "agents.json"

def load_agents():
    if not AGENT_FILE.exists():
        return []

    with open(AGENT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("agents", [])

def save_agents(agents):
    DATA_DIR.mkdir(exist_ok=True)

    with open(AGENT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"agents": agents},
            f,
            ensure_ascii=False,
            indent=2
        )

# Agent schedule
SCHEDULE_DIR = DATA_DIR / "schedules"

def save_schedule(month_key, schedule):
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

    schedule_file = SCHEDULE_DIR / f"{month_key}.json"

    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(
            schedule,
            f,
            ensure_ascii=False,
            indent=2
        )

def load_schedule(month_key):
    schedule_file = SCHEDULE_DIR / f"{month_key}.json"

    if not schedule_file.exists():
        return None

    with open(schedule_file, "r", encoding="utf-8") as f:
        return json.load(f)
