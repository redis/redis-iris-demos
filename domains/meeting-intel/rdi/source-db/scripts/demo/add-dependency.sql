-- Live CDC beat: add a non-blocking extra dependency for the demo.
INSERT INTO project_dependencies (
  dependency_id, project_id, depends_on_project_id, description, blocking
) VALUES (
  'dep-cdc-portal-pipeline',
  'proj-portal',
  'proj-pipeline',
  'CDC demo: portal analytics also waits on the warehouse stream.',
  FALSE
)
ON CONFLICT (dependency_id) DO UPDATE SET description = EXCLUDED.description;
