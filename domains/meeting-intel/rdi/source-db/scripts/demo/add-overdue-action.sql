-- Live CDC beat: insert a new overdue Platform action visible via RDI within seconds.
INSERT INTO action_items (
  action_id, meeting_id, project_id, owner_person_id, text, status,
  due_date, created_at, updated_at, source_segment_id, visibility
) VALUES (
  'act-cdc-live-overdue',
  'mtg-2026-09-04-platform',
  'proj-platform',
  'person-maya',
  'CDC demo: page SRE about dual-write lag before the next Platform weekly.',
  'overdue',
  '2026-09-06',
  NOW(),
  NOW(),
  NULL,
  'team'
)
ON CONFLICT (action_id) DO UPDATE SET
  status = EXCLUDED.status,
  updated_at = NOW(),
  text = EXCLUDED.text;
