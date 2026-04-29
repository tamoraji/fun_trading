# Strategy Manual

This guide explains each trading strategy available in the framework — what it does, how it works, what signals it generates, and how to configure it.

---

## 1. Moving Average Crossover (SMA)

**Config name:** `moving_average_crossover`

### What it is

A trend-following strategy that uses two Simple Moving Averages (SMAs) of different lengths. The shorter (fast) SMA reacts quickly to price changes, while the longer (slow) SMA smooths out noise and represents the broader trend.

### How it works

A Simple Moving Average is the arithmetic mean of the last N closing prices. For example, a 5-period SMA is the average of the last 5 closes.

The strategy compares two SMAs on every bar:

- **Fast SMA** (short window): Tracks recent price movement.
- **Slow SMA** (long window): Tracks the overall trend.

When the fast SMA crosses above the slow SMA, it suggests upward momentum is building. When it crosses below, momentum is turning downward.

### Signals

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **BUY** | Fast SMA crosses above slow SMA | Short-term momentum has turned bullish — price is rising faster than the trend. |
| **SELL** | Fast SMA crosses below slow SMA | Short-term momentum has turned bearish — price is falling below the trend. |
| **HOLD** | No crossover on the current bar | No change in trend direction. |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `short_window` | 5 | Number of bars for the fast SMA. Smaller = more responsive, more signals, more noise. |
| `long_window` | 20 | Number of bars for the slow SMA. Larger = smoother trend, fewer signals, more lag. |

### Recommended ranges

- **Intraday (1m-15m bars):** short 5-10, long 20-50
- **Swing trading (1h-1d bars):** short 10-20, long 50-200
- **The classic "Golden Cross / Death Cross":** short 50, long 200 (daily bars)

### When to use

- Markets with clear trending behavior (stocks in an uptrend/downtrend).
- Works best on longer timeframes where trends are more reliable.
- Less effective in choppy, sideways markets where it generates false crossovers.

### Example

With `short_window=5` and `long_window=20` on 5-minute bars:

```
Bar 1-20: Price consolidating around $150
Bar 21:   Price starts rising to $155
Bar 25:   5-bar SMA = $154.00, 20-bar SMA = $151.50
           Fast SMA crosses above slow SMA
           -> BUY signal at $155.00
```

### Strengths and limitations

**Strengths:**
- Simple and easy to understand
- Catches major trend reversals
- Few false signals in strong trending markets

**Limitations:**
- Lags behind the actual price move (signals come after the trend starts)
- Generates many false signals in sideways/ranging markets
- The crossover itself doesn't tell you how strong the trend is

---

## 2. Relative Strength Index (RSI)

**Config name:** `rsi`

### What it is

A momentum oscillator that measures the speed and magnitude of recent price changes to evaluate whether an asset is overbought (too expensive, likely to drop) or oversold (too cheap, likely to bounce).

RSI ranges from 0 to 100. Values below the oversold threshold suggest the price has fallen too fast and may reverse upward. Values above the overbought threshold suggest the price has risen too fast and may reverse downward.

### How it works

RSI is calculated using the Wilder smoothing method:

1. **Calculate price changes:** For each bar, compute `close - previous_close`.
2. **Separate gains and losses:** Gains are positive changes, losses are the absolute value of negative changes.
3. **Smooth averages:** Use an exponential moving average (Wilder method) to smooth gains and losses over the configured period.
4. **Compute RS:** `RS = average_gain / average_loss`
5. **Compute RSI:** `RSI = 100 - (100 / (1 + RS))`

The Wilder smoothing gives more weight to recent changes while still considering the full history, making it less noisy than a simple average.

### Signals

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **BUY** | RSI crosses below the oversold threshold | Price momentum has become extremely bearish — potential reversal or bounce. |
| **SELL** | RSI crosses above the overbought threshold | Price momentum has become extremely bullish — potential pullback or reversal. |
| **HOLD** | RSI is between oversold and overbought thresholds | Momentum is within normal range. |

**Important:** Signals fire on the *crossover* — when RSI moves from normal territory into the extreme zone. This prevents repeated signals while RSI stays in the same zone.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `period` | 14 | Number of bars used to calculate RSI. Smaller = more sensitive, more signals. Larger = smoother, fewer signals. |
| `oversold` | 30 | RSI level below which a BUY signal is generated. |
| `overbought` | 70 | RSI level above which a SELL signal is generated. |

### Recommended ranges

- **Standard (Wilder's original):** period 14, oversold 30, overbought 70
- **More sensitive (shorter-term trading):** period 7-10, oversold 20, overbought 80
- **More conservative (fewer signals):** period 21, oversold 25, overbought 75
- **Wide thresholds for strong trends:** oversold 20, overbought 80 (avoids premature signals in strong trends)

### When to use

- Range-bound or mean-reverting markets where prices oscillate.
- To identify potential reversal points after strong moves.
- Works well as a *filter* alongside trend-following strategies.

### Example

With `period=14`, `oversold=30`, `overbought=70` on 5-minute bars:

```
Bars 1-14: Price drops from $150 to $135 (steady decline)
Bar 15:    RSI = 32 (above 30, still normal)
Bar 16:    Price drops sharply to $132
           RSI = 28 (crossed below 30)
           -> BUY signal at $132.00

Later...
Bars 30-44: Price rises from $135 to $155 (steady climb)
Bar 45:    RSI = 68 (below 70, still normal)
Bar 46:    Price jumps to $158
           RSI = 73 (crossed above 70)
           -> SELL signal at $158.00
```

### Strengths and limitations

**Strengths:**
- Good at identifying potential reversal points
- Bounded between 0-100, making it easy to interpret
- Works well in ranging markets

**Limitations:**
- Can stay in overbought/oversold territory for extended periods during strong trends (RSI at 80 doesn't mean the price will immediately drop)
- Less useful in strongly trending markets where assets can remain overbought/oversold for long periods
- A single indicator — best combined with other signals for confirmation

---

## Choosing a Strategy

| If you want to... | Use |
|---|---|
| Follow the trend and catch big moves | Moving Average Crossover |
| Catch reversals and buy dips / sell rallies | RSI |
| Trade trending markets (stocks in momentum) | Moving Average Crossover with longer windows |
| Trade ranging markets (consolidating stocks) | RSI with standard thresholds |
| Get fewer but higher-confidence signals | Either strategy with wider parameters |
| Get more frequent signals | Either strategy with tighter parameters |

### Combining strategies (future feature)

In a future release, the framework will support running multiple strategies simultaneously and combining their signals through a composite scoring system. For example, a BUY signal from both SMA crossover and RSI would carry more weight than either signal alone.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Bar** | A single price candlestick (OHLCV: open, high, low, close, volume) for a time period. |
| **Crossover** | When one value (e.g., a fast SMA) moves from below to above another value (e.g., a slow SMA). |
| **Lookback** | How far back in time the framework fetches historical bars. Default is 5 days. |
| **Momentum** | The rate of price change — how fast the price is moving up or down. |
| **Overbought** | A condition where an asset's price has risen quickly and may be due for a pullback. |
| **Oversold** | A condition where an asset's price has fallen quickly and may be due for a bounce. |
| **Period** | The number of bars used in a calculation (e.g., 14-period RSI). |
| **SMA** | Simple Moving Average — the arithmetic mean of the last N closing prices. |
| **RSI** | Relative Strength Index — a momentum oscillator ranging from 0 to 100. |
| **Signal** | A BUY, SELL, or HOLD recommendation generated by a strategy. |
| **Wilder smoothing** | An exponential moving average method created by J. Welles Wilder Jr., giving more weight to recent data. |
