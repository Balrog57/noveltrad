/**
 * Pre-flight Zone - renders the pre-launch advice under the Start button.
 *
 * preflight-rules.js decides *what* to advise; this module owns how it looks and
 * what a click does. Rules arrive as i18n keys only, so every visible string is
 * resolved with t() inside the render pass — that, plus the `localeChanged`
 * listener, is what makes the zone repaint in the new language with no reload.
 *
 * #preflightPanel hosts the five per-run options (bilingual, plain text, OCR
 * cleanup, glossary, custom instructions). They are static markup owned by the
 * template, so this module only expands/collapses the panel and locks it while a
 * translation is running — it never rebuilds the controls.
 */

import { DomHelpers } from './dom-helpers.js';
import { StateManager } from '../core/state-manager.js';
import { t } from '../i18n/i18n.js';
import { buildContext, evaluateRules } from './preflight-rules.js';
import { focusElement, navigateToSetting, registerPanelOpener, WATCHED_IDS } from './settings-summary.js';

const STORAGE_KEY = 'tbl_preflight_dismissed_v1';
const PANEL_STATE_KEY = 'ui.isPreflightPanelOpen';

// Marks the controls *this module* disabled when the run lock came on, so
// unlocking restores each one instead of blanket-enabling. Preferred over a
// WeakMap because the flag lives on the element: no parallel structure to keep
// in sync, and the lock state is visible in devtools.
const LOCK_FLAG = 'data-preflight-locked';

// Only keys here, never resolved text: caching a t() result at module scope
// would freeze the label at boot and break the locale switch.
const TOGGLE_LABEL_KEYS = {
    open: 'translation:preflight_collapse',
    closed: 'translation:preflight_adjust',
};

// The rules currently on screen, so the delegated click handler can recover the
// rule behind a chip without re-evaluating the context.
let visibleRules = new Map();
let pendingRefresh = null;

// The panel help line is transient — it explains the advice the user just acted
// on, or the run lock. Its key is kept here rather than its text so every
// repaint re-resolves it in the current locale.
let helpState = null;

// Exported: shared with preflight-modal.js, which must read the same store.
export function loadDismissed() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed.filter(id => typeof id === 'string') : [];
    } catch {
        return [];
    }
}

function saveDismissed(ids) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch {
        /* ignore quota errors */
    }
}

// The only writer of the dismissal store. The chips in this zone are the sole
// place a tip can be suppressed for good; preflight-modal.js only reads it.
function dismissRule(id) {
    if (!id) return;
    const ids = loadDismissed();
    if (ids.includes(id)) return;
    ids.push(id);
    saveDismissed(ids);
}

function clearDismissed() {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch {
        /* ignore */
    }
}

function renderWarningCard(rule) {
    // t() output carries a model name, a language and a file extension, all
    // user-influenced.
    const reason = DomHelpers.escapeHtml(t(rule.reasonKey, rule.params));
    const label = DomHelpers.escapeHtml(t(rule.labelKey, rule.params));
    // 'danger' outranks 'warning': the run is misconfigured rather than risky,
    // so the card wears the same brick red as the destructive buttons.
    const variant = rule.severity === 'danger' ? ' preflight-warning--danger' : '';

    return `<div class="preflight-warning${variant}">`
        + `<span>${reason}</span>`
        + `<button type="button" class="preflight-warning__action"`
        + ` data-preflight-action="${DomHelpers.escapeHtml(rule.id)}">${label}</button>`
        + `</div>`;
}

// One card per non-advice rule rather than the single highest one: a same-language
// run and a small-model-on-tagged-file run can apply at once, and each names a
// different control to fix.
function renderWarnings(rules) {
    const container = DomHelpers.getElement('preflightWarning');
    if (!container) return;

    if (!rules.length) {
        container.innerHTML = '';
        container.hidden = true;
        return;
    }

    container.innerHTML = rules.map(renderWarningCard).join('');
    container.hidden = false;
}

function renderChip(rule, dismissTip) {
    const id = DomHelpers.escapeHtml(rule.id);
    const label = DomHelpers.escapeHtml(t(rule.labelKey, rule.params));
    const reason = DomHelpers.escapeHtml(t(rule.reasonKey, rule.params));

    // The pill is a <span>, not a <button>: a button may not contain the dismiss
    // button, and the parser would close the outer one early.
    return `<span class="preflight-chip">`
        + `<button type="button" class="preflight-chip__body"`
        + ` data-preflight-action="${id}" title="${reason}">+ ${label}</button>`
        + `<button type="button" class="preflight-chip__dismiss"`
        + ` data-preflight-dismiss="${id}" aria-label="${dismissTip}" title="${dismissTip}">`
        + `&times;</button>`
        + `</span>`;
}

