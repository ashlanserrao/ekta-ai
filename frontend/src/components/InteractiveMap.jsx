import React, { useState } from "react";

const NODE_COORDINATES = {
  // Gates
  "Gate 1": { x: 250, y: 70 },
  "Gate 2": { x: 430, y: 250 },
  "Gate 3": { x: 250, y: 430 },
  "Gate 4": { x: 70, y: 250 },
  // Intermediary/Access points
  "North Concourse Ramp A": { x: 200, y: 130 },
  "North Main Stairs": { x: 280, y: 130 },
  "East elevator block": { x: 360, y: 220 },
  "East Escalator A": { x: 360, y: 280 },
  "South elevator B": { x: 250, y: 360 },
  "South Concourse Stairs 4": { x: 200, y: 360 },
  "West Concourse level path": { x: 140, y: 280 },
  "West Escalator B": { x: 140, y: 220 },
  // Seating Entries
  "Section 102 Entry": { x: 250, y: 170 },
  "Section 105 Entry": { x: 160, y: 190 },
  "Section 204 Entry": { x: 320, y: 250 },
  "Section 305 Entry": { x: 250, y: 310 }
};

export default function InteractiveMap({ gates = [], zones = [], activeRoute }) {
  const [hoveredZone, setHoveredZone] = useState(null);

  const getCongestionColor = (level) => {
    if (level === "low") return "var(--color-low)";
    if (level === "medium") return "var(--color-medium)";
    return "var(--color-high)";
  };

  const getZoneColor = (zoneId) => {
    const zone = zones.find(z => z.id === zoneId);
    if (!zone) return "rgba(255, 255, 255, 0.05)";
    const density = zone.density;
    if (density > 0.85) return "rgba(239, 68, 68, 0.4)";
    if (density >= 0.70) return "rgba(245, 158, 11, 0.3)";
    if (density >= 0.40) return "rgba(251, 191, 36, 0.2)";
    return "rgba(16, 185, 129, 0.2)";
  };

  const getZoneStroke = (zoneId) => {
    const zone = zones.find(z => z.id === zoneId);
    if (!zone) return "var(--border-color)";
    const density = zone.density;
    if (density > 0.85) return "var(--color-high)";
    if (density >= 0.70) return "#f97316";
    if (density >= 0.40) return "var(--color-medium)";
    return "var(--color-low)";
  };

  const hoveredZoneData = zones.find(z => z.id === hoveredZone);

  return (
    <div className="glass-panel map-container">
      <div className="map-header">
        <h2>Stadium Live Map & Route Planner</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
          Hover stands sectors to view live digital twin sensor feed.
        </p>
      </div>
      <div className="map-body" aria-label="Interactive map representation of stadium gates and sections">
        <svg className="stadium-svg" viewBox="0 0 500 500">
          {/* Inner Stands dashed guideline */}
          <circle cx="250" cy="250" r="130" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" strokeDasharray="3,3" />

          {/* Render Stadium Zone Arches (North, East, South, West) */}
          <g className="stadium-zones">
            {/* Zone-A (North Stand - Top) */}
            <path 
              d="M 116 116 L 158 158 A 130 130 0 0 1 342 158 L 384 116 A 190 190 0 0 0 116 116 Z" 
              fill={getZoneColor("Zone-A")} 
              stroke={getZoneStroke("Zone-A")} 
              strokeWidth="2"
              className={zones.find(z => z.id === "Zone-A")?.density > 0.85 ? "pulse-zone" : "interactive-zone"}
              onMouseEnter={() => setHoveredZone("Zone-A")}
              onMouseLeave={() => setHoveredZone(null)}
            />

            {/* Zone-B (East Stand - Right) */}
            <path 
              d="M 384 116 L 342 158 A 130 130 0 0 1 342 342 L 384 384 A 190 190 0 0 0 384 116 Z" 
              fill={getZoneColor("Zone-B")} 
              stroke={getZoneStroke("Zone-B")} 
              strokeWidth="2"
              className={zones.find(z => z.id === "Zone-B")?.density > 0.85 ? "pulse-zone" : "interactive-zone"}
              onMouseEnter={() => setHoveredZone("Zone-B")}
              onMouseLeave={() => setHoveredZone(null)}
            />

            {/* Zone-C (South Stand - Bottom) */}
            <path 
              d="M 384 384 L 342 342 A 130 130 0 0 1 158 342 L 116 384 A 190 190 0 0 0 384 384 Z" 
              fill={getZoneColor("Zone-C")} 
              stroke={getZoneStroke("Zone-C")} 
              strokeWidth="2"
              className={zones.find(z => z.id === "Zone-C")?.density > 0.85 ? "pulse-zone" : "interactive-zone"}
              onMouseEnter={() => setHoveredZone("Zone-C")}
              onMouseLeave={() => setHoveredZone(null)}
            />

            {/* Zone-D (West Stand - Left) */}
            <path 
              d="M 116 384 L 158 342 A 130 130 0 0 1 158 158 L 116 116 A 190 190 0 0 0 116 384 Z" 
              fill={getZoneColor("Zone-D")} 
              stroke={getZoneStroke("Zone-D")} 
              strokeWidth="2"
              className={zones.find(z => z.id === "Zone-D")?.density > 0.85 ? "pulse-zone" : "interactive-zone"}
              onMouseEnter={() => setHoveredZone("Zone-D")}
              onMouseLeave={() => setHoveredZone(null)}
            />
          </g>

          {/* Outer boundary */}
          <circle cx="250" cy="250" r="190" fill="none" stroke="var(--border-color)" strokeWidth="4" />
          {/* Inner stands */}
          <circle cx="250" cy="250" r="130" fill="none" stroke="var(--border-color)" strokeWidth="2" strokeDasharray="5,5" />
          {/* Pitch representation */}
          <rect x="180" y="200" width="140" height="100" fill="none" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="2" />
          
          {/* Render route if active */}
          {activeRoute && activeRoute.path_nodes && activeRoute.path_nodes.length > 1 && (
            <g>
              {activeRoute.path_nodes.map((nodeName, idx) => {
                if (idx === activeRoute.path_nodes.length - 1) return null;
                const start = NODE_COORDINATES[nodeName];
                const end = NODE_COORDINATES[activeRoute.path_nodes[idx + 1]];
                if (!start || !end) return null;
                return (
                  <line 
                    key={`path-line-${idx}`}
                    x1={start.x} 
                    y1={start.y} 
                    x2={end.x} 
                    y2={end.y} 
                    stroke={activeRoute.is_accessible === 1 ? "var(--accent-secondary)" : "var(--accent-color)"}
                    strokeWidth="5" 
                    strokeDasharray={activeRoute.is_accessible === 1 ? "none" : "8,4"}
                    strokeLinecap="round"
                    className="pulse-path"
                  />
                );
              })}
            </g>
          )}
          
          {/* Render node markers in active route */}
          {activeRoute && activeRoute.path_nodes && activeRoute.path_nodes.map((nodeName, idx) => {
            const coord = NODE_COORDINATES[nodeName];
            if (!coord) return null;
            const isStart = idx === 0;
            const isEnd = idx === activeRoute.path_nodes.length - 1;
            return (
              <g key={`route-node-${idx}`}>
                <circle 
                  cx={coord.x} 
                  cy={coord.y} 
                  r="7" 
                  fill={isStart ? "var(--color-low)" : isEnd ? "var(--accent-secondary)" : "var(--text-primary)"} 
                />
                <text 
                  x={coord.x} 
                  y={coord.y - 12} 
                  fill="white" 
                  fontSize="9" 
                  fontWeight="700" 
                  textAnchor="middle"
                  style={{ textShadow: "0 2px 4px rgba(0,0,0,0.8)" }}
                >
                  {nodeName}
                </text>
              </g>
            );
          })}
          
          {/* Render general gates if not routed */}
          {!activeRoute && gates.map((gate) => {
            const coord = NODE_COORDINATES[gate.name];
            if (!coord) return null;
            const color = getCongestionColor(gate.congestion_level);
            return (
              <g key={gate.id}>
                <circle 
                  cx={coord.x} 
                  cy={coord.y} 
                  r="10" 
                  fill={gate.status === "open" ? color : "#4b5563"} 
                  stroke="white" 
                  strokeWidth="2"
                  className="node-marker" 
                />
                <text 
                  x={coord.x} 
                  y={coord.y - 14} 
                  fill="white" 
                  fontSize="10" 
                  fontWeight="700" 
                  textAnchor="middle"
                  style={{ textShadow: "0 2px 4px rgba(0,0,0,0.8)" }}
                >
                  {gate.name}
                </text>
              </g>
            );
          })}
        </svg>
        
        {/* HUD Details Panel */}
        {hoveredZoneData ? (
          <div style={{ position: "absolute", bottom: "10px", left: "15px", background: "rgba(0,0,0,0.85)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-active)", fontSize: "0.8rem", animation: "slideIn 0.2s ease", zIndex: 10 }}>
            <strong style={{ color: "var(--accent-secondary)", display: "block", marginBottom: "4px" }}>{hoveredZoneData.name} Sensor Feed</strong>
            <div>Occupants: <strong>{hoveredZoneData.current_crowd}</strong> / {hoveredZoneData.capacity}</div>
            <div>Density: <strong>{Math.round(hoveredZoneData.density * 100)}%</strong></div>
          </div>
        ) : (
          <div style={{ position: "absolute", bottom: "10px", left: "15px", background: "rgba(0,0,0,0.75)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            Hover stands quadrant for detailed sensor metrics
          </div>
        )}

        {/* Map Legend */}
        <div style={{ position: "absolute", bottom: "10px", right: "15px", display: "flex", gap: "10px", background: "rgba(0,0,0,0.75)", padding: "8px 12px", borderRadius: "8px", fontSize: "0.7rem", border: "1px solid var(--border-color)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--color-low)" }}></span> Low
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--color-medium)" }}></span> Med
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--color-high)" }}></span> High
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#4b5563" }}></span> Closed
          </div>
        </div>
      </div>
    </div>
  );
}
