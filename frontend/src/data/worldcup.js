// Illustrative FIFA World Cup 2026 data (real teams/players, fabricated stats)
// used to populate the fan Stats and Schedule views. Not official.

export const TOP_SCORERS = [
  { player: "Kylian Mbappé", team: "France", flag: "🇫🇷", goals: 6, assists: 2 },
  { player: "Lionel Messi", team: "Argentina", flag: "🇦🇷", goals: 5, assists: 4 },
  { player: "Vinícius Júnior", team: "Brazil", flag: "🇧🇷", goals: 5, assists: 3 },
  { player: "Harry Kane", team: "England", flag: "🏴", goals: 4, assists: 1 },
  { player: "Christian Pulisic", team: "USA", flag: "🇺🇸", goals: 3, assists: 3 },
  { player: "Jude Bellingham", team: "England", flag: "🏴", goals: 3, assists: 2 },
];

export const RECENT_RESULTS = [
  { home: "Argentina", homeFlag: "🇦🇷", away: "Mexico", awayFlag: "🇲🇽", score: "2 – 1", stage: "Quarter-final" },
  { home: "France", homeFlag: "🇫🇷", away: "Canada", awayFlag: "🇨🇦", score: "3 – 0", stage: "Quarter-final" },
  { home: "Brazil", homeFlag: "🇧🇷", away: "England", awayFlag: "🏴", score: "2 – 2 (4–3 pens)", stage: "Quarter-final" },
  { home: "USA", homeFlag: "🇺🇸", away: "Netherlands", awayFlag: "🇳🇱", score: "1 – 0", stage: "Round of 16" },
];

export const STANDINGS = {
  group: "Group A",
  rows: [
    { team: "Argentina", flag: "🇦🇷", p: 3, w: 3, d: 0, l: 0, gd: "+6", pts: 9 },
    { team: "Mexico", flag: "🇲🇽", p: 3, w: 1, d: 1, l: 1, gd: "+1", pts: 4 },
    { team: "Poland", flag: "🇵🇱", p: 3, w: 1, d: 0, l: 2, gd: "-2", pts: 3 },
    { team: "Saudi Arabia", flag: "🇸🇦", p: 3, w: 0, d: 1, l: 2, gd: "-5", pts: 1 },
  ],
};

export const TOURNAMENT_STATS = [
  { label: "Matches Played", value: "58" },
  { label: "Goals Scored", value: "164" },
  { label: "Avg Goals / Match", value: "2.83" },
  { label: "Total Attendance", value: "3.9M" },
];

export const SCHEDULE = [
  { date: "Jul 15, 2026", time: "16:00", home: "Argentina", homeFlag: "🇦🇷", away: "France", awayFlag: "🇫🇷", venue: "MetLife Stadium, NJ", stage: "Semi-final" },
  { date: "Jul 15, 2026", time: "20:00", home: "Brazil", homeFlag: "🇧🇷", away: "Spain", awayFlag: "🇪🇸", venue: "AT&T Stadium, Dallas", stage: "Semi-final" },
  { date: "Jul 18, 2026", time: "15:00", home: "France", homeFlag: "🇫🇷", away: "Spain", awayFlag: "🇪🇸", venue: "Estadio Azteca, Mexico City", stage: "Third place" },
  { date: "Jul 19, 2026", time: "15:00", home: "Argentina", homeFlag: "🇦🇷", away: "Brazil", awayFlag: "🇧🇷", venue: "MetLife Stadium, NJ", stage: "Final" },
];

export const TEAMS = [
  "Argentina", "Brazil", "France", "Spain", "England", "USA", "Mexico", "Canada",
];
