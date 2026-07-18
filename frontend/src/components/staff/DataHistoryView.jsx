import React, { useState, useEffect } from "react";
import { ShieldCheck } from "lucide-react";
import { API_BASE } from "../../lib/api";
import { useTranslation } from "../../lib/LanguageContext";

const EVENT_LABEL_KEYS = {
  login: "staffHistory.eventLogin",
  logout: "staffHistory.eventLogout",
  chat_message: "staffHistory.eventChatMessage",
  page_view: "staffHistory.eventPageView",
};

const ROLE_LABEL_KEYS = {
  fan: "staffHistory.roleFan",
  staff: "staffHistory.roleStaff",
};

export default function DataHistoryView({ token, onLogout }) {
  const { t } = useTranslation();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    const fetchHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/interactions?limit=100`, {
          headers: { "Authorization": `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setSummary(data);
        } else if (res.status === 401) {
          onLogout();
        }
      } catch (err) {
        console.error("Error fetching interaction history:", err);
      }
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 10000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [token, onLogout]);

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>{t("staffHistory.heading")}</h1>
        <p>{t("staffHistory.sub")}</p>
      </div>

      <div className="glass-panel stats-panel data-history-notice">
        <ShieldCheck size={18} style={{ verticalAlign: "-4px", marginRight: "0.4rem" }} />
        {t("staffHistory.notice")}
      </div>

      {summary && (
        <div className="stat-tiles">
          {Object.entries(EVENT_LABEL_KEYS).map(([key, labelKey]) => (
            <div key={key} className="glass-panel stat-tile">
              <div className="stat-tile-value">{summary.counts_by_type[key] || 0}</div>
              <div className="stat-tile-label">{t(labelKey)}</div>
            </div>
          ))}
        </div>
      )}

      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title">{t("staffHistory.recentEvents")}</h3>
        {!summary ? (
          <div className="stats-empty">{t("staffHistory.loading")}</div>
        ) : summary.events.length === 0 ? (
          <div className="stats-empty">{t("staffHistory.noEvents")}</div>
        ) : (
          <div className="table-scroll capped-table-scroll">
            <table className="stats-table">
              <thead>
                <tr>
                  <th>{t("staffHistory.colTime")}</th>
                  <th>{t("staffHistory.colSession")}</th>
                  <th>{t("staffHistory.colRole")}</th>
                  <th>{t("staffHistory.colEvent")}</th>
                  <th>{t("staffHistory.colView")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.events.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.ts).toLocaleString()}</td>
                    <td className="text-small-muted">{e.session_id.slice(0, 8)}…</td>
                    <td>{ROLE_LABEL_KEYS[e.role] ? t(ROLE_LABEL_KEYS[e.role]) : e.role}</td>
                    <td>{EVENT_LABEL_KEYS[e.event_type] ? t(EVENT_LABEL_KEYS[e.event_type]) : e.event_type}</td>
                    <td>{e.view || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
