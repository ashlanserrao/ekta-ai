import React from "react";

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

export default function InteractiveMap({ gates, activeRoute }) {
  const getCongestionColor = (level) => {
    if (level === "low") return "var(--color-low)";
    if (level === "medium") return "var(--color-medium)";
    return "var(--color-high)";
  };

  return (
    <div className="glass-panel map-container">
      <div className="map-header">
        <h2>Stadium Live Map & Route Planner</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
          Interactive routing map showing gates congestion status.
        </p>
      </div>
      <div className="map-body" aria-label="Interactive map representation of stadium gates and sections">
        <svg className="stadium-svg" viewBox="0 0 500 500">
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
        
        {/* Map Legend */}
        <div style={{ position: "absolute", bottom: "10px", right: "15px", display: "flex", gap: "10px", background: "rgba(0,0,0,0.7)", padding: "8px 12px", borderRadius: "8px", fontSize: "0.75rem" }}>
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
