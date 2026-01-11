#!/usr/bin/env python3
"""
ML-Enhanced JVI Analytics with PyTorch Neural Network
Provides machine learning predictions and clustering for JVI rankings
"""

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import PyTorch
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - falling back to Linear Regression")

# Database configuration
from config import DB_CONFIG

# Model paths
MODEL_DIR = '/home/rod/home_ai_stack/jvi_models'
MODEL_PATH = os.path.join(MODEL_DIR, 'jvi_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'jvi_scaler.pkl')
METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.json')

# Features
FEATURES = [
    'hits', 'total_payout', 'avg_jackpot', 'max_jackpot',
    'hit_rate_per_day', 'avg_hours_between_hits', 'inv_gap',
    'volatility', 'n_total', 'n_avg', 'n_rate'
]

# Global model variables
JVI_MODEL = None
JVI_SCALER = None
MODEL_METADATA = None
PREDICTION_STD_ERROR = None  # For confidence intervals

# ------------------------------
# Neural Network Definition
# ------------------------------
if TORCH_AVAILABLE:
    class JVINet(nn.Module):
        def __init__(self, input_size: int):
            super(JVINet, self).__init__()
            self.network = nn.Sequential(
                nn.Linear(input_size, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(32, 1)
            )

        def forward(self, x):
            return self.network(x)

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"DB connection error: {e}")
        return None

def get_training_data():
    """Extract training data from database"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get comprehensive machine stats for training
        cur.execute("""
            WITH stats AS (
                SELECT
                    machine_name,
                    normalized_denomination as denomination,
                    COUNT(*) AS hits,
                    SUM(amount) AS total_payout,
                    AVG(amount) AS avg_jackpot,
                    MAX(amount) AS max_jackpot,
                    COUNT(DISTINCT DATE(hit_timestamp)) AS active_days,
                    COUNT(*)::float / NULLIF(COUNT(DISTINCT DATE(hit_timestamp)), 0) AS hit_rate_per_day,
                    24.0 * COUNT(DISTINCT DATE(hit_timestamp)) / NULLIF(COUNT(*), 0) AS avg_hours_between_hits,
                    STDDEV(amount) AS volatility
                FROM jackpots
                WHERE amount IS NOT NULL
                  AND hit_timestamp > NOW() - INTERVAL '60 days'
                GROUP BY machine_name, normalized_denomination
                HAVING COUNT(*) >= 5
            ),
            normals AS (
                SELECT
                    *,
                    1.0 / NULLIF(avg_hours_between_hits, 0) AS inv_gap,
                    total_payout / NULLIF(MAX(total_payout) OVER (), 0) AS n_total,
                    avg_jackpot / NULLIF(MAX(avg_jackpot) OVER (), 0) AS n_avg,
                    hit_rate_per_day / NULLIF(MAX(hit_rate_per_day) OVER (), 0) AS n_rate
                FROM stats
            )
            SELECT
                machine_name,
                denomination,
                hits,
                total_payout,
                avg_jackpot,
                max_jackpot,
                active_days,
                hit_rate_per_day,
                avg_hours_between_hits,
                COALESCE(inv_gap, 0) AS inv_gap,
                COALESCE(volatility, 0) AS volatility,
                COALESCE(n_total, 0) AS n_total,
                COALESCE(n_avg, 0) AS n_avg,
                COALESCE(n_rate, 0) AS n_rate,
                -- Calculate JVI as target (Frequency-Weighted: n_rate 50%, n_total 25%, n_avg 25%)
                total_payout * (0.25 * COALESCE(n_total, 0) + 0.25 * COALESCE(n_avg, 0) + 0.50 * COALESCE(n_rate, 0)) AS jvi_balanced
            FROM normals
            WHERE total_payout > 0
        """)
        
        data = cur.fetchall()
        cur.close()
        conn.close()
        
        return pd.DataFrame([dict(row) for row in data])
        
    except Exception as e:
        logger.error(f"Training data extraction error: {e}")
        return None

def train_jvi_model():
    """Train ML model for JVI prediction with PyTorch Neural Network"""
    global JVI_MODEL, JVI_SCALER, MODEL_METADATA
    
    logger.info("📊 Training JVI ML model...")
    
    # Create model directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Backup existing model if it exists
    if os.path.exists(MODEL_PATH):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_model = os.path.join(MODEL_DIR, f'jvi_model_v{timestamp}.pkl')
        backup_scaler = os.path.join(MODEL_DIR, f'jvi_scaler_v{timestamp}.pkl')
        
        try:
            import shutil
            shutil.copy2(MODEL_PATH, backup_model)
            shutil.copy2(SCALER_PATH, backup_scaler)
            logger.info(f"✅ Backed up existing model to v{timestamp}")
            
            # Clean up old backups (keep last 3)
            backups = sorted([f for f in os.listdir(MODEL_DIR) if f.startswith('jvi_model_v')])
            if len(backups) > 3:
                for old_backup in backups[:-3]:
                    try:
                        os.remove(os.path.join(MODEL_DIR, old_backup))
                        os.remove(os.path.join(MODEL_DIR, old_backup.replace('model', 'scaler')))
                    except:
                        pass
        except Exception as e:
            logger.warning(f"⚠️  Backup warning: {e}")
    
    # Get training data from database
    df = get_training_data()
    
    if df is None or len(df) < 10:
        logger.error("❌ Insufficient training data")
        return False
    
    # Prepare data
    X = df[FEATURES].fillna(0).values.astype(np.float32)
    y = df['jvi_balanced'].fillna(df['jvi_balanced'].median()).values.astype(np.float32)
    
    # Remove any infinite values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Scale features
    JVI_SCALER = StandardScaler()
    X_scaled = JVI_SCALER.fit_transform(X)
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )
    
    model_type = "PyTorch Neural Network" if TORCH_AVAILABLE else "Linear Regression"
    
    if TORCH_AVAILABLE:
        # Train PyTorch Neural Network
        JVI_MODEL = JVINet(X.shape[1])
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(JVI_MODEL.parameters(), lr=0.001)
        
        train_tensor_x = torch.FloatTensor(X_train)
        train_tensor_y = torch.FloatTensor(y_train).unsqueeze(1)
        
        # Training loop
        JVI_MODEL.train()
        for epoch in range(600):
            optimizer.zero_grad()
            outputs = JVI_MODEL(train_tensor_x)
            loss = criterion(outputs, train_tensor_y)
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 100 == 0:
                logger.info(f"Epoch [{epoch+1}/600], Loss: {loss.item():.4f}")
        
        # Evaluation
        JVI_MODEL.eval()
        with torch.no_grad():
            test_pred = JVI_MODEL(torch.FloatTensor(X_test)).numpy().flatten()
            rmse = np.sqrt(mean_squared_error(y_test, test_pred))
            
            # Calculate R² manually
            ss_res = np.sum((y_test - test_pred) ** 2)
            ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
            r2_score = 1 - (ss_res / ss_tot)
            
            # Calculate prediction standard error for confidence intervals
            residuals = y_test - test_pred
            PREDICTION_STD_ERROR = np.std(residuals)
        
        # Save model state dict
        model_to_save = JVI_MODEL.state_dict()
        
    else:
        # Fallback to Linear Regression
        from sklearn.linear_model import LinearRegression
        JVI_MODEL = LinearRegression()
        JVI_MODEL.fit(X_train, y_train)
        
        test_pred = JVI_MODEL.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, test_pred))
        r2_score = JVI_MODEL.score(X_test, y_test)
        
        # Calculate prediction standard error
        residuals = y_test - test_pred
        PREDICTION_STD_ERROR = np.std(residuals)
        
        model_to_save = JVI_MODEL
    
    # Save models
    try:
        joblib.dump(model_to_save, MODEL_PATH)
        joblib.dump(JVI_SCALER, SCALER_PATH)
        
        # Save metadata
        MODEL_METADATA = {
            'training_date': datetime.now().isoformat(),
            'record_count': len(df),
            'feature_count': len(FEATURES),
            'features': FEATURES,
            'r2_score': float(r2_score),
            'rmse': float(rmse),
            'std_error': float(PREDICTION_STD_ERROR),
            'model_type': model_type,
            'scaler_type': 'StandardScaler',
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
        
        with open(METADATA_PATH, 'w') as f:
            import json
            json.dump(MODEL_METADATA, f, indent=2)
        
        logger.info(f"✅ Model trained on {len(df)} machines and saved")
        logger.info(f"   Model Type: {model_type}")
        logger.info(f"   R² Score: {r2_score:.3f}")
        logger.info(f"   RMSE: {rmse:.2f}")
        logger.info(f"   Features: {len(FEATURES)}")
        return True
    except Exception as e:
        logger.error(f"❌ Model save error: {e}")
        return False

def load_models():
    """Load pre-trained models with auto-retrain check"""
    global JVI_MODEL, JVI_SCALER, MODEL_METADATA
    
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            JVI_SCALER = joblib.load(SCALER_PATH)
            
            # Load metadata first to determine model type
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r') as f:
                    import json
                    MODEL_METADATA = json.load(f)
                    model_type = MODEL_METADATA.get('model_type', 'Linear Regression')
            else:
                model_type = 'Linear Regression'
            
            # Load appropriate model
            if 'PyTorch' in model_type and TORCH_AVAILABLE:
                state_dict = joblib.load(MODEL_PATH)
                JVI_MODEL = JVINet(len(FEATURES))
                JVI_MODEL.load_state_dict(state_dict)
                JVI_MODEL.eval()
            else:
                JVI_MODEL = joblib.load(MODEL_PATH)
            
            # Check if auto-retrain is needed
            if MODEL_METADATA:
                training_date = datetime.fromisoformat(MODEL_METADATA['training_date'])
                days_old = (datetime.now() - training_date).days
                
                # Get current record count
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM jackpots WHERE amount IS NOT NULL")
                    current_count = cur.fetchone()[0]
                    cur.close()
                    conn.close()
                    
                    training_count = MODEL_METADATA.get('record_count', 0)
                    growth_pct = ((current_count - training_count) / training_count * 100) if training_count > 0 else 0
                    
                    # Auto-retrain conditions
                    if days_old > 7:
                        logger.warning(f"⚠️  Model is {days_old} days old - consider retraining")
                    elif growth_pct > 20:
                        logger.warning(f"⚠️  Data grew {growth_pct:.1f}% since training - consider retraining")
            
            logger.info(f"✅ JVI ML models loaded ({model_type})")
            return True
        except Exception as e:
            logger.error(f"⚠️  Model load error: {e}")
            return False
    return False

def predict_jvi(features_row: dict, return_intervals=False):
    """Predict JVI for a single machine row with optional confidence intervals"""
    if JVI_MODEL is None or JVI_SCALER is None:
        # Fallback to existing balanced JVI
        fallback = features_row.get('jvi_balanced', 0)
        if return_intervals:
            return fallback, fallback, fallback
        return fallback

    try:
        vec = np.array([[features_row.get(f, 0) for f in FEATURES]], dtype=np.float32)
        vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
        scaled = JVI_SCALER.transform(vec)
        
        if TORCH_AVAILABLE and isinstance(JVI_MODEL, nn.Module):
            tensor = torch.FloatTensor(scaled)
            with torch.no_grad():
                pred = JVI_MODEL(tensor).item()
        else:
            pred = JVI_MODEL.predict(scaled)[0]
        
        pred = float(pred)
        
        if return_intervals and PREDICTION_STD_ERROR is not None:
            # 95% confidence interval (1.96 * std_error)
            interval = 1.96 * PREDICTION_STD_ERROR
            return pred, max(0, pred - interval), pred + interval
        
        return pred
    except Exception as e:
        logger.warning(f"Prediction error: {e}")
        fallback = features_row.get('jvi_balanced', 0)
        if return_intervals:
            return fallback, fallback, fallback
        return fallback

def get_ml_enhanced_rankings(limit=50, sort_by='balanced'):
    """Get JVI rankings with ML predictions and clustering"""
    conn = get_db_connection()
    if not conn:
        logger.error("DB connection failed in get_ml_enhanced_rankings")
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get comprehensive stats
        cur.execute("""
            WITH stats AS (
                SELECT
                    machine_name,
                    normalized_denomination as denomination,
                    COALESCE(location_id, 'N/A') AS bank,
                    COUNT(*) AS hits,
                    SUM(amount) AS total_payout,
                    AVG(amount) AS avg_jackpot,
                    MAX(amount) AS max_jackpot,
                    COUNT(DISTINCT DATE(hit_timestamp)) AS active_days,
                    COUNT(*)::float / NULLIF(COUNT(DISTINCT DATE(hit_timestamp)), 0) AS hit_rate_per_day,
                    24.0 * COUNT(DISTINCT DATE(hit_timestamp)) / NULLIF(COUNT(*), 0) AS avg_hours_between_hits,
                    STDDEV(amount) AS volatility
                FROM jackpots
                WHERE amount IS NOT NULL
                  AND machine_name NOT ILIKE '%Poker%' 
                  AND machine_name NOT ILIKE '%Keno%'
                  AND hit_timestamp > NOW() - INTERVAL '30 days'
                GROUP BY machine_name, normalized_denomination, location_id
                HAVING COUNT(*) >= 3
            ),
            normals AS (
                SELECT
                    *,
                    1.0 / NULLIF(avg_hours_between_hits, 0) AS inv_gap,
                    total_payout / NULLIF(MAX(total_payout) OVER (), 0) AS n_total,
                    avg_jackpot / NULLIF(MAX(avg_jackpot) OVER (), 0) AS n_avg,
                    hit_rate_per_day / NULLIF(MAX(hit_rate_per_day) OVER (), 0) AS n_rate,
                    (1.0 / NULLIF(avg_hours_between_hits, 0)) / NULLIF(MAX(1.0 / NULLIF(avg_hours_between_hits, 0)) OVER (), 0) AS n_invgap
                FROM stats
            )
            SELECT
                machine_name,
                denomination,
                bank,
                hits,
                ROUND(total_payout::numeric, 0) AS total_payout,
                ROUND(avg_jackpot::numeric, 2) AS avg_jackpot,
                ROUND(max_jackpot::numeric, 2) AS max_jackpot,
                active_days,
                ROUND(hit_rate_per_day, 3) AS hit_rate_per_day,
                ROUND(avg_hours_between_hits, 2) AS avg_hours_between_hits,
                ROUND(COALESCE(inv_gap, 0), 6) AS inv_gap,
                ROUND(COALESCE(volatility, 0), 2) AS volatility,
                ROUND(COALESCE(n_total, 0), 6) AS n_total,
                ROUND(COALESCE(n_avg, 0), 6) AS n_avg,
                ROUND(COALESCE(n_rate, 0), 6) AS n_rate,
                ROUND(COALESCE(n_invgap, 0), 6) AS n_invgap,
                ROUND(total_payout * (0.25 * COALESCE(n_total, 0) + 0.25 * COALESCE(n_avg, 0) + 0.50 * COALESCE(n_rate, 0) + 0.25 * COALESCE(n_invgap, 0)), 2) AS jvi_balanced,
                ROUND(COALESCE(n_total, 0) + 0.5 * COALESCE(n_avg, 0), 4) AS jvi_big,
                ROUND(COALESCE(n_rate, 0) + 0.7 * COALESCE(n_invgap, 0), 4) AS jvi_fast
            FROM normals
            ORDER BY 
                CASE WHEN %s = 'balanced' THEN total_payout * (0.25 * COALESCE(n_total, 0) + 0.25 * COALESCE(n_avg, 0) + 0.50 * COALESCE(n_rate, 0) + 0.25 * COALESCE(n_invgap, 0))
                     WHEN %s = 'big' THEN (COALESCE(n_total, 0) + COALESCE(n_avg, 0))
                     WHEN %s = 'fast' THEN (COALESCE(n_rate, 0) + COALESCE(n_invgap, 0))
                END DESC
            LIMIT %s
        """, (sort_by, sort_by, sort_by, limit))
        
        rankings = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        # ML Enhancement: Add predictions with error isolation and confidence intervals
        for r in rankings:
            try:
                pred, pred_low, pred_high = predict_jvi(r, return_intervals=True)
                r['predicted_jvi'] = round(pred, 2)
                r['pred_low'] = round(pred_low, 2)
                r['pred_high'] = round(pred_high, 2)
                r['jvi_growth'] = round(pred - r['jvi_balanced'], 2)
            except Exception as e:
                logger.warning(f"Prediction error for {r.get('machine_name', 'unknown')}: {e}")
                r['predicted_jvi'] = r['jvi_balanced']
                r['pred_low'] = r['jvi_balanced']
                r['pred_high'] = r['jvi_balanced']
                r['jvi_growth'] = 0
        
        # KMeans Clustering with error handling and adaptive labeling
        try:
            if len(rankings) >= 3:
                feat_df = pd.DataFrame(rankings)
                
                # Use more features for better clustering
                cluster_features = ['hits', 'total_payout', 'avg_jackpot', 'hit_rate_per_day',
                                  'avg_hours_between_hits', 'inv_gap', 'n_total', 'n_avg', 'n_rate']
                
                X = feat_df[cluster_features].fillna(0)
                
                if len(X) > 0:
                    # Scale features
                    scaler_cluster = StandardScaler()
                    X_scaled = scaler_cluster.fit_transform(X)
                    
                    # Adaptive cluster count (max 4)
                    n_clusters = min(4, len(rankings))
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(X_scaled)
                    
                    # Analyze centroids to auto-label clusters
                    centroids_scaled = kmeans.cluster_centers_
                    centroids_orig = scaler_cluster.inverse_transform(centroids_scaled)
                    centroids_df = pd.DataFrame(centroids_orig, columns=cluster_features)
                    
                    # Smart labeling based on centroid characteristics
                    labels = []
                    for i in range(n_clusters):
                        row = centroids_df.iloc[i]
                        
                        # Fast Cycle: High hit rate + low hours between hits
                        if row['hit_rate_per_day'] > centroids_df['hit_rate_per_day'].quantile(0.7) and \
                           row['avg_hours_between_hits'] < centroids_df['avg_hours_between_hits'].quantile(0.3):
                            labels.append('Fast Cycle')
                        
                        # Big Payout: High total payout + high avg jackpot
                        elif row['total_payout'] > centroids_df['total_payout'].quantile(0.7) and \
                             row['avg_jackpot'] > centroids_df['avg_jackpot'].quantile(0.7):
                            labels.append('Big Wins')
                        
                        # High Volume: High hits but not necessarily big payouts
                        elif row['hits'] > centroids_df['hits'].quantile(0.7):
                            labels.append('High Volume')
                        
                        # Everything else is balanced
                        else:
                            labels.append('Balanced')
                    
                    # Assign to rankings
                    for idx, r in enumerate(rankings):
                        cluster_id = cluster_labels[idx]
                        r['ml_cluster'] = labels[cluster_id]
                        r['cluster_id'] = int(cluster_id)
                        
        except Exception as e:
            logger.warning(f"Clustering error: {e}")
            for r in rankings:
                r['ml_cluster'] = 'Balanced'
                r['cluster_id'] = 0
        
        return rankings
        
    except Exception as e:
        import traceback
        logger.error(f"Error in get_ml_enhanced_rankings: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

if __name__ == '__main__':
    logger.info("🤖 JVI ML SYSTEM\n")
    
    # Try to load existing models
    if not load_models():
        logger.info("No existing models found. Training new model...")
        train_jvi_model()
    
    # Test predictions
    logger.info("\n📊 Testing ML-Enhanced Rankings:")
    rankings = get_ml_enhanced_rankings(limit=10, sort_by='balanced')
    
    for i, r in enumerate(rankings[:5], 1):
        logger.info(f"\n{i}. {r['machine_name']}")
        logger.info(f"   JVI: {r['jvi_balanced']} → Predicted: {r['predicted_jvi']} (Growth: {r['jvi_growth']})")
        logger.info(f"   Cluster: {r.get('ml_cluster', 'N/A')}")
        logger.info(f"   Hits: {r['hits']}, Avg: ${r['avg_jackpot']}")
    
    logger.info("\n✅ ML system ready!")
