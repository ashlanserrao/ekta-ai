import React from "react";

export default function SettingsView({ highContrast, largeText, setHighContrast, setLargeText }) {
  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Settings</h1>
        <p>Accessibility options for a more comfortable experience.</p>
      </div>

      <div className="glass-panel settings-card">
        <div className="settings-row">
          <div>
            <div className="settings-name">🔍 Large Text</div>
            <div className="settings-desc">Increase font sizes across the app.</div>
          </div>
          <button
            className={`toggle ${largeText ? "on" : ""}`}
            onClick={() => setLargeText(!largeText)}
            aria-pressed={largeText}
            aria-label="Toggle large text"
          >
            <span className="toggle-knob" />
          </button>
        </div>

        <div className="settings-row">
          <div>
            <div className="settings-name">♿ High Contrast</div>
            <div className="settings-desc">Maximise contrast for low-vision readability.</div>
          </div>
          <button
            className={`toggle ${highContrast ? "on" : ""}`}
            onClick={() => setHighContrast(!highContrast)}
            aria-pressed={highContrast}
            aria-label="Toggle high contrast"
          >
            <span className="toggle-knob" />
          </button>
        </div>
      </div>
    </div>
  );
}
