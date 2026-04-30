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

## 3. Breakout (Channel)

**Config name:** `breakout`

### What it is

A momentum strategy that detects when price breaks out of a recent trading range (channel). The channel is defined by the highest high and lowest low over a lookback window. An optional volume filter ensures breakouts are backed by conviction.

### How it works

1. Look at the previous N bars (the lookback window).
2. Find the **highest high** and **lowest low** in that window.
3. Compare the current bar's close to the channel:
   - Close above the channel high = potential upward breakout
   - Close below the channel low = potential downward breakout
4. If volume confirmation is enabled, check that current volume >= `volume_factor * average_volume`.

### Signals

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **BUY** | Close > channel high AND volume confirmed | Price broke above resistance with conviction. |
| **SELL** | Close < channel low AND volume confirmed | Price broke below support with conviction. |
| **HOLD** | Price within channel, or breakout without sufficient volume | No breakout or not confirmed. |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `lookback` | 20 | Number of previous bars to define the channel. |
| `volume_factor` | 1.5 | Current volume must be >= this multiple of average volume. Set to 0 to disable volume confirmation. |

### Recommended ranges

- **Tight channel (more signals):** lookback 10, volume_factor 1.0
- **Standard:** lookback 20, volume_factor 1.5
- **Wide channel (fewer, stronger signals):** lookback 50, volume_factor 2.0
- **No volume filter (for low-volume assets):** volume_factor 0

### When to use

- Range-bound markets that eventually break out (consolidation patterns).
- Stocks approaching key support/resistance levels.
- Pairs well with volume — breakouts without volume often fail (false breakouts).

### Strengths and limitations

**Strengths:**
- Catches the start of big moves early
- Volume confirmation reduces false signals
- Simple, intuitive logic

**Limitations:**
- False breakouts are common, especially in choppy markets
- Doesn't indicate trend direction before the breakout
- No profit target or stop-loss built in

---

## 4. MACD (Moving Average Convergence Divergence)

**Config name:** `macd`

### What it is

A trend-following momentum indicator that shows the relationship between two Exponential Moving Averages (EMAs). It's one of the most widely used indicators in technical analysis, combining trend detection with momentum measurement.

### How it works

1. **Fast EMA** (default 12-period): Short-term exponential moving average of closing prices.
2. **Slow EMA** (default 26-period): Long-term exponential moving average of closing prices.
3. **MACD Line** = Fast EMA - Slow EMA. When positive, short-term momentum is above long-term; when negative, it's below.
4. **Signal Line** (default 9-period): An EMA of the MACD line itself — smooths the MACD to reduce noise.
5. **Histogram** = MACD Line - Signal Line. Shows the gap between MACD and its signal.

Unlike SMA, EMA gives more weight to recent prices: `EMA = close * multiplier + previous_EMA * (1 - multiplier)` where `multiplier = 2 / (period + 1)`.

### Signals

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **BUY** | MACD line crosses above signal line | Bullish momentum is accelerating — short-term trend is turning up faster than the signal. |
| **SELL** | MACD line crosses below signal line | Bearish momentum is accelerating — short-term trend is turning down. |
| **HOLD** | No crossover | Current momentum hasn't changed direction. |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast_period` | 12 | Fast EMA period. Smaller = more responsive. |
| `slow_period` | 26 | Slow EMA period. Larger = smoother trend. |
| `signal_period` | 9 | Signal line EMA period. Smooths the MACD line. |

### Recommended ranges

