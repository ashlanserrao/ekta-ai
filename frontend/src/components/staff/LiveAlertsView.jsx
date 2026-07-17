import React from "react";

export default function LiveAlertsView({ alerts }) {
  return (
    <div className="fan-view">
      <div className="glass-panel alert-panel padding-large">
        <h2>Operations Live Alerts (GenAI Action Engine)</h2>
        <p className="alert-panel-desc">
          Plain-language alerts triggered automatically by digital twin anomalies.
        </p>

        <div className="alert-list">
          {alerts.map((alert) => (
            <div key={alert.id} className={`alert-item ${alert.severity}`}>
              <div className="alert-title">
                <span>{alert.message}</span>
                <span className="alert-severity-badge">
                  {alert.severity}
                </span>
              </div>
              <div className="alert-action">
                <strong>Recommendation:</strong> {alert.recommended_action}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
