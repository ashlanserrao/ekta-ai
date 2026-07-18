import React, { useState, useMemo } from "react";
import { MapPin } from "lucide-react";
import MATCHES from "../../../data/matches.json";
import { useTranslation } from "../../../lib/LanguageContext";
import MatchDetailModal from "./MatchDetailModal";
import { roundLabel, formatScore } from "./scheduleHelpers";

const SUB_TABS = [
  { key: "ongoing", labelKey: "schedule.subTabOngoing" },
  { key: "recent", labelKey: "schedule.subTabRecent" },
  { key: "upcoming", labelKey: "schedule.subTabUpcoming" },
];

const MATCHERS = {
  ongoing: (m) => m.status === "live",
  recent: (m) => m.status === "completed",
  upcoming: (m) => m.status === "upcoming" || m.status === "tbd",
};

export default function MatchesTab() {
  const { t } = useTranslation();
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
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={subTab === tab.key}
            className={`stats-tab ${subTab === tab.key ? "active" : ""}`}
            onClick={() => setSubTab(tab.key)}
          >
            {t(tab.labelKey)}{tab.key === "ongoing" && hasLive ? <span className="live-dot" aria-hidden="true" /> : ""}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="stats-empty">{t("schedule.noMatches", { status: t(SUB_TABS.find((tab) => tab.key === subTab).labelKey).toLowerCase() })}</div>
      ) : subTab === "upcoming" ? (
        <div className="schedule-list match-list">
          {rows.map((m) => (
            <div key={m.id} className="glass-panel schedule-row clickable-row" onClick={() => setSelectedMatch(m)}>
              <div className="schedule-date">
                <span className="schedule-day">{m.date}</span>
                <span className="schedule-time">{m.time}</span>
              </div>
              <div className="schedule-match">
                <span className="schedule-team">{m.teamA ? `${m.teamA.flag} ${m.teamA.name}` : t("schedule.tbd")}</span>
                <span className="schedule-vs">vs</span>
                <span className="schedule-team">{m.teamB ? `${m.teamB.name} ${m.teamB.flag}` : t("schedule.tbd")}</span>
              </div>
              <div className="schedule-meta">
                <span className={`schedule-stage ${m.round === "F" ? "final" : ""}`}>{roundLabel(m.round, t)}</span>
                <span className="schedule-venue"><MapPin size={13} style={{ verticalAlign: "-2px", marginRight: "0.25rem" }} />{m.venue}</span>
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
              <span className="result-stage">{roundLabel(m.round, t)}</span>
            </div>
          ))}
        </div>
      )}

      {selectedMatch && <MatchDetailModal match={selectedMatch} onClose={() => setSelectedMatch(null)} />}
    </div>
  );
}