- **Standard (Gerald Appel's original):** 12, 26, 9
- **Faster (shorter-term trading):** 8, 17, 9
- **Slower (longer-term, fewer signals):** 19, 39, 9
- **Crypto (volatile markets):** 12, 26, 9 on 4h or daily bars

### When to use

- Trending markets where you want to catch momentum shifts.
- As confirmation alongside other strategies (e.g., MACD confirms RSI signal).
- Works well on longer timeframes (1h, 4h, daily) — noisy on very short timeframes.

### Example

With defaults (12, 26, 9) on daily bars:

```
Days 1-26:  Price trending up from $100 to $130
Day 27:     Fast EMA = $128, Slow EMA = $120, MACD = +8
            Signal line = +6
            MACD above signal -> bullish
Day 35:     Price reverses, drops to $118
            Fast EMA = $120, Slow EMA = $122, MACD = -2
            Signal line = +1
            MACD crossed below signal
            -> SELL signal
```

### Strengths and limitations

**Strengths:**
- Combines trend and momentum in one indicator
- Signal line crossovers are clear, objective entry/exit points
- Histogram shows momentum acceleration/deceleration visually
- Very widely used — well-understood behavior

**Limitations:**
- Lagging indicator (based on moving averages, signals come after moves start)
- Can give false signals in choppy/sideways markets
- Default parameters may not suit all timeframes or asset classes

---

## 5. Goslin Three-Line Momentum

**Config name:** `goslin_momentum`

### What it is

A three-line momentum system from Chick Goslin's "Intelligent Futures Trading." It combines a long-term trend indicator with a short-term timing oscillator and an intermediate-term confirming filter. Signals only fire when all three lines agree — this makes it selective but high-conviction.

### The Three Lines

**Direction Line** (49-day SMA): The overall trend. Price above the direction line = uptrend, below = downtrend. Think of it as a compass — you only trade in the direction it points.

**Timing Line** (3-day SMA minus 10-day SMA): A short-term momentum oscillator. It swings above and below zero. When it crosses from negative to positive, short-term momentum has turned bullish. When it crosses from positive to negative, momentum has turned bearish. This is your entry trigger.

**Confirming Line** (15-day SMA of the timing line): Smooths out the timing line to show the intermediate-term trend of momentum. Acts as a filter — it must support the trade direction for a signal to fire.

### Signals

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **BUY** | Price above direction line + timing line crosses above zero + confirming line is bullish | All three timeframes align bullish — high-conviction long entry. |
| **SELL** | Price below direction line + timing line crosses below zero + confirming line is bearish | All three timeframes align bearish — high-conviction short entry. |
| **HOLD** | Any line disagrees | Not enough alignment — wait for all three to agree. |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `direction_period` | 49 | SMA period for the direction/trend line (Goslin's ten-week average). |
| `timing_short` | 3 | Short SMA period for the timing oscillator. |
| `timing_long` | 10 | Long SMA period for the timing oscillator. |
| `confirming_period` | 15 | SMA period for smoothing the timing line into the confirming line. |

### Recommended ranges

- **Goslin's original**: 49, 3, 10, 15 (designed for daily futures charts)
- **Faster (stocks/crypto)**: 35, 3, 8, 12
- **Slower (weekly charts)**: 49, 5, 15, 20

### When to use

- Markets with clear trending behavior — the direction line keeps you on the right side
- When you want **fewer but higher-quality signals** (all three lines must agree)
- Futures, commodities, forex, and trending stocks — originally designed for futures
- Best on daily bars (the original system used daily data)

### Example

With defaults (49, 3, 10, 15) on daily bars:

```
Days 1-49:  AAPL trends upward from $150 to $180
Day 50:     Direction Line (49-day SMA) = $165
            Price ($180) is ABOVE direction line → trend is UP
            Recent dip: price dropped to $172 then bounced to $180
            Timing Line crosses from -0.5 to +1.2 (turned positive)
            Confirming Line = +0.8 (bullish)
            All three lines agree → BUY signal
```

### Strengths and limitations

**Strengths:**
- Three-layer confirmation reduces false signals significantly
- Direction line keeps you trading with the trend
- Timing line provides precise entry points
- Confirming line filters out weak setups
- Based on 25+ years of Goslin's real trading experience

**Limitations:**
- Very selective — may generate few signals in quiet markets
- Requires ~65 bars of history before it can generate the first signal
- Designed for futures/daily data — may need parameter adjustment for intraday
- All three lines must agree, so you'll miss some valid moves where only two agree

---

## Choosing a Strategy

| If you want to... | Use |
|---|---|
| Follow the trend and catch big moves | Moving Average Crossover or MACD |
| Catch reversals and buy dips / sell rallies | RSI |
| Catch breakouts from consolidation | Breakout |
| Trade trending markets (stocks in momentum) | MACD or Moving Average Crossover with longer windows |
| Trade ranging markets (consolidating stocks) | RSI with standard thresholds |
| Combine trend + momentum | MACD (built-in) or SMA + RSI together |
| High-conviction, selective signals | Goslin Momentum (three-line confirmation) |
| Trade futures or commodities | Goslin Momentum (designed for futures) |
| Get fewer but higher-confidence signals | Any strategy with wider parameters, or Goslin |
| Volume-confirmed entries | Breakout with volume_factor > 0 |

### Combining strategies

The framework supports running multiple strategies simultaneously. Enter `1,2,3,4` at the strategy prompt to run all four. Each strategy evaluates independently, so you'll see signals from each one — useful for confirmation (e.g., both MACD and RSI agree on BUY).

---

## Glossary

| Term | Definition |
|------|-----------|
| **Bar** | A single price candlestick (OHLCV: open, high, low, close, volume) for a time period. |
| **Breakout** | When price moves above resistance (channel high) or below support (channel low). |
| **Channel** | The range between the highest high and lowest low over a lookback period. |
| **Confirming Line** | In Goslin's system, an SMA of the timing line values that filters and qualifies trade signals. |
| **Crossover** | When one value (e.g., a fast SMA) moves from below to above another value (e.g., a slow SMA). |
| **Direction Line** | In Goslin's system, a long-term SMA (49-day) that determines the overall market trend. |
| **EMA** | Exponential Moving Average — a weighted average giving more importance to recent prices. |
| **Histogram** | The difference between the MACD line and its signal line, showing momentum strength. |
| **Lookback** | How far back in time the framework fetches historical bars. |
| **MACD** | Moving Average Convergence Divergence — the difference between fast and slow EMAs. |
| **Momentum** | The rate of price change — how fast the price is moving up or down. |
| **Overbought** | A condition where an asset's price has risen quickly and may be due for a pullback. |
| **Oversold** | A condition where an asset's price has fallen quickly and may be due for a bounce. |
| **Period** | The number of bars used in a calculation (e.g., 14-period RSI). |
| **RSI** | Relative Strength Index — a momentum oscillator ranging from 0 to 100. |
| **Signal line** | An EMA of the MACD line, used to generate buy/sell signals on crossover. |
| **Timing Line** | In Goslin's system, a short-term momentum oscillator (difference of two SMAs) used for trade entry timing. |
| **Three-Point System** | Goslin's method requiring all three lines (direction, timing, confirming) to agree before trading. |
| **SMA** | Simple Moving Average — the arithmetic mean of the last N closing prices. |
| **Signal** | A BUY, SELL, or HOLD recommendation generated by a strategy. |
| **Volume confirmation** | Requiring above-average volume to validate a price move (reduces false signals). |
| **Wilder smoothing** | An exponential moving average method created by J. Welles Wilder Jr., giving more weight to recent data. |
