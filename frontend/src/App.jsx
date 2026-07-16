import React, { useState, useEffect } from "react";
import FanAssistant from "./components/FanAssistant";
import StaffDashboard from "./components/StaffDashboard";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  // View mode: 'fan' or 'staff'
  const [viewMode, setViewMode] = useState("fan");
  
  // Theme state
  const [highContrast, setHighContrast] = useState(false);
  
  // Accessibility text size state
  const [largeText, setLargeText] = useState(false);
  
  // Settings dropdown visibility state
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  // Live Stadium Data
  const [gates, setGates] = useState([]);
  const [zones, setZones] = useState([]);
  const [alerts, setAlerts] = useState([]);
  
  // JWT Token state (loaded strictly from sessionStorage)
  const [token, setToken] = useState(() => sessionStorage.getItem("staff_token") || "");

  const handleLogout = () => {
    sessionStorage.removeItem("staff_token");
    setToken("");
  };

  // 1. Connect to SSE stream for gates & zones (Public telemetry data)
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/api/v1/stadium/stream`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGates(data.gates);
        setZones(data.zones);
      } catch (err) {
        console.error("Error parsing SSE status event:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource connection error:", err);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // 2. Poll for staff alerts (Requires auth header)
  useEffect(() => {
    if (viewMode !== "staff" || !token) {
      setAlerts([]);
      return;
    }

    const fetchAlerts = async () => {
      try {
        const alertsRes = await fetch(`${API_BASE}/api/v1/staff/alerts`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (alertsRes.ok) {
          const data = await alertsRes.json();
          setAlerts(data);
        } else if (alertsRes.status === 401) {
          handleLogout();
        }
      } catch (err) {
        console.error("Error polling alerts state:", err);
      }
    };

    fetchAlerts(); // Initial call
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, [viewMode, token]);

  // Apply accessibility high-contrast theme
  useEffect(() => {
    if (highContrast) {
      document.body.classList.add("high-contrast");
    } else {
      document.body.classList.remove("high-contrast");
    }
  }, [highContrast]);

  // Apply accessibility text size theme
  useEffect(() => {
    if (largeText) {
      document.body.classList.add("large-text");
    } else {
      document.body.classList.remove("large-text");
    }
  }, [largeText]);

  // Initial loading state (gates/zones are empty on first fetch window)
  const initialLoading = gates.length === 0 || zones.length === 0;

  const LoadingSpinner = () => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: "1.5rem" }}>
      <div style={{
        width: "50px",
        height: "50px",
        border: "5px solid rgba(255, 255, 255, 0.1)",
        borderTop: "5px solid var(--accent-color)",
        borderRadius: "50%",
        animation: "spin 1s linear infinite"
      }} />
      <p style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>Connecting to Digital Twin Live Feeds...</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );

  return (
    <div>
      <a href="#main" className="skip-link">Skip to main content</a>
      {/* Header Panel */}
      <header role="banner">
        <div className="logo-container">
          <div className="logo-badge">EKTA 26</div>
          <div>
            <h1 className="logo-text">EktaAI</h1>
            <div className="logo-sub">Stadium Operations Twin</div>
          </div>
        </div>
        
        <div className="nav-controls" style={{ position: "relative" }}>
          <button 
            className={`btn-secondary ${viewMode === "fan" ? "active-tab" : ""}`}
            onClick={() => setViewMode("fan")}
            aria-label="Switch to Fan Assistant view"
          >
            Fan Assistant
          </button>
          
          <button 
            className={`btn-secondary ${viewMode === "staff" ? "active-tab" : ""}`}
            onClick={() => setViewMode("staff")}
            aria-label="Switch to Staff Operations Dashboard view"
          >
            Staff Portal
          </button>
          
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

          {/* Collapsed Settings Popover */}
          <button 
            className={`btn-secondary ${settingsOpen ? "active-tab" : ""}`}
            onClick={() => setSettingsOpen(!settingsOpen)}
            aria-label="Toggle settings popover"
          >
            ⚙️ Settings
          </button>

          {settingsOpen && (
            <div className="glass-panel" style={{
              position: "absolute",
              top: "100%",
              right: 0,
              marginTop: "0.5rem",
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
              zIndex: 1000,
              minWidth: "220px",
              textAlign: "left",
              border: "1px solid var(--border-active)"
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
      
      {/* Main Container */}
      <main role="main" id="main">
        {viewMode === "fan" ? (
          initialLoading ? (
            <LoadingSpinner />
          ) : (
            <FanAssistant gates={gates} zones={zones} />
          )
        ) : !token ? (
          <StaffLogin onLoginSuccess={(newToken) => {
            sessionStorage.setItem("staff_token", newToken);
            setToken(newToken);
          }} />
        ) : initialLoading ? (
          <LoadingSpinner />
        ) : (
          <StaffDashboard zones={zones} alerts={alerts} gates={gates} token={token} onLogout={handleLogout} />
        )}
      </main>
    </div>
  );
}

function StaffLogin({ onLoginSuccess }) {
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!passcode.trim()) return;
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/staff/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode })
      });

      if (res.ok) {
        const data = await res.json();
        onLoginSuccess(data.token);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || "Authentication failed. Invalid passcode.");
      }
    } catch (err) {
      console.error(err);
      setError("Network connection issue. Please verify backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh", padding: "1rem" }}>
      <div className="glass-panel" style={{ padding: "2.5rem", maxWidth: "450px", width: "100%", textAlign: "center", border: "1px solid rgba(255,255,255,0.12)" }}>
        <div style={{
          display: "inline-block",
          background: "linear-gradient(135deg, var(--accent-color), var(--accent-secondary))",
          color: "white",
          borderRadius: "12px",
          padding: "0.75rem",
          marginBottom: "1.5rem",
          fontSize: "2rem"
        }}>
          🔐
        </div>
        <h2 style={{ fontSize: "1.75rem", marginBottom: "0.5rem", fontWeight: "700", background: "linear-gradient(135deg, #ffffff, var(--text-secondary))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Staff Access Gate
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: "2rem" }}>
          Please enter the passcode to access the operations intelligence dashboard.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ textAlign: "left" }}>
            <label htmlFor="passcode-input" style={{ fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: "0.5rem", fontWeight: "600" }}>
              Passcode
            </label>
            <input
              id="passcode-input"
              type="password"
              className="chat-input"
              placeholder="••••••••"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              style={{ width: "100%", padding: "0.85rem 1.2rem", fontSize: "1rem", borderRadius: "10px" }}
              disabled={loading}
              autoFocus
            />
          </div>

          {error && (
            <div style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "var(--color-high)",
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              fontSize: "0.85rem",
              textAlign: "left"
            }}>
              ⚠️ {error}
            </div>
          )}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", display: "flex", justifyContent: "center", padding: "0.85rem", borderRadius: "10px", marginTop: "0.5rem", fontSize: "1rem" }}
            disabled={loading || !passcode.trim()}
          >
            {loading ? "Verifying..." : "Authenticate"}
          </button>
        </form>
      </div>
    </div>
  );
}
