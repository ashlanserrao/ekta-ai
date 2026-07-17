import React from "react";
import { SCHEDULE } from "../../data/worldcup";

export default function ScheduleView() {
  return (
    <div className="fan-view">
      <div className="view-heading">
        <h1>Match Schedule</h1>
        <p>Upcoming FIFA World Cup 2026 fixtures across host venues.</p>
      </div>

      <div className="schedule-list">
        {SCHEDULE.map((m, i) => (
          <div key={i} className="glass-panel schedule-row">
            <div className="schedule-date">
              <span className="schedule-day">{m.date}</span>
              <span className="schedule-time">{m.time}</span>
            </div>
            <div className="schedule-match">
              <span className="schedule-team">{m.homeFlag} {m.home}</span>
              <span className="schedule-vs">vs</span>
              <span className="schedule-team">{m.away} {m.awayFlag}</span>
            </div>
            <div className="schedule-meta">
              <span className={`schedule-stage ${m.stage === "Final" ? "final" : ""}`}>{m.stage}</span>
              <span className="schedule-venue">📍 {m.venue}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
