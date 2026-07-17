import React from "react";
import InteractiveMap from "../InteractiveMap";

export default function MapView({ gates, zones, activeRoute }) {
  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Live Stadium Map</h1>
        <p>Real-time crowd density and route planning. Ask the assistant (bottom-right) for directions to light up a path.</p>
      </div>
      <div className="map-view-center">
        <InteractiveMap gates={gates} zones={zones} activeRoute={activeRoute} />
      </div>
    </div>
  );
}
