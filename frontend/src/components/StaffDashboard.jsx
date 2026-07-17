import React, { useState, useEffect, useRef } from "react";
import InteractiveMap from "./InteractiveMap";
import { useChatStream } from "../hooks/useChatStream";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const getProviderBadge = (provider) => {
  if (provider === "groq") {
    return <span className="provider-badge groq">⚡ Groq Core</span>;
  }
  return <span className="provider-badge offline">🔌 Offline Mode</span>;
};

export default function StaffDashboard({ zones, alerts, gates, token, onLogout }) {
  // Chat state - Staff
  const [staffMessages, setStaffMessages] = useState([
    { sender: "bot", text: "Operations Intelligence Portal Active. Ask about crowd densities, gates status, or incident mitigations." }
  ]);
  const [staffInput, setStaffInput] = useState("");
  const [staffChatLoading, setStaffChatLoading] = useState(false);
  
  // AI Provider transparency state
  const [activeProvider, setActiveProvider] = useState("groq");

  // Operations Copilot (proactive forecast + recommendations)
  const [copilot, setCopilot] = useState(null);

  const readChatStream = useChatStream();
  const staffChatEndRef = useRef(null);

  // Scroll chat to bottom
  useEffect(() => {
    staffChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [staffMessages]);

  // Poll the Operations Copilot forecast/recommendations
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

  // Send message - Staff Assistant
  const handleStaffSend = async (e) => {
    e.preventDefault();
    if (!staffInput.trim()) return;
    
    const userMsg = staffInput;
    setStaffMessages(prev => [...prev, { sender: "user", text: userMsg }]);
    setStaffInput("");
    setStaffChatLoading(true);
    
    try {
      const historyPayload = staffMessages.slice(-3).map(m => ({
        role: m.sender === "bot" ? "assistant" : "user",
        content: m.text
      }));

      const res = await fetch(`${API_BASE}/api/v1/chat/staff`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          message: userMsg,
          history: historyPayload
        })
      });
      
      if (res.ok) {
        setStaffMessages(prev => [...prev, { sender: "bot", text: "" }]);

        let botReply = "";
        const setLastBotText = (text) => setStaffMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].sender === "bot") {
            updated[updated.length - 1] = { ...updated[updated.length - 1], text };
          }
          return updated;
        });

        await readChatStream(res, {
          // Discard any leaked first-pass tool-call text before the real answer.
          onReset: () => { botReply = ""; setLastBotText(""); },
          onToken: (token) => { botReply += token; setLastBotText(botReply); },
          onProvider: setActiveProvider,
        });
      } else if (res.status === 401) {
        setStaffMessages(prev => [...prev, { sender: "bot", text: "Session expired or unauthorized. Logging out..." }]);
        setTimeout(() => {
          onLogout();
        }, 1500);
      } else {
        setStaffMessages(prev => [...prev, { sender: "bot", text: "Error fetching operations details." }]);
      }
    } catch (err) {
      console.error(err);
      setStaffMessages(prev => [...prev, { sender: "bot", text: "Network connection lost." }]);
    }
    setStaffChatLoading(false);
  };

  return (
    <div className="view-container">
      {/* Left Col: Crowd Densities & Alert log */}
      <div className="staff-left-col">
        {/* Operations Copilot — proactive forecast + recommendations */}
        <div className="glass-panel copilot-panel padding-large">
          <div className="copilot-header">
            <h2>
              🧠 Operations Copilot
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
                    const trendIcon = r.trend === "rising" ? "▲" : r.trend === "falling" ? "▼" : "●";
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
                          {trendIcon} {r.trend}
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
                <div className="copilot-nominal">✅ No interventions required — all zones nominal.</div>
              )}
            </>
          ) : (
            <div className="copilot-nominal">Connecting to Operations Copilot…</div>
          )}
        </div>

        {/* Density list */}
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
                  {/* Progress Bar */}
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
        
        {/* Stadium Live Map Visualizer */}
        <InteractiveMap gates={gates} zones={zones} />
        
        {/* Operational alerts */}
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
      
      {/* Right Col: Staff Operations Chat widget */}
      <div className="glass-panel chat-container" aria-label="Staff operations query portal">
        <div className="chat-header">
          <div>
            <h2 className="chat-title-container">
              Staff Decision Support Console {getProviderBadge(activeProvider)}
            </h2>
            <p className="chat-subtitle">
              Query why bottlenecks are occurring, get layout mitigations, etc.
            </p>
          </div>
        </div>
        
        <div className="chat-messages" aria-live="polite">
          {staffMessages.map((msg, idx) => (
            <div key={idx} className={`message-bubble ${msg.sender === "bot" ? "bot staff-bot" : "user"}`}>
              {msg.text}
            </div>
          ))}
          {staffChatLoading && <div className="message-bubble bot typing-indicator">Orchestrating response...</div>}
          <div ref={staffChatEndRef} />
        </div>
        
        <form onSubmit={handleStaffSend} className="chat-input-area">
          <input 
            type="text" 
            className="chat-input"
            placeholder="Ask: Why is Gate 3 congested? / Recommend mitigation plan..."
            value={staffInput}
            onChange={(e) => setStaffInput(e.target.value)}
            aria-label="Staff instruction input"
            disabled={staffChatLoading}
          />
          
          <button type="submit" className="btn-primary" disabled={staffChatLoading || !staffInput.trim()}>Run</button>
        </form>
      </div>
    </div>
  );
}
