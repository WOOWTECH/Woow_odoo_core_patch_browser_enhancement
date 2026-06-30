{
    "name": "Core Patch: Browser Enhancement + OAuth Fallback",
    "summary": "Safari HTML editor fix + OAuth email-based login fallback for Odoo 18",
    "description": """
Two production patches for Odoo 18:

1. Safari HTML Editor Bug Fix — Three JS Owl patches that eliminate race conditions
   in the html_editor overlay/position subsystem, preventing crashes on Safari/WebKit
   when the editor component is destroyed while async events are still firing.

2. OAuth Email Fallback — Python override of _auth_oauth_signin that auto-links an
   existing local Odoo user to an OAuth provider (Google, Azure AD, etc.) by matching
   email address on first OAuth login. Eliminates the "user not found" error for
   pre-existing accounts without requiring admin to manually set oauth_uid.
    """,
    "author": "WoowTech",
    "website": "https://woowtech.io",
    "category": "Technical",
    "version": "18.0.1.2.0",
    "depends": ["auth_oauth", "web"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_core_patch_browser_enhancement/static/src/js/overlay_plugin_patch.js",
            "odoo_core_patch_browser_enhancement/static/src/js/position_hook_patch.js",
            "odoo_core_patch_browser_enhancement/static/src/js/position_plugin_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
