import React, { useState } from "react";
import MatchesTab from "./schedule/MatchesTab";
import BracketTab from "./schedule/BracketTab";

const TABS = [
  { key: "matches", label: "Matches" },
  { key: "bracket", label: "Bracket" },
];

export default function ScheduleView() {
  const [activeTab, setActiveTab] = useState("matches");

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Match Schedule</h1>
        <p>FIFA World Cup 2026 — results, fixtures, and the road to the final.</p>
      </div>

      <div className="stats-tabs" role="tablist" aria-label="Schedule tabs">
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

      {activeTab === "matches" ? <MatchesTab /> : <BracketTab />}
    </div>
  );
}
