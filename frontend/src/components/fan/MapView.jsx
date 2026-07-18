import React from "react";
import InteractiveMap from "../InteractiveMap";

export default function MapView({ gates, zones, activeRoute, profile }) {
  return (
    <div className="fan-view map-page">
      <p className="map-page-hint">Ask the assistant (bottom-right) for directions to light up a path.</p>
      <div className="map-view-center">
        <InteractiveMap gates={gates} zones={zones} activeRoute={activeRoute} homeGate={profile?.homeGate} />
      </div>
    </div>
  );
}
