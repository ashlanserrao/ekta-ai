import React, { useState, useEffect } from "react";
import { TrainFront, BusFront, Bus, Leaf, Sparkles, Zap, WifiOff, Clock } from "lucide-react";
import { API_BASE } from "../../lib/api";
import { useTranslation } from "../../lib/useTranslation";

const MODE_ICONS = { metro: TrainFront, rail: TrainFront, shuttle: BusFront, bus: Bus };

const POLL_INTERVAL_MS = 10000;

export default function TransitView() {
  const { t } = useTranslation();
  const [transit, setTransit] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchTransit = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/transit`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setTransit(data);
        }
      } catch (err) {
        console.error("Error fetching transit status:", err);
      }
    };

    fetchTransit();
    const interval = setInterval(fetchTransit, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (!transit) {
    return (
      <div className="fan-view">
        <div className="glass-panel padding-large">
          <h2>{t("transit.heading")}</h2>
          <p className="panel-desc">{t("transit.loading")}</p>
        </div>
      </div>
    );
  }

  const providerBadge = transit.advisory.provider === "groq"
    ? <span className="provider-badge groq"><Zap size={14} /> {t("transit.providerGroq")}</span>
    : <span className="provider-badge offline"><WifiOff size={14} /> {t("transit.providerOffline")}</span>;

  return (
    <div className="fan-view">
      <div className="glass-panel padding-large">
        <h2>{t("transit.heading")}</h2>
        <p className="panel-desc">{t("transit.sub")}</p>

        <div className="glass-panel density-card density-card-bg" style={{ marginBottom: "1rem" }}>
          <div className="flex-between">
            <span className="bold-text">
              <Sparkles size={16} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />
              {t("transit.advisoryHeading")}
            </span>
            {providerBadge}
          </div>
          <p style={{ margin: "0.6rem 0 0.4rem" }}>{transit.advisory.summary}</p>
          <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
            {transit.advisory.tips.map((tip, idx) => (
              <li key={idx} className="text-small-muted" style={{ marginBottom: "0.25rem" }}>
                <Leaf size={13} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />
                {tip}
              </li>
            ))}
          </ul>
        </div>

        <div className="density-grid">
          {transit.lines.map((line) => {
            const ModeIcon = MODE_ICONS[line.mode] || Bus;
            const loadPct = Math.round(line.current_load * 100);
            return (
              <div key={line.id} className="glass-panel density-card density-card-bg">
                <div className="flex-between">
                  <span className="bold-text">
                    <ModeIcon size={16} style={{ verticalAlign: "-3px", marginRight: "0.35rem" }} />
                    {line.name}
                  </span>
                  <span className={`status-badge ${line.crowding}`}>{t(`transit.${line.crowding}`)}</span>
                </div>
                <div className="text-small-muted">→ {line.destination}</div>
                <div className="density-val">
                  <Clock size={18} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />
                  {Math.ceil(line.minutes_to_next)} {t("transit.minSuffix")}
                </div>
                <div className="text-small-muted">
                  {t("transit.nextDeparture")} · {loadPct}% {t("transit.full")} · {line.status === "delayed" ? t("transit.statusDelayed") : t("transit.statusOnTime")}
                </div>
                <div className="progress-bar-bg">
                  <div className={`progress-bar-fill ${line.crowding}`} style={{ width: `${loadPct}%` }} />
                </div>
                <div className="text-small-muted" style={{ marginTop: "0.4rem" }}>
                  <Leaf size={13} style={{ verticalAlign: "-2px", marginRight: "0.3rem" }} />
                  {t("transit.co2Note", { kg: line.co2_saved_kg_per_trip })}
                </div>
              </div>
            );
          })}
        </div>

        <p className="text-small-muted" style={{ marginTop: "1rem" }}>
          {t("transit.capacityLabel")}: {transit.egress_capacity_per_minute} {t("transit.perMinute")}
        </p>
      </div>
    </div>
  );
}
