import React, { useState } from "react";
import FanChat from "./FanChat";

// Floating bottom-right assistant. Collapsed = a circular robot button with an
// "Ask me anything" bubble; expanded = the full chat panel.
export default function ChatWidget({ onRoute }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-widget-panel glass-panel" role="dialog" aria-label="Fan assistant chat">
          <FanChat onRoute={onRoute} />
        </div>
      )}

      <div className="chat-widget-launcher">
        {!open && (
          <span className="chat-bubble-hint" aria-hidden="true">Ask me anything</span>
        )}
        <button
          className={`chat-fab ${open ? "open" : ""}`}
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close assistant" : "Open assistant"}
          aria-expanded={open}
        >
          {open ? "▾" : "🤖"}
        </button>
      </div>
    </div>
  );
}
