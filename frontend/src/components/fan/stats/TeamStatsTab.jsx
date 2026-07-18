import React, { useState, useMemo } from "react";
import { ClipboardList, Scale, ChevronDown } from "lucide-react";
import TEAMS from "../../../data/teams.json";
import { useTranslation } from "../../../lib/LanguageContext";
import TeamDetailModal from "./TeamDetailModal";
import RadarChartView from "./RadarChartView";
import { formBadgeClass, sortByKey } from "./statsHelpers";

const COLUMNS = [
  { key: "name", labelKey: "stats.colTeam", get: (t) => t.name },
  { key: "p", labelKey: "stats.colP", get: (t) => t.stats.matchesPlayed },
  { key: "w", labelKey: "stats.colW", get: (t) => t.stats.wins },
  { key: "d", labelKey: "stats.colD", get: (t) => t.stats.draws },
  { key: "l", labelKey: "stats.colL", get: (t) => t.stats.losses },
  { key: "gf", labelKey: "stats.colGF", get: (t) => t.stats.goalsFor },
  { key: "ga", labelKey: "stats.colGA", get: (t) => t.stats.goalsAgainst },
  { key: "gd", labelKey: "stats.colGD", get: (t) => t.stats.goalDifference },
  { key: "pts", labelKey: "stats.colPts", get: (t) => t.stats.points },
];

const COMPARE_AXES = [
  { key: "possessionAvg", labelKey: "stats.axisPossession" },
  { key: "passAccuracy", labelKey: "stats.axisPassing" },
  { key: "shotsPerGame", labelKey: "stats.axisShooting" },
  { key: "tacklesPerGame", labelKey: "stats.axisDefense" },
  { key: "cornersPerGame", labelKey: "stats.axisCorners" },
];

export default function TeamStatsTab() {
  const { t } = useTranslation();
  const [sortKey, setSortKey] = useState("pts");
  const [sortDir, setSortDir] = useState("desc");
  const [selectedTeamId, setSelectedTeamId] = useState(null);
  const [compareAId, setCompareAId] = useState(TEAMS[0].id);
  const [compareBId, setCompareBId] = useState(TEAMS[1].id);

  const rows = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sortKey);
    return sortByKey(TEAMS, col.get, sortDir);
  }, [sortKey, sortDir]);

  const toggleSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const teamA = TEAMS.find((team) => team.id === compareAId);
  const teamB = TEAMS.find((team) => team.id === compareBId);

  return (
    <>
      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title"><ClipboardList size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />{t("stats.leagueTable")}</h3>
        <div className="table-scroll">
          <table className="stats-table">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} className="sortable" onClick={() => toggleSort(c.key)}>
                    {t(c.labelKey)}{sortKey === c.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                ))}
                <th>{t("stats.form")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((team) => (
                <tr key={team.id} className="clickable-row" onClick={() => setSelectedTeamId(team.id)}>
                  <td>{team.flag} {team.name}</td>
                  <td className="num">{team.stats.matchesPlayed}</td>
                  <td className="num">{team.stats.wins}</td>
                  <td className="num">{team.stats.draws}</td>
                  <td className="num">{team.stats.losses}</td>
                  <td className="num">{team.stats.goalsFor}</td>
                  <td className="num">{team.stats.goalsAgainst}</td>
                  <td className="num">{team.stats.goalDifference}</td>
                  <td className="num bold">{team.stats.points}</td>
                  <td>
                    <div className="form-badges">
                      {team.form.map((r, i) => (
                        <span key={i} className={`status-badge ${formBadgeClass(r)} form-badge`}>{r}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title"><Scale size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />{t("stats.compareTeams")}</h3>
        <div className="team-compare-picker">
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Compare team A" value={compareAId} onChange={(e) => setCompareAId(e.target.value)}>
              {TEAMS.map((team) => <option key={team.id} value={team.id}>{team.flag} {team.name}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
          <span className="compare-vs">{t("stats.vs")}</span>
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Compare team B" value={compareBId} onChange={(e) => setCompareBId(e.target.value)}>
              {TEAMS.map((team) => <option key={team.id} value={team.id}>{team.flag} {team.name}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
        </div>
        {teamA && teamB && (
          <RadarChartView
            axes={COMPARE_AXES.map((a) => ({ key: a.key, label: t(a.labelKey) }))}
            maxValue={100}
            series={[
              { name: teamA.name, color: "#2563eb", values: teamA.stats },
              { name: teamB.name, color: "#06b6d4", values: teamB.stats },
            ]}
          />
        )}
      </div>

      {selectedTeamId && (
        <TeamDetailModal teamId={selectedTeamId} onClose={() => setSelectedTeamId(null)} />
      )}
    </>
  );
}
