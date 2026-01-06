# Polymarket Trading Bot & Gemma 3 Fine-Tuning Context

## Polymarket Trading Bot (Temporal Arbitrage)
**Logic**: Exploits lag between Binance (Leader) and Polymarket (Lagger).
- **Buy YES** if Binance Price > Strike Price but Polymarket < 90c.
- **Hardware**: VPS recommended (NJ/VA). Python 3.11+.

### Key Libraries
`py-clob-client`, `python-binance`, `python-dotenv`, `cryptography`

### Code Snippet (Arbitrage Logic)
```python
def check_for_arbitrage(poly_price, kalshi_price):
    k_norm = kalshi_price / 100 
    p_norm = poly_price
    spread = k_norm - p_norm
    if spread > 0.02:
        print(f"Opportunity: Buy on Poly at {p_norm}, Sell on Kalshi at {k_norm}")
```

### Kalshi Integration
- Requires Session Manager (expires 30m).
- RSA Key signing for high-speed API.

## Gemma 3 1B-IT Fine-Tuning
- **Model**: Google's Gemma 3 1B Instruct.
- **Goal**: Financial Sentiment Analysis.
- **Technique**: PEFT (LoRA) + 4-bit Quantization (QLoRA).
- **Dataset**: FinancialPhraseBank (Positive/Neutral/Negative).
- **Performance**: ~88% Accuracy after fine-tuning.

### Training Config
- `lora_alpha=32`, `r=64`.
- `learning_rate=2e-4`.
- Optimized for Consumer Hardware (e.g. Kaggle P100).
