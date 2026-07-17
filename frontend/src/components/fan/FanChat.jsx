import React, { useState, useEffect, useRef } from "react";
import { useVoice } from "../../hooks/useVoice";
import { useChatStream } from "../../hooks/useChatStream";
import { API_BASE } from "../../lib/api";

const getProviderBadge = (provider) => {
  if (provider === "groq") return <span className="provider-badge groq">⚡ Groq Core</span>;
  return <span className="provider-badge offline">🔌 Offline Mode</span>;
};

const PROMPT_SUGGESTIONS = {
  en: [
    "♿ Wheelchair route from Gate 2 to Section 204",
    "🚻 Where are the accessible restrooms?",
    "🍽️ Any halal food options?",
  ],
  es: [
    "♿ Ruta accesible de Gate 1 a Section 105",
    "🚻 ¿Dónde están los baños accesibles?",
    "🍽️ ¿Opciones de comida halal?",
  ],
  fr: [
    "♿ Itinéraire accessible de Porte 3 à Section 305",
    "🚻 Où sont les toilettes accessibles ?",
    "🍽️ Options de nourriture halal ?",
  ],
};

const chipText = (chip) => chip.replace(/^[^\p{L}\p{N}]+/u, "").trim();

// The fan chat assistant, decoupled from the map. Emits generated routes via onRoute
// so the parent can render them on the Live Stadium Map.
export default function FanChat({ onRoute }) {
  const [fanMessages, setFanMessages] = useState([
    { sender: "bot", text: "Welcome to the World Cup 2026! I am EktaAI, your stadium assistant. How can I help you find your seat, food stalls, or accessible routes today?" },
  ]);
  const [fanInput, setFanInput] = useState("");
  const [fanLanguage, setFanLanguage] = useState("en");
  const [chatLoading, setChatLoading] = useState(false);
  const [rateLimitMessage, setRateLimitMessage] = useState("");
  const [activeProvider, setActiveProvider] = useState("groq");

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [fanMessages]);

  const { isListening, voiceEnabled, setVoiceEnabled, toggleListening, speakText } = useVoice(fanLanguage, setFanInput);
  const readChatStream = useChatStream();

  const handleFanSend = async (e, overrideText) => {
    if (e) e.preventDefault();
    const userMsg = (overrideText ?? fanInput).trim();
    if (!userMsg || chatLoading) return;

    setFanMessages((prev) => [...prev, { sender: "user", text: userMsg }]);
    setFanInput("");
    setChatLoading(true);
    setRateLimitMessage("");

    try {
      const historyPayload = fanMessages.slice(-3).map((m) => ({
        role: m.sender === "bot" ? "assistant" : "user",
        content: m.text,
      }));

      const res = await fetch(`${API_BASE}/api/v1/chat/fan`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ message: userMsg, language: fanLanguage, history: historyPayload }),
      });

      if (res.status === 429) {
        const err = await res.json();
        setRateLimitMessage(err.detail);
        setFanMessages((prev) => [...prev, { sender: "bot", text: "⚠️ System busy. Rate limit exceeded. Please wait a moment." }]);
        setChatLoading(false);
        return;
      }

      if (res.ok) {
        setFanMessages((prev) => [...prev, { sender: "bot", text: "" }]);
        let botReply = "";
        const setLastBotText = (text) => setFanMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].sender === "bot") {
            updated[updated.length - 1] = { ...updated[updated.length - 1], text };
          }
          return updated;
        });

        await readChatStream(res, {
          onReset: () => { botReply = ""; setLastBotText(""); },
          onToken: (token) => { botReply += token; setLastBotText(botReply); },
          onProvider: setActiveProvider,
          onRoute: (route) => onRoute?.(route),
        });

        speakText(botReply, fanLanguage);
      } else {
        setFanMessages((prev) => [...prev, { sender: "bot", text: "Sorry, I'm experiencing troubles connecting to the database." }]);
      }
    } catch (err) {
      console.error(err);
      setFanMessages((prev) => [...prev, { sender: "bot", text: "Network error occurred." }]);
    }
    setChatLoading(false);
  };

  return (
    <div className="fanchat" aria-label="Fan chat assistant">
      <div className="chat-header">
        <div>
          <h2 className="chat-title-container">Assistant {getProviderBadge(activeProvider)}</h2>
          <p className="chat-subtitle">Ask directions, gate info or facilities.</p>
        </div>
        <div className="flex-align-center">
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
          <button
            onClick={() => {
              setVoiceEnabled(!voiceEnabled);
              if (!voiceEnabled && window.speechSynthesis) speakText("Voice response activated", fanLanguage);
            }}
            className={`btn-secondary voice-toggle-btn ${voiceEnabled ? "active-voice" : ""}`}
            aria-label="Toggle voice output read back"
            disabled={chatLoading}
          >
            🔊 {voiceEnabled ? "On" : "Off"}
          </button>
        </div>
      </div>

      <div className="chat-messages" aria-live="polite">
        {fanMessages.map((msg, idx) => (
          <div key={idx} className={`message-bubble ${msg.sender}`}>{msg.text}</div>
        ))}
        {!fanMessages.some((m) => m.sender === "user") && !chatLoading && (
          <div className="prompt-chips" role="group" aria-label="Example questions">
            {(PROMPT_SUGGESTIONS[fanLanguage] || PROMPT_SUGGESTIONS.en).map((chip, i) => (
              <button key={i} type="button" className="prompt-chip" onClick={() => handleFanSend(null, chipText(chip))}>
                {chip}
              </button>
            ))}
          </div>
        )}
        {chatLoading && <div className="message-bubble bot typing-indicator">Assistant is typing...</div>}
        {rateLimitMessage && <div className="rate-limit-alert">{rateLimitMessage}</div>}
        <div ref={chatEndRef} />
      </div>

      <form onSubmit={handleFanSend} className="chat-input-area">
        <input
          type="text"
          className="chat-input"
          placeholder={fanLanguage === "es" ? "Escribe un mensaje..." : fanLanguage === "fr" ? "Écrivez un message..." : "Ask gate details, route, accessibility..."}
          value={fanInput}
          onChange={(e) => setFanInput(e.target.value)}
          aria-label="Type your message here"
          disabled={chatLoading}
        />
        <button type="button" onClick={toggleListening} className={`voice-btn ${isListening ? "active" : ""}`} aria-label="Toggle Voice Input Recording" disabled={chatLoading}>
          🎙️
        </button>
        <button type="submit" className="btn-primary" disabled={chatLoading || !fanInput.trim()}>Send</button>
      </form>
    </div>
  );
}
