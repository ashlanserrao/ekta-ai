import React from "react";
import { X } from "lucide-react";
import PLAYERS from "../../../data/players.json";
import TEAMS from "../../../data/teams.json";
import { useTranslation } from "../../../lib/LanguageContext";
import RadarChartView from "./RadarChartView";
import { ratingBadgeClass, initials } from "./statsHelpers";

const teamById = Object.fromEntries(TEAMS.map((t) => [t.id, t]));

const FIFA_AXES = [
  { key: "pace", labelKey: "playerModal.axisPace" },
  { key: "shooting", labelKey: "playerModal.axisShooting" },
  { key: "passing", labelKey: "playerModal.axisPassing" },
  { key: "dribbling", labelKey: "playerModal.axisDribbling" },
  { key: "defending", labelKey: "playerModal.axisDefending" },
  { key: "physical", labelKey: "playerModal.axisPhysical" },
];

export default function PlayerDetailModal({ playerId, onClose }) {
  const { t } = useTranslation();
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
          axes={FIFA_AXES.map((a) => ({ key: a.key, label: t(a.labelKey) }))}
          maxValue={99}
          series={[{ name: player.name, color: "#2563eb", values: player.fifaAttributes }]}
        />

        <h4 className="stats-panel-title">{t("playerModal.tournamentStats")}</h4>
        <div className="profile-details">
          <div className="profile-row"><span className="profile-key">{t("playerModal.appearances")}</span><span className="profile-val">{s.appearances}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.minutesPlayed")}</span><span className="profile-val">{s.minutesPlayed}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.goals")}</span><span className="profile-val">{s.goals}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.assists")}</span><span className="profile-val">{s.assists}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.shotsOnTarget")}</span><span className="profile-val">{s.shots} ({s.shotsOnTarget})</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.passAccuracy")}</span><span className="profile-val">{s.passAccuracy}%</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.keyPasses")}</span><span className="profile-val">{s.keyPasses}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.dribbles")}</span><span className="profile-val">{s.dribblesCompleted} ({s.dribbleSuccessRate}%)</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.tackles")}</span><span className="profile-val">{s.tackles}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.interceptions")}</span><span className="profile-val">{s.interceptions}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.duelsWon")}</span><span className="profile-val">{s.duelsWon}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.fouls")}</span><span className="profile-val">{s.foulsCommitted} / {s.foulsSuffered}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.cards")}</span><span className="profile-val"><span className="card-chip yellow" /> {s.yellowCards} · <span className="card-chip red" /> {s.redCards}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.distanceCovered")}</span><span className="profile-val">{s.distanceCovered} km</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.avgMatchRating")}</span><span className="profile-val">{s.avgMatchRating}</span></div>
        </div>

        <div className="profile-details fifa-bio-grid">
          <div className="profile-row"><span className="profile-key">{t("playerModal.age")}</span><span className="profile-val">{player.age}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.heightWeight")}</span><span className="profile-val">{player.height}cm / {player.weight}kg</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.preferredFoot")}</span><span className="profile-val">{player.preferredFoot}</span></div>
          <div className="profile-row"><span className="profile-key">{t("playerModal.marketValue")}</span><span className="profile-val">€{player.marketValue}M</span></div>
        </div>
      </div>
    </div>
  );
}
