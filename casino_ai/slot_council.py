"""
Slot Multi-Agent Decision System
4-agent council for slot machine recommendations
"""

from enum import Enum
from typing import Dict, List
import psycopg2

DB_CONFIG = {'database': 'postgres', 'user': 'rod', 'host': '192.168.1.211'}

class Vote(Enum):
    STRONG_YES = 2
    YES = 1
    ABSTAIN = 0
    NO = -1
    STRONG_NO = -2


class ValueAgent:
    """Evaluates mathematical edge and RTP"""
    weight = 2.5
    
    def evaluate(self, machine: Dict, context: Dict) -> tuple:
        score = 0.0
        
        # RTP score (0-3 points)
        rtp = machine.get('rtp_percentage', 0.90)
        if rtp >= 0.96:
            score += 3.0
        elif rtp >= 0.94:
            score += 2.0
        elif rtp >= 0.92:
            score += 1.0
        
        # Progressive jackpot bonus
        if 'Progressive' in str(machine.get('features', '')):
            score += 2.0
        
        if score >= 4.0:
            return Vote.STRONG_YES, f"High RTP ({rtp:.1%})"
        elif score >= 2.5:
            return Vote.YES, f"Good RTP ({rtp:.1%})"
        elif score < 1.0:
            return Vote.NO, f"Low RTP ({rtp:.1%})"
        else:
            return Vote.ABSTAIN, "Moderate value"


class RiskAgent:
    """Evaluates volatility and bankroll requirements"""
    weight = 2.0
    
    def evaluate(self, machine: Dict, context: Dict) -> tuple:
        bankroll = context.get('user_bankroll', 100)
        
        volatility = machine.get('volatility', 'medium').lower()
        min_bet = 0.25  # Placeholder
        
        required_bankroll = min_bet * 100
        
        if bankroll < required_bankroll:
            return Vote.STRONG_NO, "Insufficient bankroll"
        
        # Volatility match
        if volatility == 'low' and bankroll < 50:
            return Vote.YES, "Low volatility safe for small bankroll"
        elif volatility == 'high' and bankroll > 200:
            return Vote.YES, "High volatility good for large bankroll"
        elif volatility == 'medium':
            return Vote.YES, "Balanced risk"
        else:
            return Vote.ABSTAIN, "Neutral risk profile"


class ThemeAgent:
    """Evaluates player engagement factors"""
    weight = 1.0
    
    def evaluate(self, machine: Dict, context: Dict) -> tuple:
        theme_score = 0.0
        
        # Manufacturer reputation
        mfg = machine.get('manufacturer', '')
        premium_mfgs = ['IGT', 'Aristocrat', 'Konami', 'WMS']
        if mfg in premium_mfgs:
            theme_score += 1.5
        
        # Features
        features = str(machine.get('features', ''))
        if 'Bonus' in features or 'Free Spins' in features:
            theme_score += 1.0
        
        if theme_score >= 2.0:
            return Vote.YES, f"High engagement ({mfg})"
        elif theme_score >= 1.0:
            return Vote.ABSTAIN, "Moderate appeal"
        else:
            return Vote.NO, "Low engagement"


class LocationAgent:
    """Evaluates machine placement and activity"""
    weight = 1.5
    
    def evaluate(self, machine: Dict, context: Dict) -> tuple:
        machine_name = machine.get('machine_name', '')
        
        # Get recent activity from jackpots
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM jackpots 
            WHERE machine_name = %s 
            AND hit_timestamp > NOW() - INTERVAL '7 days'
        """, (machine_name,))
        
        hits_7d = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        # Hot machine = recently paid out (avoid)
        if hits_7d > 5:
            return Vote.NO, f"Too hot ({hits_7d} hits in 7 days)"
        elif hits_7d < 2:
            return Vote.YES, f"Cold machine ({hits_7d} hits in 7 days)"
        else:
            return Vote.ABSTAIN, f"Normal activity ({hits_7d} hits)"


class SlotCouncil:
    """Multi-agent slot recommendation system"""
    
    def __init__(self):
        self.agents = [
            ValueAgent(),
            RiskAgent(),
            ThemeAgent(),
            LocationAgent()
        ]
    
    def evaluate_machine(self, machine: Dict, user_context: Dict) -> Dict:
        """Get collective recommendation from all agents"""
        votes = []
        weighted_sum = 0
        total_weight = 0
        
        for agent in self.agents:
            vote, explanation = agent.evaluate(machine, user_context)
            votes.append({
                'agent': agent.__class__.__name__,
                'vote': vote.name,
                'weight': agent.weight,
                'explanation': explanation
            })
            
            weighted_sum += vote.value * agent.weight
            total_weight += agent.weight
        
        # Calculate weighted score
        final_score = weighted_sum / total_weight
        
        # Determine recommendation
        if final_score >= 1.0:
            recommendation = "STRONG PLAY"
            confidence = min(final_score / 2.0, 1.0)
        elif final_score >= 0.5:
            recommendation = "PLAY"
            confidence = abs(final_score) / 2.0
        elif final_score <= -0.5:
            recommendation = "AVOID"
            confidence = abs(final_score) / 2.0
        else:
            recommendation = "NEUTRAL"
            confidence = 0.3
        
        return {
            'machine': machine.get('machine_name', 'Unknown'),
            'recommendation': recommendation,
            'confidence': confidence,
            'weighted_score': final_score,
            'votes': votes
        }


if __name__ == "__main__":
    # Test the council
    print("Slot Multi-Agent Council Test")
    print("=" * 60)
    
    # Example machine
    machine = {
        'machine_name': 'BUFFALO GOLD',
        'rtp_percentage': 0.96,
        'manufacturer': 'Aristocrat',
        'volatility': 'high',
        'features': ['Progressive', 'Free Spins', 'Bonus']
    }
    
    # User context
    context = {
        'user_bankroll': 250,
        'casino': 'Coushatta'
    }
    
    council = SlotCouncil()
    result = council.evaluate_machine(machine, context)
    
    print(f"\nMachine: {result['machine']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Confidence: {result['confidence']*100:.0f}%")
    print(f"Weighted Score: {result['weighted_score']:.2f}")
    print(f"\nAgent Votes:")
    for vote in result['votes']:
        print(f"  {vote['agent']:15} {vote['vote']:12} (weight: {vote['weight']}) - {vote['explanation']}")
