#!/usr/bin/env python3
"""
Analyze "Double Gold" machines - compare manufacturer volatility vs actual performance
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import sys
sys.path.insert(0, '..')
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Find all Double Gold machines
print("=" * 80)
print("DOUBLE GOLD MACHINE ANALYSIS")
print("=" * 80)

cur.execute("""
    SELECT DISTINCT machine_name, manufacturer, denomination, volatility
    FROM slot_machines
    WHERE machine_name ILIKE '%Double%Gold%'
    ORDER BY machine_name
""")

machines = cur.fetchall()

if not machines:
    print("\n❌ No 'Double Gold' machines found in inventory")
else:
    print(f"\n📊 Found {len(machines)} Double Gold variant(s):\n")
    
    for machine in machines:
        print(f"\n{'='*80}")
        print(f"🎰 MACHINE: {machine['machine_name']}")
        print(f"   Manufacturer: {machine['manufacturer']}")
        print(f"   Denomination: {machine['denomination']}")
        
        # Clean volatility
        vol_raw = machine['volatility'] if machine['volatility'] else 'Unknown'
        vol_clean = vol_raw.split('View')[0].split('$')[0].strip()
        print(f"   MFG Stated Volatility: {vol_clean}")
        
        # Get jackpot history
        cur.execute("""
            SELECT amount, hit_timestamp, location_id
            FROM jackpots
            WHERE machine_name = %s
            ORDER BY hit_timestamp ASC
        """, (machine['machine_name'],))
        
        hits = cur.fetchall()
        
        if not hits:
            print(f"\n   ⚠️  No jackpot history found")
            continue
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([dict(h) for h in hits])
        df['amount'] = pd.to_numeric(df['amount'])
        df['hit_timestamp'] = pd.to_datetime(df['hit_timestamp'])
        
        print(f"\n   📈 JACKPOT HISTORY ({len(df)} total hits)")
        print(f"   Date Range: {df['hit_timestamp'].min().strftime('%Y-%m-%d')} to {df['hit_timestamp'].max().strftime('%Y-%m-%d')}")
        
        # Calculate volatility metrics
        avg_payout = df['amount'].mean()
        std_dev = df['amount'].std()
        median_payout = df['amount'].median()
        min_payout = df['amount'].min()
        max_payout = df['amount'].max()
        
        # Coefficient of Variation (CV) - key volatility indicator
        cv = std_dev / avg_payout if avg_payout > 0 else 0
        
        print(f"\n   💰 PAYOUT STATISTICS")
        print(f"   Average:  ${avg_payout:,.2f}")
        print(f"   Median:   ${median_payout:,.2f}")
        print(f"   Std Dev:  ${std_dev:,.2f}")
        print(f"   Min:      ${min_payout:,.2f}")
        print(f"   Max:      ${max_payout:,.2f}")
        print(f"   Range:    ${max_payout - min_payout:,.2f}")
        
        # Hit frequency analysis
        df['time_diff'] = df['hit_timestamp'].diff()
        avg_hours_between = df['time_diff'].mean().total_seconds() / 3600 if len(df) > 1 else 0
        
        print(f"\n   ⏱️  HIT FREQUENCY")
        print(f"   Avg Time Between Hits: {int(avg_hours_between)}h {int((avg_hours_between % 1) * 60)}m")
        print(f"   Hits Per Day (avg): {24 / avg_hours_between:.2f}" if avg_hours_between > 0 else "   N/A")
        
        # Payout distribution
        bins = [0, 1500, 2500, 5000, float('inf')]
        labels = ['Small (<$1.5k)', 'Medium ($1.5k-$2.5k)', 'Large ($2.5k-$5k)', 'Huge ($5k+)']
        df['bucket'] = pd.cut(df['amount'], bins=bins, labels=labels)
        dist = df['bucket'].value_counts().sort_index()
        
        print(f"\n   📊 PAYOUT DISTRIBUTION")
        for bucket, count in dist.items():
            pct = (count / len(df)) * 100
            print(f"   {bucket}: {count} hits ({pct:.1f}%)")
        
        # Calculate MY volatility rating
        print(f"\n   🔬 CALCULATED VOLATILITY ANALYSIS")
        print(f"   Coefficient of Variation: {cv:.3f}")
        
        if cv < 0.3:
            my_vol = "Low"
            desc = "Payouts cluster tightly around average (consistent)"
        elif cv < 0.7:
            my_vol = "Medium"
            desc = "Moderate payout variance"
        else:
            my_vol = "High"
            desc = "Wide payout swings (high risk/reward)"
        
        print(f"   My Rating: {my_vol} ({desc})")
        
        # Compare with manufacturer
        print(f"\n   ⚖️  VOLATILITY COMPARISON")
        print(f"   Manufacturer Says: {vol_clean}")
        print(f"   My Analysis Says: {my_vol}")
        
        if vol_clean == 'Unknown' or vol_clean == 'N/A':
            print(f"   Assessment: ⚠️  No manufacturer data to compare")
        elif my_vol.lower() in vol_clean.lower():
            print(f"   Assessment: ✅ AGREEMENT - Data supports manufacturer rating")
        else:
            print(f"   Assessment: ⚠️  DISCREPANCY - My calc suggests {my_vol}, MFG says {vol_clean}")
            print(f"      Possible reasons: Small sample size, recent changes, or MFG uses different metrics")
        
        # Recent trend (last 30 days vs overall)
        last_30 = df[df['hit_timestamp'] > (datetime.now() - pd.Timedelta(days=30))]
        if len(last_30) > 3:
            recent_avg = last_30['amount'].mean()
            recent_std = last_30['amount'].std()
            recent_cv = recent_std / recent_avg if recent_avg > 0 else 0
            
            print(f"\n   📅 RECENT TREND (Last 30 Days)")
            print(f"   Recent Hits: {len(last_30)}")
            print(f"   Recent Avg: ${recent_avg:,.2f} (Overall: ${avg_payout:,.2f})")
            print(f"   Recent CV: {recent_cv:.3f} (Overall: {cv:.3f})")
            
            if recent_cv > cv * 1.2:
                print(f"   Trend: 📈 Volatility INCREASING recently")
            elif recent_cv < cv * 0.8:
                print(f"   Trend: 📉 Volatility DECREASING recently (more consistent)")
            else:
                print(f"   Trend: ➡️  Stable volatility pattern")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("Analysis complete.")
print("=" * 80)
