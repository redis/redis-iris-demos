-- Meeting-intel schema. Run before 01-seed.sql.
-- The debezium/postgres image already sets wal_level=logical.

CREATE TABLE IF NOT EXISTS people (
  person_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  team TEXT NOT NULL,
  email TEXT NOT NULL,
  access_role TEXT NOT NULL CHECK (access_role IN ('team', 'leadership'))
);

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  team TEXT NOT NULL,
  lead_person_id TEXT NOT NULL REFERENCES people(person_id),
  target_date DATE NOT NULL,
  summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meetings (
  meeting_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  title TEXT NOT NULL,
  meeting_date DATE NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('sync', 'steering', 'retro')),
  status TEXT NOT NULL CHECK (status IN ('held', 'upcoming')),
  summary TEXT NOT NULL,
  visibility TEXT NOT NULL CHECK (visibility IN ('team', 'leadership', 'all'))
);

CREATE TABLE IF NOT EXISTS meeting_participants (
  participant_id TEXT PRIMARY KEY,
  meeting_id TEXT NOT NULL REFERENCES meetings(meeting_id) ON DELETE CASCADE,
  person_id TEXT NOT NULL REFERENCES people(person_id),
  UNIQUE (meeting_id, person_id)
);

CREATE TABLE IF NOT EXISTS transcripts (
  transcript_id TEXT PRIMARY KEY,
  meeting_id TEXT NOT NULL REFERENCES meetings(meeting_id) ON DELETE CASCADE,
  segment_id TEXT NOT NULL,
  start_ts TEXT NOT NULL,
  speaker_person_id TEXT NOT NULL REFERENCES people(person_id),
  text TEXT NOT NULL,
  UNIQUE (meeting_id, segment_id)
);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY,
  meeting_id TEXT NOT NULL REFERENCES meetings(meeting_id),
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  text TEXT NOT NULL,
  decided_at DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'superseded')),
  superseded_by_decision_id TEXT REFERENCES decisions(decision_id),
  source_segment_id TEXT,
  visibility TEXT NOT NULL CHECK (visibility IN ('team', 'leadership', 'all'))
);

CREATE TABLE IF NOT EXISTS action_items (
  action_id TEXT PRIMARY KEY,
  meeting_id TEXT NOT NULL REFERENCES meetings(meeting_id),
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  owner_person_id TEXT NOT NULL REFERENCES people(person_id),
  text TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'done', 'overdue')),
  due_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  source_segment_id TEXT,
  visibility TEXT NOT NULL CHECK (visibility IN ('team', 'leadership', 'all'))
);

CREATE TABLE IF NOT EXISTS risks (
  risk_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  meeting_id TEXT NOT NULL REFERENCES meetings(meeting_id),
  text TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'med', 'high')),
  status TEXT NOT NULL CHECK (status IN ('open', 'mitigated')),
  source_segment_id TEXT,
  visibility TEXT NOT NULL CHECK (visibility IN ('team', 'leadership', 'all'))
);

CREATE TABLE IF NOT EXISTS project_dependencies (
  dependency_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  depends_on_project_id TEXT NOT NULL REFERENCES projects(project_id),
  description TEXT NOT NULL,
  blocking BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS agendas (
  agenda_id TEXT PRIMARY KEY,
  meeting_id TEXT NOT NULL UNIQUE REFERENCES meetings(meeting_id),
  human_agenda TEXT NOT NULL,
  ai_agenda TEXT,
  ai_agenda_sources JSONB,
  generated_at TIMESTAMPTZ,
  generated_by TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft', 'approved')),
  visibility TEXT NOT NULL CHECK (visibility IN ('team', 'leadership', 'all'))
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dbzuser') THEN
    CREATE ROLE dbzuser WITH REPLICATION LOGIN PASSWORD 'dbz';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO dbzuser;
GRANT USAGE ON SCHEMA public TO dbzuser;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbzuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dbzuser;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'meeting_intel_pub') THEN
    CREATE PUBLICATION meeting_intel_pub FOR TABLE
      people, projects, meetings, meeting_participants, transcripts,
      decisions, action_items, risks, project_dependencies, agendas;
  END IF;
END
$$;
