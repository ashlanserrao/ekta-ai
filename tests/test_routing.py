import pytest
from backend.app.database import init_db, get_db_connection
from backend.app.routing import find_path

@pytest.fixture(scope="module", autouse=True)
def setup_db_for_routing():
    init_db()
    
    # Insert an isolated node that has no edges connected to it
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO nodes (id, name, type) VALUES ('Isolated Node', 'Isolated Node', 'section')")
    conn.commit()
    conn.close()
    yield

def test_reachable_path_standard():
    # Gate 1 to Section 102 Standard: should prefer stairs (5.0 + 4.0 = 9.0) over ramp (10.0 + 8.0 = 18.0)
    path = find_path("Gate 1", "Section 102 Entry", accessible_only=False)
    assert path == ["Gate 1", "North Main Stairs", "Section 102 Entry"]

def test_reachable_path_accessible():
    # Gate 1 to Section 102 Accessible: must use ramp (10.0 + 8.0 = 18.0) as stairs is not accessible
    path = find_path("Gate 1", "Section 102 Entry", accessible_only=True)
    assert path == ["Gate 1", "North Concourse Ramp A", "Section 102 Entry"]

def test_no_path_isolated_node():
    # Isolated Node is not connected to any edge, so find_path should return an empty list
    path = find_path("Gate 1", "Isolated Node", accessible_only=False)
    assert path == []

def test_same_start_end_node():
    # Same start/end node should immediately return the node itself
    path = find_path("Gate 1", "Gate 1", accessible_only=False)
    assert path == ["Gate 1"]
