import os
import unittest

os.environ.setdefault(
    "AZURE_OPENAI_ENDPOINT",
    "https://example.cognitiveservices.azure.com/",
)
os.environ.setdefault("AZURE_OPENAI_KEY", "test-key")

from app.config import settings
from app.user_auth import _identity_from_claims


class UserAuthTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "AUTH_ISSUER": settings.AUTH_ISSUER,
            "AUTH_POLICY": settings.AUTH_POLICY,
            "AUTH_TENANT_ID": settings.AUTH_TENANT_ID,
        }
        settings.AUTH_ISSUER = "https://example.b2clogin.com/tenant/v2.0/"
        settings.AUTH_POLICY = "B2C_1_SUSI"
        settings.AUTH_TENANT_ID = "tenant-id"

    def tearDown(self):
        for name, value in self.original.items():
            setattr(settings, name, value)

    def test_accepts_expected_b2c_issuer_policy_and_scope(self):
        identity = _identity_from_claims({
            "iss": "https://example.b2clogin.com/tenant/v2.0/",
            "tfp": "b2c_1_susi",
            "scp": "access_as_user",
            "oid": "customer-object-id",
            "emails": ["customer@example.com"],
        })

        self.assertEqual(identity.memory_scope, "entra:tenant-id:customer-object-id")
        self.assertEqual(identity.display_name, "customer@example.com")

    def test_rejects_token_from_another_user_flow(self):
        with self.assertRaisesRegex(ValueError, "unexpected user flow"):
            _identity_from_claims({
                "iss": "https://example.b2clogin.com/tenant/v2.0/",
                "tfp": "B2C_1_OTHER",
                "scp": "access_as_user",
                "sub": "customer-subject",
            })


if __name__ == "__main__":
    unittest.main()
