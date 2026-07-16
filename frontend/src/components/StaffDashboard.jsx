import React, { useState, useEffect, useRef } from "react";
import InteractiveMap from "./InteractiveMap";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const getProviderBadge = (provider) => {
  if (provider === "gemini") {
    return <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "10px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid var(--color-low)", color: "var(--color-low)", fontWeight: "600", display: "inline-block" }}>🤖 Live Gemini</span>;
  }
  if (provider === "groq") {
    return <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "10px", background: "rgba(245, 158, 11, 0.1)", border: "1px solid var(--color-medium)", color: "var(--color-medium)", fontWeight: "600", display: "inline-block" }}>⚡ Groq Core</span>;
  }
  return <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "10px", background: "rgba(148, 163, 184, 0.1)", border: "1px solid var(--text-muted)", color: "var(--text-secondary)", fontWeight: "600", display: "inline-block" }}>🔌 Offline Mode</span>;
};

export default function StaffDashboard({ zones, alerts, gates, token, onLogout }) {
  // Chat state - Staff
  const [staffMessages, setStaffMessages] = useState([
    { sender: "bot", text: "Operations Intelligence Portal Active. Ask about crowd densities, gates status, or incident mitigations." }
  ]);
  const [staffInput, setStaffInput] = useState("");
  const [staffChatLoading, setStaffChatLoading] = useState(false);
  
  // AI Provider transparency state
  const [activeProvider, setActiveProvider] = useState("gemini");
  
  const staffChatEndRef = useRef(null);

  // Scroll chat to bottom
  useEffect(() => {
    staffChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [staffMessages]);

  // Send message - Staff Assistant
  const handleStaffSend = async (e) => {
    e.preventDefault();
    if (!staffInput.trim()) return;
    
    const userMsg = staffInput;
    setStaffMessages(prev => [...prev, { sender: "user", text: userMsg }]);
    setStaffInput("");
    setStaffChatLoading(true);
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/staff`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMsg })
      });
      
      if (res.ok) {
        setStaffMessages(prev => [...prev, { sender: "bot", text: "" }]);
        
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let done = false;
        let botReply = "";
        
        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;
          if (value) {
            const chunkStr = decoder.decode(value, { stream: !done });
            const lines = chunkStr.split("\n");
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (data.token) {
                    botReply += data.token;
                    setStaffMessages(prev => {
                      const updated = [...prev];
                      if (updated.length > 0 && updated[updated.length - 1].sender === "bot") {
                        updated[updated.length - 1].text = botReply;
                      }
                      return updated;
                    });
                  }
                  if (data.provider) {
                    setActiveProvider(data.provider);
                  }
                } catch (e) {
                  // Partial chunk parse error - ignore safely
                }
              }
            }
          }
        }
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
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", flex: 1 }}>
        {/* Density list */}
        <div className="glass-panel" style={{ padding: "1.5rem" }}>
          <h2>Live Crowd Densities (Digital Twin Sensors)</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
            Crowd counts are simulated in real-time from SQLite digital twin model.
          </p>
          
          <div className="density-grid">
            {zones.map((zone) => {
              const densityPct = Math.min(100, Math.round(zone.density * 100));
              let colorClass = "low";
              if (zone.density > 0.75) colorClass = "high";
              else if (zone.density >= 0.40) colorClass = "medium";
              
              return (
                <div key={zone.id} className="glass-panel density-card" style={{ background: "rgba(255,255,255,0.01)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontWeight: "700" }}>{zone.name}</span>
                    <span className={`status-badge ${colorClass}`}>{colorClass}</span>
                  </div>
                  <div className="density-val">{densityPct}%</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    {zone.current_crowd} / {zone.capacity} occupants
                  </div>
                  {/* Progress Bar */}
                  <div style={{ width: "100%", height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden", marginTop: "5px" }}>
                    <div 
                      style={{ 
                        width: `${densityPct}%`, 
                        height: "100%", 
                        background: zone.density > 0.75 ? "var(--color-high)" : zone.density >= 0.40 ? "var(--color-medium)" : "var(--color-low)",
                        transition: "width 0.5s ease"
                      }}
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
        <div className="glass-panel alert-panel" style={{ padding: "1.5rem" }}>
          <h2>Operations Live Alerts (GenAI Action Engine)</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            Plain-language alerts triggered automatically by digital twin anomalies.
          </p>
          
          <div className="alert-list">
            {alerts.map((alert) => (
              <div key={alert.id} className={`alert-item ${alert.severity}`}>
                <div className="alert-title">
                  <span>{alert.message}</span>
                  <span style={{ textTransform: "uppercase", fontSize: "0.75rem", padding: "0.1rem 0.4rem", borderRadius: "4px", background: "rgba(0,0,0,0.3)" }}>
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
            <h2 style={{ fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              Staff Decision Support Console {getProviderBadge(activeProvider)}
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.80rem" }}>
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
          {staffChatLoading && <div className="message-bubble bot" style={{ opacity: 0.6 }}>Orchestrating response...</div>}
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
