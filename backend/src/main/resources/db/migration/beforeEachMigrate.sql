-- Normalize the generated PostgreSQL constraint name on fresh V1 databases.
-- Existing Alembic databases already use the name expected by V3.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = to_regclass('device_actions')
          AND conname = 'device_actions_target_check'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = to_regclass('device_actions')
          AND conname = 'ck_device_actions_target'
    ) THEN
        ALTER TABLE device_actions RENAME CONSTRAINT device_actions_target_check
            TO ck_device_actions_target;
    END IF;
END $$;
