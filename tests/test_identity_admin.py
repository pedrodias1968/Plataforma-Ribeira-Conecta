from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from ribeira_platform.identity_admin import (
    load_request_file,
    load_revocation_request_file,
    load_role_change_request_file,
)
from ribeira_platform.identity_provisioning import ProvisioningRequestError


class IdentityAdminRequestFileTests(unittest.TestCase):
    def request_file(self, mode: int) -> Path:
        descriptor, filename = tempfile.mkstemp(prefix="ribeira-provisioning-test-")
        os.close(descriptor)
        path = Path(filename)
        path.write_text(
            json.dumps(
                {
                    "external_issuer": "https://issuer.synthetic.test/",
                    "external_subject": "provider|synthetic-test-subject",
                    "tenant_id": "00000000-0000-4000-8000-000000000001",
                    "role": "VIEWER",
                    "operator_actor": "SYSTEM_OPERATOR_TEST",
                }
            ),
            encoding="utf-8",
        )
        path.chmod(mode)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_secure_request_file_accepts_non_uuid_subject(self) -> None:
        request = load_request_file(self.request_file(0o600))
        self.assertEqual(request.role, "VIEWER")

    def test_insecure_request_file_is_rejected(self) -> None:
        with self.assertRaises(ProvisioningRequestError):
            load_request_file(self.request_file(0o644))

    def test_symbolic_link_request_file_is_rejected(self) -> None:
        target = self.request_file(0o600)
        link = target.with_name(target.name + "-link")
        link.symlink_to(target)
        self.addCleanup(link.unlink, missing_ok=True)
        with self.assertRaises(ProvisioningRequestError):
            load_request_file(link)

    def test_secure_revocation_request_requires_viewer_guardrail(self) -> None:
        path = self.request_file(0o600)
        path.write_text(
            json.dumps(
                {
                    "external_issuer": "https://issuer.synthetic.test/",
                    "external_subject": "provider|synthetic-test-subject",
                    "tenant_id": "00000000-0000-4000-8000-000000000001",
                    "expected_role": "VIEWER",
                    "operator_actor": "SYSTEM_OPERATOR_TEST",
                }
            ),
            encoding="utf-8",
        )
        request = load_revocation_request_file(path)
        self.assertEqual(request.expected_role, "VIEWER")

    def test_insecure_or_symbolic_link_revocation_request_is_rejected(self) -> None:
        insecure = self.request_file(0o644)
        insecure.write_text(
            json.dumps(
                {
                    "external_issuer": "https://issuer.synthetic.test/",
                    "external_subject": "provider|synthetic-test-subject",
                    "tenant_id": "00000000-0000-4000-8000-000000000001",
                    "expected_role": "VIEWER",
                    "operator_actor": "SYSTEM_OPERATOR_TEST",
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ProvisioningRequestError):
            load_revocation_request_file(insecure)
        target = self.request_file(0o600)
        target.write_text(insecure.read_text(encoding="utf-8"), encoding="utf-8")
        link = target.with_name(target.name + "-revoke-link")
        link.symlink_to(target)
        self.addCleanup(link.unlink, missing_ok=True)
        with self.assertRaises(ProvisioningRequestError):
            load_revocation_request_file(link)

    def role_change_file(self, expected_role: str, new_role: str, mode: int = 0o600) -> Path:
        path = self.request_file(mode)
        path.write_text(
            json.dumps(
                {
                    "external_issuer": "https://issuer.synthetic.test/",
                    "external_subject": "provider|synthetic-test-subject",
                    "tenant_id": "00000000-0000-4000-8000-000000000001",
                    "expected_role": expected_role,
                    "new_role": new_role,
                    "operator_actor": "SYSTEM_OPERATOR_TEST",
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_role_change_request_accepts_only_viewer_manager_transitions(self) -> None:
        request = load_role_change_request_file(self.role_change_file("VIEWER", "MANAGER"))
        self.assertEqual((request.expected_role, request.new_role), ("VIEWER", "MANAGER"))
        back = load_role_change_request_file(self.role_change_file("MANAGER", "VIEWER"))
        self.assertEqual(back.new_role, "VIEWER")
        for expected, new in (("VIEWER", "TENANT_ADMIN"), ("VIEWER", "VIEWER"), ("ANALYST", "MANAGER")):
            with self.assertRaises(ProvisioningRequestError):
                load_role_change_request_file(self.role_change_file(expected, new))

    def test_insecure_role_change_request_is_rejected(self) -> None:
        with self.assertRaises(ProvisioningRequestError):
            load_role_change_request_file(self.role_change_file("VIEWER", "MANAGER", 0o644))


if __name__ == "__main__":
    unittest.main()
