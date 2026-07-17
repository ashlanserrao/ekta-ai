import React, { useState } from "react";
import TeamStatsTab from "./stats/TeamStatsTab";
import PlayerStatsTab from "./stats/PlayerStatsTab";

const TABS = [
  { key: "team", label: "Team Stats" },
  { key: "player", label: "Player Stats" },
];

export default function StatsView() {
  const [activeTab, setActiveTab] = useState("team");

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Stats</h1>
        <p>FIFA World Cup 2026 — team and player statistics for the tournament.</p>
      </div>

      <div className="stats-tabs" role="tablist" aria-label="Stats tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={activeTab === t.key}
            className={`stats-tab ${activeTab === t.key ? "active" : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "team" ? <TeamStatsTab /> : <PlayerStatsTab />}
    </div>
  );
}
