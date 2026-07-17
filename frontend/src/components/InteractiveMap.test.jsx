import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InteractiveMap from "./InteractiveMap";

const zones = [
  { id: "Zone-A", name: "North Concourse A", type: "zone", capacity: 5000, current_crowd: 1500, density: 0.3 },
  { id: "Zone-C", name: "South Concourse C", type: "zone", capacity: 8000, current_crowd: 7200, density: 0.9 },
];
const gates = [
  { id: "Gate-1", name: "Gate 1 (North)", status: "open", congestion_level: "low", zone_id: "Zone-A" },
  { id: "Gate-3", name: "Gate 3 (South)", status: "open", congestion_level: "high", zone_id: "Zone-C" },
];

describe("InteractiveMap", () => {
  it("renders the map heading and legend", () => {
    render(<InteractiveMap gates={gates} zones={zones} />);
    expect(screen.getByText(/Stadium Live Map/i)).toBeInTheDocument();
    expect(screen.getByText(/Low/)).toBeInTheDocument();
    expect(screen.getByText(/High/)).toBeInTheDocument();
  });

  it("exposes zone density in an accessible label", () => {
    render(<InteractiveMap gates={gates} zones={zones} />);
    // Zone-C seeded at 90% density
    expect(screen.getByLabelText(/South Stand: 90% density/i)).toBeInTheDocument();
  });

  it("renders gate markers using the '(North)'-suffixed names from the API", () => {
    render(<InteractiveMap gates={gates} zones={zones} />);
    // Regression: coord keys are 'Gate 1' but API sends 'Gate 1 (North)'
    expect(screen.getByText("Gate 1 (North)")).toBeInTheDocument();
    expect(screen.getByText("Gate 3 (South)")).toBeInTheDocument();
  });

  it("draws the route path when an active route is provided", () => {
    const activeRoute = {
      is_accessible: 1,
      path_nodes: ["Gate 2", "East elevator block", "Section 204 Entry"],
    };
    render(<InteractiveMap gates={gates} zones={zones} activeRoute={activeRoute} />);
    expect(screen.getByText("Section 204 Entry")).toBeInTheDocument();
  });
});
