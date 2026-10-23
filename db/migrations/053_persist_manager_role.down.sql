-- Never remove the MANAGER role while any membership (active or historical) uses it.
DO $$
DECLARE
  manager_role uuid := '00000000-0000-5000-8000-000000000053';
BEGIN
  IF EXISTS (SELECT 1 FROM tenant_membership WHERE role_id = manager_role) THEN
    RAISE EXCEPTION 'cannot rollback 053 while the seeded MANAGER role has memberships';
  END IF;
  IF EXISTS (SELECT 1 FROM role_permission WHERE role_id = manager_role) THEN
    RAISE EXCEPTION 'cannot rollback 053 while the seeded MANAGER role has permissions';
  END IF;
END
$$;

DELETE FROM iam_role
WHERE id = '00000000-0000-5000-8000-000000000053'
  AND code = 'MANAGER';
