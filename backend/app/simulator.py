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
        # Per-zone momentum ("ingress/egress pressure"). Slowly-varying so crowd
        # levels move in sustained trends a forecast can extrapolate, rather than
        # pure white noise. Expressed as a fraction of capacity per tick.
        self._bias = {}

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
        
        from backend.app.telemetry import get_telemetry
        telemetry = get_telemetry()

        for zone in zones:
            zone_id = zone["id"]
            capacity = zone["capacity"]
            current_crowd = zone["current_crowd"]

            # Evolve the zone's momentum: mostly persists (0.85) with a small random
            # innovation, so trends build and decay smoothly instead of jittering.
            bias = self._bias.get(zone_id, 0.0)
            bias = bias * 0.85 + random.uniform(-0.006, 0.006)
            bias = max(-0.03, min(0.03, bias))

            # Reflect momentum away from hard bounds so zones don't stick at the
            # ceiling/floor (mimics a filling stand starting to level off / drain).
            density_now = current_crowd / capacity if capacity else 0.0
            if density_now > 0.95 and bias > 0:
                bias = -abs(bias)
            elif density_now < 0.10 and bias < 0:
                bias = abs(bias)
            self._bias[zone_id] = bias

            # Directional drift from momentum + small unbiased sensor noise.
            drift = int(capacity * bias)
            noise = random.randint(-int(capacity * 0.005), int(capacity * 0.005))
            new_crowd = current_crowd + drift + noise
            # Bound the crowd between 5% and 98% of capacity (leaving room for dynamics)
            new_crowd = max(int(capacity * 0.05), min(new_crowd, int(capacity * 0.98)))

            # Recalculate density
            new_density = round(new_crowd / capacity, 2)

            # Update zone in database
            cursor.execute(
                "UPDATE zones SET current_crowd = ?, density = ? WHERE id = ?",
                (new_crowd, new_density, zone_id)
            )

            # Record the sample so the Operations Copilot can trend/forecast it.
            telemetry.record(zone_id, new_density, new_crowd)
            
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
