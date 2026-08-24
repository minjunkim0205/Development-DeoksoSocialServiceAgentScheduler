from __future__ import annotations

import calendar
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.holidays import get_month_off_dates
from core.storage import DEFAULT_SETTINGS, load_agents

SCHEDULE_DIR = ROOT / "data" / "schedules"

SHIFT_TO_CODE = {"주": "D", "야": "N", "비": "R", "휴": "O", "#": "X"}
CODE_TO_SHIFT = {value: key for key, value in SHIFT_TO_CODE.items()}

MANUAL_ROWS = {
    5: {
        "\uc774\uaddc\uc6d0": "ODODNRODOODONRODONRODODNRODDODO",
        "\uc774\uc6b0\uc194": "NROODNRONRODOODOODONRONRONRONRO",
        "\uc7a5\uc900\ud601": "RONROODNRODOODOODONRODODNRONROD",
        "\uae40\uc138\uc911": "DNROODDOONRONRONRODONROODONROON",
        "\ud558\uc740\uc218": "OODNROOONRONRODDNRODONRONROODOD",
        "\uc774\uc900\uc601": "OOODODDDOODDDDOODNRONRONRODOONR",
        "\uace0\ud0dc\uc724": "ONRONROODNRODNRONROODDOOODDDDOO",
        "\ubc15\uc2b9\uc644": "NRONRONRODNROONROONRONROODONROO",
        "\uae40\ubbfc\uc900": "RONRONRODOONRONROOONRONRONRONRO",
    },
    6: {
        "\uc774\uaddc\uc6d0": "DNRODNROODDNRODNRONRODDODXXXXX",
        "\uc774\uc6b0\uc194": "NRONRODDNRONRONRODODNRONRODNRO",
        "\uc7a5\uc900\ud601": "NRODNRONRONRODODODNRODODNRODNR",
        "\uae40\uc138\uc911": "RONRODNRODNRONRODNRODDNRODONRO",
        "\ud558\uc740\uc218": "OODNRONRONRODNRODNRODNRONRODDN",
        "\uc774\uc900\uc601": "ONRONRONRODDNRODNROONRODDNRODN",
        "\uace0\ud0dc\uc724": "DDODDOODDDDOODDNRODNRONRODNROD",
        "\ubc15\uc2b9\uc644": "ODNRONRODNRONROONRODDNRODNRONR",
        "\uae40\ubbfc\uc900": "DDDODDDDDOODDDODDODDOODDDDDOOD",
        "\uc815\ud61c\uc131": "DDODDODONRODDONRODDNRODNRONROD",
    },
    7: {
        "\uc774\uc6b0\uc194": "DNRONRODNRODDNRONROONRONRODDNRO",
        "\uc7a5\uc900\ud601": "ODNRODNRONRONRONRODNRODDODNRODN",
        "\uae40\uc138\uc911": "NRONRODNRODNRODNRODNRONRONROODD",
        "\ud558\uc740\uc218": "RODNRONRODDNROODNRODNRODNRONRON",
        "\uc774\uc900\uc601": "RONRODONRONRONRODNRODDNRODNRONR",
        "\uace0\ud0dc\uc724": "NRODNROONRODNROODNRODNRODNRODNR",
        "\ubc15\uc2b9\uc644": "ONRODNRODDNRODNRODNRONRONRODNRO",
        "\uae40\ubbfc\uc900": "DDDDOODDDDDOODDDDODDDDOODDDDDOO",
        "\uc815\ud61c\uc131": "DDDODNRODNRODONRODNROODNRODNROD",
    },
    8: {
        "\uc774\uc6b0\uc194": "DNRONRODNRONROODODNRODODDODXXXX",
        "\uc7a5\uc900\ud601": "RONROODNROONRONROODNRODNRODNRON",
        "\uae40\uc138\uc911": "NROODNRONROODNRONRONRONRODNROOD",
        "\ud558\uc740\uc218": "ROONRODNROODNRONROODNRONRONRONR",
        "\uc774\uc900\uc601": "OODNRONRODNRODNRONRONROONRODNRO",
        "\uace0\ud0dc\uc724": "OONRONRODNRONRODNROODNRONRODNRO",
        "\ubc15\uc2b9\uc644": "NRODNRODONROONROONRODNROONRODNR",
        "\uae40\ubbfc\uc900": "DDDDDOOODDDDDOOODDDDOODDDDOOODD",
        "\uc815\ud61c\uc131": "ONROODNROONRODDNRONRODNRONRODON",
    }
}


