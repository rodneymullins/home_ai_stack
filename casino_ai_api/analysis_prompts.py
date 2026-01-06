"""
Advanced analysis prompt builders for Casino AI
"""

def build_hot_cold_prompt(machines):
    """Analyze hot and cold streaks"""
    return f"""Analyze {len(machines)} slot machines for hot and cold streaks.

Machines: {', '.join([f"{m['machine_id']} (Win Rate: {m.get('win_rate', 'N/A')}%)" for m in machines[:10]])}

Identify:
1. Which machines are on hot streaks (consistently high win rates)
2. Which machines are cold (underperforming)
3. Patterns in streak duration

Format response as:
SUMMARY: [2-3 sentences]
FINDINGS:
- [hot streak insight]
- [cold streak insight]
- [pattern observation]
RECOMMENDATIONS:
- [actionable suggestion 1]
- [actionable suggestion 2]
- [actionable suggestion 3]"""


def build_placement_prompt(machines):
    """Analyze optimal floor placement"""
    locations = {}
    for m in machines:
        loc = m.get('location', 'Unknown')
        if loc not in locations:
            locations[loc] = []
        locations[loc].append(m)
    
    loc_summary = []
    for loc, machines_list in list(locations.items())[:5]:
        avg_win = sum(m.get('win_rate', 0) for m in machines_list) / len(machines_list) if machines_list else 0
        loc_summary.append(f"{loc}: {len(machines_list)} machines, avg {avg_win:.1f}% win rate")
    
    return f"""Analyze floor placement optimization for these locations:

{chr(10).join(loc_summary)}

Determine:
1. Which locations generate best performance
2. Underutilized high-value locations
3. Placement recommendations

Format response as:
SUMMARY: [your analysis]
FINDINGS:
- [best location insight]
- [underperforming location]
- [pattern observation]
RECOMMENDATIONS:
- [move suggestion 1]
- [move suggestion 2]
- [optimization tip]"""


def build_denomination_prompt(machines):
    """Compare performance across denominations"""
    denoms = {}
    for m in machines:
        denom = m.get('denomination', 'Unknown')
        if denom not in denoms:
            denoms[denom] = []
        denoms[denom].append(m)
    
    denom_summary = []
    for denom, machines_list in list(denoms.items())[:6]:
        count = len(machines_list)
        denom_summary.append(f"{denom}: {count} machines")
    
    return f"""Analyze denomination performance:

{chr(10).join(denom_summary)}

Compare:
1. Which denominations perform best
2. Player preferences by bet size
3. Revenue optimization opportunities

Format response as:
SUMMARY: [denomination analysis]
FINDINGS:
- [best denomination]
- [player preference insight]
- [revenue opportunity]
RECOMMENDATIONS:
- [denomination adjustment 1]
- [denomination adjustment 2]
- [portfolio optimization]"""


def build_time_patterns_prompt(machines):
    """Analyze time-based performance patterns"""
    return f"""Analyze time-based patterns for {len(machines)} machines.

Based on available data, identify:
1. Peak performance hours/days
2. Seasonal variations
3. Time-based optimization opportunities

Format response as:
SUMMARY: [time pattern analysis]
FINDINGS:
- [peak time insight]
- [low-traffic period]
- [temporal pattern]
RECOMMENDATIONS:
- [scheduling suggestion]
- [maintenance timing]
- [promotional timing]"""


def build_cluster_prompt(machines):
    """Group similar-performing machines"""
    machine_summary = []
    for m in machines[:15]:
        machine_summary.append(
            f"{m.get('machine_id', 'Unknown')}: "
            f"Win {m.get('win_rate', 0)}%, "
            f"Denom {m.get('denomination', 'N/A')}"
        )
    
    return f"""Group these machines into performance clusters:

{chr(10).join(machine_summary)}

Create clusters based on:
1. Win rate similarity
2. Denomination grouping
3. Performance tier

Format response as:
SUMMARY: [cluster analysis]
FINDINGS:
- [high-performance cluster]
- [mid-tier cluster]
- [low-performance cluster]
RECOMMENDATIONS:
- [cluster management 1]
- [cluster management 2]
- [optimization strategy]"""


