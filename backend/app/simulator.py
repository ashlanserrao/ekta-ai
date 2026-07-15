import time
import random
import threading
import logging
from backend.app.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulator")

class StadiumSimulator(threading.Thread):
    def __init__(self, interval_seconds: float = 3.0):
        super().__init__()
        self.interval_seconds = interval_seconds
        self.running = False
        self.daemon = True

    def run(self):
        self.running = True
        logger.info("Stadium Digital Twin Simulator started.")
        while self.running:
            try:
                self.update_crowd_dynamics()
            except Exception as e:
                logger.error(f"Error in simulator loop: {e}")
            time.sleep(self.interval_seconds)

    def stop(self):
        self.running = False
        logger.info("Stadium Digital Twin Simulator stopped.")

    def update_crowd_dynamics(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fetch zones
        cursor.execute("SELECT id, capacity, current_crowd FROM zones")
        zones = cursor.fetchall()
        
        for zone in zones:
            zone_id = zone["id"]
            capacity = zone["capacity"]
            current_crowd = zone["current_crowd"]
            
            # Simulate crowd changes: fluctuate by +/- 2% of capacity
            max_change = int(capacity * 0.02)
            change = random.randint(-max_change, max_change)
            
            new_crowd = current_crowd + change
            # Bound the crowd between 10% and 95% of capacity (leaving room for dynamics)
            new_crowd = max(int(capacity * 0.05), min(new_crowd, int(capacity * 0.98)))
            
            # Recalculate density
            new_density = round(new_crowd / capacity, 2)
            
            # Update zone in database
            cursor.execute(
                "UPDATE zones SET current_crowd = ?, density = ? WHERE id = ?",
                (new_crowd, new_density, zone_id)
            )
            
            # 2. Update gate congestion based on the associated zone's density
            # Low congestion: < 0.40 density
            # Medium congestion: 0.40 to 0.75 density
            # High congestion: > 0.75 density
            congestion = "low"
            if new_density > 0.75:
                congestion = "high"
            elif new_density >= 0.40:
                congestion = "medium"
                
            cursor.execute(
                "UPDATE gates SET congestion_level = ? WHERE zone_id = ?",
                (congestion, zone_id)
            )
            
        conn.commit()
        conn.close()

# Singleton instance
simulator_instance = StadiumSimulator()
