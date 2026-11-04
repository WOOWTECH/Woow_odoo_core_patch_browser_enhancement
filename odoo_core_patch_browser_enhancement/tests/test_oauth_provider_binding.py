import json
from unittest.mock import patch

from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOAuthProviderBinding(TransactionCase):
    """The email fallback only works for an enabled provider the admin chose."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Provider = cls.env["auth.oauth.provider"]
        vals = {
            "client_id": "placeholder-client",
            "auth_endpoint": "https://idp.example.test/auth",
            "validation_endpoint": "https://idp.example.test/tokeninfo",
            "body": "Login",
        }
        cls.good = Provider.create(dict(vals, name="Test Good IdP", enabled=True))
        cls.weak = Provider.create(dict(vals, name="Test Weak IdP", enabled=False))
        cls.Users = cls.env["res.users"]
        cls.user = cls.Users.create({
            "name": "Provider Staff",
            "login": "provider.staff.local",
            "email": "provider.staff.local@example.test",
            "oauth_email": "staff@example.test",
            "oauth_provider_id": cls.good.id,
        })

    def _auth(self, provider, sub="sub-A", token="placeholder-token", **claims):
        rpc = {"id": sub, "email": "staff@example.test", "email_verified": True}
        rpc.update(claims)
        params = {
            "access_token": token,
            "state": json.dumps({"d": self.env.cr.dbname, "p": provider.id}),
        }
        with patch.object(type(self.Users), "_auth_oauth_rpc", return_value=rpc):
            return self.Users.with_context(no_user_creation=True).auth_oauth(
                provider.id, params
            )

    def test_disabled_provider_cannot_bind_unspecified_user(self):
        self.user.oauth_provider_id = False
        with self.assertRaises(AccessDenied):
            self._auth(self.weak)
        self.assertFalse(self.user.oauth_uid)
        self.assertFalse(self.user.oauth_provider_id)

    def test_disabled_provider_cannot_bind_even_if_preauthorised(self):
        self.user.oauth_provider_id = self.weak
        with self.assertRaises(AccessDenied):
            self._auth(self.weak)
        self.assertFalse(self.user.oauth_uid)

    def test_provider_disabled_later_stops_first_bind(self):
        self.good.enabled = False
        with self.assertRaises(AccessDenied):
            self._auth(self.good)
        self.assertFalse(self.user.oauth_uid)

    def test_designated_enabled_provider_binds(self):
        _db, login, _key = self._auth(self.good)
        self.assertEqual(login, self.user.login)
        self.assertEqual(self.user.oauth_uid, "sub-A")
        self.assertEqual(self.user.oauth_provider_id, self.good)
        # and the same identity can sign in again
        _db, login, _key = self._auth(self.good)
        self.assertEqual(login, self.user.login)

    def test_other_enabled_provider_cannot_bind(self):
        other = self.good.copy({"name": "Test Other IdP", "enabled": True})
        with self.assertRaises(AccessDenied):
            self._auth(other)
        self.assertFalse(self.user.oauth_uid)
        self.assertEqual(self.user.oauth_provider_id, self.good)
