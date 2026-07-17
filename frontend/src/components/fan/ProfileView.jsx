import React from "react";

const initials = (name) =>
  (name || "Guest Fan").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

export default function ProfileView({ profile }) {
  const p = profile || {};
  const details = [
    { label: "Email", value: p.email },
    { label: "City", value: p.city },
    { label: "Favorite team", value: p.favoriteTeam },
    { label: "Home gate", value: p.homeGate },
    { label: "Drink preference", value: p.drink },
    { label: "Dietary preference", value: p.dietary },
    { label: "Preferred language", value: p.language },
    { label: "Accessible routes", value: p.accessibility ? "Enabled" : "Not required" },
  ];

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Profile</h1>
        <p>Your fan account and match-day preferences.</p>
      </div>

      <div className="glass-panel profile-card">
        <div className="profile-header">
          <div className="profile-avatar">{initials(p.fullName)}</div>
          <div>
            <h2 className="profile-name">{p.fullName || "Guest Fan"}</h2>
            <span className="profile-role">🎫 Fan · World Cup 2026</span>
          </div>
        </div>

        <div className="profile-details">
          {details.map((d) => (
            <div key={d.label} className="profile-row">
              <span className="profile-key">{d.label}</span>
              <span className="profile-val">{d.value || "—"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