function renderAdvice(rules) {
    const container = DomHelpers.getElement('preflightAdvice');
    if (!container) return;

    if (!rules.length) {
        container.innerHTML = '';
        container.hidden = true;
        return;
    }

    const dismissTip = DomHelpers.escapeHtml(t('translation:preflight_dismiss_tip'));
    const caption = DomHelpers.escapeHtml(t('translation:preflight_advised_label'));
    container.innerHTML = `<span class="preflight-advice__label">${caption}</span>`
        + rules.map(rule => renderChip(rule, dismissTip)).join('');
    container.hidden = false;
}

function renderDismissedLink(count) {
    const link = DomHelpers.getElement('preflightDismissedLink');
    if (!link) return;

    if (!count) {
        link.innerHTML = '';
        link.hidden = true;
        return;
    }
    link.innerHTML = DomHelpers.escapeHtml(t('translation:preflight_show_dismissed', { count }));
    link.hidden = false;
}

function renderPanelHelp() {
    const help = DomHelpers.getElement('preflightPanelHelp');
    if (!help) return;
    help.textContent = helpState ? t(helpState.key, helpState.params) : '';
    // Hidden rather than merely emptied: the element lives in the zone, not in
    // the panel, so an empty paragraph would still contribute its top margin.
    help.hidden = !helpState;
}

/**
 * Set (or clear, with a null key) the contextual line under the zone. It sits
 * outside #preflightPanel so the run-lock message survives the panel collapsing.
 * @param {string|null} key - i18n key, 'ns:key' form
 * @param {Object} [params] - interpolation params
 */
function setPanelHelp(key, params) {
    helpState = key ? { key, params: params || {} } : null;
    renderPanelHelp();
}

/**
 * Expand or collapse #preflightPanel.
 * Never short-circuits on the run lock: an explicit open must still work while a
 * translation is running, so the fallback recommendation panel can reach the
 * control it advises about (read-only, since the control itself is disabled).
 * @param {boolean} open - Target state
 */
function setPanelOpen(open) {
    const panel = DomHelpers.getElement('preflightPanel');
    const toggle = DomHelpers.getElement('preflightToggle');

    if (panel) panel.hidden = !open;

    if (toggle) {
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        // The chevron rotation is keyed off aria-expanded in the stylesheet, so
        // there is deliberately no style.transform written from here.
        const label = toggle.querySelector('[data-i18n]');
        if (label) {
            // The label alternates between two keys, so its data-i18n attribute
            // has to follow: applyToDOM() re-reads that attribute on a locale
            // switch and would otherwise restore the other key's text.
            const key = open ? TOGGLE_LABEL_KEYS.open : TOGGLE_LABEL_KEYS.closed;
            label.setAttribute('data-i18n', key);
            label.textContent = t(key);
        }
    }

    if (!open) setPanelHelp(null);

    StateManager.setState(PANEL_STATE_KEY, open);
}

function panelControls() {
    const panel = DomHelpers.getElement('preflightPanel');
    return panel ? Array.from(panel.querySelectorAll('input, select, textarea, button')) : [];
}

function disableForLock(el) {
    if (!el || el.disabled) return;   // already disabled for another reason
    el.disabled = true;
    el.setAttribute(LOCK_FLAG, '');
}

function applyLock(locked) {
    const zone = DomHelpers.getElement('preflightZone');
    const toggle = DomHelpers.getElement('preflightToggle');

    if (locked) {
        if (zone) zone.classList.add('preflight-zone--locked');
        setPanelOpen(false);
        disableForLock(toggle);
        panelControls().forEach(disableForLock);
        setPanelHelp('translation:preflight_locked');
        return;
    }

    if (zone) zone.classList.remove('preflight-zone--locked');
    const scope = zone || document;
    scope.querySelectorAll(`[${LOCK_FLAG}]`).forEach(el => {
        el.disabled = false;
        el.removeAttribute(LOCK_FLAG);
    });
    if (helpState && helpState.key === 'translation:preflight_locked') {
        setPanelHelp(null);
    }
}

function refresh() {
    const dismissed = loadDismissed();
    const rules = evaluateRules(buildContext())
        .filter(rule => !dismissed.includes(rule.id));

    visibleRules = new Map(rules.map(rule => [rule.id, rule]));

    renderWarnings(rules.filter(rule => rule.severity !== 'advice'));
    renderAdvice(rules.filter(rule => rule.severity === 'advice'));
    renderDismissedLink(dismissed.length);
    // Re-resolved here too: `localeChanged` routes through this function, and the
    // help line is JS-owned text with no data-i18n attribute of its own.
    renderPanelHelp();
}

