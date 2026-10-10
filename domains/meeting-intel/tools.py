"""Postgres write tools. RDI owns Redis keys; these never JSON.SET synced documents."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import importlib.util
from pathlib import Path

_pg_spec = importlib.util.spec_from_file_location(
    "meeting_intel_postgres",
    Path(__file__).with_name("postgres.py"),
)
if _pg_spec is None or _pg_spec.loader is None:
    raise ImportError("Unable to load meeting-intel postgres helper")
_pg = importlib.util.module_from_spec(_pg_spec)
_pg_spec.loader.exec_module(_pg)
RDI_NOTE = _pg.RDI_NOTE
postgres_conn = _pg.postgres_conn

_ID_OK = re.compile(r"^[A-Za-z0-9._:-]+$")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _require_id(name: str, value: Any) -> str | dict[str, Any]:
    cleaned = _clean_id(value)
    if not cleaned or not _ID_OK.match(cleaned):
        return {"error": f"{name} must be a non-empty identifier."}
    return cleaned


def _row(cur, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    cur.execute(sql, params)
    rec = cur.fetchone()
    if rec is None:
        return None
    cols = [d.name for d in cur.description]
    return dict(zip(cols, rec, strict=True))


def _exists(cur, table: str, column: str, value: str) -> bool:
    cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s LIMIT 1", (value,))
    return cur.fetchone() is not None


def save_ai_agenda(arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
    del settings
    meeting_id = _require_id("meeting_id", arguments.get("meeting_id"))
    if isinstance(meeting_id, dict):
        return meeting_id
    ai_agenda = str(arguments.get("ai_agenda") or "").strip()
    if not ai_agenda:
        return {"error": "ai_agenda must be non-empty markdown/text."}
    sources = arguments.get("sources")
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except json.JSONDecodeError:
            sources = [sources]
    if sources is None:
        sources = []
    generated_by = str(arguments.get("generated_by") or os.getenv("DEMO_USER_ID") or "minutes-agent")

    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                meeting = _row(cur, "SELECT meeting_id, visibility, status FROM meetings WHERE meeting_id = %s", (meeting_id,))
                if not meeting:
                    return {"error": f"Unknown meeting_id {meeting_id}."}
                existing = _row(
                    cur,
                    "SELECT agenda_id, human_agenda FROM agendas WHERE meeting_id = %s",
                    (meeting_id,),
                )
                human_agenda = existing["human_agenda"] if existing else ""
                agenda_id = existing["agenda_id"] if existing else f"ag-{meeting_id}"
                cur.execute(
                    """
                    INSERT INTO agendas (
                        agenda_id, meeting_id, human_agenda, ai_agenda, ai_agenda_sources,
                        generated_at, generated_by, status, visibility
                    )
                    VALUES (
                        %s, %s, %s, %s, %s::jsonb, %s, %s, 'draft', %s
                    )
                    ON CONFLICT (meeting_id) DO UPDATE SET
                        ai_agenda = EXCLUDED.ai_agenda,
                        ai_agenda_sources = EXCLUDED.ai_agenda_sources,
                        generated_at = EXCLUDED.generated_at,
                        generated_by = EXCLUDED.generated_by,
                        status = 'draft'
                    RETURNING agenda_id
                    """,
                    (
                        agenda_id,
                        meeting_id,
                        human_agenda,
                        ai_agenda,
                        json.dumps(sources),
                        _now(),
                        generated_by,
                        meeting["visibility"],
                    ),
                )
                agenda_id = cur.fetchone()[0]
    except Exception as exc:
        return {"error": f"Postgres write failed: {exc}"}

    return {
        "status": "ok",
        "agenda_id": agenda_id,
        "meeting_id": meeting_id,
        "note": RDI_NOTE,
    }


def create_action_item(arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
    del settings
    meeting_id = _require_id("meeting_id", arguments.get("meeting_id"))
    project_id = _require_id("project_id", arguments.get("project_id"))
    owner_person_id = _require_id("owner_person_id", arguments.get("owner_person_id"))
    for maybe in (meeting_id, project_id, owner_person_id):
        if isinstance(maybe, dict):
            return maybe
    text = str(arguments.get("text") or "").strip()
    due_date = str(arguments.get("due_date") or "").strip()
    if not text or not due_date:
        return {"error": "text and due_date are required."}
    try:
        datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "due_date must be ISO-8601 (YYYY-MM-DD or timestamp)."}

    action_id = str(arguments.get("action_id") or f"act-live-{datetime.now(timezone.utc).strftime('%H%M%S')}")
    now = _now()
    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                if not _exists(cur, "meetings", "meeting_id", meeting_id):
                    return {"error": f"Unknown meeting_id {meeting_id}."}
                if not _exists(cur, "projects", "project_id", project_id):
                    return {"error": f"Unknown project_id {project_id}."}
                if not _exists(cur, "people", "person_id", owner_person_id):
                    return {"error": f"Unknown owner_person_id {owner_person_id}."}
                vis = _row(cur, "SELECT visibility FROM meetings WHERE meeting_id = %s", (meeting_id,))
                visibility = vis["visibility"] if vis else "team"
                due_cmp = due_date[:10]
                status = "overdue" if due_cmp < now[:10] else "open"
                cur.execute(
                    """
                    INSERT INTO action_items (
                        action_id, meeting_id, project_id, owner_person_id, text, status,
                        due_date, created_at, updated_at, source_segment_id, visibility
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s)
                    """,
                    (
                        action_id,
                        meeting_id,
                        project_id,
                        owner_person_id,
                        text,
                        status,
                        due_date[:10],
                        now,
                        now,
                        visibility,
                    ),
                )
    except Exception as exc:
        return {"error": f"Postgres write failed: {exc}"}
    return {"status": "ok", "action_id": action_id, "item_status": status, "note": RDI_NOTE}


def update_action_item_status(arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
    del settings
    action_id = _require_id("action_id", arguments.get("action_id"))
    if isinstance(action_id, dict):
        return action_id
    status = str(arguments.get("status") or "").strip().lower()
    if status not in {"open", "done", "overdue"}:
        return {"error": "status must be open, done, or overdue."}
    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                if not _exists(cur, "action_items", "action_id", action_id):
                    return {"error": f"Unknown action_id {action_id}."}
                cur.execute(
                    "UPDATE action_items SET status = %s, updated_at = %s WHERE action_id = %s",
                    (status, _now(), action_id),
                )
    except Exception as exc:
        return {"error": f"Postgres write failed: {exc}"}
    return {"status": "ok", "action_id": action_id, "item_status": status, "note": RDI_NOTE}


def _validate_extraction(cur, meeting_id: str, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    cur.execute("SELECT person_id FROM people")
    people = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT segment_id FROM transcripts WHERE meeting_id = %s", (meeting_id,))
    segments = {row[0] for row in cur.fetchall()}
    accepted: list[dict[str, Any]] = []

    for kind in ("decisions", "action_items", "risks"):
        rows = payload.get(kind) or []
        if not isinstance(rows, list):
            errors.append(f"{kind} must be a list")
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{kind}[{i}] must be an object")
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                errors.append(f"{kind}[{i}].text is required")
                continue
            seg = str(row.get("source_segment_id") or "").strip()
            if not seg:
                errors.append(f"{kind}[{i}].source_segment_id is required")
                continue
            if seg not in segments:
                errors.append(f"{kind}[{i}].source_segment_id {seg} is not in this meeting")
                continue
            if kind == "action_items":
                owner = str(row.get("owner_person_id") or "").strip()
                if owner not in people:
                    errors.append(f"{kind}[{i}].owner_person_id {owner!r} is not a known person")
                    continue
                due = str(row.get("due_date") or "").strip()
                try:
                    datetime.strptime(due[:10], "%Y-%m-%d")
                except ValueError:
                    errors.append(f"{kind}[{i}].due_date is not a valid date")
                    continue
            if kind == "risks":
                sev = str(row.get("severity") or "med").lower()
                if sev not in {"low", "med", "high"}:
                    errors.append(f"{kind}[{i}].severity must be low, med, or high")
                    continue
            accepted.append({"kind": kind, **row, "source_segment_id": seg})
    return accepted, errors


def extract_from_transcript(arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
    meeting_id = _require_id("meeting_id", arguments.get("meeting_id"))
    if isinstance(meeting_id, dict):
        return meeting_id
    api_key = getattr(settings, "openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
    model = getattr(settings, "openai_chat_model", None) or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
    if not api_key:
        return {"error": "OPENAI_API_KEY is required for extract_from_transcript."}

    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                meeting = _row(
                    cur,
                    "SELECT meeting_id, project_id, visibility FROM meetings WHERE meeting_id = %s",
                    (meeting_id,),
                )
                if not meeting:
                    return {"error": f"Unknown meeting_id {meeting_id}."}
                cur.execute(
                    """
                    SELECT segment_id, start_ts, speaker_person_id, text
                    FROM transcripts WHERE meeting_id = %s ORDER BY start_ts, segment_id
                    """,
                    (meeting_id,),
                )
                segs = cur.fetchall()
                if not segs:
                    return {"error": f"No transcript segments for {meeting_id}."}
                cur.execute("SELECT person_id, name FROM people")
                people_rows = cur.fetchall()
    except Exception as exc:
        return {"error": f"Postgres read failed: {exc}"}

    transcript_blob = "\n".join(
        f"[{row[0]} {row[1]} {row[2]}] {row[3]}" for row in segs
    )
    people_blob = ", ".join(f"{p[0]}={p[1]}" for p in people_rows)
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = (
        "Extract decisions, action items, and risks from this meeting transcript. "
        "Return JSON with keys decisions, action_items, risks. Each item needs text and "
        "source_segment_id copied from the [segment_id ...] prefix. "
        "action_items also need owner_person_id (must be one of: "
        f"{people_blob}) and due_date (YYYY-MM-DD). "
        "risks need severity low|med|high. Do not invent ids.\n\n"
        f"{transcript_blob}"
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You extract structured meeting follow-ups. JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": f"LLM extraction failed: {exc}"}

    inserted: list[str] = []
    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                accepted, errors = _validate_extraction(cur, meeting_id, payload)
                if errors:
                    return {"error": "Rejected malformed extraction; nothing written.", "details": errors}
                if len(accepted) < 3:
                    return {
                        "error": "Extraction produced fewer than 3 valid items; nothing written.",
                        "accepted": len(accepted),
                    }
                stamp = datetime.now(timezone.utc).strftime("%H%M%S")
                n = 0
                for item in accepted:
                    n += 1
                    kind = item["kind"]
                    if kind == "decisions":
                        did = f"dec-x-{meeting_id}-{n}-{stamp}"
                        cur.execute(
                            """
                            INSERT INTO decisions (
                                decision_id, meeting_id, project_id, text, decided_at, status,
                                superseded_by_decision_id, source_segment_id, visibility
                            ) VALUES (%s,%s,%s,%s,%s,'active',NULL,%s,%s)
                            """,
                            (
                                did,
                                meeting_id,
                                meeting["project_id"],
                                item["text"],
                                _now()[:10],
                                item.get("source_segment_id"),
                                meeting["visibility"],
                            ),
                        )
                        inserted.append(did)
                    elif kind == "action_items":
                        aid = f"act-x-{meeting_id}-{n}-{stamp}"
                        cur.execute(
                            """
                            INSERT INTO action_items (
                                action_id, meeting_id, project_id, owner_person_id, text, status,
                                due_date, created_at, updated_at, source_segment_id, visibility
                            ) VALUES (%s,%s,%s,%s,%s,'open',%s,%s,%s,%s,%s)
                            """,
                            (
                                aid,
                                meeting_id,
                                meeting["project_id"],
                                item["owner_person_id"],
                                item["text"],
                                str(item["due_date"])[:10],
                                _now(),
                                _now(),
                                item.get("source_segment_id"),
                                meeting["visibility"],
                            ),
                        )
                        inserted.append(aid)
                    else:
                        rid = f"risk-x-{meeting_id}-{n}-{stamp}"
                        cur.execute(
                            """
                            INSERT INTO risks (
                                risk_id, project_id, meeting_id, text, severity, status,
                                source_segment_id, visibility
                            ) VALUES (%s,%s,%s,%s,%s,'open',%s,%s)
                            """,
                            (
                                rid,
                                meeting["project_id"],
                                meeting_id,
                                item["text"],
                                str(item.get("severity") or "med").lower(),
                                item.get("source_segment_id"),
                                meeting["visibility"],
                            ),
                        )
                        inserted.append(rid)
    except Exception as exc:
        return {"error": f"Postgres write failed: {exc}"}

    return {"status": "ok", "inserted_ids": inserted, "count": len(inserted), "note": RDI_NOTE}
