import React, { useState, useEffect, useRef } from "react";
import InteractiveMap from "./InteractiveMap";
import { useVoice } from "../hooks/useVoice";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function FanAssistant({ gates, zones }) {
  // Chat state - Fan
  const [fanMessages, setFanMessages] = useState([
    { sender: "bot", text: "Welcome to FIFA World Cup 2026! I am EktaAI, your stadium assistant. How can I help you find your seat, food stalls, or accessible routes today?" }
  ]);
  const [fanInput, setFanInput] = useState("");
  const [fanLanguage, setFanLanguage] = useState("en");
  const [activeRoute, setActiveRoute] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [rateLimitMessage, setRateLimitMessage] = useState("");
  
  const chatEndRef = useRef(null);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [fanMessages]);

  const {
    isListening,
    voiceEnabled,
    setVoiceEnabled,
    toggleListening,
    speakText
  } = useVoice(fanLanguage, setFanInput);

  // Send message - Fan Assistant
  const handleFanSend = async (e) => {
    e.preventDefault();
    if (!fanInput.trim()) return;
    
    const userMsg = fanInput;
    setFanMessages(prev => [...prev, { sender: "user", text: userMsg }]);
    setFanInput("");
    setChatLoading(true);
    setRateLimitMessage("");
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/fan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, language: fanLanguage })
      });
      
      if (res.status === 429) {
        const err = await res.json();
        setRateLimitMessage(err.detail);
        setFanMessages(prev => [...prev, { sender: "bot", text: "⚠️ System busy. Rate limit exceeded. Please wait a moment." }]);
        setChatLoading(false);
        return;
      }
      
      if (res.ok) {
        const data = await res.json();
        setFanMessages(prev => [...prev, { sender: "bot", text: data.reply }]);
        
        speakText(data.reply, fanLanguage);
        
        if (data.route) {
          setActiveRoute(data.route);
        }
      } else {
        setFanMessages(prev => [...prev, { sender: "bot", text: "Sorry, I'm experiencing troubles connecting to the database." }]);
      }
    } catch (err) {
      console.error(err);
      setFanMessages(prev => [...prev, { sender: "bot", text: "Network error occurred." }]);
    }
    setChatLoading(false);
  };

  return (
    <div className="view-container">
      {/* Left Col: Map View */}
      <InteractiveMap gates={gates} zones={zones} activeRoute={activeRoute} />
      
      {/* Right Col: Chat widget */}
      <div className="glass-panel chat-container" aria-label="Fan chat assistant">
        <div className="chat-header">
          <div>
            <h2 style={{ fontSize: "1.1rem" }}>Fan Assistant (Multilingual)</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.80rem" }}>
              Voice support enabled. Ask directions or gate info.
            </p>
          </div>
          
          <div style={{ display: "flex", gap: "8px" }}>
            {/* Language Selector */}
            <select 
              value={fanLanguage} 
              onChange={(e) => setFanLanguage(e.target.value)}
              style={{ background: "var(--bg-tertiary)", color: "var(--text-primary)", border: "1px solid var(--border-color)", padding: "0.3rem", borderRadius: "6px" }}
              aria-label="Select Assistant Language"
            >
              <option value="en">English 🇬🇧</option>
              <option value="es">Español 🇪🇸</option>
            </select>
            
            {/* Text-to-speech toggle */}
            <button 
              onClick={() => {
                setVoiceEnabled(!voiceEnabled);
                if (!voiceEnabled && window.speechSynthesis) {
                  speakText("Voice response activated", fanLanguage);
                }
              }}
              className="btn-secondary"
              style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem", borderColor: voiceEnabled ? "var(--color-low)" : "var(--border-color)" }}
              aria-label="Toggle voice output read back"
            >
              🔊 {voiceEnabled ? "Voice ON" : "Voice OFF"}
            </button>
          </div>
        </div>
        
        <div className="chat-messages" aria-live="polite">
          {fanMessages.map((msg, idx) => (
            <div key={idx} className={`message-bubble ${msg.sender}`}>
              {msg.text}
            </div>
          ))}
          {chatLoading && <div className="message-bubble bot" style={{ opacity: 0.6 }}>Assistant is typing...</div>}
          {rateLimitMessage && <div style={{ color: "var(--color-high)", fontSize: "0.8rem", textAlign: "center" }}>{rateLimitMessage}</div>}
          <div ref={chatEndRef} />
        </div>
        
        <form onSubmit={handleFanSend} className="chat-input-area">
          <input 
            type="text" 
            className="chat-input"
            placeholder={fanLanguage === "es" ? "Escribe un mensaje..." : "Ask Gate details, route, accessibility support..."}
            value={fanInput}
            onChange={(e) => setFanInput(e.target.value)}
            aria-label="Type your message here"
          />
          
          <button 
            type="button" 
            onClick={toggleListening}
            className={`voice-btn ${isListening ? "active" : ""}`}
            aria-label="Toggle Voice Input Recording"
          >
            🎙️
          </button>
          
          <button type="submit" className="btn-primary">Send</button>
        </form>
      </div>
    </div>
  );
}
