from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

REPORT_COLUMNS = [
    "file_name",
    "tool_name",
    "tool_slug",
    "tool_version",
    "package_version",
    "infra",
    "location_name",
    "address_country",
    "address_region",
    "address_locality",
    "postal_code",
    "start_time",
    "end_time",
    "start_day",
    "duration_seconds",
    "input_size_bytes",
    "output_size_bytes",
    "memory_used_mb",
    "cpu_cores_assigned",
    "cpu_cores_used",
    "gpu_cores_used",
]

COUNTRY_COORDS = {
    "Germany": {"lat": 51.1657, "lon": 10.4515},
    "Spain": {"lat": 40.4637, "lon": -3.7492},
    "France": {"lat": 46.2276, "lon": 2.2137},
    "Italy": {"lat": 41.8719, "lon": 12.5674},
    "Netherlands": {"lat": 52.1326, "lon": 5.2913},
    "Belgium": {"lat": 50.5039, "lon": 4.4699},
    "Switzerland": {"lat": 46.8182, "lon": 8.2275},
    "Austria": {"lat": 47.5162, "lon": 14.5501},
    "United Kingdom": {"lat": 55.3781, "lon": -3.4360},
    "Sweden": {"lat": 60.1282, "lon": 18.6435},
}

GITHUB_REPORTS_API_URL = "https://api.github.com/repos/ghoshted/ecrdash/contents/reports_output_dir"


def _slugify(value: str) -> str:
    return "-".join(value.lower().replace("/", " ").split())


def _safe_iso_day(iso_ts: str | None) -> str | None:
    if not iso_ts:
        return None
    try:
        return datetime.fromisoformat(iso_ts).date().isoformat()
    except ValueError:
        return None


def _duration_seconds(start: str | None, end: str | None) -> int:
    if not start or not end:
        return 0
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return max(0, int((end_dt - start_dt).total_seconds()))
    except ValueError:
        return 0


def _parse_single_report(payload: dict[str, Any], file_name: str) -> dict[str, Any]:
    tool = payload.get("tool", {}) or {}
    location = payload.get("location", {}) or {}
    address = location.get("address", {}) or {}
    infra_items = payload.get("infra", []) or []

    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    duration = payload.get("duration")
    duration_seconds = int(duration) if isinstance(duration, (int, float)) and duration else _duration_seconds(start_time, end_time)

    tool_name = tool.get("name") or "Unknown Tool"

    return {
        "file_name": file_name,
        "tool_name": tool_name,
        "tool_slug": _slugify(tool_name),
        "tool_version": tool.get("version"),
        "package_version": tool.get("package_version"),
        "infra": [item.get("infra_name") for item in infra_items if item.get("infra_name")],
        "location_name": location.get("name"),
        "address_country": address.get("addressCountry"),
        "address_region": address.get("addressRegion"),
        "address_locality": address.get("addressLocality"),
        "postal_code": address.get("postalCode"),
        "start_time": start_time,
        "end_time": end_time,
        "start_day": _safe_iso_day(start_time),
        "duration_seconds": duration_seconds,
        "input_size_bytes": int(payload.get("input_size_bytes") or 0),
        "output_size_bytes": int(payload.get("final_outputs_size_bytes") or 0),
        "memory_used_mb": int(payload.get("memory_used") or 0),
        "cpu_cores_assigned": int(payload.get("cpu_cores_assigned") or 0),
        "cpu_cores_used": int(payload.get("cpu_cores_used") or 0),
        "gpu_cores_used": int(payload.get("gpu_cores_used") or 0),
    }


