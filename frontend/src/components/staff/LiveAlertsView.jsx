import React from "react";
import { useTranslation } from "../../lib/useTranslation";

export default function LiveAlertsView({ alerts }) {
  const { t } = useTranslation();
  return (
    <div className="fan-view">
      <div className="glass-panel alert-panel padding-large">
        <h2>{t("staffAlerts.heading")}</h2>
        <p className="alert-panel-desc">
          {t("staffAlerts.desc")}
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
                <strong>{t("staffAlerts.recommendation")}</strong> {alert.recommended_action}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
