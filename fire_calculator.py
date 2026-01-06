#!/usr/bin/env python3
"""
FIRE Calculator Module
Calculates Financial Independence / Retire Early metrics

Based on WenFire and cFIREsim patterns from GitHub research
"""

def calculate_fire_number(annual_expenses, withdrawal_rate=0.04):
    """
    Calculate FIRE number using safe withdrawal rate
    
    Args:
        annual_expenses: Yearly spending needs
        withdrawal_rate: Safe withdrawal rate (default 4%)
    
    Returns:
        Required net worth for financial independence
    """
    return annual_expenses / withdrawal_rate

def calculate_years_to_fire(current_net_worth, annual_savings, annual_expenses, return_rate=0.07):
    """
    Calculate years until financial independence
    
    Args:
        current_net_worth: Current total net worth
        annual_savings: Amount saved per year
        annual_expenses: Yearly spending
        return_rate: Expected annual return (default 7%)
    
    Returns:
        Years to FIRE, or None if already FI
    """
    import math
    
    fire_number = calculate_fire_number(annual_expenses)
    
    # Already financially independent
    if current_net_worth >= fire_number:
        return 0
    
    # If no savings, can't reach FIRE
    if annual_savings <= 0:
        return None
    
    # Future value of series with compound interest
    # FV = PV(1+r)^n + PMT * (((1+r)^n - 1) / r)
    # Solve for n when FV = fire_number
    
    try:
        # Approximate using logarithmic formula
        numerator = math.log((fire_number - current_net_worth) * return_rate / annual_savings + 1)
        denominator = math.log(1 + return_rate)
        years = numerator / denominator
        return max(0, years)
    except:
        return None

def calculate_retirement_projections(current_age, retirement_age, current_savings, monthly_contribution, return_rate=0.07):
    """
    Project retirement savings over time
    
    Args:
        current_age: Current age
        retirement_age: Target retirement age
        current_savings: Current retirement account balance
        monthly_contribution: Monthly savings amount
        return_rate: Expected annual return
    
    Returns:
        dict with projections
    """
    years_to_retirement = retirement_age - current_age
    if years_to_retirement <= 0:
        years_to_retirement = 1
    
    months = years_to_retirement * 12
    monthly_rate = return_rate / 12
    
    # Future value calculation
    # FV = PV * (1 + r)^n + PMT * (((1 + r)^n - 1) / r)
    compound_factor = (1 + monthly_rate) ** months
    
    # Future value of current savings
    fv_current = current_savings * compound_factor
    
    # Future value of monthly contributions
    if monthly_rate > 0:
        fv_contributions = monthly_contribution * ((compound_factor - 1) / monthly_rate)
    else:
        fv_contributions = monthly_contribution * months
    
    total_at_retirement = fv_current + fv_contributions
    
    # Calculate safe withdrawal amount (4% rule)
    safe_withdrawal_monthly = (total_at_retirement * 0.04) / 12
    safe_withdrawal_annual = total_at_retirement * 0.04
    
    # Total contributions
    total_contributions = current_savings + (monthly_contribution * months)
    
    # Investment gains
    investment_gains = total_at_retirement - total_contributions
    
    return {
        'years_to_retirement': years_to_retirement,
        'total_at_retirement': round(total_at_retirement, 2),
        'safe_withdrawal_monthly': round(safe_withdrawal_monthly, 2),
        'safe_withdrawal_annual': round(safe_withdrawal_annual, 2),
        'total_contributions': round(total_contributions, 2),
        'investment_gains': round(investment_gains, 2),
        'return_on_investment_pct': round((investment_gains / total_contributions * 100) if total_contributions > 0 else 0, 2)
    }

def calculate_savings_rate(annual_income, annual_expenses):
    """Calculate savings rate percentage"""
    if annual_income <= 0:
        return 0
    return round(((annual_income - annual_expenses) / annual_income) * 100, 2)

def calculate_fi_progress(current_net_worth, annual_expenses):
    """Calculate progress toward financial independence"""
    fire_number = calculate_fire_number(annual_expenses)
    if fire_number <= 0:
        return 0
    return round((current_net_worth / fire_number) * 100, 2)

if __name__ == "__main__":
    # Test calculations
    print("FIRE Calculator Tests")
    print("=" * 50)
    
    # Example 1: Basic FIRE number
    expenses = 50000
    fire_num = calculate_fire_number(expenses)
    print(f"\nAnnual Expenses: ${expenses:,}")
    print(f"FIRE Number (4% rule): ${fire_num:,}")
    
    # Example 2: Years to FIRE
    current_nw = 100000
    annual_savings = 30000
    years = calculate_years_to_fire(current_nw, annual_savings, expenses)
    print(f"\nCurrent Net Worth: ${current_nw:,}")
    print(f"Annual Savings: ${annual_savings:,}")
    print(f"Years to FIRE: {years:.1f}" if years else "Cannot calculate")
    
    # Example 3: Retirement projection
    projection = calculate_retirement_projections(
        current_age=30,
        retirement_age=65,
        current_savings=50000,
        monthly_contribution=1000,
        return_rate=0.07
    )
    print(f"\nRetirement Projection (age 30 → 65):")
    print(f"Total at Retirement: ${projection['total_at_retirement']:,}")
    print(f"Safe Withdrawal: ${projection['safe_withdrawal_annual']:,}/year")
    print(f"ROI: {projection['return_on_investment_pct']}%")
