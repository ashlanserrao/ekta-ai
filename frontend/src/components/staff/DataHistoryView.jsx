import React, { useState, useEffect } from "react";
import { ShieldCheck } from "lucide-react";
import { API_BASE } from "../../lib/api";

const EVENT_LABELS = {
  login: "Login",
  logout: "Logout",
  chat_message: "Chat message sent",
  page_view: "Page view",
};

export default function DataHistoryView({ token, onLogout }) {
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
        <h1>Data History</h1>
        <p>What EktaAI collects about how the platform is used.</p>
      </div>

      <div className="glass-panel stats-panel data-history-notice">
        <ShieldCheck size={18} style={{ verticalAlign: "-4px", marginRight: "0.4rem" }} />
        We log anonymized interaction events — logins, page views, and chat message counts —
        tagged with a random per-session id. We never store message content, names, emails,
        or any other personal identifier here.
      </div>

      {summary && (
        <div className="stat-tiles">
          {Object.entries(EVENT_LABELS).map(([key, label]) => (
            <div key={key} className="glass-panel stat-tile">
              <div className="stat-tile-value">{summary.counts_by_type[key] || 0}</div>
              <div className="stat-tile-label">{label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="glass-panel stats-panel">
        <h3 className="stats-panel-title">Recent Events</h3>
        {!summary ? (
          <div className="stats-empty">Loading…</div>
        ) : summary.events.length === 0 ? (
          <div className="stats-empty">No interaction events recorded yet.</div>
        ) : (
          <div className="table-scroll history-table-scroll">
            <table className="stats-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Session</th>
                  <th>Role</th>
                  <th>Event</th>
                  <th>View</th>
                </tr>
              </thead>
              <tbody>
                {summary.events.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.ts).toLocaleString()}</td>
                    <td className="text-small-muted">{e.session_id.slice(0, 8)}…</td>
                    <td>{e.role}</td>
                    <td>{EVENT_LABELS[e.event_type] || e.event_type}</td>
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
