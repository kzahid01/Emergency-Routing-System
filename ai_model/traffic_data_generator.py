"""
Generate semi-realistic historical traffic data for G-8, Islamabad.

The default output is tied to real OpenStreetMap graph edges, so the dataset
uses real roads while still avoiding unavailable/paid live traffic feeds.
"""

import argparse
import ast
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


class TrafficDataGenerator:
    """Generate semi-realistic historical traffic data."""

    ROAD_HIERARCHY = {
        'motorway': 5,
        'trunk': 4,
        'primary': 3,
        'secondary': 2,
        'tertiary': 2,
        'residential': 1,
        'living_street': 0,
    }

    TRAFFIC_LEVELS = {
        'low': 1,
        'medium': 2,
        'high': 3,
    }

    DEFAULT_SPEED_LIMITS = {
        'motorway': 100,
        'trunk': 80,
        'primary': 60,
        'secondary': 50,
        'tertiary': 40,
        'residential': 30,
        'living_street': 20,
    }

    def __init__(self, start_date='2026-01-01', num_days=60, seed=42):
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.num_days = num_days
        self.random = np.random.default_rng(seed)

    def is_rush_hour(self, hour, is_weekend):
        return (not is_weekend) and hour in [7, 8, 9, 16, 17, 18]

    def is_school_hour(self, hour, is_weekend):
        return (not is_weekend) and hour in [7, 8, 13, 14]

    def get_base_traffic(self, hour, is_weekend, road_type):
        """
        Get base traffic level from weekday/weekend and hourly patterns.

        Weekdays have morning and evening rush hours. Weekends are calmer with
        mild shopping/social activity peaks.
        """
        hour = int(hour)

        if is_weekend:
            if hour in [8, 9, 10, 15, 16, 17, 18]:
                return self.TRAFFIC_LEVELS['medium']
            return self.TRAFFIC_LEVELS['low']

        if hour in [7, 8, 9, 16, 17, 18]:
            return self.TRAFFIC_LEVELS['high']
        if hour in [11, 12, 13, 14, 15]:
            return self.TRAFFIC_LEVELS['medium']
        if hour in [0, 1, 2, 3, 4, 5]:
            return self.TRAFFIC_LEVELS['low']
        return self.TRAFFIC_LEVELS['medium']

    def apply_road_type_modifier(self, base_traffic, road_type):
        """Modify traffic by road hierarchy."""
        hierarchy = self.ROAD_HIERARCHY.get(road_type, 1)

        if hierarchy >= 4:
            return base_traffic
        if hierarchy == 3:
            return self.TRAFFIC_LEVELS['high'] if base_traffic == 3 else base_traffic
        if base_traffic == self.TRAFFIC_LEVELS['medium']:
            return self.TRAFFIC_LEVELS['medium']
        if base_traffic == self.TRAFFIC_LEVELS['high']:
            return self.TRAFFIC_LEVELS['high']
        return self.TRAFFIC_LEVELS['low']

    def add_random_noise(self, traffic_level, variation=0.15):
        """Add realistic variation so repeated hours are not identical."""
        if self.random.random() >= variation:
            return traffic_level

        if traffic_level == self.TRAFFIC_LEVELS['high']:
            return self.TRAFFIC_LEVELS['medium']
        if traffic_level == self.TRAFFIC_LEVELS['medium']:
            return int(self.random.choice([
                self.TRAFFIC_LEVELS['low'],
                self.TRAFFIC_LEVELS['high'],
            ]))
        return self.TRAFFIC_LEVELS['medium'] if self.random.random() < 0.5 else traffic_level

    def parse_numeric_osm_value(self, value, default=None):
        """Parse OSM values such as '30', '30 mph', ['30', '40'], or missing."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default

        if isinstance(value, str):
            value = value.strip()
            if value.startswith('['):
                try:
                    value = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    pass

        if isinstance(value, (list, tuple, set)):
            parsed = [self.parse_numeric_osm_value(item) for item in value]
            parsed = [item for item in parsed if item is not None]
            return float(np.median(parsed)) if parsed else default

        text = str(value).lower()
        digits = ''.join(char if char.isdigit() or char == '.' else ' ' for char in text)
        parts = [part for part in digits.split() if part]
        if not parts:
            return default

        parsed = float(parts[0])
        if 'mph' in text:
            parsed *= 1.60934
        return parsed

    def infer_speed_limit(self, road_type, raw_maxspeed=None):
        parsed = self.parse_numeric_osm_value(raw_maxspeed)
        if parsed is not None:
            return parsed
        return self.DEFAULT_SPEED_LIMITS.get(road_type, 30)

    def traffic_probabilities(self, hour, is_weekend, road_type, length, speed_limit):
        """
        Return probabilities for low/medium/high traffic.

        This keeps the data semi-synthetic but less biased toward a single
        time-only rule. It uses real OSM-derived edge features when available.
        """
        hierarchy = self.ROAD_HIERARCHY.get(road_type, 1)
        long_edge = length >= 120
        short_local = length <= 45 and hierarchy <= 1
        slow_road = speed_limit <= 30

        if hour in [0, 1, 2, 3, 4, 5]:
            probs = np.array([0.90, 0.10, 0.00])
        elif self.is_rush_hour(hour, is_weekend):
            probs = np.array([0.08, 0.32, 0.60])
        elif is_weekend and hour in [10, 11, 12, 17, 18, 19, 20]:
            probs = np.array([0.25, 0.55, 0.20])
        elif hour in [11, 12, 13, 14, 15, 19, 20, 21, 22]:
            probs = np.array([0.30, 0.58, 0.12])
        else:
            probs = np.array([0.45, 0.48, 0.07])

        if hierarchy >= 2:
            probs += np.array([-0.05, 0.00, 0.05])
        if hierarchy <= 1 and self.is_school_hour(hour, is_weekend):
            probs += np.array([-0.08, 0.00, 0.08])
        if long_edge:
            probs += np.array([-0.04, 0.01, 0.03])
        if short_local:
            probs += np.array([0.05, 0.00, -0.05])
        if slow_road and self.is_rush_hour(hour, is_weekend):
            probs += np.array([-0.04, 0.00, 0.04])

        incident_probability = 0.015 if not is_weekend else 0.01
        if self.random.random() < incident_probability:
            probs += np.array([-0.20, 0.05, 0.15])

        probs = np.clip(probs, 0.01, None)
        return probs / probs.sum()

    def sample_traffic_level(self, hour, is_weekend, road_type, length=0, speed_limit=None):
        if speed_limit is None:
            speed_limit = self.infer_speed_limit(road_type)
        probs = self.traffic_probabilities(hour, is_weekend, road_type, length, speed_limit)
        return int(self.random.choice([1, 2, 3], p=probs))

    def normalize_road_type(self, road_type):
        """
        Convert OSM highway values into a model-friendly road type.

        OSMnx can store highway as a string, list-like string, or list. When an
        edge has multiple values, keep the highest hierarchy class.
        """
        if road_type is None:
            return 'residential'

        if isinstance(road_type, str):
            road_type = road_type.strip()
            if road_type.startswith('['):
                try:
                    road_type = ast.literal_eval(road_type)
                except (SyntaxError, ValueError):
                    pass

        if isinstance(road_type, (list, tuple, set)):
            candidates = [self.normalize_road_type(item) for item in road_type]
            return max(candidates, key=lambda item: self.ROAD_HIERARCHY.get(item, 1))

        road_type = str(road_type).strip().lower()
        return road_type if road_type in self.ROAD_HIERARCHY else 'residential'

    def generate(self, road_types=None):
        """
        Generate a compact road-type-level dataset.

        Returns columns: date, hour, road_type, traffic_level, is_weekend.
        """
        if road_types is None:
            road_types = ['motorway', 'primary', 'secondary', 'residential']

        data = []
        for day_offset in range(self.num_days):
            current_date = self.start_date + timedelta(days=day_offset)
            is_weekend = current_date.weekday() >= 5

            for hour in range(24):
                for road_type in road_types:
                    road_type = self.normalize_road_type(road_type)
                    speed_limit = self.infer_speed_limit(road_type)
                    traffic = self.sample_traffic_level(
                        hour,
                        is_weekend,
                        road_type,
                        speed_limit=speed_limit,
                    )

                    data.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'weekday': current_date.weekday(),
                        'hour': hour,
                        'road_type': road_type,
                        'speed_limit': speed_limit,
                        'is_rush_hour': int(self.is_rush_hour(hour, is_weekend)),
                        'is_school_hour': int(self.is_school_hour(hour, is_weekend)),
                        'traffic_level': traffic,
                        'is_weekend': int(is_weekend),
                    })

        return pd.DataFrame(data)

    def generate_for_edges(self, edges):
        """
        Generate historical traffic records for real OSM graph edges.

        Returns columns: edge_id, u, v, key, length, date, weekday, hour,
        road_type, traffic_level, is_weekend.
        """
        data = []

        for day_offset in range(self.num_days):
            current_date = self.start_date + timedelta(days=day_offset)
            is_weekend = current_date.weekday() >= 5

            for hour in range(24):
                for edge in edges:
                    road_type = self.normalize_road_type(edge.get('highway'))
                    length = float(edge.get('length', 0))
                    speed_limit = self.infer_speed_limit(road_type, edge.get('maxspeed'))
                    lanes = self.parse_numeric_osm_value(edge.get('lanes'), default=1)
                    traffic = self.sample_traffic_level(
                        hour,
                        is_weekend,
                        road_type,
                        length=length,
                        speed_limit=speed_limit,
                    )

                    u = int(edge.get('u'))
                    v = int(edge.get('v'))
                    key = int(edge.get('key', 0))

                    data.append({
                        'edge_id': f'{u}-{v}-{key}',
                        'u': u,
                        'v': v,
                        'key': key,
                        'length': length,
                        'speed_limit': speed_limit,
                        'lanes': lanes,
                        'date': current_date.strftime('%Y-%m-%d'),
                        'weekday': current_date.weekday(),
                        'hour': hour,
                        'road_type': road_type,
                        'is_rush_hour': int(self.is_rush_hour(hour, is_weekend)),
                        'is_school_hour': int(self.is_school_hour(hour, is_weekend)),
                        'traffic_level': traffic,
                        'is_weekend': int(is_weekend),
                    })

        return pd.DataFrame(data)

    def generate_for_osm_graph(self):
        """Generate edge-based traffic data using the cached OSM graph."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        from map_load.map import MAP_DATA

        return self.generate_for_edges(MAP_DATA['edges'])

    def save_to_csv(self, output_path, df):
        """Save generated dataset to CSV."""
        df.to_csv(output_path, index=False)
        print(f"Generated {len(df)} rows")
        print(f"Saved to: {output_path}")
        print("\nDataset info:")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Road types: {', '.join(sorted(df['road_type'].unique()))}")
        print(f"  Traffic distribution:\n{df['traffic_level'].value_counts().sort_index()}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate historical traffic data for the emergency routing system.'
    )
    parser.add_argument('--start-date', default='2026-01-01')
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument(
        '--road-type-only',
        action='store_true',
        help='Generate compact road-type rows instead of OSM edge rows.',
    )
    args = parser.parse_args()

    output_dir = os.path.dirname(os.path.abspath(__file__))
    generator = TrafficDataGenerator(
        start_date=args.start_date,
        num_days=args.days,
        seed=args.seed,
    )

    if args.road_type_only:
        print("Generating road-type historical traffic dataset...")
        output_path = os.path.join(output_dir, 'traffic_historical_data.csv')
        df = generator.generate(
            road_types=['motorway', 'trunk', 'primary', 'secondary', 'residential']
        )
    else:
        print("Generating OSM edge-based historical traffic dataset...")
        output_path = os.path.join(output_dir, 'traffic_historical_edges.csv')
        df = generator.generate_for_osm_graph()

    generator.save_to_csv(output_path, df)
    return df


if __name__ == '__main__':
    main()