def build_forecast_prompt(machines):
    """Forecast future revenue"""
    return f"""Forecast revenue trends for {len(machines)} machines.

Current metrics available. Predict:
1. 30-day revenue projection
2. Growth/decline trends
3. Risk factors

Format response as:
SUMMARY: [forecast overview]
FINDINGS:
- [growth prediction]
- [risk identification]
- [trend observation]
RECOMMENDATIONS:
- [proactive measure 1]
- [proactive measure 2]
- [risk mitigation]"""


def build_competitive_prompt(machines):
    """Compare against floor averages"""
    if not machines:
        avg_win = 0
    else:
        avg_win = sum(m.get('win_rate', 0) for m in machines) / len(machines)
    
    above_avg = [m for m in machines if m.get('win_rate', 0) > avg_win]
    below_avg = [m for m in machines if m.get('win_rate', 0) <= avg_win]
    
    return f"""Floor average win rate: {avg_win:.1f}%

Machines above average: {len(above_avg)}
Machines below average: {len(below_avg)}

Analyze:
1. Top performers vs floor
2. Underperformers needing attention
3. Competitive positioning

Format response as:
SUMMARY: [competitive analysis]
FINDINGS:
- [top performer insight]
- [underperformer issue]
- [floor positioning]
RECOMMENDATIONS:
- [improve underperformers]
- [leverage top performers]
- [competitive strategy]"""


def build_volatility_prompt(machines):
    """Analyze risk/reward profiles"""
    return f"""Analyze volatility profiles for {len(machines)} machines.

Assess:
1. High-risk/high-reward machines
2. Stable, consistent performers
3. Portfolio balance

Format response as:
SUMMARY: [volatility assessment]
FINDINGS:
- [high-volatility machines]
- [stable performers]
- [balance analysis]
RECOMMENDATIONS:
- [risk management]
- [portfolio adjustment]
- [player experience optimization]"""


def build_correlation_prompt(machines):
    """Find related performance patterns"""
    return f"""Analyze correlations between {len(machines)} machines.

Look for:
1. Machines with similar performance trends
2. Location-based correlations
3. Denomination-based patterns

Format response as:
SUMMARY: [correlation analysis]
FINDINGS:
- [strong correlation 1]
- [strong correlation 2]
- [pattern insight]
RECOMMENDATIONS:
- [leverage correlation 1]
- [leverage correlation 2]
- [strategic grouping]"""


def build_roi_prompt(machines):
    """Calculate investment returns"""
    return f"""Analyze ROI for {len(machines)} machines.

Calculate:
1. Revenue per machine
2. Cost efficiency
3. Investment recommendations

Format response as:
SUMMARY: [ROI analysis]
FINDINGS:
- [highest ROI machines]
- [lowest ROI machines]
- [efficiency insight]
RECOMMENDATIONS:
- [investment priority 1]
- [investment priority 2]
- [cost optimization]"""


def build_retention_prompt(machines):
    """Analyze player repeat-play patterns"""
    return f"""Analyze player retention patterns for {len(machines)} machines.

Examine:
1. Machines with high repeat play
2. One-time play machines
3. Engagement factors

Format response as:
SUMMARY: [retention analysis]
FINDINGS:
- [high retention machines]
- [low retention machines]
- [engagement factor]
RECOMMENDATIONS:
- [improve retention]
- [replicate success]
- [engagement strategy]"""


def build_seasonal_prompt(machines):
    """Analyze monthly/quarterly trends"""
    return f"""Analyze seasonal trends for {len(machines)} machines.

Identify:
1. Peak season performance
2. Off-season patterns
3. Yearly cycles

Format response as:
SUMMARY: [seasonal analysis]
FINDINGS:
- [peak season insight]
- [off-season pattern]
- [yearly trend]
RECOMMENDATIONS:
- [seasonal adjustment 1]
- [seasonal adjustment 2]
- [annual planning]"""
