import React, { useState } from "react";
import StaffChat from "./StaffChat";

// Floating bottom-right assistant. Collapsed = a circular robot button;
// expanded = the Staff Decision Support Console chat panel.
export default function StaffChatWidget({ token, onLogout }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-widget-panel glass-panel" role="dialog" aria-label="Staff Decision Support Console">
          <StaffChat token={token} onLogout={onLogout} />
        </div>
      )}

      <div className="chat-widget-launcher">
        {!open && (
          <span className="chat-bubble-hint" aria-hidden="true">Decision Support Console</span>
        )}
        <button
          className={`chat-fab ${open ? "open" : ""}`}
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close Staff Decision Support Console" : "Open Staff Decision Support Console"}
          aria-expanded={open}
        >
          {open ? "▾" : "🤖"}
        </button>
      </div>
    </div>
  );
}
