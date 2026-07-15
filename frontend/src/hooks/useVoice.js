import { useState, useEffect, useRef } from "react";

export function useVoice(fanLanguage, setFanInput) {
  const [isListening, setIsListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognitionRef = useRef(null);
  
  if (SpeechRecognition && !recognitionRef.current) {
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = fanLanguage === "es" ? "es-ES" : "en-US";
    
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setFanInput(transcript);
      setIsListening(false);
    };
    
    rec.onerror = (e) => {
      console.error("Speech Recognition Error:", e);
      setIsListening(false);
    };
    
    rec.onend = () => {
      setIsListening(false);
    };
    
    recognitionRef.current = rec;
  }

  // Synchronize language code changes
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.lang = fanLanguage === "es" ? "es-ES" : "en-US";
    }
  }, [fanLanguage]);
  
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech Recognition API is not supported in this browser. Please try Chrome or Safari.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };
  
  const speakText = (text, lang) => {
    if (!voiceEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel(); // Cancel current utterance
    const utterance = new SpeechUtterance(text);
    utterance.lang = lang === "es" ? "es-ES" : "en-US";
    window.speechSynthesis.speak(utterance);
  };

  return {
    isListening,
    voiceEnabled,
    setVoiceEnabled,
    toggleListening,
    speakText
  };
}
