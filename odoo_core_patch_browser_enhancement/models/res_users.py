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
             "Admin fills this field (and the OAuth Provider) to pre-authorize a Google/OAuth account "
             "to bind to this internal user. On first OAuth login, the system "
             "matches by this email and auto-sets the OAuth User ID (sub).",
    )

    @api.model
    def _oauth_email_is_verified(self, validation):
        """True only if the provider explicitly asserts the email is verified.

        Google uses ``email_verified`` (OIDC / tokeninfo v3) or ``verified_email``
        (userinfo v2); values may be bool or the strings "true"/"false".
        """
        for key in ("email_verified", "verified_email"):
            if key in validation:
                return str(validation[key]).strip().lower() == "true"
        return False

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """Secure OAuth signin with admin-authorized email matching.

        Flow:
        1. Try matching by oauth_uid (standard Odoo flow — already linked)
        2. If not found and the provider says the email is verified, match by
           oauth_email (admin pre-authorized email, same provider, no oauth_uid
           yet) → auto-link oauth_uid (one-time bind, never rebinds)
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

        # Step 2: Admin-authorized email matching (one-time bind).
        # Only when the provider asserts the email is verified, and only for a
        # user of this provider that has no oauth_uid yet. Never rebinds.
        if email and self._oauth_email_is_verified(validation):
            wanted = email.strip().lower()
            candidates = self.search([
                ("oauth_email", "!=", False),
                ("oauth_provider_id", "=", provider),
            ]).filtered(lambda u: (u.oauth_email or "").strip().lower() == wanted)
            authorized = candidates.filtered(lambda u: not u.oauth_uid)
            if len(candidates) == 1 and authorized:
                authorized.write({
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
            if candidates:
                _logger.warning(
                    "OAuth: email fallback refused for provider %s (email=%s): "
                    "already bound or ambiguous match",
                    provider, email,
                )

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
