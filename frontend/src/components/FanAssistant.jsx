import React, { useState, useEffect, useRef } from "react";
import InteractiveMap from "./InteractiveMap";
import { useVoice } from "../hooks/useVoice";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const getProviderBadge = (provider) => {
  if (provider === "groq") {
    return <span className="provider-badge groq">⚡ Groq Core</span>;
  }
  return <span className="provider-badge offline">🔌 Offline Mode</span>;
};

export default function FanAssistant({ gates, zones }) {
  // Chat state - Fan
  const [fanMessages, setFanMessages] = useState([
    { sender: "bot", text: "Welcome to the World Cup 2026! I am EktaAI, your stadium assistant. How can I help you find your seat, food stalls, or accessible routes today?" }
  ]);
  const [fanInput, setFanInput] = useState("");
  const [fanLanguage, setFanLanguage] = useState("en");
  const [activeRoute, setActiveRoute] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [rateLimitMessage, setRateLimitMessage] = useState("");
  
  // AI Provider transparency state
  const [activeProvider, setActiveProvider] = useState("groq");
  
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
      const historyPayload = fanMessages.slice(-3).map(m => ({
        role: m.sender === "bot" ? "assistant" : "user",
        content: m.text
      }));

      const res = await fetch(`${API_BASE}/api/v1/chat/fan`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "text/event-stream"
        },
        body: JSON.stringify({ 
          message: userMsg, 
          language: fanLanguage,
          history: historyPayload
        })
      });
      
      if (res.status === 429) {
        const err = await res.json();
        setRateLimitMessage(err.detail);
        setFanMessages(prev => [...prev, { sender: "bot", text: "⚠️ System busy. Rate limit exceeded. Please wait a moment." }]);
        setChatLoading(false);
        return;
      }
      
      if (res.ok) {
        setFanMessages(prev => [...prev, { sender: "bot", text: "" }]);
        
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
                  if (data.reset) {
                    // Discard any leaked first-pass tool-call text before the real answer.
                    botReply = "";
                    setFanMessages(prev => {
                      const updated = [...prev];
                      if (updated.length > 0 && updated[updated.length - 1].sender === "bot") {
                        updated[updated.length - 1] = { ...updated[updated.length - 1], text: "" };
                      }
                      return updated;
                    });
                  }
                  if (data.token) {
                    botReply += data.token;
                    setFanMessages(prev => {
                      const updated = [...prev];
                      if (updated.length > 0 && updated[updated.length - 1].sender === "bot") {
                        updated[updated.length - 1] = { ...updated[updated.length - 1], text: botReply };
                      }
                      return updated;
                    });
                  }
                  if (data.provider) {
                    setActiveProvider(data.provider);
                  }
                  if (data.route) {
                    setActiveRoute(data.route);
                  }
                } catch {
                  // Partial chunk parse error - ignore safely
                }
              }
            }
          }
        }
        
        speakText(botReply, fanLanguage);
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
            <h2 className="chat-title-container">
              Fan Assistant {getProviderBadge(activeProvider)}
            </h2>
            <p className="chat-subtitle">
              Voice support enabled. Ask directions or gate info.
            </p>
          </div>
          
          <div className="flex-align-center">
            {/* Language Selector */}
            <select 
              value={fanLanguage} 
              onChange={(e) => setFanLanguage(e.target.value)}
              className="select-language"
              aria-label="Select Assistant Language"
              disabled={chatLoading}
            >
              <option value="en">English 🇬🇧</option>
              <option value="es">Español 🇪🇸</option>
              <option value="fr">Français 🇫🇷</option>
            </select>
            
            {/* Text-to-speech toggle */}
            <button 
              onClick={() => {
                setVoiceEnabled(!voiceEnabled);
                if (!voiceEnabled && window.speechSynthesis) {
                  speakText("Voice response activated", fanLanguage);
                }
              }}
              className={`btn-secondary voice-toggle-btn ${voiceEnabled ? "active-voice" : ""}`}
              aria-label="Toggle voice output read back"
              disabled={chatLoading}
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
          {chatLoading && <div className="message-bubble bot typing-indicator">Assistant is typing...</div>}
          {rateLimitMessage && <div className="rate-limit-alert">{rateLimitMessage}</div>}
          <div ref={chatEndRef} />
        </div>
        
        <form onSubmit={handleFanSend} className="chat-input-area">
          <input 
            type="text" 
            className="chat-input"
            placeholder={fanLanguage === "es" ? "Escribe un mensaje..." : fanLanguage === "fr" ? "Écrivez un message..." : "Ask Gate details, route, accessibility support..."}
            value={fanInput}
            onChange={(e) => setFanInput(e.target.value)}
            aria-label="Type your message here"
            disabled={chatLoading}
          />
          
          <button 
            type="button" 
            onClick={toggleListening}
            className={`voice-btn ${isListening ? "active" : ""}`}
            aria-label="Toggle Voice Input Recording"
            disabled={chatLoading}
          >
            🎙️
          </button>
          
          <button type="submit" className="btn-primary" disabled={chatLoading || !fanInput.trim()}>Send</button>
        </form>
      </div>
    </div>
  );
}
