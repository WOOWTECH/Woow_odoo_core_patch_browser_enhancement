import json
import logging

from odoo import api, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsersOAuthFallback(models.Model):
    _inherit = "res.users"

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """Override to add email-based fallback for existing users.

        When oauth_uid does not match any user, try matching by login
        or email and auto-link the OAuth provider to the existing user.
        """
        oauth_uid = validation["user_id"]
        try:
            oauth_user = self.search([
                ("oauth_uid", "=", oauth_uid),
                ("oauth_provider_id", "=", provider),
            ])
            if not oauth_user:
                raise AccessDenied()
            assert len(oauth_user) == 1
            oauth_user.write({"oauth_access_token": params["access_token"]})
            return oauth_user.login
        except AccessDenied:
            # Fallback: match by login OR email and auto-link OAuth
            email = validation.get("email")
            if email:
                existing = self.search([
                    "|",
                    ("login", "=", email),
                    ("email", "=", email),
                ], limit=1)
                if existing:
                    existing.write({
                        "oauth_provider_id": provider,
                        "oauth_uid": oauth_uid,
                        "oauth_access_token": params["access_token"],
                    })
                    _logger.info(
                        "OAuth: linked existing user %s (login=%s) to provider %s (uid=%s)",
                        email, existing.login, provider, oauth_uid,
                    )
                    return existing.login

            # No email match - try original signup flow
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
