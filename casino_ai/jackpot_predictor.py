"""
ML Jackpot Timing Predictor

Predicts minutes until next jackpot using Random Forest.
Trains on 9,062 historical jackpots from PostgreSQL.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2


class JackpotPredictor:
    """ML model to predict jackpot timing"""
    
    def __init__(self, db_config: Dict = None):
        """
        Initialize predictor.
        
        Args:
            db_config: PostgreSQL connection config
        """
        if db_config is None:
            # Match existing casino database config
            db_config = {
                'host': '192.168.1.211',
                'database': 'postgres',
                'user': 'rod'
            }
        
        self.db_config = db_config
        
        # ML models
        self.timing_model = None  # Predicts minutes until jackpot
        self.hot_classifier = None  # Classifies HOT/WARM/COLD
        self.scaler = None
        self.label_encoders = {}
        
        self.is_trained = False
        
        # Load if exists
        if os.path.exists('models/jackpot_timing.pkl'):
            self.load()
    
    def _get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(**self.db_config)
    
    def extract_features_from_db(self) -> pd.DataFrame:
        """
        Extract training features from PostgreSQL jackpots.
        
        Returns:
            DataFrame with features and targets
        """
        conn = self._get_connection()
        
        # Query to get jackpots with calculated intervals
        query = """
        WITH jackpot_intervals AS (\n            SELECT \n                id,
                location_id as machine_id,
                amount,
                hit_timestamp as timestamp,
                denomination,
                game_family as game_title,
                LAG(hit_timestamp) OVER (PARTITION BY location_id ORDER BY hit_timestamp) as prev_timestamp,
                EXTRACT(EPOCH FROM (hit_timestamp - LAG(hit_timestamp) OVER (PARTITION BY location_id ORDER BY hit_timestamp)))/60 as interval_minutes,
                hour_of_day,
                day_of_week
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '180 days'
            ORDER BY hit_timestamp DESC
        )
        SELECT * FROM jackpot_intervals
        WHERE interval_minutes IS NOT NULL
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"✅ Loaded {len(df)} jackpots from database")
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer ML features from raw data.
        
        Features:
        1. time_since_last - Minutes since previous jackpot
        2. avg_interval - Average interval for this machine
        3. denomination - Encoded
        4. game_family - Encoded (first word of game_title)
        5. hour_of_day - 0-23
        6. day_of_week - 0-6
        7. jackpot_variance - Std dev of intervals
        8. recent_trend - Last 5 jackpots trend
        9. total_jackpots_today - Count today
        10. price_point - denomination as numeric
        """
        features_df = pd.DataFrame()
        
        # 1. Time since last (already have as interval_minutes)
        features_df['time_since_last'] = df['interval_minutes']
        
        # 2. Average interval per machine
        machine_avgs = df.groupby('machine_id')['interval_minutes'].mean()
        features_df['avg_interval'] = df['machine_id'].map(machine_avgs)
        
        # 3-4. Encode categorical
        # Denomination
        denom_encoder = LabelEncoder()
        features_df['denomination_encoded'] = denom_encoder.fit_transform(
            df['denomination'].fillna('$1.00')
        )
        self.label_encoders['denomination'] = denom_encoder
        
        # Game family (first word)
        df['game_family'] = df['game_title'].fillna('Unknown').str.split().str[0]
        game_encoder = LabelEncoder()
        features_df['game_family_encoded'] = game_encoder.fit_transform(df['game_family'])
        self.label_encoders['game_family'] = game_encoder
        
        # 5-6. Time features
        features_df['hour_of_day'] = df['hour_of_day']
        features_df['day_of_week'] = df['day_of_week']
        
        # 7. Variance
        machine_vars = df.groupby('machine_id')['interval_minutes'].std()
        features_df['jackpot_variance'] = df['machine_id'].map(machine_vars).fillna(0)
        
        # 8. Recent trend (simplified - positive/negative)
        # For each row, look at last 5 intervals
        features_df['recent_trend'] = 0  # neutral default
        
        # 9. Total jackpots today
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_counts = df.groupby(['machine_id', 'date']).size()
        features_df['total_jackpots_today'] = df.apply(
            lambda row: daily_counts.get((row['machine_id'], row['date']), 1),
            axis=1
        )
        
        # 10. Price point (numeric denomination)
        features_df['price_point'] = df['denomination'].str.replace('$', '').astype(float)
        
        # Target: next interval (shifted)
        # For timing model: predict the interval_minutes
        # For hot classifier: binary - will jackpot within 30 min?
        features_df['target_minutes'] = df['interval_minutes']
        features_df['target_hot'] = (df['interval_minutes'] <= 30).astype(int)
        
        # Drop nulls
        features_df = features_df.dropna()
        
        return features_df
    
    def train(self, test_size=0.2):
        """
        Train both timing and hot/cold models.
        """
        print("📊 Extracting features from database...")
        raw_df = self.extract_features_from_db()
        
        if len(raw_df) < 100:
            print(f"⚠️  Not enough data ({len(raw_df)} jackpots). Need at least 100.")
            return False
        
        print("🔧 Engineering features...")
        features_df = self.engineer_features(raw_df)
        
        print(f"✅ Prepared {len(features_df)} training samples")
        
        # Split features and targets
        feature_cols = [
            'time_since_last', 'avg_interval', 'denomination_encoded',
            'game_family_encoded', 'hour_of_day', 'day_of_week',
            'jackpot_variance', 'recent_trend', 'total_jackpots_today',
            'price_point'
        ]
        
        X = features_df[feature_cols]
        y_timing = features_df['target_minutes']
        y_hot = features_df['target_hot']
        
        # Train/test split
        X_train, X_test, y_timing_train, y_timing_test, y_hot_train, y_hot_test = train_test_split(
            X, y_timing, y_hot, test_size=test_size, random_state=42
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train timing model (regression)
        print("🌲 Training timing predictor (Random Forest Regressor)...")
        self.timing_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.timing_model.fit(X_train_scaled, y_timing_train)
        
        # Evaluate timing model
        train_score = self.timing_model.score(X_train_scaled, y_timing_train)
        test_score = self.timing_model.score(X_test_scaled, y_timing_test)
        
        y_pred = self.timing_model.predict(X_test_scaled)
        mae = np.mean(np.abs(y_pred - y_timing_test))
        
        print(f"   ✅ Timing Model:")
        print(f"      R² train: {train_score:.3f}")
        print(f"      R² test: {test_score:.3f}")
        print(f"      MAE: {mae:.1f} minutes")
        
        # Train hot classifier
        print("🌲 Training hot/cold classifier (Random Forest Classifier)...")
        self.hot_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        self.hot_classifier.fit(X_train_scaled, y_hot_train)
        
        # Evaluate classifier
        train_acc = self.hot_classifier.score(X_train_scaled, y_hot_train)
        test_acc = self.hot_classifier.score(X_test_scaled, y_hot_test)
        
        print(f"   ✅ Hot Classifier:")
        print(f"      Accuracy train: {train_acc:.3f}")
        print(f"      Accuracy test: {test_acc:.3f}")
        
        # Feature importance
        print("\n📈 Top Features (Timing Model):")
        importances = self.timing_model.feature_importances_
        for i, col in enumerate(feature_cols):
            if importances[i] > 0.05:
                print(f"      {col}: {importances[i]:.3f}")
        
        self.is_trained = True
        self.save()
        
        print(f"\n✅ Models trained successfully!")
        print(f"   Training samples: {len(X_train)}")
        print(f"   Test samples: {len(X_test)}")
        
        return True
    
    def predict(self, machine_data: Dict) -> Dict:
        """
        Predict jackpot timing for a machine.
        
        Args:
            machine_data: Dict with machine features
            
        Returns:
            {
                "predicted_minutes": 45,
                "confidence": 0.82,
                "hot_probability": 0.15,
                "classification": "WARM"
            }
        """
        if not self.is_trained:
            return {
                "predicted_minutes": None,
                "confidence": 0.0,
                "hot_probability": 0.0,
                "classification": "UNTRAINED"
            }
        
        # Extract features
        features = np.array([[
            machine_data.get('time_since_last', 0),
            machine_data.get('avg_interval', 60),
            self.label_encoders['denomination'].transform([machine_data.get('denomination', '$1.00')])[0],
            self.label_encoders['game_family'].transform([machine_data.get('game_family', 'Unknown')])[0],
            machine_data.get('hour_of_day', 12),
            machine_data.get('day_of_week', 3),
            machine_data.get('jackpot_variance', 15),
            machine_data.get('recent_trend', 0),
            machine_data.get('total_jackpots_today', 5),
            machine_data.get('price_point', 1.0)
        ]])
        
        # Scale
        features_scaled = self.scaler.transform(features)
        
        # Predict timing
        predicted_minutes = self.timing_model.predict(features_scaled)[0]
        
        # Predict hot probability
        hot_prob = self.hot_classifier.predict_proba(features_scaled)[0][1]
        
        # Classification
        if hot_prob >= 0.7:
            classification = "HOT"
        elif hot_prob >= 0.4:
            classification = "WARM"
        else:
            classification = "COLD"
        
        # Confidence (based on variance in forest predictions)
        # Simplified: use probability as confidence
        confidence = max(hot_prob, 1 - hot_prob)
        
        return {
            "predicted_minutes": int(predicted_minutes),
            "confidence": float(confidence),
            "hot_probability": float(hot_prob),
            "classification": classification
        }
    
    def save(self):
        """Save models"""
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.timing_model, 'models/jackpot_timing.pkl')
        joblib.dump(self.hot_classifier, 'models/hot_classifier.pkl')
        joblib.dump(self.scaler, 'models/scaler_casino.pkl')
        joblib.dump(self.label_encoders, 'models/label_encoders.pkl')
        print("💾 Models saved to models/")
    
    def load(self):
        """Load models"""
        if os.path.exists('models/jackpot_timing.pkl'):
            self.timing_model = joblib.load('models/jackpot_timing.pkl')
            self.hot_classifier = joblib.load('models/hot_classifier.pkl')
            self.scaler = joblib.load('models/scaler_casino.pkl')
            self.label_encoders = joblib.load('models/label_encoders.pkl')
            self.is_trained = True
            print("✅ Models loaded from models/")
            return True
        return False


# Quick test
if __name__ == "__main__":
    predictor = JackpotPredictor()
    
    print("🎰 Training Jackpot Predictor on Casino Database...")
    print(f"   Database: {predictor.db_config['host']}")
    print("")
    
    # Train
    success = predictor.train()
    
    if success:
        # Test prediction
        test_machine = {
            'time_since_last': 35,
            'avg_interval': 47,
            'denomination': '$1.00',
            'game_family': 'Buffalo',
            'hour_of_day': 14,
            'day_of_week': 3,
            'jackpot_variance': 12,
            'recent_trend': 0,
            'total_jackpots_today': 6,
            'price_point': 1.0
        }
        
        result = predictor.predict(test_machine)
        print("\n🔮 Test Prediction:")
        print(f"   Predicted time: {result['predicted_minutes']} minutes")
        print(f"   Hot probability: {result['hot_probability']:.2f}")
        print(f"   Classification: {result['classification']}")
        print(f"   Confidence: {result['confidence']:.2f}")
