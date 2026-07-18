import React, { useState } from "react";
import { X } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import TEAMS from "../../../data/teams.json";
import PLAYERS from "../../../data/players.json";
import { useTranslation } from "../../../lib/LanguageContext";
import PlayerDetailModal from "./PlayerDetailModal";
import { formBadgeClass, ratingBadgeClass } from "./statsHelpers";

export default function TeamDetailModal({ teamId, onClose }) {
  const { t } = useTranslation();
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const team = TEAMS.find((t2) => t2.id === teamId);
  if (!team) return null;

  const squad = PLAYERS
    .filter((p) => team.squadList.includes(p.id))
    .sort((a, b) => b.overallRating - a.overallRating);

  const actualLabel = t("teamModal.actual");
  const expectedLabel = t("teamModal.expected");
  const chartData = [
    { name: t("teamModal.goalsFor"), [actualLabel]: team.stats.goalsFor, [expectedLabel]: team.stats.xG },
    { name: t("teamModal.goalsAgainst"), [actualLabel]: team.stats.goalsAgainst, [expectedLabel]: team.stats.xGA },
  ];

  return (
    <>
      <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={`${team.name} team detail`}>
        <div className="modal-card glass-panel team-modal" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close" onClick={onClose} aria-label="Close"><X size={20} /></button>

          <div className="team-modal-header">
            <span className="team-modal-flag">{team.flag}</span>
            <div>
              <h2 className="modal-title">{team.name}</h2>
              <p className="modal-sub">{team.group} · {team.confederation} · FIFA #{team.fifaRanking} · {t("teamModal.coach")} {team.coach}</p>
            </div>
          </div>

          <div className="profile-details team-stat-grid">
            <div className="profile-row"><span className="profile-key">{t("teamModal.possession")}</span><span className="profile-val">{team.stats.possessionAvg}%</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.passAccuracy")}</span><span className="profile-val">{team.stats.passAccuracy}%</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.shotsPerGame")}</span><span className="profile-val">{team.stats.shotsPerGame}</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.shotsOnTargetPerGame")}</span><span className="profile-val">{team.stats.shotsOnTargetPerGame}</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.tacklesPerGame")}</span><span className="profile-val">{team.stats.tacklesPerGame}</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.foulsPerGame")}</span><span className="profile-val">{team.stats.foulsPerGame}</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.cleanSheets")}</span><span className="profile-val">{team.stats.cleanSheets}</span></div>
            <div className="profile-row"><span className="profile-key">{t("teamModal.cards")}</span><span className="profile-val"><span className="card-chip yellow" /> {team.stats.yellowCards} · <span className="card-chip red" /> {team.stats.redCards}</span></div>
          </div>

          <h4 className="stats-panel-title">{t("teamModal.xgVsActual")}</h4>
          <div className="xg-chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#192130", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
                <Bar dataKey={actualLabel} fill="#2563eb" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey={expectedLabel} fill="#06b6d4" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <h4 className="stats-panel-title">{t("teamModal.formGuide")}</h4>
          <div className="form-badges">
            {team.form.map((r, i) => (
              <span key={i} className={`status-badge ${formBadgeClass(r)} form-badge`}>{r}</span>
            ))}
          </div>

          <h4 className="stats-panel-title">{t("teamModal.squad")}</h4>
          <div className="squad-list">
            {squad.map((p) => (
              <button key={p.id} className="squad-row" onClick={() => setSelectedPlayerId(p.id)}>
                <span className="squad-number">{p.jerseyNumber}</span>
                <span className="squad-name">{p.name}</span>
                <span className="squad-position">{p.position}</span>
                <span className={`status-badge ${ratingBadgeClass(p.overallRating)}`}>{p.overallRating}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {selectedPlayerId && (
        <PlayerDetailModal playerId={selectedPlayerId} onClose={() => setSelectedPlayerId(null)} />
      )}
    </>
  );
}
