import React, { useState } from "react";
import { useTranslation } from "../../lib/LanguageContext";
import MatchesTab from "./schedule/MatchesTab";
import BracketTab from "./schedule/BracketTab";

const TABS = [
  { key: "matches", labelKey: "schedule.tabMatches" },
  { key: "bracket", labelKey: "schedule.tabBracket" },
];

export default function ScheduleView() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("matches");

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>{t("schedule.heading")}</h1>
        <p>{t("schedule.sub")}</p>
      </div>

      <div className="stats-tabs" role="tablist" aria-label="Schedule tabs">
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

      {activeTab === "matches" ? <MatchesTab /> : <BracketTab />}
    </div>
  );
}
