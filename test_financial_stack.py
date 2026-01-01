import QuantLib as ql
import yfinance as yf
import pandas as pd
import datetime

print("--- 1. Testing Data Download (yfinance) ---")
ticker = "AAPL"
print(f"Downloading data for {ticker}...")
# Verify yfinance works
try:
    data = yf.download(ticker, period="5d", progress=False)
    if not data.empty:
        print(f"Success! Downloaded {len(data)} rows.")
        # Handle multi-index columns if present (common in recent yfinance)
        try:
            last_close = data['Close'].iloc[-1].item()
        except:
            last_close = data['Close'].iloc[-1]
            
        print(f"Last close: ${last_close:.2f}")
    else:
        print("Warning: No data downloaded (could be network/API issue), but library imported fine.")
except Exception as e:
    print(f"Error downloading data: {e}")

print("\n--- 2. Testing QuantLib (Option Pricing) ---")
# Set up a simple European Option
today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

risk_free_rate = 0.05
volatility = 0.20
spot_price = 150.0
strike_price = 155.0
maturity_date = today + ql.Period(6, ql.Months)

print(f"Valuing European Call Option:")
print(f"  Spot: ${spot_price}")
print(f"  Strike: ${strike_price}")
print(f"  Volatility: {volatility:.0%}")
print(f"  Maturity: {maturity_date}")

# Construct the option
payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike_price)
exercise = ql.EuropeanExercise(maturity_date)
option = ql.VanillaOption(payoff, exercise)

# Market data
spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot_price))
# Determine risk free rate
flat_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, risk_free_rate, ql.Actual360()))
# Determine volatility
flat_vol_ts = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), volatility, ql.Actual360()))

# Black-Scholes Process
bsm_process = ql.BlackScholesProcess(spot_handle, flat_ts, flat_vol_ts)
option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))

price = option.NPV()
print(f"\nCalculated Option Price: ${price:.4f}")

if price > 0:
    print("\n✅ QuantLib & Financial Stack are fully operational!")
else:
    print("\n❌ QuantLib calculation returned 0 or failed.")
