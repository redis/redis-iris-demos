-- Live CDC beat: mark the demo action done so the agent's answer changes.
UPDATE action_items
SET status = 'done', updated_at = NOW()
WHERE action_id = 'act-cdc-live-overdue';
