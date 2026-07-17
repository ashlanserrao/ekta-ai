import React from "react";
import { TOP_SCORERS, RECENT_RESULTS, STANDINGS, TOURNAMENT_STATS } from "../../data/worldcup";

export default function StatsView() {
  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Player & Match Stats</h1>
        <p>FIFA World Cup 2026 — live tournament numbers, top scorers and results.</p>
      </div>

      {/* Tournament tiles */}
      <div className="stat-tiles">
        {TOURNAMENT_STATS.map((s) => (
          <div key={s.label} className="stat-tile glass-panel">
            <div className="stat-tile-value">{s.value}</div>
            <div className="stat-tile-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="stats-grid">
        {/* Top scorers */}
        <div className="glass-panel stats-panel">
          <h3 className="stats-panel-title">🏆 Golden Boot Race</h3>
          <table className="stats-table">
            <thead>
              <tr><th>Player</th><th>Team</th><th>G</th><th>A</th></tr>
            </thead>
            <tbody>
              {TOP_SCORERS.map((p, i) => (
                <tr key={p.player}>
                  <td><span className="rank">{i + 1}</span>{p.player}</td>
                  <td>{p.flag} {p.team}</td>
                  <td className="num">{p.goals}</td>
                  <td className="num">{p.assists}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Standings */}
        <div className="glass-panel stats-panel">
          <h3 className="stats-panel-title">📋 {STANDINGS.group} Standings</h3>
          <table className="stats-table">
            <thead>
              <tr><th>Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>Pts</th></tr>
            </thead>
            <tbody>
              {STANDINGS.rows.map((r, i) => (
                <tr key={r.team} className={i < 2 ? "qualifying" : ""}>
                  <td>{r.flag} {r.team}</td>
                  <td className="num">{r.p}</td>
                  <td className="num">{r.w}</td>
                  <td className="num">{r.d}</td>
                  <td className="num">{r.l}</td>
                  <td className="num">{r.gd}</td>
                  <td className="num bold">{r.pts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent results */}
      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title">⚽ Recent Results</h3>
        <div className="results-grid">
          {RECENT_RESULTS.map((m, i) => (
            <div key={i} className="result-card">
              <span className="result-team">{m.homeFlag} {m.home}</span>
              <span className="result-score">{m.score}</span>
              <span className="result-team away">{m.away} {m.awayFlag}</span>
              <span className="result-stage">{m.stage}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
