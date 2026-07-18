import React, { useState } from "react";
import { Shield, Ticket, AlertTriangle, X } from "lucide-react";
import { staffLogin } from "../lib/api";

// Simple test/test login gate. Fan needs no backend token; staff exchanges the
// demo passcode for a real JWT so protected endpoints keep working.
export default function AuthModal({ mode, onClose, onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isStaff = mode === "staff";
  const title = isStaff ? "Staff Login" : "Fan Login";
  const accent = isStaff ? "var(--color-high)" : "var(--accent-secondary)";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (username.trim().toLowerCase() !== "test" || password !== "test") {
      setError("Invalid credentials. For this demo, use test / test.");
      return;
    }

    setLoading(true);
    try {
      if (isStaff) {
        const token = await staffLogin();
        onSuccess({ mode: "staff", token });
      } else {
        onSuccess({ mode: "fan" });
      }
    } catch {
      setError("Could not reach the operations backend. Please ensure it is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-card glass-panel" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close login"><X size={20} /></button>

        <div className="modal-icon" style={{ background: accent }}>
          {isStaff ? <Shield size={26} /> : <Ticket size={26} />}
        </div>
        <h2 className="modal-title">{title}</h2>
        <p className="modal-sub">
          {isStaff
            ? "Access the operations intelligence dashboard."
            : "Sign in to your fan assistant."}
        </p>

        <form onSubmit={handleSubmit} className="modal-form">
          <label className="field-label" htmlFor="auth-user">Username</label>
          <input
            id="auth-user"
            className="chat-input field-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="test"
            autoFocus
            disabled={loading}
          />

          <label className="field-label" htmlFor="auth-pass">Password</label>
          <input
            id="auth-pass"
            type="password"
            className="chat-input field-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="test"
            disabled={loading}
          />

          {error && <div className="form-error"><AlertTriangle size={14} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />{error}</div>}

          <button type="submit" className="btn-primary modal-submit" disabled={loading}>
            {loading ? "Signing in…" : `Enter as ${isStaff ? "Staff" : "Fan"}`}
          </button>
          <p className="modal-hint">Demo credentials: <strong>test</strong> / <strong>test</strong></p>
        </form>
      </div>
    </div>
  );
}
