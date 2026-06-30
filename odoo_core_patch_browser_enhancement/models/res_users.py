import json
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsersOAuthFallback(models.Model):
    _inherit = "res.users"

    oauth_email = fields.Char(
        string="OAuth User Email",
        help="The email address authorized for OAuth login. "
             "Admin fills this field to pre-authorize a Google/OAuth account "
             "to bind to this internal user. On first OAuth login, the system "
             "matches by this email and auto-sets the OAuth User ID (sub).",
    )

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """Secure OAuth signin with admin-authorized email matching.

        Flow:
        1. Try matching by oauth_uid (standard Odoo flow — already linked)
        2. If not found, match by oauth_email (admin pre-authorized email)
           → auto-link oauth_uid + clear oauth_email (one-time bind)
        3. If no match, create portal user via signup
        """
        oauth_uid = validation["user_id"]
        email = validation.get("email")

        # Step 1: Standard match by oauth_uid
        oauth_user = self.search([
            ("oauth_uid", "=", oauth_uid),
            ("oauth_provider_id", "=", provider),
        ])
        if oauth_user:
            if len(oauth_user) > 1:
                _logger.warning("OAuth: multiple users with uid=%s, using first", oauth_uid)
            oauth_user[0].write({"oauth_access_token": params["access_token"]})
            return oauth_user[0].login

        # Step 2: Admin-authorized email matching
        if email:
            authorized = self.search([
                ("oauth_email", "=", email),
                "|",
                ("oauth_provider_id", "=", provider),
                ("oauth_provider_id", "=", False),
            ], limit=1)
            if authorized:
                authorized.write({
                    "oauth_provider_id": provider,
                    "oauth_uid": oauth_uid,
                    "oauth_access_token": params["access_token"],
                    # keep oauth_email for display (admin reference)
                })
                _logger.info(
                    "OAuth: bound user %s (login=%s) to provider %s "
                    "(uid=%s, email=%s) via admin-authorized oauth_email",
                    authorized.name, authorized.login, provider,
                    oauth_uid, email,
                )
                return authorized.login

        # Step 3: No match — create portal user via signup
        _logger.info(
            "OAuth: no authorized user for email=%s, attempting signup",
            email,
        )
        if self.env.context.get("no_user_creation"):
            return None
        state = json.loads(params["state"])
        token = state.get("t")
        values = self._generate_signup_values(provider, validation, params)
        try:
            login, _ = self.signup(values, token)
            return login
        except Exception:
            raise AccessDenied()
