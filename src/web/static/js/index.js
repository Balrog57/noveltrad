/**
 * Main Application Entry Point
 *
 * Coordinates all modules and initializes the translation application.
 * This file serves as the central coordinator for the modular architecture.
 */

// ========================================
// Core Infrastructure
// ========================================
import { StateManager } from './core/state-manager.js';
import { ApiClient } from './core/api-client.js';
import { WebSocketManager } from './core/websocket-manager.js';
import { SettingsManager } from './core/settings-manager.js';

// ========================================
// UI Modules
// ========================================
import { DomHelpers } from './ui/dom-helpers.js';
import { MessageLogger } from './ui/message-logger.js';
import { FormManager } from './ui/form-manager.js';
import { SettingsSummary } from './ui/settings-summary.js';
import { PreflightZone } from './ui/preflight-zone.js';
import { PreflightModal } from './ui/preflight-modal.js';
import { NotificationsManager } from './ui/notifications-manager.js';
import { GlossaryManager } from './glossary/glossary-manager.js';
import { StyleManager } from './style/style-manager.js';

// ========================================
// Provider Modules
// ========================================
import { ProviderManager } from './providers/provider-manager.js';
import { ModelDetector } from './providers/model-detector.js';
import { CostEstimator } from './providers/cost-estimator.js';

// ========================================
// File Management Modules
// ========================================
import { FileUpload } from './files/file-upload.js';
import { FileManager } from './files/file-manager.js';
import { FileActions } from './files/file-actions.js';

// ========================================
// Translation Modules
// ========================================
import { TranslationTracker } from './translation/translation-tracker.js';
import { BatchController } from './translation/batch-controller.js';
import { ProgressManager } from './translation/progress-manager.js';
import { ResumeManager } from './translation/resume-manager.js';
import { QuickTestManager } from './translation/quick-test.js';

// ========================================
// Utilities
// ========================================
import { Validators } from './utils/validators.js';
import { LifecycleManager } from './utils/lifecycle-manager.js';
import { StatusManager } from './utils/status-manager.js';
import { initializeThemeManager } from './utils/theme-manager.js';
import { UpdateChecker } from './utils/update-checker.js';

// ========================================
// TTS Modules
// ========================================
import { TTSManager } from './tts/tts-manager.js';

// ========================================
// Sample & Compare
// ========================================
import { SampleManager } from './sample/sample-manager.js';

// ========================================
// i18n
// ========================================
import { initI18n, applyToDOM, t } from './i18n/i18n.js';
import { UiLocaleControl } from './i18n/settings-control.js';

// ========================================
// TTS Event Handler
// ========================================

/**
 * Handle TTS update events from WebSocket
 * @param {Object} data - TTS update data
 */
function handleTtsUpdate(data) {
    const { status, progress, message, audio_filename, error, current_chunk, total_chunks } = data;

    // Update TTS progress section
    const ttsProgressSection = DomHelpers.getElement('ttsProgressSection');
    const ttsProgressBar = DomHelpers.getElement('ttsProgressBar');
    const ttsStatusText = DomHelpers.getElement('ttsStatusText');

    switch (status) {
        case 'started':
            if (ttsProgressSection) {
                ttsProgressSection.style.display = 'block';
            }
            if (ttsProgressBar) {
                ttsProgressBar.style.width = '0%';
                ttsProgressBar.textContent = '0%';
            }
            if (ttsStatusText) {
                ttsStatusText.textContent = t('tts:starting_status');
            }
            MessageLogger.addLog(t('tts:starting_log'));
            break;

        case 'processing':
            if (ttsProgressBar) {
                ttsProgressBar.style.width = `${progress}%`;
                ttsProgressBar.textContent = `${progress}%`;
            }
            if (ttsStatusText) {
                const chunkInfo = current_chunk && total_chunks
                    ? ` (${current_chunk}/${total_chunks})`
                    : '';
                ttsStatusText.textContent = `🔊 ${message || t('tts:processing_default')}${chunkInfo}`;
            }
            break;

        case 'completed':
            if (ttsProgressBar) {
                ttsProgressBar.style.width = '100%';
                ttsProgressBar.textContent = '100%';
            }
            if (ttsStatusText) {
                ttsStatusText.textContent = t('tts:completed_status', { name: audio_filename || 'audio file' });
            }
            MessageLogger.addLog(t('tts:completed_log', { name: audio_filename || 'audio file' }));

            setTimeout(() => {
                if (ttsProgressSection) {
                    ttsProgressSection.style.display = 'none';
                }
            }, 5000);
            break;

        case 'failed':
            if (ttsProgressBar) {
                ttsProgressBar.style.width = '0%';
                ttsProgressBar.textContent = t('tts:failed_label');
                ttsProgressBar.style.background = '#ef4444';
            }

            const errorText = error || message || t('errors:unknown_error');
            const isFFmpegError = errorText.toLowerCase().includes('ffmpeg');

            if (ttsStatusText) {
                if (isFFmpegError) {
                    ttsStatusText.innerHTML = `
                        <span style="color: #ef4444;">❌ ${t('tts:ffmpeg_required')}</span>
                        <div style="margin-top: 10px;">
                            <button id="installFFmpegBtn" class="btn btn-primary" style="margin-right: 10px;" onclick="window.installFFmpeg()">
                                <span class="material-symbols-outlined" style="font-size: 18px; vertical-align: middle;">download</span>
                                ${t('tts:ffmpeg_install')}
                            </button>
                            <a href="https://ffmpeg.org/download.html" target="_blank" class="btn btn-secondary" style="text-decoration: none;">
                                ${t('tts:ffmpeg_manual')}
                            </a>
                        </div>
                        <p style="margin-top: 8px; font-size: 0.8rem; color: var(--text-secondary);">
                            ${t('tts:ffmpeg_restart_hint')}
                        </p>
                    `;
                } else {
                    ttsStatusText.textContent = t('tts:failed_status', { error: errorText });
                }
            }
            MessageLogger.addLog(t('tts:failed_log', { error: errorText }));
            break;
    }
}

