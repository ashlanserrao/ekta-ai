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
  
  // Live Stadium Data (polled every 3 seconds)
  const [gates, setGates] = useState([]);
  const [zones, setZones] = useState([]);
  const [alerts, setAlerts] = useState([]);
  
  // JWT Token state (loaded strictly from sessionStorage)
  const [token, setToken] = useState(() => sessionStorage.getItem("staff_token") || "");

  const handleLogout = () => {
    sessionStorage.removeItem("staff_token");
    setToken("");
  };

  // Fetch Stadium Data (Poll)
  useEffect(() => {
    const fetchData = async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/api/v1/stadium/status`);
        if (statusRes.ok) {
          const data = await statusRes.json();
          setGates(data.gates);
          setZones(data.zones);
        }
        
        if (viewMode === "staff" && token) {
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
        } else {
          setAlerts([]); // Clear alerts when not in staff mode or not logged in
        }
      } catch (err) {
        console.error("Error polling stadium state:", err);
      }
    };
    
    fetchData(); // Initial load
    const interval = setInterval(fetchData, 3000);
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

  return (
    <div>
      {/* Header Panel */}
      <header role="banner">
        <div className="logo-container">
          <div className="logo-badge">FIFA 26</div>
          <div>
            <h1 className="logo-text">EktaAI</h1>
            <div className="logo-sub">Stadium Operations Twin</div>
          </div>
        </div>
        
        <div className="nav-controls">
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

          <button 
            className="btn-secondary"
            onClick={() => setLargeText(!largeText)}
            aria-label={largeText ? "Disable large text size" : "Enable large text size"}
            style={{ border: largeText ? "2px solid var(--accent-color)" : "1px solid var(--border-color)" }}
          >
            🔍 {largeText ? "Normal Text" : "Large Text"}
          </button>

          <button 
            className="btn-secondary"
            onClick={() => setHighContrast(!highContrast)}
            aria-label={highContrast ? "Disable high contrast mode" : "Enable high contrast mode"}
            style={{ border: highContrast ? "2px solid #ffff00" : "1px solid var(--border-color)" }}
          >
            ♿ High Contrast
          </button>
        </div>
      </header>
      
      {/* Main Container */}
      <main role="main">
        {viewMode === "fan" ? (
          <FanAssistant gates={gates} zones={zones} />
        ) : token ? (
          <StaffDashboard zones={zones} alerts={alerts} gates={gates} token={token} onLogout={handleLogout} />
        ) : (
          <StaffLogin onLoginSuccess={(newToken) => {
            sessionStorage.setItem("staff_token", newToken);
            setToken(newToken);
          }} />
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
