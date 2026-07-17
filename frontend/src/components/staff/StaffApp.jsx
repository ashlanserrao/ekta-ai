import React, { useState } from "react";
import OperationsCopilotView from "./OperationsCopilotView";
import LiveCrowdView from "./LiveCrowdView";
import StadiumMapView from "./StadiumMapView";
import LiveAlertsView from "./LiveAlertsView";
import StaffChatWidget from "./StaffChatWidget";

const NAV = [
  { key: "copilot", icon: "🧠", label: "Operations Copilot" },
  { key: "crowd", icon: "👥", label: "Live Crowd" },
  { key: "map", icon: "🗺️", label: "Stadium Live Map" },
  { key: "alerts", icon: "🚨", label: "Live Alerts" },
];

export default function StaffApp({ zones, alerts, gates, token, onLogout, highContrast, largeText, setHighContrast, setLargeText }) {
  const [activeView, setActiveView] = useState("copilot");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const go = (key) => { setActiveView(key); setMobileOpen(false); };

  const renderView = () => {
    switch (activeView) {
      case "crowd": return <LiveCrowdView zones={zones} />;
      case "map": return <StadiumMapView gates={gates} zones={zones} />;
      case "alerts": return <LiveAlertsView alerts={alerts} />;
      case "copilot":
      default: return <OperationsCopilotView token={token} onLogout={onLogout} />;
    }
  };

  return (
    <div className="fan-shell">
      <button className="sidebar-toggle" onClick={() => setMobileOpen((o) => !o)} aria-label="Toggle menu">☰</button>

      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-brand" onClick={() => go("copilot")} style={{ cursor: "pointer" }}>
          <div className="logo-badge">EKTA 26</div>
          <div>
            <div className="logo-text">EktaAI</div>
            <div className="logo-sub">Staff Operations</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <button
              key={item.key}
              className={`sidebar-item ${activeView === item.key ? "active" : ""}`}
              onClick={() => go(item.key)}
              aria-current={activeView === item.key ? "page" : undefined}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div style={{ position: "relative" }}>
          <button
            className={`sidebar-item ${settingsOpen ? "active" : ""}`}
            onClick={() => setSettingsOpen((o) => !o)}
            aria-expanded={settingsOpen}
          >
            <span className="sidebar-icon">⚙️</span>
            <span>Settings</span>
          </button>

          {settingsOpen && (
            <div className="glass-panel" style={{
              position: "absolute", bottom: "100%", left: 0, marginBottom: "0.5rem", padding: "1rem",
              display: "flex", flexDirection: "column", gap: "0.75rem", zIndex: 1000, minWidth: "220px",
              textAlign: "left", border: "1px solid var(--border-active)",
            }}>
              <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-muted)", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.4rem", marginBottom: "0.25rem", fontWeight: "700" }}>
                Accessibility settings
              </h4>
              <button
                className="btn-secondary"
                onClick={() => setLargeText(!largeText)}
                aria-label={largeText ? "Disable large text size" : "Enable large text size"}
                style={{ width: "100%", justifyContent: "flex-start", fontSize: "0.9rem", border: largeText ? "2px solid var(--accent-color)" : "1px solid var(--border-color)" }}
              >
                🔍 {largeText ? "Normal Text" : "Large Text"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setHighContrast(!highContrast)}
                aria-label={highContrast ? "Disable high contrast mode" : "Enable high contrast mode"}
                style={{ width: "100%", justifyContent: "flex-start", fontSize: "0.9rem", border: highContrast ? "2px solid #ffff00" : "1px solid var(--border-color)" }}
              >
                ♿ High Contrast
              </button>
            </div>
          )}
        </div>

        <button className="sidebar-item logout" onClick={onLogout}>
          <span className="sidebar-icon">🚪</span>
          <span>Log Out</span>
        </button>
      </aside>

      {mobileOpen && <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} />}

      <main className="fan-content" id="main">
        {renderView()}
      </main>

      <StaffChatWidget token={token} onLogout={onLogout} />
    </div>
  );
}
