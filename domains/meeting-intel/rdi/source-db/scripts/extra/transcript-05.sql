-- Held-out transcript for live extraction (Section 6). Not in 01-seed.sql.
BEGIN;
INSERT INTO meetings (meeting_id, project_id, title, meeting_date, kind, status, summary, visibility)
VALUES (
  'mtg-2026-09-01-pipeline-extra', 'proj-pipeline', 'Pipeline ad-hoc extraction dry-run',
  '2026-09-01', 'sync', 'held',
  'Held-out transcript used to demo live extract_from_transcript.', 'team'
)
ON CONFLICT (meeting_id) DO NOTHING;

INSERT INTO meeting_participants (participant_id, meeting_id, person_id) VALUES
  ('part-mtg-2026-09-01-pipeline-extra-person-chris', 'mtg-2026-09-01-pipeline-extra', 'person-chris'),
  ('part-mtg-2026-09-01-pipeline-extra-person-jordan', 'mtg-2026-09-01-pipeline-extra', 'person-jordan')
ON CONFLICT (participant_id) DO NOTHING;

INSERT INTO transcripts (transcript_id, meeting_id, segment_id, start_ts, speaker_person_id, text) VALUES
  ('tr-extra-01', 'mtg-2026-09-01-pipeline-extra', 'seg-extra-01', '00:00:10', 'person-chris',
   'This is a held-out pipeline working session. We decided to delay payments CDC until PII tags ship.'),
  ('tr-extra-02', 'mtg-2026-09-01-pipeline-extra', 'seg-extra-02', '00:01:00', 'person-jordan',
   'Action: Chris will file the PII tag spreadsheet by September 12. I will warn compliance if it slips.'),
  ('tr-extra-03', 'mtg-2026-09-01-pipeline-extra', 'seg-extra-03', '00:02:10', 'person-chris',
   'Risk: if payments CDC goes live without tags we will fail the SOC2 sample.'),
  ('tr-extra-04', 'mtg-2026-09-01-pipeline-extra', 'seg-extra-04', '00:03:00', 'person-jordan',
   'Decision: do not enable the payments connector in production this month.'),
  ('tr-extra-05', 'mtg-2026-09-01-pipeline-extra', 'seg-extra-05', '00:03:40', 'person-chris',
   'I will also add a lineage stub page so extract_from_transcript has a fourth follow-up.')
ON CONFLICT (transcript_id) DO NOTHING;
COMMIT;
