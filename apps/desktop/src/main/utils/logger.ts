/**
 * SDD §18.6 — Structured JSON logger.
 *
 * Wraps electron-log to produce JSON-lines output in files and
 * human-readable output on the console.
 *
 * Backward compatible: all existing `logger.info("msg", err)` calls still work.
 */

import electronLog from "electron-log";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LogContext {
  correlationId?: string;
  durationMs?: number;
  tokensIn?: number;
  tokensOut?: number;
  error?: string;
  projectId?: string;
  chapterId?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  component: string;
  correlationId?: string;
  message: string;
  durationMs?: number;
  tokensIn?: number;
  tokensOut?: number;
  error?: string;
  projectId?: string;
  chapterId?: string;
  extra?: unknown[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const KNOWN_CONTEXT_KEYS = new Set([
  "correlationId",
  "durationMs",
  "tokensIn",
  "tokensOut",
  "error",
  "projectId",
  "chapterId",
]);

const SENSITIVE_KEY_PATTERNS = [/api[_-]?key/i, /password/i, /secret/i, /authorization/i, /bearer/i];

const MAX_MESSAGE_LENGTH = 1000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Check whether `obj` is a plain object with at least one known LogContext key. */
function isLogContext(obj: unknown): obj is LogContext {
  if (typeof obj !== "object" || obj === null) {return false;}
  if (obj instanceof Error) {return false;}
  if (Array.isArray(obj)) {return false;}
  return Object.keys(obj).some((key) => KNOWN_CONTEXT_KEYS.has(key));
}

/** Check whether `obj` is a plain (non-Error, non-Array) object. */
function isPlainObject(obj: unknown): obj is Record<string, unknown> {
  if (typeof obj !== "object" || obj === null) {return false;}
  if (obj instanceof Error) {return false;}
  if (Array.isArray(obj)) {return false;}
  return true;
}

/** Recursively redact sensitive keys in-place. */
function redactSensitiveData(value: unknown): unknown {
  if (typeof value !== "object" || value === null) {return value;}

  if (Array.isArray(value)) {
    return value.map(redactSensitiveData);
  }

  const obj = value as Record<string, unknown>;
  for (const key of Object.keys(obj)) {
    if (SENSITIVE_KEY_PATTERNS.some((p) => p.test(key))) {
      obj[key] = "[REDACTED]";
    } else if (typeof obj[key] === "object" && obj[key] !== null) {
      obj[key] = redactSensitiveData(obj[key]);
    }
  }
  return obj;
}

/** Truncate long messages for UI logging. */
function truncateMessage(msg: string): string {
  if (msg.length > MAX_MESSAGE_LENGTH) {
    return msg.slice(0, MAX_MESSAGE_LENGTH) + "... [truncated]";
  }
  return msg;
}

// ---------------------------------------------------------------------------
// StructuredLogger
// ---------------------------------------------------------------------------

export class StructuredLogger {
  private _component: string;
  private _correlationId?: string;

  constructor(component = "App", correlationId?: string) {
    this._component = component;
    this._correlationId = correlationId;
  }

  // -- Public API ----------------------------------------------------------

  debug(message: string, ...args: unknown[]): void {
    const entry = this.buildEntry("DEBUG", message, args);
    electronLog.debug(entry);
  }

  info(message: string, ...args: unknown[]): void {
    const entry = this.buildEntry("INFO", message, args);
    electronLog.info(entry);
  }

  warn(message: string, ...args: unknown[]): void {
    const entry = this.buildEntry("WARN", message, args);
    electronLog.warn(entry);
  }

  error(message: string, ...args: unknown[]): void {
    const entry = this.buildEntry("ERROR", message, args);
    electronLog.error(entry);
  }

  /** Return a child logger with a preset component name. */
  child(component: string): StructuredLogger {
    return new StructuredLogger(component, this._correlationId);
  }

  /** Return a new logger whose every entry carries the given correlationId. */
  withCorrelationId(id: string): StructuredLogger {
    return new StructuredLogger(this._component, id);
  }

  // -- Internal ------------------------------------------------------------

  private buildEntry(level: string, message: string, args: unknown[]): LogEntry {
    // Build base entry with required fields
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      component: this._component,
      message: truncateMessage(message),
    };

    // Inherited correlationId from withCorrelationId()
    if (this._correlationId) {
      entry.correlationId = this._correlationId;
    }

    if (args.length === 1 && args[0] instanceof Error) {
      // Old-style: logger.error("msg", error)
      const err = args[0];
      entry.error = err.stack || err.message;
    } else if (args.length === 1 && isLogContext(args[0])) {
      // New-style: logger.info("msg", { correlationId: "x", durationMs: 100 })
      // Also accepts arbitrary fields (e.g. apiKey, which will be redacted below)
      const ctx = args[0] as Record<string, unknown>;
      if (ctx.correlationId !== undefined) {entry.correlationId = String(ctx.correlationId);}
      if (ctx.durationMs !== undefined) {entry.durationMs = Number(ctx.durationMs);}
      if (ctx.tokensIn !== undefined) {entry.tokensIn = Number(ctx.tokensIn);}
      if (ctx.tokensOut !== undefined) {entry.tokensOut = Number(ctx.tokensOut);}
      if (ctx.error !== undefined) {entry.error = String(ctx.error);}
      if (ctx.projectId !== undefined) {entry.projectId = String(ctx.projectId);}
      if (ctx.chapterId !== undefined) {entry.chapterId = String(ctx.chapterId);}
      // Pass through any extra keys not explicitly handled (they'll be redacted)
      for (const key of Object.keys(ctx)) {
        if (!KNOWN_CONTEXT_KEYS.has(key) && !(key in entry)) {
          (entry as Record<string, unknown>)[key] = ctx[key];
        }
      }
    } else if (args.length === 1 && isPlainObject(args[0])) {
      // Old-style: logger.info("msg", { arbitrary: "fields" })
      // Merge fields into the entry (they will be redacted below)
      Object.assign(entry, args[0]);
    } else if (args.length > 0) {
      // Multiple unstructured extra args → keep as extra array
      entry.extra = args.map((a) => (a instanceof Error ? a.stack || a.message : a));
    }

    // Redact sensitive data (in-place)
    redactSensitiveData(entry);

    return entry;
  }
}

// ---------------------------------------------------------------------------
// Transport configuration
// ---------------------------------------------------------------------------

function configureTransports(): void {
  try {
    // File transport: one JSON object per line (NDJSON)
    if (electronLog.transports?.file) {
      electronLog.transports.file.format = ({ data }: { data: unknown[] }) => {
        if (isStructuredEntry(data)) {
          return [JSON.stringify(data[0])];
        }
        // Fallback for direct electron-log calls (shouldn't happen in practice)
        return [JSON.stringify({ timestamp: new Date().toISOString(), level: "UNKNOWN", component: "unknown", message: String(data[0] ?? "") })];
      };
    }
  } catch {
    // Guard: transport config unavailable (e.g. in test mocks)
  }

  try {
    // Console transport: human-readable format with colours for dev
    if (electronLog.transports?.console) {
      electronLog.transports.console.format = ({ data }: { data: unknown[] }) => {
        if (isStructuredEntry(data)) {
          const entry = data[0];
          const ts = entry.timestamp.slice(0, 19).replace("T", " ");
          let text = `[${ts}] [${entry.level}] [${entry.component}] ${entry.message}`;
          if (entry.durationMs !== undefined) {
            text += ` (${(entry.durationMs / 1000).toFixed(2)} s)`;
          }
          if (entry.tokensIn !== undefined || entry.tokensOut !== undefined) {
            const tin = entry.tokensIn ?? "?";
            const tout = entry.tokensOut ?? "?";
            text += ` [${tin}→${tout} tokens]`;
          }
          if (entry.correlationId) {
            text += ` [${entry.correlationId}]`;
          }
          if (entry.error) {
            text += `\n${entry.error}`;
          }
          if (entry.extra && entry.extra.length > 0) {
            text += `\n${JSON.stringify(entry.extra)}`;
          }
          return [text];
        }
        // Fallback for direct electron-log calls
        return [`[${new Date().toISOString()}] ${String(data[0] ?? "")}`];
      };
    }
  } catch {
    // Guard: transport config unavailable
  }
}

function isStructuredEntry(data: unknown[]): data is [LogEntry] {
  return (
    data.length === 1 &&
    typeof data[0] === "object" &&
    data[0] !== null &&
    "timestamp" in (data[0] as Record<string, unknown>) &&
    "level" in (data[0] as Record<string, unknown>) &&
    "component" in (data[0] as Record<string, unknown>) &&
    "message" in (data[0] as Record<string, unknown>)
  );
}

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------

electronLog.initialize();
configureTransports();

export const logger = new StructuredLogger();

export default logger;
