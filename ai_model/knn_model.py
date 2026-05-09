import argparse
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder


class TrafficPredictor:

    REQUIRED_COLUMNS = {'hour', 'road_type', 'is_weekend', 'traffic_level'}
    FEATURE_COLUMNS = [
        'hour',
        'is_weekend',
        'road_type_encoded',
        'length',
        'speed_limit',
        'is_rush_hour',
        'is_school_hour',
    ]

    def __init__(self, n_neighbors=5):
        self.n_neighbors = n_neighbors
        self.model = KNeighborsClassifier(n_neighbors=n_neighbors)
        self.road_type_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'knn_traffic_model.pkl',
        )

    def train(self, df):
        missing = self.REQUIRED_COLUMNS.difference(df.columns)
        if missing:
            raise ValueError(f"Training data is missing columns: {sorted(missing)}")

        print("Training KNN traffic prediction model...")

        X = self.prepare_features(df, fit_encoder=True)
        X_scaled = self.scaler.fit_transform(X)
        y = df['traffic_level'].values

        self.model.fit(X_scaled, y)
        self.is_trained = True

        print(f"Model trained on {len(df)} samples")
        print(f"Features: {', '.join(self.FEATURE_COLUMNS)}")
        print(f"Traffic levels: {sorted(np.unique(y))}")

    def prepare_features(self, df, fit_encoder=False):
        def column_or_default(column, default):
            if column in df.columns:
                return df[column]
            return pd.Series(default, index=df.index)

        X = pd.DataFrame(index=df.index)
        X['hour'] = df['hour'].astype(int)
        X['is_weekend'] = df['is_weekend'].astype(int)

        if fit_encoder:
            X['road_type_encoded'] = self.road_type_encoder.fit_transform(df['road_type'])
        else:
            X['road_type_encoded'] = [
                self.encode_road_type(value) for value in df['road_type']
            ]

        X['length'] = column_or_default('length', 0).fillna(0).astype(float)
        X['speed_limit'] = column_or_default('speed_limit', 30).fillna(30).astype(float)
        X['is_rush_hour'] = column_or_default('is_rush_hour', 0).fillna(0).astype(int)
        X['is_school_hour'] = column_or_default('is_school_hour', 0).fillna(0).astype(int)
        return X[self.FEATURE_COLUMNS]

    def encode_road_type(self, road_type):
        try:
            return self.road_type_encoder.transform([road_type])[0]
        except ValueError:
            return self.road_type_encoder.transform(['residential'])[0]

    def predict(
        self,
        hour,
        road_type,
        is_weekend=False,
        length=0,
        speed_limit=30,
        is_rush_hour=0,
        is_school_hour=0,
    ):
        
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        record = pd.DataFrame([{
            'hour': hour,
            'is_weekend': int(is_weekend),
            'road_type': road_type,
            'length': length,
            'speed_limit': speed_limit,
            'is_rush_hour': int(is_rush_hour),
            'is_school_hour': int(is_school_hour),
        }])
        features = self.prepare_features(record)
        return int(self.model.predict(self.scaler.transform(features))[0])

    def predict_batch(self, records):
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        df = pd.DataFrame(records)
        for column, default in {
            'hour': 0,
            'is_weekend': 0,
            'road_type': 'residential',
            'length': 0,
            'speed_limit': 30,
            'is_rush_hour': 0,
            'is_school_hour': 0,
        }.items():
            if column not in df.columns:
                df[column] = default

        features = self.prepare_features(df)
        return self.model.predict(self.scaler.transform(features))

    def save_model(self):
        if not self.is_trained:
            raise RuntimeError("Model not trained. Cannot save.")

        joblib.dump({
            'model': self.model,
            'encoder': self.road_type_encoder,
            'scaler': self.scaler,
        }, self.model_path)
        print(f"Model saved to: {self.model_path}")

    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at: {self.model_path}")

        data = joblib.load(self.model_path)
        self.model = data['model']
        self.road_type_encoder = data['encoder']
        self.scaler = data.get('scaler', StandardScaler())
        self.is_trained = True
        print(f"Model loaded from: {self.model_path}")


def traffic_level_to_multiplier(traffic_level):
    multipliers = {
        1: 1.0,
        2: 1.5,
        3: 2.0,
    }
    return multipliers.get(int(traffic_level), 1.0)


def traffic_level_to_string(traffic_level):
    levels = {1: 'Low', 2: 'Medium', 3: 'High'}
    return levels.get(int(traffic_level), 'Unknown')


