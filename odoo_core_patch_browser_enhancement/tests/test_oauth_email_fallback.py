from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOAuthEmailFallback(TransactionCase):
    """Email fallback of _auth_oauth_signin: verified, one-time, same provider."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Provider = cls.env["auth.oauth.provider"]
        cls.p1 = Provider.create({
            "name": "Test Google",
            "client_id": "placeholder-client-1",
            "auth_endpoint": "https://idp1.example.test/auth",
            "validation_endpoint": "https://idp1.example.test/tokeninfo",
            "body": "Login",
            "enabled": True,
        })
        cls.p2 = Provider.create({
            "name": "Test Other",
            "client_id": "placeholder-client-2",
            "auth_endpoint": "https://idp2.example.test/auth",
            "validation_endpoint": "https://idp2.example.test/tokeninfo",
            "body": "Login",
            "enabled": True,
        })
        cls.user = cls.env["res.users"].create({
            "name": "Sweep Staff",
            "login": "sweep.staff.local",
            "email": "sweep.staff.local@example.test",
            "oauth_email": "staff@example.test",
            "oauth_provider_id": cls.p1.id,
        })

    def _validation(self, sub, email="staff@example.test", **extra):
        val = {"user_id": sub, "email": email, "email_verified": True}
        val.update(extra)
        return val

    def _signin(self, provider, validation, token="placeholder-token", no_creation=True):
        Users = self.env["res.users"]
        if no_creation:
            Users = Users.with_context(no_user_creation=True)
        return Users._auth_oauth_signin(
            provider.id, validation, {"access_token": token, "state": "{}"}
        )

    # --- positive controls -------------------------------------------------
    def test_first_verified_login_binds_once(self):
        login = self._signin(self.p1, self._validation("sub-A"))
        self.assertEqual(login, self.user.login)
        self.assertEqual(self.user.oauth_uid, "sub-A")
        self.assertEqual(self.user.oauth_provider_id, self.p1)
        # the very same identity logs in again through the standard path
        login = self._signin(self.p1, self._validation("sub-A"), token="placeholder-2")
        self.assertEqual(login, self.user.login)
        self.assertEqual(self.user.oauth_uid, "sub-A")

    def test_existing_binding_still_logs_in(self):
        self.user.write({"oauth_uid": "sub-A", "oauth_email": False})
        login = self._signin(
            self.p1, {"user_id": "sub-A"}  # no email claim at all is fine
        )
        self.assertEqual(login, self.user.login)

    def test_verified_email_claim_string_true(self):
        login = self._signin(
            self.p1, self._validation("sub-A", email_verified="true")
        )
        self.assertEqual(login, self.user.login)

    def test_case_insensitive_email(self):
        login = self._signin(self.p1, self._validation("sub-A", email="Staff@Example.TEST"))
        self.assertEqual(login, self.user.login)
        self.assertEqual(self.user.oauth_uid, "sub-A")

    # --- findings ---------------------------------------------------------
    def test_unverified_email_not_bound(self):
        for flag in (False, "false", None, ""):
            login = self._signin(self.p1, self._validation("sub-X", email_verified=flag))
            self.assertFalse(login)
            self.assertFalse(self.user.oauth_uid)

    def test_missing_verified_claim_not_bound(self):
        login = self._signin(self.p1, {"user_id": "sub-X", "email": "staff@example.test"})
        self.assertFalse(login)
        self.assertFalse(self.user.oauth_uid)

    def test_no_rebind_after_first_bind(self):
        self.assertEqual(self._signin(self.p1, self._validation("sub-A")), self.user.login)
        login = self._signin(self.p1, self._validation("sub-B"), token="placeholder-evil")
        self.assertFalse(login)
        self.assertEqual(self.user.oauth_uid, "sub-A")
        self.assertNotEqual(self.user.oauth_access_token, "placeholder-evil")

    def test_no_rebind_when_signup_allowed(self):
        # same login as the claimed email: core signup cannot take it over
        self.user.login = "staff@example.test"
        self._signin(self.p1, self._validation("sub-A"))
        try:
            login = self._signin(self.p1, self._validation("sub-B"), no_creation=False)
        except AccessDenied:
            login = None
        self.assertFalse(login)
        self.assertEqual(self.user.oauth_uid, "sub-A")

    def test_other_provider_cannot_bind(self):
        login = self._signin(self.p2, self._validation("sub-X"))
        self.assertFalse(login)
        self.assertFalse(self.user.oauth_uid)

    def test_user_without_provider_not_bound(self):
        self.user.oauth_provider_id = False
        login = self._signin(self.p1, self._validation("sub-X"))
        self.assertFalse(login)
        self.assertFalse(self.user.oauth_uid)

    def test_no_alias_or_wildcard_match(self):
        for email in ("staff+x@example.test", "staff@example.test.evil.test",
                      "st_ff@example.test", "%@example.test"):
            login = self._signin(self.p1, self._validation("sub-X", email=email))
            self.assertFalse(login, email)
        self.assertFalse(self.user.oauth_uid)

    def test_underscore_in_email_is_literal(self):
        self.user.oauth_email = "first_last@example.test"
        self.assertFalse(
            self._signin(self.p1, self._validation("sub-X", email="firstXlast@example.test"))
        )
        self.assertEqual(
            self._signin(self.p1, self._validation("sub-A", email="first_last@example.test")),
            self.user.login,
        )