@dataclass(frozen=True)
class PhotoConfig:
    month: int
    filename: str
    days: int
    names: list[str]
    x0: float
    x1: float
    y0: float
    y1: float
    row0_codes: str
    inactive_cells: set[tuple[int, int]]


CONFIGS = {
    4: PhotoConfig(
        month=4,
        filename="4월.jpg",
        days=30,
        names=["이규원", "이우솔", "장준혁", "김세중", "하은수", "이준영", "고태윤", "박승완", "김민준"],
        x0=148,
        x1=1203,
        y0=214,
        y1=627,
        row0_codes="DODNRODNRONDRODNRodoDNRoDNR",
        inactive_cells={(8, day) for day in range(16)},
    ),
    5: PhotoConfig(
        month=5,
        filename="5월.jpg",
        days=31,
        names=["이규원", "이우솔", "장준혁", "김세중", "하은수", "이준영", "고태윤", "박승완", "김민준"],
        x0=509,
        x1=4973,
        y0=735,
        y1=2535,
        row0_codes="ODODNRODOODONRODONRODODNRODDODO",
        inactive_cells=set(),
    ),
    6: PhotoConfig(
        month=6,
        filename="6월.jpg",
        days=30,
        names=["이규원", "이우솔", "장준혁", "김세중", "하은수", "이준영", "고태윤", "박승완", "김민준", "정혜성"],
        x0=399,
        x1=3367,
        y0=498,
        y1=1882,
        row0_codes="DNRDNRDOODDNRDNRONROODDODXXXXX",
        inactive_cells={(0, day) for day in range(25, 30)},
    ),
    7: PhotoConfig(
        month=7,
        filename="7월.jpg",
        days=31,
        names=["이우솔", "장준혁", "김세중", "하은수", "이준영", "고태윤", "박승완", "김민준", "정혜성"],
        x0=588,
        x1=4730,
        y0=980,
        y1=2920,
        row0_codes="DNROONRODRODDNRODNROONRONRODDNRO",
        inactive_cells=set(),
    ),
    8: PhotoConfig(
        month=8,
        filename="8월.jpg",
        days=31,
        names=["이우솔", "장준혁", "김세중", "하은수", "이준영", "고태윤", "박승완", "김민준", "정혜성"],
        x0=276,
        x1=2367,
        y0=346,
        y1=1288,
        row0_codes="DNROONRODROONDRODODNRODODDOXXXXX",
        inactive_cells={(0, day) for day in range(27, 31)},
    ),
}


def crop_cell(image: np.ndarray, cfg: PhotoConfig, row: int, day: int) -> np.ndarray:
    cell_w = (cfg.x1 - cfg.x0) / cfg.days
    cell_h = (cfg.y1 - cfg.y0) / len(cfg.names)
    left = int(round(cfg.x0 + day * cell_w + cell_w * 0.18))
    right = int(round(cfg.x0 + (day + 1) * cell_w - cell_w * 0.18))
    top = int(round(cfg.y0 + row * cell_h + cell_h * 0.2))
    bottom = int(round(cfg.y0 + (row + 1) * cell_h - cell_h * 0.2))
    crop = image[top:bottom, left:right]
    if crop.size == 0:
        raise ValueError(f"empty crop: month={cfg.month}, row={row}, day={day}")
    return crop


