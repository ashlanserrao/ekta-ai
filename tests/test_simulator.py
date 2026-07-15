import pytest
from backend.app.database import init_db, get_db_connection
from backend.app.simulator import StadiumSimulator

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    yield

def test_simulator_updates():
    # 1. Fetch initial values
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, current_crowd, density FROM zones")
    initial_zones = {row["id"]: (row["current_crowd"], row["density"]) for row in cursor.fetchall()}
    conn.close()
    
    # 2. Run simulation cycle once
    sim = StadiumSimulator()
    sim.update_crowd_dynamics()
    
    # 3. Fetch updated values
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, capacity, current_crowd, density FROM zones")
    updated_zones = {row["id"]: row for row in cursor.fetchall()}
    
    # 4. Verify something changed (since it relies on random.randint, it might occasionally match, but we bound check)
    changes_detected = False
    for zone_id, init_val in initial_zones.items():
        init_crowd, init_density = init_val
        updated_row = updated_zones[zone_id]
        
        # Crowd must be within logical capacity boundaries
        assert updated_row["current_crowd"] >= int(updated_row["capacity"] * 0.05)
        assert updated_row["current_crowd"] <= int(updated_row["capacity"] * 0.98)
        
        # Density must equal current_crowd / capacity (rounded to 2)
        expected_density = round(updated_row["current_crowd"] / updated_row["capacity"], 2)
        assert updated_row["density"] == expected_density
        
        if updated_row["current_crowd"] != init_crowd:
            changes_detected = True
            
    # Under standard random fluctuations, at least one of the 5 zones should change crowd levels
    assert changes_detected is True
    
    # 5. Verify gate congestion aligns with associated zone density
    cursor.execute("SELECT id, congestion_level, zone_id FROM gates")
    gates = cursor.fetchall()
    
    for g in gates:
        gate_id = g["id"]
        congestion = g["congestion_level"]
        zone_id = g["zone_id"]
        
        if zone_id in updated_zones:
            zone_density = updated_zones[zone_id]["density"]
            if zone_density > 0.75:
                assert congestion == "high"
            elif zone_density >= 0.40:
                assert congestion == "medium"
            else:
                assert congestion == "low"
                
    conn.close()
