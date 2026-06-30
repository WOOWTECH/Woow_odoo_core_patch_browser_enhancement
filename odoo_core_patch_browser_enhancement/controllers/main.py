import json
import logging

from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin

_logger = logging.getLogger(__name__)


class OAuthLoginProxyFix(OAuthLogin):
    """Fix OAuth redirect_uri when behind a reverse proxy (e.g. Cloudflare Tunnel)
    that does not send X-Forwarded-Host header.

    Odoo's ProxyFix middleware only activates when X-Forwarded-Host is present.
    Without it, request.httprequest.url_root returns http:// even though the
    site is served over https://, causing Google OAuth redirect_uri_mismatch.

    This override uses web.base.url (from system parameters) to build the
    redirect_uri, ensuring it always matches the configured domain and scheme.
    """

    def _get_oauth_return_url(self):
        """Build OAuth return URL from web.base.url instead of request URL."""
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if base_url:
            return base_url.rstrip("/") + "/auth_oauth/signin"
        return request.httprequest.url_root + "auth_oauth/signin"

    @http.route()
    def web_login(self, *args, **kw):
        """Override to inject corrected redirect_uri into OAuth providers."""
        response = super().web_login(*args, **kw)
        if response.is_qweb:
            providers = response.qcontext.get("providers", [])
            if providers:
                return_url = self._get_oauth_return_url()
                for provider in providers:
                    if "auth_link" in provider:
                        # Replace the redirect_uri in the auth_link
                        old_link = provider["auth_link"]
                        # The auth_link contains redirect_uri=<encoded_url>
                        import urllib.parse
                        parsed = urllib.parse.urlparse(old_link)
                        params = urllib.parse.parse_qs(parsed.query)
                        if "redirect_uri" in params:
                            params["redirect_uri"] = [return_url]
                        # Also fix the state parameter's redirect URL
                        if "state" in params:
                            try:
                                state = json.loads(params["state"][0])
                                if "r" in state:
                                    base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
                                    if base_url and state["r"].startswith("http://"):
                                        state["r"] = state["r"].replace("http://", "https://", 1)
                                    params["state"] = [json.dumps(state)]
                            except (json.JSONDecodeError, KeyError):
                                pass
                        new_query = urllib.parse.urlencode(params, doseq=True)
                        provider["auth_link"] = urllib.parse.urlunparse(
                            parsed._replace(query=new_query)
                        )
                        _logger.debug(
                            "OAuth ProxyFix: rewrote redirect_uri to %s", return_url
                        )
        return response
