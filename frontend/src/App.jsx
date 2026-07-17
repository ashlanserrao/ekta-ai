import React, { useState, useEffect } from "react";
import Landing from "./components/Landing";
import FanApp from "./components/fan/FanApp";
import StaffApp from "./components/staff/StaffApp";
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

  // Live Stadium Data
  const [gates, setGates] = useState([]);
  const [zones, setZones] = useState([]);
  const [alerts, setAlerts] = useState([]);

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

  // Staff workspace: sidebar layout, no top navbar
  const initialLoading = gates.length === 0 || zones.length === 0;

  if (!token || initialLoading) {
    return (
      <div>
        <a href="#main" className="skip-link">Skip to main content</a>
        <main role="main" id="main" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: "1.5rem" }}>
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
        </main>
      </div>
    );
  }

  return (
    <StaffApp
      zones={zones}
      alerts={alerts}
      gates={gates}
      token={token}
      onLogout={handleLogout}
      highContrast={highContrast}
      largeText={largeText}
      setHighContrast={setHighContrast}
      setLargeText={setLargeText}
    />
  );
}
