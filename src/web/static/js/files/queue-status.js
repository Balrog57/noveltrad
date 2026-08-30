/**
 * File-queue status codes.
 *
 * Status is stored as a stable code (queued, processing, …) and displayed
 * through i18n. Legacy English display strings from localStorage are migrated
 * on read so comparisons never depend on the UI language.
 */

import { t } from '../i18n/i18n.js';

export const QueueStatus = Object.freeze({
    QUEUED: 'queued',
    PREPARING: 'preparing',
    SUBMITTED: 'submitted',
    PROCESSING: 'processing',
    COMPLETED: 'completed',
    PARTIAL: 'partial',
    INTERRUPTED: 'interrupted',
    RATE_LIMITED: 'rate_limited',
    ERROR: 'error',
    MISSING_API_KEY: 'missing_api_key',
    PATH_ERROR: 'path_error',
    INITIATION_ERROR: 'initiation_error',
});

export const QUEUE_STATUS_I18N = Object.freeze({
    queued: 'files:queue_status_queued',
    preparing: 'files:queue_status_preparing',
    submitted: 'files:queue_status_submitted',
    processing: 'files:queue_status_processing',
    completed: 'files:queue_status_completed',
    partial: 'files:queue_status_partial',
    interrupted: 'files:queue_status_interrupted',
    rate_limited: 'files:queue_status_rate_limited',
    error: 'files:queue_status_error',
    missing_api_key: 'files:queue_status_missing_api_key',
    path_error: 'files:queue_status_path_error',
    initiation_error: 'files:queue_status_initiation_error',
});

const LEGACY_STATUS = Object.freeze({
    Queued: QueueStatus.QUEUED,
    'Preparing...': QueueStatus.PREPARING,
    Submitted: QueueStatus.SUBMITTED,
    Processing: QueueStatus.PROCESSING,
    Completed: QueueStatus.COMPLETED,
    Partial: QueueStatus.PARTIAL,
    Interrupted: QueueStatus.INTERRUPTED,
    'Rate Limited': QueueStatus.RATE_LIMITED,
    Error: QueueStatus.ERROR,
    'Error: Missing API key': QueueStatus.MISSING_API_KEY,
    'Path Error': QueueStatus.PATH_ERROR,
    'Initiation Error': QueueStatus.INITIATION_ERROR,
});

export function migrateQueueStatus(status) {
    if (status == null || status === '') return QueueStatus.QUEUED;
    if (Object.prototype.hasOwnProperty.call(LEGACY_STATUS, status)) {
        return LEGACY_STATUS[status];
    }
    if (Object.prototype.hasOwnProperty.call(QUEUE_STATUS_I18N, status)) {
        return status;
    }
    if (String(status).startsWith('Error')) return QueueStatus.ERROR;
    return QueueStatus.ERROR;
}

export function isQueued(status) {
    return migrateQueueStatus(status) === QueueStatus.QUEUED;
}

export function isCompleted(status) {
    return migrateQueueStatus(status) === QueueStatus.COMPLETED;
}

export function isInFlight(status) {
    const code = migrateQueueStatus(status);
    return (
        code === QueueStatus.QUEUED
        || code === QueueStatus.PREPARING
        || code === QueueStatus.SUBMITTED
    );
}

export function queueStatusI18nKey(status) {
    const code = migrateQueueStatus(status);
    return QUEUE_STATUS_I18N[code] || QUEUE_STATUS_I18N[QueueStatus.ERROR];
}

export function paintQueueStatus(el, status) {
    if (!el) return;
    const key = queueStatusI18nKey(status);
    el.setAttribute('data-i18n', key);
    el.textContent = t(key);
}
