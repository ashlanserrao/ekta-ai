import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import ScheduleView from "./ScheduleView";
import MATCHES from "../../data/matches.json";

describe("ScheduleView", () => {
  it("renders the Matches tab by default, defaulting to Ongoing since a match is live", () => {
    render(<ScheduleView />);
    expect(screen.getByRole("tab", { name: /^Matches$/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Ongoing/i })).toHaveAttribute("aria-selected", "true");

    const liveMatches = MATCHES.filter((m) => m.status === "live");
    expect(screen.getAllByText(/LIVE/i).length).toBeGreaterThanOrEqual(liveMatches.length);
  });

  it("switches between Recent and Upcoming sub-tabs", () => {
    render(<ScheduleView />);
    fireEvent.click(screen.getByRole("tab", { name: /^Recent$/i }));
    const recentMatch = MATCHES.find((m) => m.status === "completed");
    expect(screen.getByText(new RegExp(recentMatch.teamA.name))).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /^Upcoming$/i }));
    const upcomingMatch = MATCHES.find((m) => m.status === "upcoming" && m.teamA && m.teamB);
    expect(screen.getByText(new RegExp(upcomingMatch.teamA.name))).toBeInTheDocument();
  });

  it("opens a match detail modal on click and closes it", () => {
    render(<ScheduleView />);
    fireEvent.click(screen.getByRole("tab", { name: /^Recent$/i }));
    const recentMatch = MATCHES.find((m) => m.status === "completed");

    fireEvent.click(screen.getByText(new RegExp(recentMatch.teamA.name)).closest(".result-card"));
    expect(screen.getByText(/Full-time/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Close$/i }));
    expect(screen.queryByText(/Full-time/i)).not.toBeInTheDocument();
  });

  it("switches to the Bracket tab and renders all 5 rounds with correct match counts", () => {
    render(<ScheduleView />);
    fireEvent.click(screen.getByRole("tab", { name: /^Bracket$/i }));

    const expected = { "Round of 32": 16, "Round of 16": 8, "Quarter-Final": 4, "Semi-Final": 2, "Final": 1 };
    Object.entries(expected).forEach(([title, count]) => {
      const column = screen.getByText(title).closest(".bracket-round");
      expect(within(column).getAllByText(/./).length).toBeGreaterThan(0);
      expect(column.querySelectorAll(".bracket-match").length).toBe(count);
    });
  });

  it("highlights a team's path through the bracket when its name is clicked", () => {
    render(<ScheduleView />);
    fireEvent.click(screen.getByRole("tab", { name: /^Bracket$/i }));

    const r32Match = MATCHES.find((m) => m.round === "R32");
    const teamButton = screen.getByRole("button", { name: new RegExp(r32Match.teamA.name) });

    expect(teamButton).not.toHaveClass("highlighted");
    fireEvent.click(teamButton);
    expect(teamButton).toHaveClass("highlighted");
    fireEvent.click(teamButton);
    expect(teamButton).not.toHaveClass("highlighted");
  });
});