def balance_training_data(df, max_per_group=50000, seed=42):
    samples = []
    for _, group in df.groupby(['road_type', 'traffic_level']):
        samples.append(group.sample(
            n=min(len(group), max_per_group),
            random_state=seed,
        ))

    return pd.concat(samples, ignore_index=True).sample(
        frac=1,
        random_state=seed,
    ).reset_index(drop=True)


def generate_training_data(use_edges=True, days=60, start_date='2026-01-01', seed=42):
    from traffic_data_generator import TrafficDataGenerator

    generator = TrafficDataGenerator(
        start_date=start_date,
        num_days=days,
        seed=seed,
    )

    if use_edges:
        df = generator.generate_for_osm_graph()
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'traffic_historical_edges.csv',
        )
    else:
        df = generator.generate(
            road_types=['motorway', 'trunk', 'primary', 'secondary', 'residential']
        )
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'traffic_historical_data.csv',
        )

    generator.save_to_csv(output_path, df)
    return df


def load_existing_training_data(use_edges=True):
    filename = 'traffic_historical_edges.csv' if use_edges else 'traffic_historical_data.csv'
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Training data not found: {path}")
    print(f"Loading existing training data: {path}")
    return pd.read_csv(path)


def main():
    parser = argparse.ArgumentParser(description='Train the KNN traffic model.')
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--start-date', default='2026-01-01')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--neighbors', type=int, default=5)
    parser.add_argument(
        '--road-type-only',
        action='store_true',
        help='Train on compact road-type data instead of OSM edge data.',
    )
    parser.add_argument(
        '--balance-training',
        action='store_true',
        help='Train on a balanced road_type/traffic_level sample after saving the full dataset.',
    )
    parser.add_argument(
        '--use-existing-data',
        action='store_true',
        help='Load the existing CSV instead of regenerating traffic data.',
    )
    args = parser.parse_args()

    print("=" * 60)
    print("TRAFFIC PREDICTION MODEL TRAINING")
    print("=" * 60)

    if args.use_existing_data:
        print("\n[1/3] Loading historical traffic data...")
        df = load_existing_training_data(use_edges=not args.road_type_only)
    else:
        print("\n[1/3] Generating historical traffic data...")
        df = generate_training_data(
            use_edges=not args.road_type_only,
            days=args.days,
            start_date=args.start_date,
            seed=args.seed,
        )

    if args.balance_training:
        print("\nBalancing training sample by road_type and traffic_level...")
        df = balance_training_data(df, seed=args.seed)
        print(f"Balanced training rows: {len(df)}")

    print("\n[2/3] Training KNN model...")
    predictor = TrafficPredictor(n_neighbors=args.neighbors)
    predictor.train(df)

    print("\n[3/3] Saving model...")
    predictor.save_model()

    print("\n" + "=" * 60)
    print("TEST PREDICTIONS")
    print("=" * 60)

    test_cases = [
        {
            'hour': 8,
            'road_type': 'tertiary',
            'is_weekend': False,
            'length': 180,
            'speed_limit': 60,
            'is_rush_hour': 1,
            'is_school_hour': 1,
            'label': 'Weekday morning rush (tertiary)',
        },
        {
            'hour': 14,
            'road_type': 'secondary',
            'is_weekend': False,
            'length': 220,
            'speed_limit': 60,
            'is_rush_hour': 0,
            'is_school_hour': 1,
            'label': 'Weekday school closing (secondary)',
        },
        {
            'hour': 17,
            'road_type': 'residential',
            'is_weekend': False,
            'length': 60,
            'speed_limit': 30,
            'is_rush_hour': 1,
            'is_school_hour': 0,
            'label': 'Weekday evening (residential)',
        },
        {
            'hour': 2,
            'road_type': 'tertiary',
            'is_weekend': False,
            'length': 180,
            'speed_limit': 60,
            'is_rush_hour': 0,
            'is_school_hour': 0,
            'label': 'Night time (tertiary)',
        },
        {
            'hour': 10,
            'road_type': 'residential',
            'is_weekend': True,
            'length': 60,
            'speed_limit': 30,
            'is_rush_hour': 0,
            'is_school_hour': 0,
            'label': 'Weekend morning (residential)',
        },
    ]

    for test in test_cases:
        traffic = predictor.predict(
            test['hour'],
            test['road_type'],
            test['is_weekend'],
            length=test['length'],
            speed_limit=test['speed_limit'],
            is_rush_hour=test['is_rush_hour'],
            is_school_hour=test['is_school_hour'],
        )
        multiplier = traffic_level_to_multiplier(traffic)
        print(f"{test['label']}")
        print(f"  -> Traffic: {traffic_level_to_string(traffic)} | Multiplier: {multiplier}x\n")

    print("=" * 60)
    print("Model training complete")
    print("=" * 60)


if __name__ == '__main__':
    main()
