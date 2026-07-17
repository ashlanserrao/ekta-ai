import React from "react";
import { roundLabel, teamLabel, formatScore, statusText } from "./scheduleHelpers";

export default function MatchDetailModal({ match, onClose }) {
  if (!match) return null;
  const score = formatScore(match);

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`${teamLabel(match.teamA)} vs ${teamLabel(match.teamB)} match detail`}
    >
      <div className="modal-card glass-panel match-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>

        <p className="schedule-stage match-modal-round">{roundLabel(match.round)}</p>

        <div className="match-modal-teams">
          <span className="result-team">{teamLabel(match.teamA)}</span>
          <span className="result-score">
            {match.status === "live" && <span className="status-badge high live-badge">LIVE</span>}
            {score || "vs"}
          </span>
          <span className="result-team away">{teamLabel(match.teamB)}</span>
        </div>

        <div className="profile-details">
          <div className="profile-row"><span className="profile-key">Date</span><span className="profile-val">{match.date}</span></div>
          <div className="profile-row"><span className="profile-key">Time</span><span className="profile-val">{match.time}</span></div>
          <div className="profile-row"><span className="profile-key">Venue</span><span className="profile-val">📍 {match.venue}</span></div>
          <div className="profile-row"><span className="profile-key">Status</span><span className="profile-val">{statusText(match.status)}</span></div>
        </div>
      </div>
    </div>
  );
}
