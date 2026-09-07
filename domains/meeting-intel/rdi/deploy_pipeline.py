"""Deploy meeting-intel RDI pipeline + jobs non-interactively via the RDI API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import yaml

RDI_DIR = Path(__file__).resolve().parent
PIPELINE = RDI_DIR / "pipeline-config.yaml"
JOBS_DIR = RDI_DIR / "jobs"

PREFIX_MAP = {
    "people": "person:",
    "projects": "project:",
    "meetings": "meeting:",
    "meeting_participants": "participant:",
    "transcripts": "transcript:",
    "decisions": "decision:",
    "action_items": "action:",
    "risks": "risk:",
    "project_dependencies": "dependency:",
    "agendas": "agenda:",
}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _render_pipeline() -> str:
    raw = PIPELINE.read_text(encoding="utf-8")
    replacements = {
        "${SOURCE_DB_HOST}": _env("MEETING_INTEL_RDI_SOURCE_HOST") or "postgres.meeting-intel.svc.cluster.local",
        "${SOURCE_DB_PORT}": _env("MEETING_INTEL_PG_PORT", "5432"),
        "${SOURCE_DB_NAME}": _env("MEETING_INTEL_PG_DB", "postgres"),
        "${SOURCE_DB_USERNAME}": _env("MEETING_INTEL_RDI_SOURCE_USER") or "dbzuser",
        "${SOURCE_DB_PASSWORD}": _env("MEETING_INTEL_RDI_SOURCE_PASSWORD") or "dbz",
        "${TARGET_DB_HOST}": _env("REDIS_HOST", ""),
        "${TARGET_DB_PORT}": _env("REDIS_PORT", "6379"),
        "${TARGET_DB_USERNAME}": _env("REDIS_USERNAME", "default"),
        "${TARGET_DB_PASSWORD}": _env("REDIS_PASSWORD", ""),
    }
    for key, value in replacements.items():
        raw = raw.replace(key, value)
    if not _env("REDIS_HOST") or not _env("REDIS_PASSWORD"):
        raise SystemExit("REDIS_HOST and REDIS_PASSWORD must be set (target is the iris-demos Redis Cloud DB).")
    yaml.safe_load(raw)
    return raw


def _rdi_base() -> str:
    return (_env("RDI_API_URL") or "http://127.0.0.1:8080").rstrip("/")


def deploy() -> None:
    api = _rdi_base()
    token = _env("RDI_API_TOKEN")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    config_text = _render_pipeline()
    jobs = {path.stem: path.read_text(encoding="utf-8") for path in sorted(JOBS_DIR.glob("*.yaml"))}
    payload = {"config": config_text, "jobs": jobs}

    # RDI 1.8+ Kubernetes API: POST /api/v1/pipelines
    url = f"{api}/api/v1/pipelines"
    print(f"Deploying pipeline to {url}")
    print("Prefix map:")
    for table, prefix in PREFIX_MAP.items():
        print(f"  {table:24} {prefix}")
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            # Fallback used by some rdi-api builds
            alt = client.put(f"{api}/pipelines/deploy", headers=headers, json=payload)
            if alt.status_code >= 400:
                raise SystemExit(
                    f"RDI deploy failed ({response.status_code}): {response.text[:500]}\n"
                    f"Fallback PUT /pipelines/deploy failed ({alt.status_code}): {alt.text[:500]}\n"
                    "Set RDI_API_URL to the RDI API ingress and RDI_API_TOKEN from helm values api.jwtKey."
                )
            response = alt
        print(f"Deploy accepted: HTTP {response.status_code}")
        print(response.text[:800])


if __name__ == "__main__":
    try:
        import yaml as _yaml  # noqa: F401
    except ImportError:
        print("PyYAML is required for pipeline rendering. It ships with the helm/k8s toolchain; install pyyaml if missing.", file=sys.stderr)
    deploy()
