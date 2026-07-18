import React, { useState } from "react";
import { useTranslation } from "../../lib/LanguageContext";
import TeamStatsTab from "./stats/TeamStatsTab";
import PlayerStatsTab from "./stats/PlayerStatsTab";

const TABS = [
  { key: "team", labelKey: "stats.tabTeam" },
  { key: "player", labelKey: "stats.tabPlayer" },
];

export default function StatsView() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("team");

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>{t("stats.heading")}</h1>
        <p>{t("stats.sub")}</p>
      </div>

      <div className="stats-tabs" role="tablist" aria-label="Stats tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            className={`stats-tab ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {activeTab === "team" ? <TeamStatsTab /> : <PlayerStatsTab />}
    </div>
  );
}
