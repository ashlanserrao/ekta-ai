import React, { useState } from "react";
import { Brain, Map, BarChart3, Globe } from "lucide-react";
import Stadium3D from "./Stadium3D";
import AuthModal from "./AuthModal";
import OnboardingWizard from "./OnboardingWizard";

const CAPABILITIES = [
  { icon: Brain, title: "Operations Copilot", desc: "Forecasts congestion minutes ahead and recommends actions before bottlenecks form.", span: "bento-featured" },
  { icon: Map, title: "Smart Navigation", desc: "Step-free, accessible routing from any gate to any seat, live on an interactive map." },
  { icon: BarChart3, title: "Live Crowd Intelligence", desc: "A real-time digital twin of every zone and gate, with automatic plain-language alerts." },
  { icon: Globe, title: "Multilingual Assistance", desc: "Voice and chat help in English, Spanish, and French for every fan.", span: "bento-wide" },
];

const STEPS = [
  { num: "1", title: "Choose your role", desc: "Join as a fan or a stadium staff member." },
  { num: "2", title: "Tell us about you", desc: "A few basic details to set up your profile." },
  { num: "3", title: "Set preferences", desc: "Team, gate & accessibility — or your department & assignment." },
  { num: "4", title: "Enter the platform", desc: "Jump straight into your personalized dashboard." },
];

export default function Landing({ onAuthenticated }) {
  const [modal, setModal] = useState(null); // 'fan-login' | 'staff-login' | 'get-started'

  return (
    <div className="landing">
      {/* Navbar */}
      <nav className="landing-nav">
        <div className="logo-container">
          <div className="logo-badge">EKTA 26</div>
          <div>
            <h1 className="logo-text">EktaAI</h1>
            <div className="logo-sub">Stadium Operations Twin</div>
          </div>
        </div>
        <div className="landing-nav-actions">
          <button className="btn-secondary" onClick={() => setModal("fan-login")}>Fan Login</button>
          <button className="btn-secondary" onClick={() => setModal("staff-login")}>Staff Login</button>
          <button className="btn-primary" onClick={() => setModal("get-started")}>Get Started</button>
        </div>
      </nav>

      {/* Hero */}
      <header className="landing-hero">
        <Stadium3D />
        <h2 className="hero-tagline">Manage Every Moment</h2>
        <p className="hero-sub">
          A GenAI operations twin for the FIFA World Cup 2026 — real-time crowd intelligence,
          accessible navigation, and proactive decision support in one platform.
        </p>
        <div className="hero-cta">
          <button className="btn-primary hero-btn" onClick={() => setModal("get-started")}>Get Started</button>
          <button className="btn-secondary hero-btn" onClick={() => setModal("fan-login")}>Explore as Fan</button>
        </div>
      </header>

      {/* Platform Capabilities */}
      <section className="landing-section" aria-label="Platform capabilities">
        <h3 className="section-title">Platform Capabilities</h3>
        <p className="section-sub">Everything a venue needs to run a world-class match day.</p>
        <div className="card-row bento-grid">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className={`feature-card glass-panel ${c.span || ""}`}>
              <div className="feature-icon"><c.icon size={c.span === "bento-featured" ? 30 : 22} /></div>
              <h4 className="feature-title">{c.title}</h4>
              <p className="feature-desc">{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Steps to Register */}
      <section className="landing-section alt" aria-label="Steps to register">
        <h3 className="section-title">Steps to Register</h3>
        <p className="section-sub">Up and running in under a minute.</p>
        <div className="card-row">
          {STEPS.map((s) => (
            <div key={s.num} className="step-card glass-panel">
              <div className="step-num">{s.num}</div>
              <h4 className="feature-title">{s.title}</h4>
              <p className="feature-desc">{s.desc}</p>
            </div>
          ))}
        </div>
        <div className="section-cta">
          <button className="btn-primary hero-btn" onClick={() => setModal("get-started")}>Create your account</button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-brand">
          <div className="logo-badge">EKTA 26</div>
          <div>
            <div className="logo-text" style={{ fontSize: "1.1rem" }}>EktaAI</div>
            <div className="logo-sub">Manage Every Moment</div>
          </div>
        </div>
        <div className="footer-cols">
          <div className="footer-col">
            <span className="footer-head">Platform</span>
            <span>Operations Copilot</span>
            <span>Digital Twin</span>
            <span>Accessible Navigation</span>
          </div>
          <div className="footer-col">
            <span className="footer-head">Access</span>
            <button className="footer-link" onClick={() => setModal("fan-login")}>Fan Login</button>
            <button className="footer-link" onClick={() => setModal("staff-login")}>Staff Login</button>
            <button className="footer-link" onClick={() => setModal("get-started")}>Get Started</button>
          </div>
          <div className="footer-col">
            <span className="footer-head">Event</span>
            <span>FIFA World Cup 2026</span>
            <span>USA · Canada · Mexico</span>
          </div>
        </div>
        <div className="footer-bottom">© 2026 EktaAI · Built for PromptWars. Demo credentials: test / test.</div>
      </footer>

      {/* Modals */}
      {modal === "fan-login" && (
        <AuthModal mode="fan" onClose={() => setModal(null)} onSuccess={onAuthenticated} />
      )}
      {modal === "staff-login" && (
        <AuthModal mode="staff" onClose={() => setModal(null)} onSuccess={onAuthenticated} />
      )}
      {modal === "get-started" && (
        <OnboardingWizard onClose={() => setModal(null)} onComplete={onAuthenticated} />
      )}
    </div>
  );
}
