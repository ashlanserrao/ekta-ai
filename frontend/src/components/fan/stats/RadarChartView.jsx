import React from "react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Legend, Tooltip,
} from "recharts";

// Shared radar chart for both the team-comparison view and the player FIFA
// pentagon chart. `series` is one or two { name, color, values } entries,
// `axes` is [{ key, label }] — values are read from values[axis.key].
export default function RadarChartView({ axes, series, maxValue = 99 }) {
  const data = axes.map((axis) => {
    const row = { axis: axis.label };
    series.forEach((s) => { row[s.name] = s.values[axis.key] ?? 0; });
    return row;
  });

  return (
    <div className="radar-chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="75%">
          <PolarGrid stroke="rgba(255, 255, 255, 0.12)" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, maxValue]} tick={{ fill: "#7c8aa3", fontSize: 9 }} />
          {series.map((s) => (
            <Radar key={s.name} name={s.name} dataKey={s.name} stroke={s.color} fill={s.color} fillOpacity={0.35} isAnimationActive={false} />
          ))}
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: "0.8rem", color: "#f8fafc" }} />}
          <Tooltip
            contentStyle={{ background: "#192130", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
            labelStyle={{ color: "#f8fafc" }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
