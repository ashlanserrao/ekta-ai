import sqlite3
from backend.app.config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    # Enable WAL mode to support concurrent read/write execution
    conn.execute("PRAGMA journal_mode=WAL;")
    # Set busy timeout to 5 seconds so connections wait for locks to clear
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        current_crowd INTEGER NOT NULL DEFAULT 0,
        density REAL NOT NULL DEFAULT 0.0
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        congestion_level TEXT NOT NULL DEFAULT 'low',
        zone_id TEXT,
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_node TEXT NOT NULL,
        to_node TEXT NOT NULL,
        distance_or_weight REAL NOT NULL,
        is_accessible INTEGER NOT NULL,
        edge_type TEXT NOT NULL,
        FOREIGN KEY (from_node) REFERENCES nodes(id),
        FOREIGN KEY (to_node) REFERENCES nodes(id)
    )
    """)

    # Anonymized product-analytics log: a random per-browser-session id, a coarse
    # event type/view, and small non-sensitive counters only. Never raw chat text,
    # names, or emails — this exists to demonstrate what is (and isn't) collected.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interaction_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        event_type TEXT NOT NULL,
        view TEXT,
        meta TEXT
    )
    """)

    conn.commit()

    # 2. Seed data (if empty)
    cursor.execute("SELECT COUNT(*) as count FROM zones")
    if cursor.fetchone()["count"] == 0:
        # Zones
        zones_data = [
            ("Zone-A", "North Concourse A", "zone", 5000, 1500, 0.3),
            ("Zone-B", "East Concourse B", "zone", 6000, 3600, 0.6),
            ("Zone-C", "South Concourse C", "zone", 8000, 7200, 0.9),
            ("Zone-D", "West Concourse D", "zone", 4000, 400, 0.1),
            ("Zone-VIP", "VIP Club Lounge", "zone", 1000, 200, 0.2)
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO zones (id, name, type, capacity, current_crowd, density) VALUES (?, ?, ?, ?, ?, ?)",
            zones_data
        )
        
        # Gates
        gates_data = [
            ("Gate-1", "Gate 1 (North)", "open", "low", "Zone-A"),
            ("Gate-2", "Gate 2 (East)", "open", "medium", "Zone-B"),
            ("Gate-3", "Gate 3 (South)", "open", "high", "Zone-C"),
            ("Gate-4", "Gate 4 (West)", "closed", "low", "Zone-D")
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO gates (id, name, status, congestion_level, zone_id) VALUES (?, ?, ?, ?, ?)",
            gates_data
        )
        conn.commit()

    # Seed nodes and edges if empty
    cursor.execute("SELECT COUNT(*) as count FROM nodes")
    if cursor.fetchone()["count"] == 0:
        nodes_data = [
            ("Gate 1", "Gate 1 (North)", "gate"),
            ("Gate 2", "Gate 2 (East)", "gate"),
            ("Gate 3", "Gate 3 (South)", "gate"),
            ("Gate 4", "Gate 4 (West)", "gate"),
            ("North Concourse Ramp A", "North Concourse Ramp A", "ramp"),
            ("North Main Stairs", "North Main Stairs", "stairs"),
            ("East elevator block", "East elevator block", "elevator"),
            ("East Escalator A", "East Escalator A", "escalator"),
            ("South elevator B", "South elevator B", "elevator"),
            ("South Concourse Stairs 4", "South Concourse Stairs 4", "stairs"),
            ("West Concourse level path", "West Concourse level path", "concourse"),
            ("West Escalator B", "West Escalator B", "escalator"),
            ("Section 102 Entry", "Section 102 Entry", "section"),
            ("Section 105 Entry", "Section 105 Entry", "section"),
            ("Section 204 Entry", "Section 204 Entry", "section"),
            ("Section 305 Entry", "Section 305 Entry", "section"),
            
            # Concourse Junctions
            ("Concourse NW", "Concourse NW Junction", "concourse"),
            ("Concourse NE", "Concourse NE Junction", "concourse"),
            ("Concourse SE", "Concourse SE Junction", "concourse"),
            ("Concourse SW", "Concourse SW Junction", "concourse")
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO nodes (id, name, type) VALUES (?, ?, ?)",
            nodes_data
        )
        
        edges_data = [
            ("Gate 1", "North Concourse Ramp A", 10.0, 1, "ramp"),
            ("Gate 1", "North Main Stairs", 5.0, 0, "stairs"),
            ("Gate 2", "East elevator block", 12.0, 1, "elevator"),
            ("Gate 2", "East Escalator A", 6.0, 0, "escalator"),
            ("Gate 3", "South elevator B", 15.0, 1, "elevator"),
            ("Gate 3", "South Concourse Stairs 4", 8.0, 0, "stairs"),
            ("Gate 4", "West Concourse level path", 8.0, 1, "concourse"),
            ("Gate 4", "West Escalator B", 7.0, 0, "escalator"),
            ("North Concourse Ramp A", "Section 102 Entry", 8.0, 1, "concourse"),
            ("North Main Stairs", "Section 102 Entry", 4.0, 1, "concourse"),
            ("East elevator block", "Section 204 Entry", 6.0, 1, "concourse"),
            ("East Escalator A", "Section 204 Entry", 3.0, 1, "concourse"),
            ("South elevator B", "Section 305 Entry", 5.0, 1, "concourse"),
            ("South Concourse Stairs 4", "Section 305 Entry", 4.0, 1, "concourse"),
            ("West Concourse level path", "Section 105 Entry", 6.0, 1, "concourse"),
            ("West Escalator B", "Section 105 Entry", 3.0, 1, "concourse"),
            
            # Concourse Ring Edges
            ("Concourse NW", "Concourse NE", 10.0, 1, "ring"),
            ("Concourse NE", "Concourse SE", 10.0, 1, "ring"),
            ("Concourse SE", "Concourse SW", 10.0, 1, "ring"),
            ("Concourse SW", "Concourse NW", 10.0, 1, "ring"),
            
            # Section Entries connections to Concourse Junctions
            ("Section 102 Entry", "Concourse NW", 5.0, 1, "ring"),
            ("Section 102 Entry", "Concourse NE", 5.0, 1, "ring"),
            ("Section 204 Entry", "Concourse NE", 5.0, 1, "ring"),
            ("Section 204 Entry", "Concourse SE", 5.0, 1, "ring"),
            ("Section 305 Entry", "Concourse SE", 5.0, 1, "ring"),
            ("Section 305 Entry", "Concourse SW", 5.0, 1, "ring"),
            ("Section 105 Entry", "Concourse SW", 5.0, 1, "ring"),
            ("Section 105 Entry", "Concourse NW", 5.0, 1, "ring")
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO edges (from_node, to_node, distance_or_weight, is_accessible, edge_type) VALUES (?, ?, ?, ?, ?)",
            edges_data
        )
        
        conn.commit()
    
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
