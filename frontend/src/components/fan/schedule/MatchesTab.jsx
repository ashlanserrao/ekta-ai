import React, { useState, useMemo } from "react";
import MATCHES from "../../../data/matches.json";
import MatchDetailModal from "./MatchDetailModal";
import { roundLabel, formatScore } from "./scheduleHelpers";

const SUB_TABS = [
  { key: "ongoing", label: "Ongoing" },
  { key: "recent", label: "Recent" },
  { key: "upcoming", label: "Upcoming" },
];

const MATCHERS = {
  ongoing: (m) => m.status === "live",
  recent: (m) => m.status === "completed",
  upcoming: (m) => m.status === "upcoming" || m.status === "tbd",
};

export default function MatchesTab() {
  const hasLive = MATCHES.some((m) => m.status === "live");
  const [subTab, setSubTab] = useState(hasLive ? "ongoing" : "recent");
  const [selectedMatch, setSelectedMatch] = useState(null);

  const rows = useMemo(() => {
    const filtered = MATCHES.filter(MATCHERS[subTab]);
    return [...filtered].sort((a, b) =>
      subTab === "recent" ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date)
    );
  }, [subTab]);

  return (
    <div className="glass-panel stats-panel">
      <div className="stats-tabs" role="tablist" aria-label="Match status">
        {SUB_TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={subTab === t.key}
            className={`stats-tab ${subTab === t.key ? "active" : ""}`}
            onClick={() => setSubTab(t.key)}
          >
            {t.label}{t.key === "ongoing" && hasLive ? " 🔴" : ""}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="stats-empty">No {SUB_TABS.find((t) => t.key === subTab).label.toLowerCase()} matches right now.</div>
      ) : subTab === "upcoming" ? (
        <div className="schedule-list match-list">
          {rows.map((m) => (
            <div key={m.id} className="glass-panel schedule-row clickable-row" onClick={() => setSelectedMatch(m)}>
              <div className="schedule-date">
                <span className="schedule-day">{m.date}</span>
                <span className="schedule-time">{m.time}</span>
              </div>
              <div className="schedule-match">
                <span className="schedule-team">{m.teamA ? `${m.teamA.flag} ${m.teamA.name}` : "TBD"}</span>
                <span className="schedule-vs">vs</span>
                <span className="schedule-team">{m.teamB ? `${m.teamB.name} ${m.teamB.flag}` : "TBD"}</span>
              </div>
              <div className="schedule-meta">
                <span className={`schedule-stage ${m.round === "F" ? "final" : ""}`}>{roundLabel(m.round)}</span>
                <span className="schedule-venue">📍 {m.venue}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="results-grid match-list">
          {rows.map((m) => (
            <div key={m.id} className="result-card clickable-row" onClick={() => setSelectedMatch(m)}>
              {m.status === "live" && <span className="status-badge high live-badge">LIVE</span>}
              <span className="result-team">{m.teamA.flag} {m.teamA.name}</span>
              <span className="result-score">{formatScore(m)}</span>
              <span className="result-team away">{m.teamB.name} {m.teamB.flag}</span>
              <span className="result-stage">{roundLabel(m.round)}</span>
            </div>
          ))}
        </div>
      )}

      {selectedMatch && <MatchDetailModal match={selectedMatch} onClose={() => setSelectedMatch(null)} />}
    </div>
  );
}
