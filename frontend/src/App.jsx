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
        
        if (viewMode === "staff") {
          const alertsRes = await fetch(`${API_BASE}/api/v1/staff/alerts`);
          if (alertsRes.ok) {
            const data = await alertsRes.json();
            setAlerts(data);
          }
        } else {
          setAlerts([]); // Clear alerts when not in staff mode
        }
      } catch (err) {
        console.error("Error polling stadium state:", err);
      }
    };
    
    fetchData(); // Initial load
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [viewMode]);

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
        ) : (
          <StaffDashboard zones={zones} alerts={alerts} gates={gates} />
        )}
      </main>
    </div>
  );
}