def _sample_reports(total: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    tools = [
        "FastQC",
        "InterProScan",
        "AlphaFold 2",
        "Bismark Mapper",
        "VCFsort",
        "Protein Calculator",
    ]
    infra_pool = ["Galaxy", "HTCondor", "Kubernetes", "Slurm"]
    countries = ["Germany", "Spain", "France", "Italy", "Netherlands", ""]

    end = date.today()
    rows: list[dict[str, Any]] = []

    for idx in range(total):
        tool = tools[idx % len(tools)]
        day_offset = int(rng.integers(0, 45))
        start = datetime.combine(end - timedelta(days=day_offset), datetime.min.time()) + timedelta(
            hours=int(rng.integers(0, 23)),
            minutes=int(rng.integers(0, 59)),
            seconds=int(rng.integers(0, 59)),
        )
        duration = int(max(12, rng.normal(560, 220)))
        end_time = start + timedelta(seconds=duration)

        rows.append(
            {
                "file_name": f"sample_report_{idx:04d}.json",
                "tool_name": tool,
                "tool_slug": _slugify(tool),
                "tool_version": "1.0.0",
                "package_version": "demo",
                "infra": list(rng.choice(infra_pool, size=int(rng.integers(1, 3)), replace=False)),
                "location_name": "",
                "address_country": countries[int(rng.integers(0, len(countries)))],
                "address_region": "",
                "address_locality": "",
                "postal_code": "",
                "start_time": start.isoformat(),
                "end_time": end_time.isoformat(),
                "start_day": start.date().isoformat(),
                "duration_seconds": duration,
                "input_size_bytes": int(max(100, rng.normal(125_000_000, 22_000_000))),
                "output_size_bytes": int(max(0, rng.normal(420_000, 110_000))),
                "memory_used_mb": int(max(500, rng.normal(14_500, 4_000))),
                "cpu_cores_assigned": int(rng.integers(1, 16)),
                "cpu_cores_used": int(rng.integers(1, 8)),
                "gpu_cores_used": int(rng.integers(0, 2)),
            }
        )

    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    return df.sort_values("start_time", ascending=False).reset_index(drop=True)


def _df_with_source(rows: list[dict[str, Any]], source: str) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df = df.reindex(columns=REPORT_COLUMNS)
    df = df.sort_values("start_time", ascending=False).reset_index(drop=True)
    df.attrs["source"] = source
    return df


def _fetch_json(url: str, timeout: int = 20) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ecrdashpy-streamlit",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


@lru_cache(maxsize=1)
def _load_remote_reports(api_url: str = GITHUB_REPORTS_API_URL) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    try:
        listing = _fetch_json(api_url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return parsed

    if not isinstance(listing, list):
        return parsed

    for item in listing:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "file":
            continue
        name = str(item.get("name") or "")
        if not name.endswith(".json"):
            continue

        download_url = item.get("download_url")
        if not isinstance(download_url, str) or not download_url:
            continue

        try:
            payload = _fetch_json(download_url)
            if isinstance(payload, dict):
                parsed.append(_parse_single_report(payload, name))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
            continue

    return parsed


def _load_local_reports(root: str | Path = ".") -> list[dict[str, Any]]:
    root_path = Path(root)
    report_dir = root_path / "reports_output_dir"

    parsed: list[dict[str, Any]] = []
    if report_dir.exists() and report_dir.is_dir():
        for path in sorted(report_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                parsed.append(_parse_single_report(payload, path.name))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue

    return parsed


def load_reports(root: str | Path = ".", source: str = "remote") -> pd.DataFrame:
    source = source.lower().strip()
    if source not in {"remote", "local", "auto"}:
        source = "remote"

    if source in {"remote", "auto"}:
        remote_rows = _load_remote_reports()
        if remote_rows:
            return _df_with_source(remote_rows, "remote")

    if source in {"local", "auto"}:
        local_rows = _load_local_reports(root)
        if local_rows:
            return _df_with_source(local_rows, "local")

    sample_df = _sample_reports()
    sample_df.attrs["source"] = "sample"
    return sample_df


def aggregate_reports(df: pd.DataFrame) -> dict[str, Any]:
    safe = df.fillna({
        "duration_seconds": 0,
        "input_size_bytes": 0,
        "output_size_bytes": 0,
        "memory_used_mb": 0,
        "cpu_cores_assigned": 0,
        "cpu_cores_used": 0,
        "gpu_cores_used": 0,
        "tool_name": "Unknown Tool",
    }).copy()

    totals = {
        "reports": int(len(safe)),
        "duration_seconds": int(safe["duration_seconds"].sum()),
        "input_size_bytes": int(safe["input_size_bytes"].sum()),
        "output_size_bytes": int(safe["output_size_bytes"].sum()),
        "memory_used_mb": int(safe["memory_used_mb"].sum()),
        "cpu_cores_assigned": int(safe["cpu_cores_assigned"].sum()),
        "cpu_cores_used": int(safe["cpu_cores_used"].sum()),
        "gpu_cores_used": int(safe["gpu_cores_used"].sum()),
    }

    divisor = max(1, totals["reports"])
    averages = {
        "duration_seconds": int(round(totals["duration_seconds"] / divisor)),
        "input_size_bytes": int(round(totals["input_size_bytes"] / divisor)),
        "output_size_bytes": int(round(totals["output_size_bytes"] / divisor)),
        "memory_used_mb": int(round(totals["memory_used_mb"] / divisor)),
    }

    by_tool = (
        safe.groupby("tool_name", as_index=False)
        .agg(
            count=("tool_name", "size"),
            total_duration_seconds=("duration_seconds", "sum"),
            total_input_bytes=("input_size_bytes", "sum"),
            total_output_bytes=("output_size_bytes", "sum"),
        )
        .sort_values(["count", "tool_name"], ascending=[False, True])
    )

    by_day = (
        safe[safe["start_day"].notna()]
        .groupby("start_day", as_index=False)
        .agg(count=("start_day", "size"), duration_seconds=("duration_seconds", "sum"))
        .sort_values("start_day")
    )

    by_infra = (
        safe.explode("infra")
        .dropna(subset=["infra"])
        .groupby("infra", as_index=False)
        .agg(count=("infra", "size"), total_duration_seconds=("duration_seconds", "sum"))
        .sort_values(["count", "infra"], ascending=[False, True])
        .rename(columns={"infra": "name"})
    )

    by_day_tool_memory = (
        safe[safe["start_day"].notna()]
        .groupby(["start_day", "tool_name"], as_index=False)
        .agg(memory_used_mb=("memory_used_mb", "sum"))
        .sort_values(["start_day", "memory_used_mb"], ascending=[True, False])
    )

    by_country = (
        safe[safe["address_country"].astype(str).str.len() > 0]
        .groupby("address_country", as_index=False)
        .agg(count=("address_country", "size"))
        .sort_values(["count", "address_country"], ascending=[False, True])
        .rename(columns={"address_country": "country"})
    )

    return {
        "totals": totals,
        "averages": averages,
        "by_tool": by_tool,
        "by_day": by_day,
        "by_infra": by_infra,
        "by_day_tool_memory": by_day_tool_memory,
        "by_country": by_country,
    }


def map_points_from_reports(df: pd.DataFrame) -> pd.DataFrame:
    countries = (
        df[df["address_country"].astype(str).str.len() > 0]
        .groupby("address_country", as_index=False)
        .agg(count=("address_country", "size"))
        .rename(columns={"address_country": "country"})
    )

    if countries.empty:
        return pd.DataFrame(columns=["country", "count", "lat", "lon"])

    points = countries.assign(
        lat=countries["country"].map(lambda c: COUNTRY_COORDS.get(c, {}).get("lat")),
        lon=countries["country"].map(lambda c: COUNTRY_COORDS.get(c, {}).get("lon")),
    )
    return points.dropna(subset=["lat", "lon"]).sort_values("count", ascending=False)


def format_bytes(num_bytes: int) -> str:
    value = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    precision = 2 if value < 10 and idx > 0 else 1
    return f"{value:.{precision}f} {units[idx]}"


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
