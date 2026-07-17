import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import StatsView from "./StatsView";
import TEAMS from "../../data/teams.json";
import PLAYERS from "../../data/players.json";

const leagueTable = () => screen.getByText(/League Table/i).closest(".stats-panel").querySelector("table");
const playersTable = () => screen.getByText(/All Players/i).closest(".stats-panel").querySelector("table");

describe("StatsView", () => {
  it("renders the Team Stats tab by default with the league table", () => {
    render(<StatsView />);
    expect(screen.getByRole("tab", { name: /Team Stats/i })).toHaveAttribute("aria-selected", "true");
    expect(within(leagueTable()).getByText(new RegExp(TEAMS[0].name))).toBeInTheDocument();
  });

  it("switches to the Player Stats tab and shows leaderboards + filters", () => {
    render(<StatsView />);
    fireEvent.click(screen.getByRole("tab", { name: /Player Stats/i }));
    expect(screen.getByRole("tab", { name: /Player Stats/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Top Scorers/i)).toBeInTheDocument();
    expect(screen.getByText(/All Players/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Filter by team/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Filter by position/i)).toBeInTheDocument();
  });

  it("sorts the team league table when a sortable header is clicked", () => {
    render(<StatsView />);
    const table = leagueTable();
    const getFirstRowTeam = () => within(table).getAllByRole("row")[1].textContent;

    const ptsHeader = within(table).getByText(/^Pts/);
    // Default sort is Pts desc — clicking once flips to ascending.
    const beforeText = getFirstRowTeam();
    fireEvent.click(ptsHeader);
    const afterText = getFirstRowTeam();
    expect(afterText).not.toBe(beforeText);
  });

  it("filters the player table by team", () => {
    render(<StatsView />);
    fireEvent.click(screen.getByRole("tab", { name: /Player Stats/i }));

    const targetTeam = TEAMS[0];
    fireEvent.change(screen.getByLabelText(/Filter by team/i), { target: { value: targetTeam.id } });

    const table = playersTable();
    const rows = within(table).getAllByRole("row").slice(1); // drop header row
    expect(rows.length).toBe(23);
    rows.forEach((row) => {
      expect(within(row).getByText(new RegExp(targetTeam.shortName))).toBeInTheDocument();
    });
  });

  it("shows an empty state when filters match no players", () => {
    render(<StatsView />);
    fireEvent.click(screen.getByRole("tab", { name: /Player Stats/i }));
    fireEvent.change(screen.getByLabelText(/Filter by team/i), { target: { value: "no-such-team" } });
    expect(screen.getByText(/No players match the selected filters/i)).toBeInTheDocument();
  });

  it("opens a team detail modal on row click and closes it", () => {
    render(<StatsView />);
    fireEvent.click(within(leagueTable()).getByText(new RegExp(TEAMS[0].name)));
    expect(screen.getByRole("dialog", { name: new RegExp(`${TEAMS[0].name} team detail`) })).toBeInTheDocument();
    expect(screen.getByText(/xG vs Actual Goals/i)).toBeInTheDocument();
    expect(screen.getByText(/Squad/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Close$/i }));
    expect(screen.queryByRole("dialog", { name: new RegExp(`${TEAMS[0].name} team detail`) })).not.toBeInTheDocument();
  });

  it("opens a player detail modal from the squad list inside a team modal", () => {
    render(<StatsView />);
    fireEvent.click(within(leagueTable()).getByText(new RegExp(TEAMS[0].name)));

    const squadPlayer = PLAYERS.find((p) => p.teamId === TEAMS[0].id);
    const squadList = screen.getByText(/Squad/i).closest(".modal-card").querySelector(".squad-list");
    fireEvent.click(within(squadList).getByText(squadPlayer.name).closest(".squad-row"));

    expect(screen.getByRole("dialog", { name: new RegExp(`${squadPlayer.name} player card`) })).toBeInTheDocument();
    expect(screen.getByText(/Tournament Stats/i)).toBeInTheDocument();
  });

  it("opens a player detail modal from the Player Stats leaderboard", () => {
    render(<StatsView />);
    fireEvent.click(screen.getByRole("tab", { name: /Player Stats/i }));

    const topScorer = [...PLAYERS].sort((a, b) => b.tournamentStats.goals - a.tournamentStats.goals)[0];
    const topScorersPanel = screen.getByText(/Top Scorers/i).closest(".stats-panel");
    fireEvent.click(within(topScorersPanel).getByText(topScorer.name));

    expect(screen.getByRole("dialog", { name: new RegExp(`${topScorer.name} player card`) })).toBeInTheDocument();
  });
});
