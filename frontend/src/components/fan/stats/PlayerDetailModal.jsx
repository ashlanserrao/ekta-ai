import React from "react";
import { X } from "lucide-react";
import PLAYERS from "../../../data/players.json";
import TEAMS from "../../../data/teams.json";
import RadarChartView from "./RadarChartView";
import { ratingBadgeClass, initials } from "./statsHelpers";

const teamById = Object.fromEntries(TEAMS.map((t) => [t.id, t]));

const FIFA_AXES = [
  { key: "pace", label: "Pace" },
  { key: "shooting", label: "Shooting" },
  { key: "passing", label: "Passing" },
  { key: "dribbling", label: "Dribbling" },
  { key: "defending", label: "Defending" },
  { key: "physical", label: "Physical" },
];

export default function PlayerDetailModal({ playerId, onClose }) {
  const player = PLAYERS.find((p) => p.id === playerId);
  if (!player) return null;
  const team = teamById[player.teamId];
  const s = player.tournamentStats;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={`${player.name} player card`}>
      <div className="modal-card glass-panel fifa-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close"><X size={20} /></button>

        <div className="fifa-card-header">
          <div className="profile-avatar">{initials(player.name)}</div>
          <div>
            <h2 className="modal-title">{player.name}</h2>
            <p className="modal-sub">{team?.flag} {team?.name} · {player.position} · #{player.jerseyNumber}</p>
          </div>
          <span className={`status-badge ${ratingBadgeClass(player.overallRating)} fifa-rating-badge`}>{player.overallRating}</span>
        </div>

        <RadarChartView
          axes={FIFA_AXES}
          maxValue={99}
          series={[{ name: player.name, color: "#2563eb", values: player.fifaAttributes }]}
        />

        <h4 className="stats-panel-title">Tournament Stats</h4>
        <div className="profile-details">
          <div className="profile-row"><span className="profile-key">Appearances</span><span className="profile-val">{s.appearances}</span></div>
          <div className="profile-row"><span className="profile-key">Minutes Played</span><span className="profile-val">{s.minutesPlayed}</span></div>
          <div className="profile-row"><span className="profile-key">Goals</span><span className="profile-val">{s.goals}</span></div>
          <div className="profile-row"><span className="profile-key">Assists</span><span className="profile-val">{s.assists}</span></div>
          <div className="profile-row"><span className="profile-key">Shots (on target)</span><span className="profile-val">{s.shots} ({s.shotsOnTarget})</span></div>
          <div className="profile-row"><span className="profile-key">Pass Accuracy</span><span className="profile-val">{s.passAccuracy}%</span></div>
          <div className="profile-row"><span className="profile-key">Key Passes</span><span className="profile-val">{s.keyPasses}</span></div>
          <div className="profile-row"><span className="profile-key">Dribbles (success)</span><span className="profile-val">{s.dribblesCompleted} ({s.dribbleSuccessRate}%)</span></div>
          <div className="profile-row"><span className="profile-key">Tackles</span><span className="profile-val">{s.tackles}</span></div>
          <div className="profile-row"><span className="profile-key">Interceptions</span><span className="profile-val">{s.interceptions}</span></div>
          <div className="profile-row"><span className="profile-key">Duels Won</span><span className="profile-val">{s.duelsWon}</span></div>
          <div className="profile-row"><span className="profile-key">Fouls (committed/suffered)</span><span className="profile-val">{s.foulsCommitted} / {s.foulsSuffered}</span></div>
          <div className="profile-row"><span className="profile-key">Cards</span><span className="profile-val"><span className="card-chip yellow" /> {s.yellowCards} · <span className="card-chip red" /> {s.redCards}</span></div>
          <div className="profile-row"><span className="profile-key">Distance Covered</span><span className="profile-val">{s.distanceCovered} km</span></div>
          <div className="profile-row"><span className="profile-key">Avg Match Rating</span><span className="profile-val">{s.avgMatchRating}</span></div>
        </div>

        <div className="profile-details fifa-bio-grid">
          <div className="profile-row"><span className="profile-key">Age</span><span className="profile-val">{player.age}</span></div>
          <div className="profile-row"><span className="profile-key">Height / Weight</span><span className="profile-val">{player.height}cm / {player.weight}kg</span></div>
          <div className="profile-row"><span className="profile-key">Preferred Foot</span><span className="profile-val">{player.preferredFoot}</span></div>
          <div className="profile-row"><span className="profile-key">Market Value</span><span className="profile-val">€{player.marketValue}M</span></div>
        </div>
      </div>
    </div>
  );
}
