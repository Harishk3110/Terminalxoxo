"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  Check,
  Copy,
  KeyRound,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  X,
} from "lucide-react";
import { useApi } from "./core-pages";
import { Badge, Field, Panel, timestamp } from "./ui";

type SecurityStatus = {
  totp_enabled: boolean;
  recovery_codes_remaining: number;
  sessions: {
    id: string;
    created_at: string;
    expires_at: string;
    current: boolean;
  }[];
};
type Mode = "enroll" | "confirm" | "disable" | "password" | "recovery-codes";
type Result = {
  secret?: string;
  expires_at?: string;
  recovery_codes?: string[];
};

export function AccountSecurity() {
  const query = useApi<SecurityStatus>(
    "account-security",
    "/api/v1/auth/security",
  );
  const client = useQueryClient();
  const [mode, setMode] = useState<Mode | null>(null);
  const [password, setPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [code, setCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function begin(action: Mode) {
    setMode(action);
    setPassword("");
    setNextPassword("");
    setCode("");
    setUseRecovery(false);
    setResult(null);
    setError("");
    setMessage("");
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!mode) return;
    setBusy(true);
    setError("");
    setMessage("");
    const path =
      mode === "password" || mode === "recovery-codes" ? mode : `totp/${mode}`;
    try {
      const response = await knkApi.post<Result>(`/api/v1/auth/${path}`, {
        password,
        ...(mode === "password" ? { new_password: nextPassword } : {}),
        ...(code
          ? useRecovery
            ? { recovery_code: code }
            : { totp_code: code }
          : {}),
      });
      setCode("");
      if (mode === "password") {
        client.clear();
        window.location.assign("/login");
        return;
      }
      setResult(response);
      if (mode === "enroll") setMode("confirm");
      else {
        setPassword("");
        setMode(null);
        setMessage(
          mode === "confirm"
            ? "Authenticator enabled"
            : mode === "disable"
              ? "Authenticator disabled"
              : "Recovery codes replaced",
        );
      }
      await query.refetch();
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string, current: boolean) {
    setBusy(true);
    setError("");
    try {
      await knkApi.post(`/api/v1/auth/sessions/${id}/revoke`);
      if (current) {
        client.clear();
        window.location.assign("/login");
      } else await query.refetch();
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title="Account security"
      source="KnK authentication service"
      quality="PRIVATE"
      loading={query.isLoading}
      error={query.error}
    >
      <div className="section-pad account-security">
        <div className="toolbar">
          <Badge>
            {query.data?.totp_enabled ? "TOTP ENABLED" : "TOTP DISABLED"}
          </Badge>
          <button
            disabled={busy || !query.data}
            onClick={() =>
              begin(query.data?.totp_enabled ? "disable" : "enroll")
            }
          >
            {query.data?.totp_enabled ? (
              <ShieldOff size={13} />
            ) : (
              <ShieldCheck size={13} />
            )}
            {query.data?.totp_enabled
              ? "Disable authenticator"
              : "Enable authenticator"}
          </button>
          <button disabled={busy} onClick={() => begin("password")}>
            <LockKeyhole size={13} /> Change password
          </button>
          {query.data?.totp_enabled && (
            <button disabled={busy} onClick={() => begin("recovery-codes")}>
              <RefreshCw size={13} /> Replace recovery codes
            </button>
          )}
        </div>
        {mode && (
          <form onSubmit={submit} className="security-form">
            <Field label="Current password">
              <input
                aria-label="Current password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={1024}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            {mode === "password" && (
              <Field label="New password">
                <input
                  aria-label="New password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  maxLength={1024}
                  value={nextPassword}
                  onChange={(e) => setNextPassword(e.target.value)}
                />
              </Field>
            )}
            {result?.secret && (
              <div className="security-key">
                <Field label="Authenticator key">
                  <input
                    aria-label="Authenticator key"
                    readOnly
                    value={result.secret}
                  />
                </Field>
                <button
                  type="button"
                  title="Copy authenticator key"
                  aria-label="Copy authenticator key"
                  onClick={() =>
                    navigator.clipboard
                      .writeText(result.secret!)
                      .catch(() => setError("Clipboard unavailable"))
                  }
                >
                  <Copy size={13} />
                </button>
                <span>Expires {timestamp(result.expires_at)}</span>
              </div>
            )}
            {(query.data?.totp_enabled || mode === "confirm") && (
              <>
                {mode !== "confirm" && (
                  <label className="security-checkbox">
                    <input
                      type="checkbox"
                      checked={useRecovery}
                      onChange={(e) => {
                        setUseRecovery(e.target.checked);
                        setCode("");
                      }}
                    />{" "}
                    Use recovery code
                  </label>
                )}
                <Field
                  label={useRecovery ? "Recovery code" : "Authenticator code"}
                >
                  <input
                    aria-label={
                      useRecovery ? "Recovery code" : "Authenticator code"
                    }
                    autoComplete="one-time-code"
                    inputMode={useRecovery ? "text" : "numeric"}
                    required
                    maxLength={useRecovery ? 128 : 6}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </Field>
              </>
            )}
            <div className="toolbar">
              <button className="primary-button" type="submit" disabled={busy}>
                <Check size={13} />
                {busy
                  ? "Verifying..."
                  : mode === "confirm"
                    ? "Confirm authenticator"
                    : mode === "enroll"
                      ? "Create enrollment"
                      : mode === "password"
                        ? "Change password and sign out"
                        : mode === "disable"
                          ? "Confirm disable"
                          : "Replace codes"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setMode(null);
                  setResult(null);
                  setPassword("");
                  setNextPassword("");
                  setCode("");
                }}
              >
                <X size={13} />
                Cancel
              </button>
            </div>
          </form>
        )}
        {result?.recovery_codes && (
          <section className="recovery-output" aria-label="New recovery codes">
            <div className="toolbar">
              <KeyRound size={14} />
              <strong>Recovery codes: shown once</strong>
              <button
                title="Copy recovery codes"
                aria-label="Copy recovery codes"
                onClick={() =>
                  navigator.clipboard
                    .writeText(result.recovery_codes!.join("\n"))
                    .catch(() => setError("Clipboard unavailable"))
                }
              >
                <Copy size={13} />
              </button>
              <button
                title="Dismiss recovery codes"
                aria-label="Dismiss recovery codes"
                onClick={() => setResult(null)}
              >
                <X size={13} />
              </button>
            </div>
            <div className="recovery-code-list">
              {result.recovery_codes.map((value) => (
                <code key={value}>{value}</code>
              ))}
            </div>
          </section>
        )}
        {message && (
          <p role="status" className="positive">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="error-state">
            {error}
          </p>
        )}
        <h3>Active sessions</h3>
        <div className="security-session-list">
          {query.data?.sessions.map((row) => (
            <div className="security-session" key={row.id}>
              <span>
                {row.current ? "This session" : "Other session"}
                <small>
                  Created {timestamp(row.created_at)}
                  <br />
                  Expires {timestamp(row.expires_at)}
                </small>
              </span>
              <button
                aria-label={
                  row.current
                    ? "Revoke this session"
                    : `Revoke session ${row.id}`
                }
                title="Revoke session"
                disabled={busy}
                onClick={() => revoke(row.id, row.current)}
              >
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
