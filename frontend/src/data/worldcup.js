// Illustrative FIFA World Cup 2026 data (real teams/players, fabricated stats)
// used to populate the fan Stats and Schedule views. Not official.

export const TOP_SCORERS = [
  { player: "Kylian Mbappé", team: "France", flag: "FRA", goals: 6, assists: 2 },
  { player: "Lionel Messi", team: "Argentina", flag: "ARG", goals: 5, assists: 4 },
  { player: "Vinícius Júnior", team: "Brazil", flag: "BRA", goals: 5, assists: 3 },
  { player: "Harry Kane", team: "England", flag: "ENG", goals: 4, assists: 1 },
  { player: "Christian Pulisic", team: "USA", flag: "USA", goals: 3, assists: 3 },
  { player: "Jude Bellingham", team: "England", flag: "ENG", goals: 3, assists: 2 },
];

export const RECENT_RESULTS = [
  { home: "Argentina", homeFlag: "ARG", away: "Mexico", awayFlag: "MEX", score: "2 – 1", stage: "Quarter-final" },
  { home: "France", homeFlag: "FRA", away: "Canada", awayFlag: "CAN", score: "3 – 0", stage: "Quarter-final" },
  { home: "Brazil", homeFlag: "BRA", away: "England", awayFlag: "ENG", score: "2 – 2 (4–3 pens)", stage: "Quarter-final" },
  { home: "USA", homeFlag: "USA", away: "Netherlands", awayFlag: "NED", score: "1 – 0", stage: "Round of 16" },
];

export const STANDINGS = {
  group: "Group A",
  rows: [
    { team: "Argentina", flag: "ARG", p: 3, w: 3, d: 0, l: 0, gd: "+6", pts: 9 },
    { team: "Mexico", flag: "MEX", p: 3, w: 1, d: 1, l: 1, gd: "+1", pts: 4 },
    { team: "Poland", flag: "POL", p: 3, w: 1, d: 0, l: 2, gd: "-2", pts: 3 },
    { team: "Saudi Arabia", flag: "KSA", p: 3, w: 0, d: 1, l: 2, gd: "-5", pts: 1 },
  ],
};

export const TOURNAMENT_STATS = [
  { label: "Matches Played", value: "58" },
  { label: "Goals Scored", value: "164" },
  { label: "Avg Goals / Match", value: "2.83" },
  { label: "Total Attendance", value: "3.9M" },
];

export const SCHEDULE = [
  { date: "Jul 15, 2026", time: "16:00", home: "Argentina", homeFlag: "ARG", away: "France", awayFlag: "FRA", venue: "MetLife Stadium, NJ", stage: "Semi-final" },
  { date: "Jul 15, 2026", time: "20:00", home: "Brazil", homeFlag: "BRA", away: "Spain", awayFlag: "ESP", venue: "AT&T Stadium, Dallas", stage: "Semi-final" },
  { date: "Jul 18, 2026", time: "15:00", home: "France", homeFlag: "FRA", away: "Spain", awayFlag: "ESP", venue: "Estadio Azteca, Mexico City", stage: "Third place" },
  { date: "Jul 19, 2026", time: "15:00", home: "Argentina", homeFlag: "ARG", away: "Brazil", awayFlag: "BRA", venue: "MetLife Stadium, NJ", stage: "Final" },
];

export const TEAMS = [
  "Argentina", "Brazil", "France", "Spain", "England", "USA", "Mexico", "Canada",
];
