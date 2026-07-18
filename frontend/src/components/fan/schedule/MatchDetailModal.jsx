import React from "react";
import { X, MapPin } from "lucide-react";
import { useTranslation } from "../../../lib/LanguageContext";
import { roundLabel, teamLabel, formatScore, statusText } from "./scheduleHelpers";

export default function MatchDetailModal({ match, onClose }) {
  const { t } = useTranslation();
  if (!match) return null;
  const score = formatScore(match);

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${teamLabel(match.teamA, t)} vs ${teamLabel(match.teamB, t)} match detail`}
    >
      <div className="modal-card glass-panel match-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close"><X size={20} /></button>

        <p className="schedule-stage match-modal-round">{roundLabel(match.round, t)}</p>

        <div className="match-modal-teams">
          <span className="result-team">{teamLabel(match.teamA, t)}</span>
          <span className="result-score">
            {match.status === "live" && <span className="status-badge high live-badge">LIVE</span>}
            {score || "vs"}
          </span>
          <span className="result-team away">{teamLabel(match.teamB, t)}</span>
        </div>

        <div className="profile-details">
          <div className="profile-row"><span className="profile-key">{t("schedule.matchDetailDate")}</span><span className="profile-val">{match.date}</span></div>
          <div className="profile-row"><span className="profile-key">{t("schedule.matchDetailTime")}</span><span className="profile-val">{match.time}</span></div>
          <div className="profile-row"><span className="profile-key">{t("schedule.matchDetailVenue")}</span><span className="profile-val"><MapPin size={13} style={{ verticalAlign: "-2px", marginRight: "0.25rem" }} />{match.venue}</span></div>
          <div className="profile-row"><span className="profile-key">{t("schedule.matchDetailStatus")}</span><span className="profile-val">{statusText(match.status, t)}</span></div>
        </div>
      </div>
    </div>
  );
}
