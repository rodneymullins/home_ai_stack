from flask import Blueprint, send_file, request, current_app
import pandas as pd
import io
import os
from datetime import datetime
from utils.db_pool import get_db_connection
from app.services.browse_service import get_all_machine_stats

# Try importing specialized modules
try:
    from jvi_ml import get_ml_enhanced_rankings, load_models, train_jvi_model
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: jvi_ml not found")

try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: weasyprint not found")

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/retrain-jvi', methods=['GET', 'POST'])
def retrain_jvi():
    """Manually retrain the JVI ML model"""
    if not ML_AVAILABLE:
        return "ML module not available", 500
        
    try:
        # Import train_jvi_model here
        from jvi_ml import train_jvi_model, load_models
        
        if request.method == 'POST':
            # Perform retraining
            import time
            start_time = time.time()
            
            success = train_jvi_model()
            training_time = time.time() - start_time
            
            if success:
                # Reload models
                load_models()
                
                return f"""
                <html>
                <head>
                    <title>Model Retrained</title>
                    <!-- Styles assumed global or inline -->
                    <style>
                        body {{ background: #1a1a1a; color: #f4e8d0; font-family: Arial; padding: 40px; }}
                        .success {{ background: rgba(0, 255, 159, 0.1); border: 2px solid #00ff9f; padding: 20px; border-radius: 8px; }}
                        .metric {{ margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.05); }}
                        a {{ color: #00ff9f; text-decoration: none; }}
                    </style>
                </head>
                <body>
                    <div class="success">
                        <h1>✅ Model Retrained Successfully!</h1>
                        <div class="metric"><strong>Training Time:</strong> {training_time:.2f} seconds</div>
                        <div class="metric"><strong>Status:</strong> Model loaded and ready</div>
                        <p style="margin-top: 20px;">
                            <a href="/analytics/jvi-rankings">→ View JVI Rankings</a> | 
                            <a href="/">→ Back to Dashboard</a>
                        </p>
                    </div>
                </body>
                </html>
                """
            else:
                return "❌ Model retraining failed. Check logs for details.", 500
        
        # GET request - show confirmation page
        return render_template('admin/retrain_jvi.html')
        
    except Exception as e:
        return f"Error: {e}", 500

@admin_bp.route('/export/pdf/analytics-report')
def export_pdf_report():
    """Generate comprehensive PDF analytics report"""
    if not PDF_AVAILABLE or not ML_AVAILABLE:
        return "PDF generation or ML module not available", 500
        
    try:
        load_models()
        rankings = get_ml_enhanced_rankings(limit=50, sort_by='balanced')
        
        # Create HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Casino Analytics Report</title>
            <style>
                @page {{ size: A4; margin: 1cm; }}
                body {{ font-family: Arial, sans-serif; color: #333; }}
                h1 {{ color: #d4af37; border-bottom: 3px solid #d4af37; padding-bottom: 10px; }}
                h2 {{ color: #cd7f32; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #d4af37; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                .cluster-badge {{ padding: 3px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }}
                .cluster-big {{ background: #ff6b6b; color: white; }}
                .cluster-fast {{ background: #4dabf7; color: white; }}
                .cluster-high {{ background: #20c997; color: white; }}
                .cluster-balanced {{ background: #ffd43b; color: #333; }}
            </style>
        </head>
        <body>
            <h1>🎰 Casino Analytics Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Machines Analyzed:</strong> {len(rankings)}</p>
            
            <h2>Top 20 JVI Rankings (ML-Enhanced)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Machine</th>
                        <th>Cluster</th>
                        <th>JVI</th>
                        <th>Predicted</th>
                        <th>Growth</th>
                        <th>Hits</th>
                        <th>Avg Payout</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, m in enumerate(rankings[:20], 1):
            cluster_class = m.get('ml_cluster', 'Balanced').lower().replace(' ', '-').split()[0]
            html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{m['machine_name'][:40]}</td>
                        <td><span class="cluster-badge cluster-{cluster_class}">{m.get('ml_cluster', 'N/A')}</span></td>
                        <td>{m.get('jvi_balanced', 0):.0f}</td>
                        <td>{m.get('predicted_jvi', 0):.0f}</td>
                        <td>{m.get('jvi_growth', 0):+.0f}</td>
                        <td>{m.get('hits', 0)}</td>
                        <td>${m.get('avg_jackpot', 0):,.0f}</td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            
            <h2>Cluster Distribution</h2>
            <p>Machines are automatically clustered using KMeans ML algorithm based on behavioral patterns.</p>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()
        
        # Send as download
        pdf_buffer = io.BytesIO(pdf)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'casino_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        import traceback
        return f"PDF generation error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@admin_bp.route('/export/csv/jvi-rankings')
def export_jvi_csv():
    """Export JVI rankings as CSV - ALL machines"""
    if not ML_AVAILABLE:
        return "ML module not available", 500
        
    try:
        # Load models and get ALL rankings (no limit)
        load_models()
        rankings = get_ml_enhanced_rankings(limit=1000, sort_by='balanced')  # Get all machines
        
        # Convert to DataFrame
        df = pd.DataFrame(rankings)
        
        # Select relevant columns
        columns = ['machine_name', 'denomination', 'bank', 'hits', 'total_payout', 
                  'avg_jackpot', 'max_jackpot', 'jvi_balanced', 'predicted_jvi', 
                  'pred_low', 'pred_high', 'jvi_growth', 'ml_cluster']
        
        # Filter to existing columns
        export_cols = [c for c in columns if c in df.columns]
        df_export = df[export_cols]
        
        # Create CSV in memory
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Convert to bytes
        bytes_buffer = io.BytesIO(csv_data.encode('utf-8'))
        bytes_buffer.seek(0)
        
        return send_file(
            bytes_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'jvi_rankings_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        import traceback
        return f"Export error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@admin_bp.route('/import-data', methods=['GET'])
def import_data():
    """Import legacy CSV data"""
    conn = get_db_connection()
    if not conn:
        return "DB error", 500
    cur = conn.cursor()

    try:
        # Load CSV (expected in app root)
        # Note: current_app.root_path points to app/, we need parent dir usually
        # or just assume CWD if running from root
        csv_path = 'jackpot_raw_clean.csv'
        if not os.path.exists(csv_path):
             # Try parent dir
             csv_path = '../jackpot_raw_clean.csv'
             if not os.path.exists(csv_path):
                return "Error: jackpot_raw_clean.csv not found in server directory.", 404

        df = pd.read_csv(csv_path)
        # Ensure regex formatting or specific date parsing if needed
        df['hit_timestamp'] = pd.to_datetime(df['datetime'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        df['location_id'] = df['bank'] 
        
        inserted = 0
        for _, row in df.iterrows():
            if pd.isnull(row['hit_timestamp']):
                continue
                
            try:
                machine = row.get('machine_name', 'Unknown')
                denom = row.get('denomination', 'Unknown')
                amount = row.get('amount', 0)
                
                # Clean amount
                if isinstance(amount, str):
                    amount = float(amount.replace('$', '').replace(',', ''))
                
                cur.execute("""
                    INSERT INTO jackpots (location_id, machine_name, denomination, amount, hit_timestamp, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (row['bank'], machine, denom, amount, row['hit_timestamp'], datetime.now()))
                inserted += cur.rowcount
            except Exception:
                pass

        conn.commit()
        cur.close()
        conn.close()
        return f"✅ Imported {inserted} new jackpots!"
        
    except Exception as e:
        return f"Import failed: {str(e)}", 500