// Repaints are coalesced onto a macrotask for two reasons. A single provider
// change fans out into several of the watched signals, and provider-manager.js
// registers its own `llmProvider` change listener *after* this module (see the
// init order in index.js) — so reading #parallelWorkersGroup synchronously would
// still see the previous provider's visibility. Yielding one task lets every
// listener for the same event settle first. Nothing is scheduled unless a signal
// actually fired, so this is a coalescer, not a polling loop.
function scheduleRefresh() {
    if (pendingRefresh !== null) return;
    pendingRefresh = setTimeout(() => {
        pendingRefresh = null;
        refresh();
    }, 0);
}

// Exported: shared with preflight-modal.js, which routes its Adjust button here.
export function actOnRule(rule) {
    if (!rule) return;

    if (rule.action === 'navigate') {
        navigateToSetting(rule.navigateKey);
        return;
    }

    // expandPanel: the control lives in this very panel, so there is no tab to
    // switch — expand in place, explain why, then reveal the control.
    setPanelOpen(true);
    setPanelHelp(rule.reasonKey, rule.params);
    focusElement(rule.focusId);
}

// One delegated listener on #preflightZone: the warning and advice containers are
// rewritten wholesale on every refresh(), so per-element listeners would leak a
// new closure per repaint. Clicks on #settingsSummary bubble through here too,
// but they carry data-summary-action and match none of the selectors below.
function handleClick(event) {
    const dismiss = event.target.closest('[data-preflight-dismiss]');
    if (dismiss) {
        // Keep the chip's own action from firing on top of the dismissal.
        event.stopPropagation();
        dismissRule(dismiss.getAttribute('data-preflight-dismiss'));
        refresh();
        return;
    }

    if (event.target.closest('#preflightDismissedLink')) {
        clearDismissed();
        refresh();
        return;
    }

    const toggle = event.target.closest('#preflightToggle');
    if (toggle) {
        setPanelOpen(toggle.getAttribute('aria-expanded') !== 'true');
        return;
    }

    const action = event.target.closest('[data-preflight-action]');
    if (action) {
        actOnRule(visibleRules.get(action.getAttribute('data-preflight-action')));
    }
}

export const PreflightZone = {
    /**
     * Wire listeners and do a first render. Called from index.js right after
     * SettingsSummary.initialize(), whose WATCHED_IDS this module reuses.
     */
    initialize() {
        for (const id of WATCHED_IDS) {
            const el = DomHelpers.getElement(id);
            if (!el) continue;
            el.addEventListener('change', scheduleRefresh);
            // Free-text controls (the custom language fields) only fire `change`
            // on blur, which would leave the same-language warning a beat behind
            // the settings summary right above it.
            if (el.tagName === 'INPUT' && el.type === 'text') {
                el.addEventListener('input', scheduleRefresh);
            }
        }

        // parallelWorkers is not in WATCHED_IDS (it is .env-backed, so the
        // summary never shows it). `input` rather than `change` so the advice
        // clears while the user is still adjusting the value.
        const parallel = DomHelpers.getElement('parallelWorkers');
        if (parallel) parallel.addEventListener('input', scheduleRefresh);

        // Several dropdowns are populated asynchronously and never fire a native
        // change event; these are the signals they emit instead.
        window.addEventListener('modelChanged', scheduleRefresh);
        window.addEventListener('customInstructionsLoaded', scheduleRefresh);
        window.addEventListener('fileListChanged', scheduleRefresh);
        window.addEventListener('localeChanged', scheduleRefresh);
        // The per-file language dropdowns in the Selected file card are the second
        // place a run's languages can be set, and they write straight to the file
        // object: no form control changes, so none of the WATCHED_IDS listeners
        // above ever fire. This is the signal _updateFileField() emits instead.
        window.addEventListener('translationOptionsChanged', scheduleRefresh);

        // One delegated listener covers the chips, the dismissal buttons, the
        // dismissed-tips link and the Adjust/Collapse toggle alike.
        const zone = DomHelpers.getElement('preflightZone');
        if (zone) zone.addEventListener('click', handleClick);

        // Dependency inversion: settings-summary.js imports nothing from here,
        // so it receives the opener instead of importing it. Keeping the import
        // one-way is what avoids a module cycle.
        registerPanelOpener(setPanelOpen);

        // Default closed; the panel is an opt-in detour, not the landing state.
        setPanelOpen(StateManager.getState(PANEL_STATE_KEY) === true);

        // Options cannot influence a job that is already running, so the zone
        // goes inert for its duration. Subscribing beats polling: every writer of
        // this key goes through StateManager.setState().
        StateManager.subscribe('translation.isBatchActive', isActive => applyLock(!!isActive));
        applyLock(StateManager.getState('translation.isBatchActive') === true);

        refresh();
    },

    /** Re-evaluate the rules and repaint the warning / advice / dismissed link. */
    refresh,

    /** Expand or collapse #preflightPanel. */
    setPanelOpen,
};
