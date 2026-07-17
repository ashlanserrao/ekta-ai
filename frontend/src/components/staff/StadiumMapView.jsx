import React from "react";
import InteractiveMap from "../InteractiveMap";

export default function StadiumMapView({ gates, zones }) {
  return (
    <div className="fan-view map-page">
      <div className="map-view-center">
        <InteractiveMap gates={gates} zones={zones} />
      </div>
    </div>
  );
}
