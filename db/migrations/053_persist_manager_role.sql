-- Persist the MANAGER role with a deterministic key so an audited operator
-- command can move a validation membership from VIEWER to MANAGER.
-- Permissions stay defined in code (ribeira_platform.iam.ROLE_PERMISSIONS);
-- an existing role with the same code is never replaced.
INSERT INTO iam_role (id, code, description)
VALUES ('00000000-0000-5000-8000-000000000053', 'MANAGER', 'Tenant manager (operational and financial records)')
ON CONFLICT (code) DO NOTHING;
