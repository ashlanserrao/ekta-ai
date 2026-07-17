import React, { useState } from "react";
import MATCHES from "../../../data/matches.json";
import MatchDetailModal from "./MatchDetailModal";
import { ROUND_ORDER, roundLabel } from "./scheduleHelpers";

export default function BracketTab() {
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [highlightedTeamId, setHighlightedTeamId] = useState(null);

  const finalMatch = MATCHES.find((m) => m.round === "F");
  const champion = finalMatch?.winnerId
    ? [finalMatch.teamA, finalMatch.teamB].find((t) => t?.id === finalMatch.winnerId)
    : null;

  const toggleHighlight = (teamId, e) => {
    e.stopPropagation();
    setHighlightedTeamId((cur) => (cur === teamId ? null : teamId));
  };

  return (
    <div className="glass-panel stats-panel bracket-scroll">
      <p className="panel-desc">Click a team to trace its path through the bracket. Click a played match for details.</p>
      <div className="bracket-columns">
        {ROUND_ORDER.map((round) => (
          <div key={round} className="bracket-round">
            <h4 className="bracket-round-title">{roundLabel(round)}</h4>
            <div className="bracket-round-matches">
              {MATCHES.filter((m) => m.round === round).map((m) => (
                <div
                  key={m.id}
                  className={`bracket-match ${m.status === "live" ? "live" : ""} ${m.status === "tbd" ? "tbd" : ""}`}
                  onClick={() => m.status !== "tbd" && setSelectedMatch(m)}
                >
                  {m.status === "live" && <span className="status-badge high live-badge">LIVE</span>}
                  {[m.teamA, m.teamB].map((team, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className={`bracket-team ${team && m.winnerId === team.id ? "winner" : ""} ${team && team.id === highlightedTeamId ? "highlighted" : ""}`}
                      disabled={!team}
                      onClick={team ? (e) => toggleHighlight(team.id, e) : undefined}
                    >
                      <span className="bracket-team-name">{team ? `${team.flag} ${team.name}` : "TBD"}</span>
                      <span className="bracket-team-score">
                        {team ? (idx === 0 ? m.scoreA : m.scoreB) ?? "" : ""}
                      </span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ))}

        {champion && (
          <div className="bracket-round bracket-champion-round">
            <h4 className="bracket-round-title">Champion</h4>
            <div className="bracket-champion-card">
              <span>🏆</span>
              <span className="bracket-team-name">{champion.flag} {champion.name}</span>
            </div>
          </div>
        )}
      </div>

      {selectedMatch && <MatchDetailModal match={selectedMatch} onClose={() => setSelectedMatch(null)} />}
    </div>
  );
}
