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


def _load_dotenv() -> None:
    env_path = RDI_DIR.parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[key] = value


def _rdi_access_token(client: httpx.Client, api: str) -> str:
    """jwtKey signs tokens; login with the RDI backend Redis user/password."""
    existing = _env("RDI_API_TOKEN")
    if existing:
        probe = client.get(f"{api}/api/v1/pipelines", headers={"Authorization": f"Bearer {existing}"})
        if probe.status_code < 400:
            return existing
    username = _env("RDI_USERNAME")
    password = _env("RDI_PASSWORD")
    if not password:
        raise SystemExit(
            "RDI_PASSWORD is required to POST /api/v1/login (RDI backend Redis password, "
            "not api.jwtKey). kubectl: secret rdi-sys-config key RDI_REDIS_PASSWORD."
        )
    response = client.post(f"{api}/api/v1/login", json={"username": username or None, "password": password})
    if response.status_code >= 400:
        raise SystemExit(f"RDI login failed ({response.status_code}): {response.text[:300]}")
    token = response.json().get("access_token")
    if not token:
        raise SystemExit("RDI login succeeded but access_token was missing.")
    return token


def deploy() -> None:
    _load_dotenv()
    api = _rdi_base()
    config = yaml.safe_load(_render_pipeline())
    if not config.get("processors"):
        config.pop("processors", None)
    jobs = []
    for path in sorted(JOBS_DIR.glob("*.yaml")):
        job = yaml.safe_load(path.read_text(encoding="utf-8"))
        job["name"] = path.stem
        jobs.append(job)
    # RDI config schema: jobs is an array on the same document as sources/targets.
    payload = {**config, "jobs": jobs}

    print(f"Deploying pipeline to {api}/api/v1/pipelines")
    print("Prefix map:")
    for table, prefix in PREFIX_MAP.items():
        print(f"  {table:24} {prefix}")
    with httpx.Client(timeout=180.0) as client:
        token = _rdi_access_token(client, api)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        response = client.post(f"{api}/api/v1/pipelines", headers=headers, json=payload)
        if response.status_code >= 400:
            alt = client.put(f"{api}/pipelines/deploy", headers=headers, json=payload)
            if alt.status_code >= 400:
                raise SystemExit(
                    f"RDI deploy failed ({response.status_code}): {response.text[:500]}\n"
                    f"Fallback PUT /pipelines/deploy failed ({alt.status_code}): {alt.text[:500]}\n"
                    "Set RDI_API_URL to the RDI API ingress. Authenticate via /api/v1/login "
                    "(RDI backend user/password), not helm api.jwtKey."
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
