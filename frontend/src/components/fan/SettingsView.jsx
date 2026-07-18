import React from "react";
import { ZoomIn, Accessibility } from "lucide-react";
import { useTranslation } from "../../lib/LanguageContext";

export default function SettingsView({ highContrast, largeText, setHighContrast, setLargeText }) {
  const { t } = useTranslation();
  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>{t("settings.heading")}</h1>
        <p>{t("settings.sub")}</p>
      </div>

      <div className="glass-panel settings-card">
        <div className="settings-row">
          <div>
            <div className="settings-name"><ZoomIn size={16} style={{ verticalAlign: "-3px", marginRight: "0.3rem" }} />{t("settings.largeText")}</div>
            <div className="settings-desc">{t("settings.largeTextDesc")}</div>
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
            <div className="settings-name"><Accessibility size={16} style={{ verticalAlign: "-3px", marginRight: "0.3rem" }} />{t("settings.highContrast")}</div>
            <div className="settings-desc">{t("settings.highContrastDesc")}</div>
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
