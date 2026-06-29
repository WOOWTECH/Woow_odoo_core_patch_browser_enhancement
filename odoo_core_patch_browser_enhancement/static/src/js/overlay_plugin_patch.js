/** @odoo-module */
/**
 * OverlayPlugin.destroy() Patch
 *
 * Fixes: TypeError when throttledUpdateContainer is undefined
 * Root Cause: destroy() called before setup() completes
 * Affected Browsers: Safari (especially incognito), all browsers under race conditions
 *
 * Bug Report: RESEARCH_REPORT_Safari_OWL_Bug.md
 * PRD Reference: FR1 (P0 - CRITICAL)
 */

import { OverlayPlugin } from "@html_editor/core/overlay_plugin";
import { patch } from "@web/core/utils/patch";

patch(OverlayPlugin.prototype, {
    /**
     * Override destroy() to add defensive null check.
     * Uses optional chaining (?.) to prevent TypeError when
     * throttledUpdateContainer is undefined.
     */
    destroy() {
        // FIX: Add optional chaining to prevent crash
        // Original: this.throttledUpdateContainer.cancel();
        this.throttledUpdateContainer?.cancel();

        // Replicate base Plugin.destroy() behavior
        // (Cannot use super.destroy() in patch context)
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;

        // Close all overlays (original OverlayPlugin behavior)
        for (const overlay of this.overlays) {
            overlay.close();
        }
    },
});
