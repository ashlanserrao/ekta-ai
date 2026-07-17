import React, { useState, useEffect } from "react";
import StaffDashboard from "./components/StaffDashboard";
import Landing from "./components/Landing";
import FanApp from "./components/fan/FanApp";
import { API_BASE } from "./lib/api";

const DEFAULT_FAN_PROFILE = {
  fullName: "Guest Fan",
  email: "test@ektaai.app",
  city: "—",
  favoriteTeam: "Argentina",
  drink: "No preference",
  dietary: "None",
  homeGate: "Gate 1",
  language: "English",
  accessibility: false,
};

export default function App() {
  // Top-level screen: 'landing' (marketing + auth) or 'app' (fan/staff workspace)
  const [screen, setScreen] = useState("landing");
  // Which workspace once in the app: 'fan' or 'staff'
  const [viewMode, setViewMode] = useState("fan");

  // Accessibility state
  const [highContrast, setHighContrast] = useState(false);
  const [largeText, setLargeText] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Live Stadium Data
  const [gates, setGates] = useState([]);
  const [zones, setZones] = useState([]);
  const [alerts, setAlerts] = useState([]);

  // Live connection status + ticking clock for the context bar
  const [connected, setConnected] = useState(false);
  const [now, setNow] = useState(() => new Date());

  // JWT Token state (loaded strictly from sessionStorage)
  const [token, setToken] = useState(() => sessionStorage.getItem("staff_token") || "");

  // Fan profile (from onboarding, localStorage, or a demo default)
  const [fanProfile, setFanProfile] = useState(null);

  const enterApp = ({ mode, token: newToken, profile }) => {
    if (newToken) {
      sessionStorage.setItem("staff_token", newToken);
      setToken(newToken);
    }
    if (mode === "fan") {
      let prof = profile;
      if (!prof) {
        try { prof = JSON.parse(localStorage.getItem("ekta_fan_profile") || "null"); } catch { prof = null; }
      }
      setFanProfile(prof || DEFAULT_FAN_PROFILE);
    }
    setViewMode(mode);
    setScreen("app");
  };

  const goHome = () => setScreen("landing");

  const handleLogout = () => {
    sessionStorage.removeItem("staff_token");
    setToken("");
    setViewMode("fan");
    setScreen("landing");
  };

  // 1. Connect to SSE stream for gates & zones (public telemetry)
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/api/v1/stadium/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGates(data.gates);
        setZones(data.zones);
        setConnected(true);
      } catch (err) {
        console.error("Error parsing SSE status event:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource connection error:", err);
      setConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Tick the context-bar clock once per second
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // 2. Poll for staff alerts (requires auth header)
  useEffect(() => {
    if (screen !== "app" || viewMode !== "staff" || !token) {
      setAlerts([]);
      return;
    }

    const fetchAlerts = async () => {
      try {
        const alertsRes = await fetch(`${API_BASE}/api/v1/staff/alerts`, {
          headers: { "Authorization": `Bearer ${token}` },
        });
        if (alertsRes.ok) {
          setAlerts(await alertsRes.json());
        } else if (alertsRes.status === 401) {
          handleLogout();
        }
      } catch (err) {
        console.error("Error polling alerts state:", err);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, [screen, viewMode, token]);

  // Accessibility theme toggles (apply globally, incl. landing)
  useEffect(() => {
    document.body.classList.toggle("high-contrast", highContrast);
  }, [highContrast]);
  useEffect(() => {
    document.body.classList.toggle("large-text", largeText);
  }, [largeText]);

  // Landing page
  if (screen === "landing") {
    return <Landing onAuthenticated={enterApp} />;
  }

  // Fan workspace: sidebar layout, no top navbar
  if (viewMode === "fan") {
    return (
      <FanApp
        gates={gates}
        zones={zones}
        profile={fanProfile}
        onLogout={handleLogout}
        highContrast={highContrast}
        largeText={largeText}
        setHighContrast={setHighContrast}
        setLargeText={setLargeText}
      />
    );
  }

  const initialLoading = gates.length === 0 || zones.length === 0;

  const LoadingSpinner = () => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: "1.5rem" }}>
      <div style={{
        width: "50px",
        height: "50px",
        border: "5px solid rgba(255, 255, 255, 0.1)",
        borderTop: "5px solid var(--accent-color)",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
      }} />
      <p style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>Connecting to Digital Twin Live Feeds...</p>
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );

  return (
    <div>
      <a href="#main" className="skip-link">Skip to main content</a>

      {/* Header Panel */}
      <header role="banner">
        <div className="logo-container" onClick={goHome} style={{ cursor: "pointer" }} title="Back to home">
          <div className="logo-badge">EKTA 26</div>
          <div>
            <h1 className="logo-text">EktaAI</h1>
            <div className="logo-sub">{viewMode === "staff" ? "Staff Operations" : "Fan Assistant"}</div>
          </div>
        </div>

        <div className="nav-controls" style={{ position: "relative" }}>
          <button className="btn-secondary" onClick={goHome} aria-label="Back to home">← Home</button>

          {viewMode === "staff" && token && (
            <button
              className="btn-secondary"
              onClick={handleLogout}
              aria-label="Log out of Staff Portal"
              style={{ background: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.2)", color: "var(--color-high)" }}
            >
              Log Out
            </button>
          )}

          <button
            className={`btn-secondary ${settingsOpen ? "active-tab" : ""}`}
            onClick={() => setSettingsOpen(!settingsOpen)}
            aria-label="Toggle settings popover"
          >
            ⚙️ Settings
          </button>

          {settingsOpen && (
            <div className="glass-panel" style={{
              position: "absolute", top: "100%", right: 0, marginTop: "0.5rem", padding: "1rem",
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
      </header>

      {/* Live context bar */}
      <div className="context-bar" role="status" aria-live="polite">
        <div className="context-left">
          <span className={`live-dot ${connected ? "live" : "down"}`} aria-hidden="true"></span>
          <span className="context-status">{connected ? "Twin Live" : "Reconnecting…"}</span>
          <span className="context-sep">·</span>
          <span className="context-meta">FIFA World Cup 2026 · Match Day</span>
          <span className="context-sep context-hide-sm">·</span>
          <span className="context-meta context-hide-sm">{zones.length} zones · {gates.length} gates monitored</span>
        </div>
        <div className="context-right">
          <span className="context-clock">{now.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Main Container */}
      <main role="main" id="main">
        {!token || initialLoading ? (
          <LoadingSpinner />
        ) : (
          <StaffDashboard zones={zones} alerts={alerts} gates={gates} token={token} onLogout={handleLogout} />
        )}
      </main>
    </div>
  );
}
