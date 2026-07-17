import React, { useState, useEffect, useRef } from "react";
import { useChatStream } from "../../hooks/useChatStream";
import { API_BASE } from "../../lib/api";

const getProviderBadge = (provider) => {
  if (provider === "groq") {
    return <span className="provider-badge groq">⚡ Groq Core</span>;
  }
  return <span className="provider-badge offline">🔌 Offline Mode</span>;
};

// The Staff Decision Support Console chat, decoupled from the dashboard layout.
export default function StaffChat({ token, onLogout }) {
  const [staffMessages, setStaffMessages] = useState([
    { sender: "bot", text: "Operations Intelligence Portal Active. Ask about crowd densities, gates status, or incident mitigations." }
  ]);
  const [staffInput, setStaffInput] = useState("");
  const [staffChatLoading, setStaffChatLoading] = useState(false);
  const [activeProvider, setActiveProvider] = useState("groq");

  const readChatStream = useChatStream();
  const staffChatEndRef = useRef(null);

  useEffect(() => {
    staffChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [staffMessages]);

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
    <div className="staffchat" aria-label="Staff operations query portal">
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
  );
}
