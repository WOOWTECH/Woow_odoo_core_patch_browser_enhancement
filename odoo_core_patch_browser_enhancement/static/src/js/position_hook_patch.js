/** @odoo-module */
/**
 * position_hook Cleanup Patch
 *
 * Fixes: Missing cleanup for throttled onLayoutGeometryChange function
 * Impact: Ensures complete cleanup of animation frame callbacks in hooks
 *
 * Note: This is lower priority as OWL's useEffect handles cleanup differently,
 * but included for completeness and defensive programming.
 *
 * Bug Report: RESEARCH_REPORT_Safari_OWL_Bug.md (Related Files Audit)
 * PRD Reference: FR3 (P2 - OPTIONAL)
 */

/**
 * Note on Hook Patching:
 *
 * Unlike class methods, ES modules export functions that are harder to patch:
 * - Module exports are typically frozen
 * - Odoo's module system has specific import resolution
 * - Hooks use closures that capture references at definition time
 *
 * This file serves as documentation for the recommended fix.
 * For production, consider submitting the fix upstream to Odoo.
 */

/*
 * RECOMMENDED MANUAL FIX (if needed):
 *
 * In odoo/addons/html_editor/static/src/position_hook.js, modify the cleanup:
 *
 * return () => {
 *     onLayoutGeometryChange?.cancel?.();  // ADD THIS LINE
 *     resizeObserver.disconnect();
 *     for (const cleanup of cleanups.toReversed()) {
 *         cleanup();
 *         cleanups.pop();
 *     }
 * };
 */

console.debug(
    "[odoo_core_patch_browser_enhancement] position_hook_patch loaded. " +
    "Note: Hook patching is limited; see comments for manual fix if needed."
);
