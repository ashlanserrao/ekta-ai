import React, { useState } from "react";
import MapView from "./MapView";
import StatsView from "./StatsView";
import TicketView from "./TicketView";
import ScheduleView from "./ScheduleView";
import ProfileView from "./ProfileView";
import SettingsView from "./SettingsView";
import ChatWidget from "./ChatWidget";

const NAV = [
  { key: "map", icon: "🗺️", label: "Live Stadium Map" },
  { key: "stats", icon: "📊", label: "Player Stats" },
  { key: "ticket", icon: "🎫", label: "My Ticket" },
  { key: "schedule", icon: "📅", label: "Match Schedule" },
  { key: "profile", icon: "👤", label: "Profile" },
  { key: "settings", icon: "⚙️", label: "Settings" },
];

export default function FanApp({ gates, zones, profile, onLogout, highContrast, largeText, setHighContrast, setLargeText }) {
  const [activeView, setActiveView] = useState("map");
  const [activeRoute, setActiveRoute] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  // A route generated in the chat lights up on the map — jump there to show it.
  const handleRoute = (route) => {
    setActiveRoute(route);
    setActiveView("map");
  };

  const go = (key) => { setActiveView(key); setMobileOpen(false); };

  const renderView = () => {
    switch (activeView) {
      case "stats": return <StatsView />;
      case "ticket": return <TicketView profile={profile} />;
      case "schedule": return <ScheduleView />;
      case "profile": return <ProfileView profile={profile} />;
      case "settings": return <SettingsView highContrast={highContrast} largeText={largeText} setHighContrast={setHighContrast} setLargeText={setLargeText} />;
      case "map":
      default: return <MapView gates={gates} zones={zones} activeRoute={activeRoute} />;
    }
  };

  return (
    <div className="fan-shell">
      <button className="sidebar-toggle" onClick={() => setMobileOpen((o) => !o)} aria-label="Toggle menu">☰</button>

      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-brand" onClick={() => go("map")} style={{ cursor: "pointer" }}>
          <div className="logo-badge">EKTA 26</div>
          <div>
            <div className="logo-text">EktaAI</div>
            <div className="logo-sub">Fan Portal</div>
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

        <button className="sidebar-item logout" onClick={onLogout}>
          <span className="sidebar-icon">🚪</span>
          <span>Log Out</span>
        </button>
      </aside>

      {mobileOpen && <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} />}

      <main className="fan-content" id="main">
        {renderView()}
      </main>

      <ChatWidget onRoute={handleRoute} />
    </div>
  );
}