def normalize(crop: np.ndarray, size: int = 40) -> np.ndarray:
    img = Image.fromarray(crop).convert("L").resize((size, size))
    arr = np.array(img).astype(np.float32)
    arr = 255 - arr
    threshold = max(20.0, np.percentile(arr, 86))
    arr = (arr >= threshold).astype(np.float32)
    # Center the glyph mass to reduce small coordinate drift.
    ys, xs = np.where(arr > 0)
    if len(xs):
        x0, x1 = xs.min(), xs.max() + 1
        y0, y1 = ys.min(), ys.max() + 1
        glyph = arr[y0:y1, x0:x1]
        canvas = np.zeros_like(arr)
        top = max(0, (size - glyph.shape[0]) // 2)
        left = max(0, (size - glyph.shape[1]) // 2)
        canvas[top : top + glyph.shape[0], left : left + glyph.shape[1]] = glyph
        arr = canvas
    return arr


def classify_month(cfg: PhotoConfig) -> dict[str, list[str]]:
    image = np.array(Image.open(SCHEDULE_DIR / cfg.filename).convert("L"))
    samples: dict[str, list[np.ndarray]] = {code: [] for code in ("D", "N", "R", "O")}
    for day, code in enumerate(cfg.row0_codes.upper()):
        if code in samples:
            samples[code].append(normalize(crop_cell(image, cfg, 0, day)))

    rows: dict[str, list[str]] = {}
    for row, name in enumerate(cfg.names):
        codes = []
        for day in range(cfg.days):
            if (row, day) in cfg.inactive_cells:
                codes.append("X")
                continue
            sample = normalize(crop_cell(image, cfg, row, day))
            distances = {
                code: min(float(((sample - tmpl) ** 2).mean()) for tmpl in templates)
                for code, templates in samples.items()
            }
            codes.append(min(distances, key=distances.get))
        rows[name] = codes
    return rows


def validate_rows(rows: dict[str, list[str]], days: int) -> tuple[dict[str, Counter], list[Counter]]:
    by_agent = {name: Counter(codes) for name, codes in rows.items()}
    by_day = []
    for day in range(days):
        by_day.append(Counter(codes[day] for codes in rows.values()))
    return by_agent, by_day


def make_schedule(cfg: PhotoConfig, rows: dict[str, list[str]]) -> dict:
    _, last_day = calendar.monthrange(2026, cfg.month)
    assert last_day == cfg.days
    agent_ids_by_name = {str(agent.get("name")): str(agent.get("id")) for agent in load_agents()}
    assignments = []
    for day in range(1, cfg.days + 1):
        weekday = ["월", "화", "수", "목", "금", "토", "일"][calendar.weekday(2026, cfg.month, day)]
        is_off_day = weekday in {"토", "일"}
        for idx, (name, codes) in enumerate(rows.items(), start=1):
            code = codes[day - 1]
            agent_id = agent_ids_by_name.get(name, f"photo-{cfg.month:02d}-{idx:02d}")
            assignments.append(
                {
                    "date": f"2026-{cfg.month:02d}-{day:02d}",
                    "day": day,
                    "weekday": weekday,
                    "is_off_day": is_off_day,
                    "agent_id": agent_id,
                    "agent_name": name,
                    "shift": code,
                }
            )

    by_agent, by_day = validate_rows(rows, cfg.days)
    summary = {
        "by_agent": {
            name: {code: int(counts.get(code, 0)) for code in ("D", "N", "R", "O", "X")}
            for name, counts in by_agent.items()
        },
        "by_day": {
            str(day + 1): {code: int(counts.get(code, 0)) for code in ("D", "N", "R", "O", "X")}
            for day, counts in enumerate(by_day)
        },
    }
    off_days = sorted(work_date.day for work_date in get_month_off_dates(2026, cfg.month))
    return {
        "year": 2026,
        "month": cfg.month,
        "month_key": f"2026-{cfg.month:02d}",
        "settings": DEFAULT_SETTINGS,
        "off_days": off_days,
        "off_target": len(off_days),
        "previous_month_rest_day1_agent_ids": [],
        "previous_month_off_day1_agent_ids": [],
        "validation": {"hard_error_count": 0, "hard_errors": [], "daily_totals": summary["by_day"]},
        "source": f"photo hard input: {cfg.filename}",
        "assignments": assignments,
        "summary": summary,
    }


def main() -> None:
    write_files = "--write" in sys.argv
    for month, cfg in CONFIGS.items():
        rows = {name: list(codes) for name, codes in MANUAL_ROWS.get(month, {}).items()}
        if not rows:
            rows = classify_month(cfg)
        by_agent, by_day = validate_rows(rows, cfg.days)
        print(f"\n2026-{month:02d}")
        for name, counts in by_agent.items():
            print(name, "".join(rows[name]), dict(counts))
        print("D", " ".join(str(counts.get("D", 0)) for counts in by_day))
        print("N", " ".join(str(counts.get("N", 0)) for counts in by_day))
        print("R", " ".join(str(counts.get("R", 0)) for counts in by_day))
        print("O", " ".join(str(counts.get("O", 0)) for counts in by_day))
        if write_files and month in MANUAL_ROWS:
            out = make_schedule(cfg, rows)
            path = SCHEDULE_DIR / f"2026-{month:02d}.json"
            path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
