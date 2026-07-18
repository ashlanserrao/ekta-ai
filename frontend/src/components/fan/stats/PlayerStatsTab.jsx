import React, { useState, useMemo } from "react";
import { Trophy, Target, Shield, Star, Users, ChevronDown } from "lucide-react";
import PLAYERS from "../../../data/players.json";
import TEAMS from "../../../data/teams.json";
import PlayerDetailModal from "./PlayerDetailModal";
import { ratingBadgeClass, sortByKey } from "./statsHelpers";

const teamById = Object.fromEntries(TEAMS.map((t) => [t.id, t]));
const POSITIONS = [...new Set(PLAYERS.map((p) => p.position))].sort();

const COLUMNS = [
  { key: "name", label: "Player", get: (p) => p.name },
  { key: "team", label: "Team", get: (p) => teamById[p.teamId]?.name || "" },
  { key: "position", label: "Position", get: (p) => p.position },
  { key: "apps", label: "Apps", get: (p) => p.tournamentStats.appearances },
  { key: "goals", label: "Goals", get: (p) => p.tournamentStats.goals },
  { key: "assists", label: "Assists", get: (p) => p.tournamentStats.assists },
  { key: "rating", label: "Rating", get: (p) => p.overallRating },
];

const LEADERBOARDS = [
  { title: "Top Scorers", icon: Trophy, metric: (p) => p.tournamentStats.goals, unit: "" },
  { title: "Top Assists", icon: Target, metric: (p) => p.tournamentStats.assists, unit: "" },
  { title: "Most Tackles", icon: Shield, metric: (p) => p.tournamentStats.tackles, unit: "" },
  { title: "Highest Rated", icon: Star, metric: (p) => p.overallRating, unit: "" },
];

function Leaderboard({ title, icon: Icon, metric, unit, onSelectPlayer }) {
  const top = useMemo(() => [...PLAYERS].sort((a, b) => metric(b) - metric(a)).slice(0, 5), [metric]);
  return (
    <div className="glass-panel stats-panel">
      <h3 className="stats-panel-title"><Icon size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />{title}</h3>
      {top.map((p, i) => (
        <div key={p.id} className="leaderboard-row clickable-row" onClick={() => onSelectPlayer(p.id)}>
          <span className="rank">{i + 1}</span>
          <span className="leaderboard-name">{p.name}</span>
          <span className="text-small-muted">{teamById[p.teamId]?.flag}</span>
          <span className="leaderboard-value">{metric(p)}{unit}</span>
        </div>
      ))}
    </div>
  );
}

export default function PlayerStatsTab() {
  const [sortKey, setSortKey] = useState("rating");
  const [sortDir, setSortDir] = useState("desc");
  const [teamFilter, setTeamFilter] = useState("all");
  const [positionFilter, setPositionFilter] = useState("all");
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);

  const filtered = useMemo(() => {
    return PLAYERS.filter((p) =>
      (teamFilter === "all" || p.teamId === teamFilter) &&
      (positionFilter === "all" || p.position === positionFilter)
    );
  }, [teamFilter, positionFilter]);

  const rows = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sortKey);
    return sortByKey(filtered, col.get, sortDir);
  }, [filtered, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  return (
    <>
      <div className="stats-grid">
        {LEADERBOARDS.map((lb) => (
          <Leaderboard key={lb.title} {...lb} onSelectPlayer={setSelectedPlayerId} />
        ))}
      </div>

      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title"><Users size={17} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />All Players</h3>
        <div className="stats-filter-bar">
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Filter by team" value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
              <option value="all">All Teams</option>
              {TEAMS.map((t) => <option key={t.id} value={t.id}>{t.flag} {t.name}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
          <span className="select-wrapper">
            <select className="form-select select-language" aria-label="Filter by position" value={positionFilter} onChange={(e) => setPositionFilter(e.target.value)}>
              <option value="all">All Positions</option>
              {POSITIONS.map((pos) => <option key={pos} value={pos}>{pos}</option>)}
            </select>
            <ChevronDown size={16} className="select-chevron" aria-hidden="true" />
          </span>
        </div>

        {rows.length === 0 ? (
          <div className="stats-empty">No players match the selected filters.</div>
        ) : (
          <div className="table-scroll capped-table-scroll">
            <table className="stats-table">
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="sortable" onClick={() => toggleSort(c.key)}>
                      {c.label}{sortKey === c.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} className="clickable-row" onClick={() => setSelectedPlayerId(p.id)}>
                    <td>{p.name}</td>
                    <td>{teamById[p.teamId]?.flag} {teamById[p.teamId]?.shortName}</td>
                    <td>{p.position}</td>
                    <td className="num">{p.tournamentStats.appearances}</td>
                    <td className="num">{p.tournamentStats.goals}</td>
                    <td className="num">{p.tournamentStats.assists}</td>
                    <td className="num">
                      <span className={`status-badge ${ratingBadgeClass(p.overallRating)}`}>{p.overallRating}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedPlayerId && (
        <PlayerDetailModal playerId={selectedPlayerId} onClose={() => setSelectedPlayerId(null)} />
      )}
    </>
  );
}
