import React, { useState, useEffect } from "react";
import { Zap, WifiOff, Brain, CheckCircle2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { API_BASE } from "../../lib/api";

const getProviderBadge = (provider) => {
  if (provider === "groq") {
    return <span className="provider-badge groq"><Zap size={14} /> Groq Core</span>;
  }
  return <span className="provider-badge offline"><WifiOff size={14} /> Offline Mode</span>;
};

export default function OperationsCopilotView({ token, onLogout }) {
  const [copilot, setCopilot] = useState(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    const fetchCopilot = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/staff/copilot`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setCopilot(data);
        } else if (res.status === 401) {
          onLogout();
        }
      } catch (err) {
        console.error("Error polling copilot:", err);
      }
    };

    fetchCopilot();
    const interval = setInterval(fetchCopilot, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [token, onLogout]);

  return (
    <div className="fan-view">
      <div className="glass-panel copilot-panel padding-large">
        <div className="copilot-header">
          <h2>
            <Brain size={20} style={{ verticalAlign: "-4px", marginRight: "0.4rem" }} />
            Operations Copilot
            {copilot && getProviderBadge(copilot.provider)}
          </h2>
          <span className="copilot-horizon">
            {copilot ? `${copilot.horizon_minutes}-min forecast` : "Initializing…"}
          </span>
        </div>
        <p className="panel-desc">
          Proactive decision support: forecasts congestion from live twin trends and recommends actions before bottlenecks form.
        </p>

        {copilot ? (
          <>
            <div className="copilot-summary">{copilot.summary}</div>

            {copilot.risks && copilot.risks.length > 0 && (
              <div className="copilot-forecast">
                {copilot.risks.map((r) => {
                  const TrendIcon = r.trend === "rising" ? TrendingUp : r.trend === "falling" ? TrendingDown : Minus;
                  const trendClass = r.trend === "rising" ? "high" : r.trend === "falling" ? "low" : "medium";
                  return (
                    <div key={r.zone_id} className="copilot-forecast-row">
                      <span className="copilot-zone">{r.zone_name}</span>
                      <span className="copilot-projection">
                        {Math.round(r.current_density * 100)}%
                        <span className="copilot-arrow"> → </span>
                        <span className={`copilot-projected ${trendClass}`}>
                          {Math.round(r.projected_density * 100)}%
                        </span>
                      </span>
                      <span className={`copilot-trend ${trendClass}`}>
                        <TrendIcon size={14} style={{ verticalAlign: "-2px" }} /> {r.trend}
                        {r.eta_minutes != null && r.trend === "rising" ? ` · ~${r.eta_minutes}m to critical` : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {copilot.recommendations && copilot.recommendations.length > 0 ? (
              <div className="copilot-recs">
                {copilot.recommendations.map((rec, idx) => (
                  <div key={idx} className={`copilot-rec ${rec.priority}`}>
                    <span className="copilot-rec-priority">{rec.priority}</span>
                    <span className="copilot-rec-action">
                      <strong>{rec.zone}:</strong> {rec.action}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="copilot-nominal"><CheckCircle2 size={16} style={{ verticalAlign: "-3px", marginRight: "0.3rem" }} />No interventions required — all zones nominal.</div>
            )}
          </>
        ) : (
          <div className="copilot-nominal">Connecting to Operations Copilot…</div>
        )}
      </div>
    </div>
  );
}
