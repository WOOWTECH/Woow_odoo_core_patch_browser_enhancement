/** @odoo-module */
/**
 * PositionPlugin.destroy() Patch
 *
 * Fixes: Missing cleanup for throttled layoutGeometryChange function
 * Impact: Prevents memory leaks and orphaned animation frame callbacks
 *
 * Bug Report: RESEARCH_REPORT_Safari_OWL_Bug.md (Related Files Audit)
 * PRD Reference: FR2 (P1 - RECOMMENDED)
 */

import { PositionPlugin } from "@html_editor/main/position_plugin";
import { patch } from "@web/core/utils/patch";

patch(PositionPlugin.prototype, {
    /**
     * Override destroy() to add missing cleanup for throttled function.
     * Uses double optional chaining (?.) to safely handle cases where
     * setup() didn't complete or layoutGeometryChange wasn't created.
     */
    destroy() {
        // FIX: Add cleanup for throttled function
        // Original code was missing this cancel() call
        this.layoutGeometryChange?.cancel?.();

        // Original PositionPlugin.destroy() logic
        this.resizeObserver.disconnect();

        // Replicate base Plugin.destroy() behavior
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    },
});
