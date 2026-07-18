import React, { useState, useMemo } from "react";
import { ClipboardList, Scale, ChevronDown } from "lucide-react";
import TEAMS from "../../../data/teams.json";
import TeamDetailModal from "./TeamDetailModal";
import RadarChartView from "./RadarChartView";
import { formBadgeClass, sortByKey } from "./statsHelpers";

const COLUMNS = [
  { key: "name", label: "Team", get: (t) => t.name },
  { key: "p", label: "P", get: (t) => t.stats.matchesPlayed },
  { key: "w", label: "W", get: (t) => t.stats.wins },
  { key: "d", label: "D", get: (t) => t.stats.draws },
  { key: "l", label: "L", get: (t) => t.stats.losses },
  { key: "gf", label: "GF", get: (t) => t.stats.goalsFor },
  { key: "ga", label: "GA", get: (t) => t.stats.goalsAgainst },
  { key: "gd", label: "GD", get: (t) => t.stats.goalDifference },
  { key: "pts", label: "Pts", get: (t) => t.stats.points },
];

const COMPARE_AXES = [
  { key: "possessionAvg", label: "Possession" },
  { key: "passAccuracy", label: "Passing" },
  { key: "shotsPerGame", label: "Shooting" },
  { key: "tacklesPerGame", label: "Defense" },
  { key: "cornersPerGame", label: "Corners" },
];

export default function TeamStatsTab() {
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

  const teamA = TEAMS.find((t) => t.id === compareAId);
  const teamB = TEAMS.find((t) => t.id === compareBId);

  return (
    <>
      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title"><ClipboardList size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />League Table</h3>
        <div className="table-scroll">
          <table className="stats-table">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} className="sortable" onClick={() => toggleSort(c.key)}>
                    {c.label}{sortKey === c.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                ))}
                <th>Form</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className="clickable-row" onClick={() => setSelectedTeamId(t.id)}>
                  <td>{t.flag} {t.name}</td>
                  <td className="num">{t.stats.matchesPlayed}</td>
                  <td className="num">{t.stats.wins}</td>
                  <td className="num">{t.stats.draws}</td>
                  <td className="num">{t.stats.losses}</td>
                  <td className="num">{t.stats.goalsFor}</td>
                  <td className="num">{t.stats.goalsAgainst}</td>
                  <td className="num">{t.stats.goalDifference}</td>
                  <td className="num bold">{t.stats.points}</td>
                  <td>
                    <div className="form-badges">
                      {t.form.map((r, i) => (
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
        <h3 className="stats-panel-title"><Scale size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />Compare Teams</h3>
        <div className="team-compare-picker">
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Compare team A" value={compareAId} onChange={(e) => setCompareAId(e.target.value)}>
              {TEAMS.map((t) => <option key={t.id} value={t.id}>{t.flag} {t.name}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
          <span className="compare-vs">vs</span>
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Compare team B" value={compareBId} onChange={(e) => setCompareBId(e.target.value)}>
              {TEAMS.map((t) => <option key={t.id} value={t.id}>{t.flag} {t.name}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
        </div>
        {teamA && teamB && (
          <RadarChartView
            axes={COMPARE_AXES}
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
