import React from "react";

const SEGMENTS = 24;

// A pure-CSS 3D stadium bowl: a ring of vertical stand panels (lower + upper tier)
// around a central pitch, slowly auto-rotating. No dependencies, renders offline.
export default function Stadium3D() {
  const segments = Array.from({ length: SEGMENTS });
  const step = 360 / SEGMENTS;

  return (
    <div className="stadium-scene" aria-hidden="true">
      <div className="stadium-tilt">
        <div className="stadium-rotor">
          {/* Pitch */}
          <div className="stadium-pitch">
            <span className="pitch-circle" />
            <span className="pitch-line" />
          </div>

          {/* Lower tier stands */}
          {segments.map((_, i) => (
            <div
              key={`l${i}`}
              className="stand stand-lower"
              style={{ transform: `rotateY(${step * i}deg) translateZ(150px)` }}
            />
          ))}

          {/* Upper tier stands (raised + slightly further out) */}
          {segments.map((_, i) => (
            <div
              key={`u${i}`}
              className="stand stand-upper"
              style={{ transform: `rotateY(${step * i}deg) translateZ(178px) translateY(-40px)` }}
            />
          ))}

          {/* Floodlights at four corners */}
          {[45, 135, 225, 315].map((a) => (
            <div
              key={`f${a}`}
              className="floodlight"
              style={{ transform: `rotateY(${a}deg) translateZ(210px) translateY(-70px)` }}
            >
              <span className="floodlight-head" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
