import React from "react";
import { useTranslation } from "../../lib/useTranslation";
import InteractiveMap from "../InteractiveMap";

export default function MapView({ gates, zones, activeRoute, profile }) {
  const { t } = useTranslation();
  return (
    <div className="fan-view map-page">
      <p className="map-page-hint">{t("map.hint")}</p>
      <div className="map-view-center">
        <InteractiveMap gates={gates} zones={zones} activeRoute={activeRoute} homeGate={profile?.homeGate} />
      </div>
    </div>
  );
}
