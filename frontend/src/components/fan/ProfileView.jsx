import React from "react";
import { Ticket } from "lucide-react";
import { useTranslation } from "../../lib/useTranslation";

const initials = (name) =>
  (name || "Guest Fan").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

export default function ProfileView({ profile }) {
  const { t } = useTranslation();
  const p = profile || {};
  const details = [
    { key: "email", labelKey: "profile.email", value: p.email },
    { key: "city", labelKey: "profile.city", value: p.city },
    { key: "favoriteTeam", labelKey: "profile.favoriteTeam", value: p.favoriteTeam },
    { key: "homeGate", labelKey: "profile.homeGate", value: p.homeGate },
    { key: "drink", labelKey: "profile.drink", value: p.drink },
    { key: "dietary", labelKey: "profile.dietary", value: p.dietary },
    { key: "language", labelKey: "profile.language", value: p.language },
    { key: "accessibility", labelKey: "profile.accessibleRoutes", value: p.accessibility ? t("profile.enabled") : t("profile.notRequired") },
  ];

  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>{t("profile.heading")}</h1>
        <p>{t("profile.sub")}</p>
      </div>

      <div className="glass-panel profile-card">
        <div className="profile-header">
          <div className="profile-avatar">{initials(p.fullName)}</div>
          <div>
            <h2 className="profile-name">{p.fullName || "Guest Fan"}</h2>
            <span className="profile-role"><Ticket size={14} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />{t("profile.fanRole")}</span>
          </div>
        </div>

        <div className="profile-details">
          {details.map((d) => (
            <div key={d.key} className="profile-row">
              <span className="profile-key">{t(d.labelKey)}</span>
              <span className="profile-val">{d.value || "—"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
