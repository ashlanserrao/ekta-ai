import React from "react";

export default function LiveCrowdView({ zones }) {
  return (
    <div className="fan-view">
      <div className="glass-panel padding-large">
        <h2>Live Crowd Densities (Digital Twin Sensors)</h2>
        <p className="panel-desc">
          Crowd counts are simulated in real-time from SQLite digital twin model.
        </p>

        <div className="density-grid">
          {zones.map((zone) => {
            const densityPct = Math.min(100, Math.round(zone.density * 100));
            let colorClass = "low";
            if (zone.density > 0.75) colorClass = "high";
            else if (zone.density >= 0.40) colorClass = "medium";

            return (
              <div key={zone.id} className="glass-panel density-card density-card-bg">
                <div className="flex-between">
                  <span className="bold-text">{zone.name}</span>
                  <span className={`status-badge ${colorClass}`}>{colorClass}</span>
                </div>
                <div className="density-val">{densityPct}%</div>
                <div className="text-small-muted">
                  {zone.current_crowd} / {zone.capacity} occupants
                </div>
                <div className="progress-bar-bg">
                  <div
                    className={`progress-bar-fill ${colorClass}`}
                    style={{ width: `${densityPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