/**
 * Install FFmpeg via winget (Windows)
 */
window.installFFmpeg = async function() {
    const btn = document.getElementById('installFFmpegBtn');
    const ttsStatusText = DomHelpers.getElement('ttsStatusText');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <span class="material-symbols-outlined rotating" style="font-size: 18px; vertical-align: middle;">sync</span>
            ${t('tts:ffmpeg_installing')}
        `;
    }

    try {
        const response = await fetch('/api/tts/ffmpeg/install', { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            if (ttsStatusText) {
                ttsStatusText.innerHTML = `
                    <span style="color: #22c55e;">✅ ${result.message}</span>
                    <p style="margin-top: 8px; font-size: 0.8rem; color: var(--text-secondary);">
                        ${t('tts:ffmpeg_restart_needed')}
                    </p>
                `;
            }
            MessageLogger.addLog(t('tts:ffmpeg_installed_log'));
        } else {
            if (ttsStatusText) {
                ttsStatusText.innerHTML = `
                    <span style="color: #ef4444;">❌ ${t('tts:ffmpeg_install_failed', { error: result.error })}</span>
                    <div style="margin-top: 10px;">
                        <a href="https://ffmpeg.org/download.html" target="_blank" class="btn btn-secondary" style="text-decoration: none;">
                            ${t('tts:ffmpeg_manual')}
                        </a>
                    </div>
                `;
            }
            MessageLogger.addLog(t('tts:ffmpeg_install_failed_log', { error: result.error }));
        }
    } catch (err) {
        if (ttsStatusText) {
            ttsStatusText.innerHTML = `
                <span style="color: #ef4444;">❌ ${t('tts:ffmpeg_install_error', { error: err.message })}</span>
                <div style="margin-top: 10px;">
                    <a href="https://ffmpeg.org/download.html" target="_blank" class="btn btn-secondary" style="text-decoration: none;">
                        ${t('tts:ffmpeg_manual')}
                    </a>
                </div>
            `;
        }
        MessageLogger.addLog(t('tts:ffmpeg_install_error_log', { error: err.message }));
    }
}

// ========================================
// Global State Initialization
// ========================================

/**
 * Initialize application state
 * Note: Some state (like files.toProcess) will be restored from localStorage
 * by their respective modules, so we only set defaults if not already present
 */
function initializeState() {
    // Files state - only initialize if not already set (will be restored by FileUpload)
    if (!StateManager.getState('files.toProcess')) {
        StateManager.setState('files.toProcess', []);
    }
    if (!StateManager.getState('files.selected')) {
        StateManager.setState('files.selected', []);
    }
    if (!StateManager.getState('files.managed')) {
        StateManager.setState('files.managed', []);
    }

    // Translation state - DO NOT reset here, will be restored by TranslationTracker from localStorage
    // TranslationTracker.initialize() will handle loading saved state or initializing defaults

    // UI state
    StateManager.setState('ui.currentProvider', 'ollama');
    StateManager.setState('ui.currentModel', '');
    StateManager.setState('ui.messages', []);

    // Models state
    StateManager.setState('models.currentLoadRequest', null);
    StateManager.setState('models.availableModels', []);
}

/**
 * Calculate and apply preview height based on MAX_TOKENS_PER_CHUNK
 * @param {number} maxTokens - MAX_TOKENS_PER_CHUNK value
 */
function updatePreviewHeight(maxTokens = 450) {
    const fixedHeight = 300;
    document.documentElement.style.setProperty('--preview-height', `${fixedHeight}px`);
}

/**
 * Fetch and apply MAX_TOKENS_PER_CHUNK from server
 */
async function initializePreviewHeight() {
    try {
        // Fetch config from server
        const response = await fetch('/api/config/max-tokens');
        if (response.ok) {
            const data = await response.json();
            const maxTokens = data.max_tokens_per_chunk || 450;
            updatePreviewHeight(maxTokens);
        } else {
            updatePreviewHeight(450);
        }
    } catch {
        updatePreviewHeight(450);
    }
}

// ========================================
// Event Wiring
// ========================================

/**
 * Wire up cross-module events
 */
function wireModuleEvents() {
    // File list changed -> update display
    window.addEventListener('fileListChanged', () => {
        FileUpload.updateFileDisplay();
    });

    // File status changed -> update display
    window.addEventListener('fileStatusChanged', () => {
        FileUpload.updateFileDisplay();
    });

    // Translation started -> update active translations state
    window.addEventListener('translationStarted', () => {
        TranslationTracker.updateActiveTranslationsState();
    });

    // Translation resumed -> update active translations state
    window.addEventListener('translationResumed', () => {
        TranslationTracker.updateActiveTranslationsState();
    });

    // Translation completed -> process next in queue
    window.addEventListener('translationCompleted', () => {
        BatchController.processNextFileInQueue();
    });

    // Translation error -> process next in queue
    window.addEventListener('translationError', () => {
        BatchController.processNextFileInQueue();
    });

    // Process next file in queue (from TranslationTracker)
    window.addEventListener('processNextFile', () => {
        BatchController.processNextFileInQueue();
    });

    // WebSocket events -> module handlers
    WebSocketManager.on('connect', () => {
        // Only refresh models if we don't have any loaded yet
        const hasModels = StateManager.getState('models.availableModels')?.length > 0;
        if (!hasModels) {
            ProviderManager.refreshModels();
        }

        ResumeManager.loadResumableJobs();
        FileManager.refreshFileList();
        TranslationTracker.updateActiveTranslationsState();
    });

    // Desync recovery (visibility change / 10s consistency check) -> tracker.
    // Injected instead of imported: translation-tracker.js already imports
    // LifecycleManager, so a static import the other way would close a cycle.
    // Issue #224.
    LifecycleManager.setDesyncHandlers({
        onTerminalStatus: (data) => TranslationTracker.handleTranslationUpdate(data),
        onJobMissing: () => TranslationTracker.resetUIToIdle(),
    });

    WebSocketManager.on('translation_update', (data) => {
        TranslationTracker.handleTranslationUpdate(data);
    });

    WebSocketManager.on('file_list_changed', (data) => {
        FileManager.refreshFileList();
    });

    WebSocketManager.on('checkpoint_created', (data) => {
        ResumeManager.loadResumableJobs();
    });

    // TTS update events
    WebSocketManager.on('tts_update', (data) => {
        handleTtsUpdate(data);
    });

    // State changes -> update UI
    StateManager.subscribe('translation.isBatchActive', (isActive) => {
        const translateBtn = DomHelpers.getElement('translateBtn');
        if (translateBtn) {
            translateBtn.disabled = isActive;
        }
    });

    StateManager.subscribe('translation.hasActive', (hasActive) => {
        TranslationTracker.updateResumeButtonsState();
    });

    StateManager.subscribe('files.toProcess', (files) => {
        const translateBtn = DomHelpers.getElement('translateBtn');
        if (translateBtn && !StateManager.getState('translation.isBatchActive')) {
            // Only enable if files exist AND LLM is connected
            translateBtn.disabled = files.length === 0 || !StatusManager.isConnected();
        }
    });
}

// ========================================
// Module Initialization
// ========================================

/**
 * Initialize all modules in proper order
 *
 * CRITICAL ordering rule: every event wiring (wireModuleEvents, LifecycleManager,
 * WebSocketManager.on handlers) must run synchronously BEFORE any awaitable
 * network call AND before WebSocketManager.connect(). Otherwise:
 *   - A slow /api/health or /api/translations response can hang the await on
 *     TranslationTracker.initialize() and leave the UI un-wired (translate
 *     button disabled, no WS handlers, no lifecycle handlers).
 *   - Or the socket connects during the await and emits "connect" before its
 *     handler is registered, so the post-connect refresh (provider models,
 *     file list, resumable jobs) is silently dropped — that's why the
 *     "LLM: Checking..." indicator gets stuck (issue #155).
 */
async function initializeModules() {
    // 0. Boot i18next first so every module that renders text can call t().
    //    initI18n() resolves to applying data-i18n nodes already in the DOM
    //    and binding the languageChanged listener. We await it because the
    //    rest of the init expects translations to be available.
    try {
        await initI18n();
    } catch (e) {
        console.warn('initI18n failed:', e);
    }
    UiLocaleControl.initialize();

    // 1. Synchronous state + UI/module init (no awaits).
    initializeState();
    initializeThemeManager();
    SettingsManager.initialize();
    FormManager.initialize();
    SettingsSummary.initialize();
    PreflightZone.initialize();
    PreflightModal.initialize();
    NotificationsManager.initialize();
    GlossaryManager.initialize();
    StyleManager.initialize();
    StatusManager.initialize();
    initializePreviewHeight();
    ProviderManager.initialize();
    ModelDetector.initialize();
    // FileUpload must initialize before CostEstimator so its `change` listeners
    // on source/target language fire first and recreate the file <li>s (with
    // empty cost-badge slots) before CostEstimator's listener queries the DOM.
    FileUpload.initialize();
    CostEstimator.initialize();
    FileManager.initialize();
    ProgressManager.reset();
    ResumeManager.initialize();
    LifecycleManager.initialize();
    UpdateChecker.initialize().catch((e) => console.warn('UpdateChecker init failed:', e));

    // 2. Wire cross-module + WebSocket handlers BEFORE the socket connects.
    wireModuleEvents();

    // 3. Now safe to open the WebSocket — the "connect" handler is registered.
    WebSocketManager.connect();

    // 4. Background-only inits. Do not await: a slow server must not freeze
    //    the UI. TranslationTracker.initialize() is async and performs
    //    network calls; failures are logged and the UI stays usable.
    TTSManager.initialize();
    SampleManager.init();
    QuickTestManager.init();
    TranslationTracker.initialize().catch((error) => {
        console.error('TranslationTracker initialization failed:', error);
    });
}

// ========================================
// Global Function Exposure for HTML onclick
// ========================================

/**
 * Expose functions to window for onclick handlers in HTML
 * These functions will be called directly from HTML attributes
 */

// File Upload
window.handleFileSelect = FileUpload.handleFileSelect.bind(FileUpload);
window.handleFileSelectRefine = FileUpload.handleFileSelectRefine.bind(FileUpload);
window.resetFiles = () => {
    FileUpload.clearAll();
    DomHelpers.hide('fileInfo');
    const fileListContainer = DomHelpers.getElement('fileListContainer');
    if (fileListContainer) {
        fileListContainer.innerHTML = '';
    }
    MessageLogger.showMessage(t('translation:file_list_cleared'), 'info');
};

// Form Manager
window.toggleSettingsOptions = FormManager.toggleSettingsOptions.bind(FormManager);
window.toggleActivityLog = FormManager.toggleActivityLog.bind(FormManager);

// Notifications Manager
window.toggleNotificationOptions = NotificationsManager.toggleOptions.bind(NotificationsManager);
window.testNotification = NotificationsManager.testNotification.bind(NotificationsManager);
window.checkCustomSourceLanguage = (element) => FormManager.checkCustomSourceLanguage(element);
window.checkCustomTargetLanguage = (element) => FormManager.checkCustomTargetLanguage(element);
window.resetForm = FormManager.resetForm.bind(FormManager);

// Batch Controller
// The pre-flight confirmation is not wired here: it lives inside
// startBatchTranslation(), after that method's own validation, so a run missing a
// model reports the real problem instead of a suggestion list.
window.startBatchTranslation = BatchController.startBatchTranslation.bind(BatchController);
window.interruptCurrentTranslation = async () => {
    const currentJob = StateManager.getState('translation.currentJob');
    if (!currentJob) {
        MessageLogger.showMessage(t('translation:no_active_translation'), 'info');
        return;
    }

    const interruptBtn = DomHelpers.getElement('interruptBtn');
    if (interruptBtn) {
        interruptBtn.disabled = true;
        DomHelpers.setText(interruptBtn, t('translation:interrupting'));
    }

    try {
        await ApiClient.interruptTranslation(currentJob.translationId);
        MessageLogger.showMessage(t('translation:interrupt_request_sent'), 'info');
        MessageLogger.addLog(t('translation:interrupt_log'));
    } catch (error) {
        MessageLogger.showMessage(t('translation:interrupt_error', { error: error.message }), 'error');
        if (interruptBtn) {
            interruptBtn.disabled = false;
            DomHelpers.setText(interruptBtn, `⏹️ ${t('translation:interrupt_batch')}`);
        }
    }
};

// Resume Manager
window.resumeJob = ResumeManager.resumeJob.bind(ResumeManager);
window.deleteCheckpoint = ResumeManager.deleteCheckpoint.bind(ResumeManager);
window.loadResumableJobs = ResumeManager.loadResumableJobs.bind(ResumeManager);

// Provider Manager
window.refreshModels = ProviderManager.refreshModels.bind(ProviderManager);

// Settings Manager
window.saveSettings = async () => {
    const result = await SettingsManager.saveAllSettings(true);
    if (result.success && result.savedToEnv && result.savedToEnv.length > 0) {
        const keys = result.savedToEnv.join(', ');
        MessageLogger.showMessage(t('translation:settings_saved_env', { keys }), 'success');
        MessageLogger.addLog(t('translation:settings_saved_env_log', { keys }));
    } else if (result.success) {
        MessageLogger.showMessage(t('translation:preferences_saved'), 'success');
    } else {
        MessageLogger.showMessage(t('translation:settings_save_failed', { error: result.error }), 'error');
    }
    return result;
};

// Message Logger
window.clearActivityLog = MessageLogger.clearLog.bind(MessageLogger);

// File Manager
window.refreshFileList = FileManager.refreshFileList.bind(FileManager);
window.downloadSelectedFiles = FileManager.downloadSelectedFiles.bind(FileManager);
window.deleteSelectedFiles = FileManager.deleteSelectedFiles.bind(FileManager);
window.toggleSelectAll = FileManager.toggleSelectAll.bind(FileManager);
window.openOutputFolder = () => FileActions.openOutputFolder();

// Style Manager (Styles tab — mirrors the window.refreshFileList hook so
// glossary-manager.js's switchTopTab() can refresh the list without
// importing style-manager.js and creating a cycle)
window.refreshStyleList = StyleManager.refreshList.bind(StyleManager);

// File manager functions (exposed in file-manager.js / file-actions.js)
// window.toggleFileSelection, deleteSingleFile, openLocalFile, revealLocalFile, downloadSingleFile

// TTS Manager functions
window.refreshTTSProviders = TTSManager.loadProvidersInfo.bind(TTSManager);
window.refreshGPUStatus = TTSManager.loadGPUStatus.bind(TTSManager);
window.deleteVoicePrompt = TTSManager.deleteVoicePrompt.bind(TTSManager);

// ========================================
// TTS (Audiobook) Generation
// ========================================

/**
 * Show TTS configuration modal and start audiobook generation
 * @param {string} filename - File to generate audio from
 * @param {string} filepath - Full path to the file
 */
window.createAudiobook = async function(filename, filepath) {
    // Show TTS modal
    showTTSModal(filename, filepath);
};

/**
 * Show TTS configuration modal with provider selection
 */
async function showTTSModal(filename, filepath) {
    // Remove existing modal if present
    const existingModal = document.getElementById('ttsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Get providers info and voice prompts
    let providersInfo = {};
    let voicePrompts = [];
    let gpuStatus = { cuda_available: false };

    try {
        [providersInfo, voicePrompts, gpuStatus] = await Promise.all([
            ApiClient.getTTSProviders().catch(() => ({ providers: {} })),
            ApiClient.getTTSVoicePrompts().catch(() => ({ voice_prompts: [] })),
            ApiClient.getTTSGPUStatus().catch(() => ({ cuda_available: false }))
        ]);
        providersInfo = providersInfo.providers || {};
        voicePrompts = voicePrompts.voice_prompts || [];
    } catch {
    }

    const isChatterboxAvailable = providersInfo.chatterbox?.available || false;
    const chatterboxProviderKey = isChatterboxAvailable
        ? 'tts:provider_chatterbox_full_local'
        : 'tts:provider_chatterbox_full_unavailable';
    const gpuName = gpuStatus.cuda_available ? (gpuStatus.gpu_name || '') : '';
    const gpuI18nKey = gpuName ? '' : (gpuStatus.cuda_available ? 'tts:gpu_cuda' : 'tts:gpu_cpu');
    const subtitleParams = DomHelpers.escapeHtml(JSON.stringify({ filename }));

    // Build voice prompts options
    const voicePromptsOptions = voicePrompts.map(vp =>
        `<option value="${DomHelpers.escapeHtml(vp.path)}">${DomHelpers.escapeHtml(vp.filename)}</option>`
    ).join('');

    // Create modal HTML with provider selection
    const modalHtml = `
        <div id="ttsModal" class="modal-overlay">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 data-i18n="tts:modal_title_emoji">${t('tts:modal_title_emoji')}</h3>
                    <button class="close-btn" id="ttsModalClose">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="margin: 0 0 20px 0; color: #a3adb3; font-size: 14px;"
                       data-i18n="tts:modal_subtitle"
                       data-i18n-params="${subtitleParams}"></p>

                    <!-- Provider Selection -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div class="form-group" style="margin-bottom: 0;">
                            <label style="font-size: 13px;" data-i18n="tts:provider">${t('tts:provider')}</label>
                            <select id="ttsModalProvider" class="form-control" style="font-size: 13px;">
                                <option value="edge-tts" data-i18n="tts:provider_edge">${t('tts:provider_edge')}</option>
                                <option value="chatterbox" ${!isChatterboxAvailable ? 'disabled' : ''} data-i18n="${chatterboxProviderKey}">
                                    ${t(chatterboxProviderKey)}
                                </option>
                            </select>
                        </div>

                        <!-- GPU Status (shown when Chatterbox selected) -->
                        <div id="ttsModalGpuStatus" class="form-group" style="margin-bottom: 0; display: none;">
                            <label style="font-size: 13px;" data-i18n="tts:gpu_status">${t('tts:gpu_status')}</label>
                            <div class="gpu-status ${gpuStatus.cuda_available ? 'gpu-available' : 'gpu-unavailable'}">
                                <span class="status-dot ${gpuStatus.cuda_available ? 'available' : 'unavailable'}"></span>
                                <span${gpuI18nKey ? ` data-i18n="${gpuI18nKey}"` : ''}>${gpuName ? DomHelpers.escapeHtml(gpuName) : t(gpuI18nKey)}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Edge-TTS Options -->
                    <div id="ttsModalEdgeOptions">
                        <div style="display: grid; gap: 15px;">
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:target_language">${t('tts:target_language')}</label>
                                <select id="ttsModalLanguage" class="form-control" style="font-size: 13px;">
                                    <!-- Most Common -->
                                    <option value="Chinese" data-i18n="tts:lang_chinese">${t('tts:lang_chinese')}</option>
                                    <option value="English" data-i18n="tts:lang_english">${t('tts:lang_english')}</option>
                                    <option value="French" data-i18n="tts:lang_french">${t('tts:lang_french')}</option>
                                    <option value="Spanish" data-i18n="tts:lang_spanish">${t('tts:lang_spanish')}</option>
                                    <option value="German" data-i18n="tts:lang_german">${t('tts:lang_german')}</option>
                                    <option value="Japanese" data-i18n="tts:lang_japanese">${t('tts:lang_japanese')}</option>
                                    <option value="Korean" data-i18n="tts:lang_korean">${t('tts:lang_korean')}</option>
                                    <option value="Portuguese (Brazil)" data-i18n="tts:lang_portuguese_brazil">${t('tts:lang_portuguese_brazil')}</option>
                                    <option value="Portuguese (Portugal)" data-i18n="tts:lang_portuguese_portugal">${t('tts:lang_portuguese_portugal')}</option>
                                    <option value="Russian" data-i18n="tts:lang_russian">${t('tts:lang_russian')}</option>
                                    <option value="Arabic" data-i18n="tts:lang_arabic">${t('tts:lang_arabic')}</option>
                                    <!-- European -->
                                    <option value="Italian" data-i18n="tts:lang_italian">${t('tts:lang_italian')}</option>
                                    <option value="Dutch" data-i18n="tts:lang_dutch">${t('tts:lang_dutch')}</option>
                                    <option value="Polish" data-i18n="tts:lang_polish">${t('tts:lang_polish')}</option>
                                    <option value="Swedish" data-i18n="tts:lang_swedish">${t('tts:lang_swedish')}</option>
                                    <option value="Norwegian" data-i18n="tts:lang_norwegian">${t('tts:lang_norwegian')}</option>
                                    <option value="Danish" data-i18n="tts:lang_danish">${t('tts:lang_danish')}</option>
                                    <option value="Finnish" data-i18n="tts:lang_finnish">${t('tts:lang_finnish')}</option>
                                    <option value="Greek" data-i18n="tts:lang_greek">${t('tts:lang_greek')}</option>
                                    <option value="Czech" data-i18n="tts:lang_czech">${t('tts:lang_czech')}</option>
                                    <option value="Hungarian" data-i18n="tts:lang_hungarian">${t('tts:lang_hungarian')}</option>
                                    <option value="Romanian" data-i18n="tts:lang_romanian">${t('tts:lang_romanian')}</option>
                                    <option value="Turkish" data-i18n="tts:lang_turkish">${t('tts:lang_turkish')}</option>
                                    <option value="Ukrainian" data-i18n="tts:lang_ukrainian">${t('tts:lang_ukrainian')}</option>
                                    <option value="Bulgarian" data-i18n="tts:lang_bulgarian">${t('tts:lang_bulgarian')}</option>
                                    <option value="Croatian" data-i18n="tts:lang_croatian">${t('tts:lang_croatian')}</option>
                                    <option value="Slovak" data-i18n="tts:lang_slovak">${t('tts:lang_slovak')}</option>
                                    <option value="Slovenian" data-i18n="tts:lang_slovenian">${t('tts:lang_slovenian')}</option>
                                    <option value="Lithuanian" data-i18n="tts:lang_lithuanian">${t('tts:lang_lithuanian')}</option>
                                    <option value="Latvian" data-i18n="tts:lang_latvian">${t('tts:lang_latvian')}</option>
                                    <option value="Estonian" data-i18n="tts:lang_estonian">${t('tts:lang_estonian')}</option>
                                    <!-- Asian -->
                                    <option value="Hindi" data-i18n="tts:lang_hindi">${t('tts:lang_hindi')}</option>
                                    <option value="Vietnamese" data-i18n="tts:lang_vietnamese">${t('tts:lang_vietnamese')}</option>
                                    <option value="Thai" data-i18n="tts:lang_thai">${t('tts:lang_thai')}</option>
                                    <option value="Indonesian" data-i18n="tts:lang_indonesian">${t('tts:lang_indonesian')}</option>
                                    <option value="Malay" data-i18n="tts:lang_malay">${t('tts:lang_malay')}</option>
                                    <option value="Filipino" data-i18n="tts:lang_filipino">${t('tts:lang_filipino')}</option>
                                    <option value="Bengali" data-i18n="tts:lang_bengali">${t('tts:lang_bengali')}</option>
                                    <option value="Tamil" data-i18n="tts:lang_tamil">${t('tts:lang_tamil')}</option>
                                    <option value="Telugu" data-i18n="tts:lang_telugu">${t('tts:lang_telugu')}</option>
                                    <!-- Middle Eastern -->
                                    <option value="Hebrew" data-i18n="tts:lang_hebrew">${t('tts:lang_hebrew')}</option>
                                    <option value="Persian" data-i18n="tts:lang_persian">${t('tts:lang_persian')}</option>
                                    <option value="Urdu" data-i18n="tts:lang_urdu">${t('tts:lang_urdu')}</option>
                                </select>
                            </div>

                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:voice_optional">${t('tts:voice_optional')}</label>
                                <input type="text" id="ttsModalVoice" class="form-control" data-i18n-attr="placeholder:tts:voice_placeholder" placeholder="${t('tts:voice_placeholder')}" style="font-size: 13px;">
                                <small style="color: #6b7280;" data-i18n="tts:voice_auto_hint">${t('tts:voice_auto_hint')}</small>
                            </div>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label style="font-size: 13px;" data-i18n="tts:speech_rate">${t('tts:speech_rate')}</label>
                                    <select id="ttsModalRate" class="form-control" style="font-size: 13px;">
                                        <option value="-20%" data-i18n="tts:rate_slower">${t('tts:rate_slower')}</option>
                                        <option value="-10%" data-i18n="tts:rate_slightly_slower">${t('tts:rate_slightly_slower')}</option>
                                        <option value="+0%" selected data-i18n="tts:rate_normal">${t('tts:rate_normal')}</option>
                                        <option value="+10%" data-i18n="tts:rate_slightly_faster">${t('tts:rate_slightly_faster')}</option>
                                        <option value="+20%" data-i18n="tts:rate_faster">${t('tts:rate_faster')}</option>
                                        <option value="+30%" data-i18n="tts:rate_much_faster">${t('tts:rate_much_faster')}</option>
                                    </select>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label style="font-size: 13px;" data-i18n="tts:audio_format">${t('tts:audio_format')}</label>
                                    <select id="ttsModalFormat" class="form-control" style="font-size: 13px;">
                                        <option value="opus" selected data-i18n="tts:audio_format_opus">${t('tts:audio_format_opus')}</option>
                                        <option value="mp3" data-i18n="tts:audio_format_mp3">${t('tts:audio_format_mp3')}</option>
                                    </select>
                                </div>
                            </div>

                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:audio_bitrate">${t('tts:audio_bitrate')}</label>
                                <select id="ttsModalBitrate" class="form-control" style="font-size: 13px;">
                                    <option value="48k" data-i18n="tts:bitrate_48">${t('tts:bitrate_48')}</option>
                                    <option value="64k" selected data-i18n="tts:bitrate_64">${t('tts:bitrate_64')}</option>
                                    <option value="96k" data-i18n="tts:bitrate_96">${t('tts:bitrate_96')}</option>
                                    <option value="128k" data-i18n="tts:bitrate_128">${t('tts:bitrate_128')}</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Chatterbox Options (hidden by default) -->
                    <div id="ttsModalChatterboxOptions" style="display: none;">
                        <div style="background: #2a2a2a; border-radius: 8px; padding: 15px; margin-bottom: 15px; border: 1px solid #fbbf24;">
                            <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #fbbf24;" data-i18n="tts:voice_cloning_heading">${t('tts:voice_cloning_heading')}</h4>
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:voice_prompt">${t('tts:voice_prompt')}</label>
                                <select id="ttsModalVoicePrompt" class="form-control" style="font-size: 13px;">
                                    <option value="" data-i18n="tts:voice_prompt_default">${t('tts:voice_prompt_default')}</option>
                                    ${voicePromptsOptions}
                                </select>
                                <small style="color: #6b7280;" data-i18n="tts:voice_prompt_hint">${t('tts:voice_prompt_hint')}</small>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;">
                                    <span data-i18n="tts:exaggeration">${t('tts:exaggeration')}</span>
                                    <span id="ttsModalExaggerationValue" style="color: #fbbf24;">0.50</span>
                                </label>
                                <input type="range" id="ttsModalExaggeration" min="0" max="1" step="0.05" value="0.5" class="tts-slider">
                                <small style="color: #6b7280;" data-i18n="tts:exaggeration_hint">${t('tts:exaggeration_hint')}</small>
                            </div>
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;">
                                    <span data-i18n="tts:cfg_weight">${t('tts:cfg_weight')}</span>
                                    <span id="ttsModalCfgValue" style="color: #fbbf24;">0.50</span>
                                </label>
                                <input type="range" id="ttsModalCfgWeight" min="0" max="1" step="0.05" value="0.5" class="tts-slider">
                                <small style="color: #6b7280;" data-i18n="tts:cfg_weight_hint">${t('tts:cfg_weight_hint')}</small>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:target_language">${t('tts:target_language')}</label>
                                <select id="ttsModalChatterboxLang" class="form-control" style="font-size: 13px;">
                                    <!-- Most Common -->
                                    <option value="en" data-i18n="tts:lang_english">${t('tts:lang_english')}</option>
                                    <option value="zh" data-i18n="tts:lang_chinese">${t('tts:lang_chinese')}</option>
                                    <option value="es" data-i18n="tts:lang_spanish">${t('tts:lang_spanish')}</option>
                                    <option value="fr" data-i18n="tts:lang_french">${t('tts:lang_french')}</option>
                                    <option value="de" data-i18n="tts:lang_german">${t('tts:lang_german')}</option>
                                    <option value="it" data-i18n="tts:lang_italian">${t('tts:lang_italian')}</option>
                                    <option value="ja" data-i18n="tts:lang_japanese">${t('tts:lang_japanese')}</option>
                                    <option value="ko" data-i18n="tts:lang_korean">${t('tts:lang_korean')}</option>
                                    <option value="pt-br" data-i18n="tts:lang_portuguese_brazil">${t('tts:lang_portuguese_brazil')}</option>
                                    <option value="pt-pt" data-i18n="tts:lang_portuguese_portugal">${t('tts:lang_portuguese_portugal')}</option>
                                    <option value="ru" data-i18n="tts:lang_russian">${t('tts:lang_russian')}</option>
                                    <option value="ar" data-i18n="tts:lang_arabic">${t('tts:lang_arabic')}</option>
                                    <!-- European -->
                                    <option value="pl" data-i18n="tts:lang_polish">${t('tts:lang_polish')}</option>
                                    <option value="tr" data-i18n="tts:lang_turkish">${t('tts:lang_turkish')}</option>
                                    <option value="nl" data-i18n="tts:lang_dutch">${t('tts:lang_dutch')}</option>
                                    <option value="cs" data-i18n="tts:lang_czech">${t('tts:lang_czech')}</option>
                                    <option value="sv" data-i18n="tts:lang_swedish">${t('tts:lang_swedish')}</option>
                                    <option value="da" data-i18n="tts:lang_danish">${t('tts:lang_danish')}</option>
                                    <option value="fi" data-i18n="tts:lang_finnish">${t('tts:lang_finnish')}</option>
                                    <option value="hu" data-i18n="tts:lang_hungarian">${t('tts:lang_hungarian')}</option>
                                    <!-- Asian -->
                                    <option value="hi" data-i18n="tts:lang_hindi">${t('tts:lang_hindi')}</option>
                                    <option value="vi" data-i18n="tts:lang_vietnamese">${t('tts:lang_vietnamese')}</option>
                                    <option value="id" data-i18n="tts:lang_indonesian">${t('tts:lang_indonesian')}</option>
                                    <!-- Other -->
                                    <option value="el" data-i18n="tts:lang_greek">${t('tts:lang_greek')}</option>
                                </select>
                            </div>
                            <div class="form-group" style="margin-bottom: 0;">
                                <label style="font-size: 13px;" data-i18n="tts:audio_format">${t('tts:audio_format')}</label>
                                <select id="ttsModalChatterboxFormat" class="form-control" style="font-size: 13px;">
                                    <option value="wav" data-i18n="tts:audio_format_wav">${t('tts:audio_format_wav')}</option>
                                    <option value="mp3" selected data-i18n="tts:audio_format_mp3">${t('tts:audio_format_mp3')}</option>
                                    <option value="opus" data-i18n="tts:audio_format_opus">${t('tts:audio_format_opus')}</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="modal-footer">
                    <button id="ttsModalCancel" class="btn btn-secondary" data-i18n="common:cancel">${t('common:cancel')}</button>
                    <button id="ttsModalGenerate" class="btn btn-primary" style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);" data-i18n="tts:generate_audio_with_icon">
                        ${t('tts:generate_audio_with_icon')}
                    </button>
                </div>
            </div>
        </div>
    `;

    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Get modal elements
    const modal = document.getElementById('ttsModal');
    applyToDOM(modal);
    const closeBtn = document.getElementById('ttsModalClose');
    const cancelBtn = document.getElementById('ttsModalCancel');
    const generateBtn = document.getElementById('ttsModalGenerate');
    const providerSelect = document.getElementById('ttsModalProvider');
    const edgeOptions = document.getElementById('ttsModalEdgeOptions');
    const chatterboxOptions = document.getElementById('ttsModalChatterboxOptions');
    const gpuStatusDiv = document.getElementById('ttsModalGpuStatus');

    // Slider value updates
    const exaggerationSlider = document.getElementById('ttsModalExaggeration');
    const cfgSlider = document.getElementById('ttsModalCfgWeight');
    const exaggerationValue = document.getElementById('ttsModalExaggerationValue');
    const cfgValue = document.getElementById('ttsModalCfgValue');

    if (exaggerationSlider && exaggerationValue) {
        exaggerationSlider.addEventListener('input', () => {
            exaggerationValue.textContent = parseFloat(exaggerationSlider.value).toFixed(2);
        });
    }
    if (cfgSlider && cfgValue) {
        cfgSlider.addEventListener('input', () => {
            cfgValue.textContent = parseFloat(cfgSlider.value).toFixed(2);
        });
    }

    // Provider change handler
    providerSelect.addEventListener('change', () => {
        const isChatterbox = providerSelect.value === 'chatterbox';
        edgeOptions.style.display = isChatterbox ? 'none' : 'block';
        chatterboxOptions.style.display = isChatterbox ? 'block' : 'none';
        gpuStatusDiv.style.display = isChatterbox ? 'block' : 'none';
    });

    // Close handlers
    const closeModal = () => modal.remove();
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);

    // Generate audio
    generateBtn.addEventListener('click', async () => {
        const provider = providerSelect.value;

        // Build config based on provider
        let config = {
            filename: filename,
            tts_provider: provider
        };

        if (provider === 'edge-tts') {
            config.target_language = document.getElementById('ttsModalLanguage').value;
            config.tts_voice = document.getElementById('ttsModalVoice').value;
            config.tts_rate = document.getElementById('ttsModalRate').value;
            config.tts_format = document.getElementById('ttsModalFormat').value;
            config.tts_bitrate = document.getElementById('ttsModalBitrate').value;
        } else {
            // Chatterbox
            config.target_language = document.getElementById('ttsModalChatterboxLang').value;
            config.tts_voice_prompt_path = document.getElementById('ttsModalVoicePrompt').value;
            config.tts_exaggeration = parseFloat(document.getElementById('ttsModalExaggeration').value);
            config.tts_cfg_weight = parseFloat(document.getElementById('ttsModalCfgWeight').value);
            config.tts_format = document.getElementById('ttsModalChatterboxFormat').value;
        }

        // Disable button and show loading
        generateBtn.disabled = true;
        generateBtn.setAttribute('data-i18n', 'tts:starting');
        generateBtn.textContent = t('tts:starting');

        try {
            const result = await ApiClient.generateTTS(config);

            MessageLogger.showMessage(t('tts:tts_started', { filename }), 'success');
            MessageLogger.addLog(t('tts:tts_started_log', { provider, filename, jobId: result.job_id }));

            closeModal();

            const ttsProgressSection = DomHelpers.getElement('ttsProgressSection');
            if (ttsProgressSection) {
                ttsProgressSection.style.display = 'block';
            }

        } catch (error) {
            MessageLogger.showMessage(t('tts:tts_error', { error: error.message }), 'error');
            generateBtn.disabled = false;
            generateBtn.setAttribute('data-i18n', 'tts:generate_audio_with_icon');
            generateBtn.textContent = t('tts:generate_audio_with_icon');
        }
    });
}

// ========================================
// API Endpoint Configuration
// ========================================

// Set API base URL (same origin)
if (typeof window !== 'undefined') {
    window.API_BASE_URL = window.location.origin;
}

// ========================================
// Application Bootstrap
// ========================================

/**
 * Start application when DOM is ready
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
        await initializeModules();
    });
} else {
    // DOM already loaded - initialize immediately
    (async () => {
        await initializeModules();
    })();
}

// ========================================
// Module Exports (for testing)
// ========================================

export {
    StateManager,
    ApiClient,
    WebSocketManager,
    SettingsManager,
    DomHelpers,
    MessageLogger,
    FormManager,
    ProviderManager,
    ModelDetector,
    FileUpload,
    FileManager,
    TranslationTracker,
    BatchController,
    ProgressManager,
    ResumeManager,
    Validators,
    LifecycleManager,
    TTSManager,
    StatusManager
};
