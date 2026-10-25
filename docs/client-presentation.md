# WindScope UK — Client Presentation & Demonstration Deck

**UK Day-Ahead Wind Forecast Intelligence & Procurement Decision Support Platform**  
*Audience: Electricity Procurement Lead, Wholesale Trading Analyst, Risk Manager*  
*Duration: 5–7 Minutes Pitch & Interactive Demonstration*

---

## Slide 1 — The Business Challenge

### Balancing Renewable Variability in the Day-Ahead Wholesale Electricity Market

* **The Mandate:** The procurement desk must secure sufficient wholesale electricity volume day-ahead to meet consumer demand at lowest risk and lowest cost.
* **The Intermittent Reality:** While wind power provides zero-marginal-cost renewable energy, UK national wind output fluctuates by thousands of megawatts across hours.
* **The Core Dilemma:**
  1. *Under-procurement risk:* If wind generation falls short of expectations, the utility faces expensive System Buy Prices (cash-out penalties) or must dispatch peaking plants at volatile intraday prices.
  2. *Over-procurement risk:* If wind generates more than forecasted, the surplus energy may have to be spilled or sold back into the balancing mechanism at a loss (or even negative prices).
* **The Key Need:** Procurement decisions require transparent visibility into **what forecasts were actually published before the procurement window closed**, and a **quantitative understanding of historical forecast errors and systematic bias**.

---

## Slide 2 — Introducing WindScope UK

### "See the latest available wind forecast. Measure its accuracy. Make better-informed procurement decisions."

WindScope UK is an enterprise-grade forecast intelligence and decision-support web application tailored for UK day-ahead power buyers.

### Dual Core Capabilities:
1. **Decision-Time Forecast Visibility:** 
   * Reconstructs the exact forecast state available to the analyst at any specified historical procurement cutoff (e.g., 09:00 UTC day-ahead).
   * Guaranteed zero future information leakage: strictly quarantines revisions broadcast after the decision cutoff.
2. **Quantitative Accuracy & Uncertainty Analytics:**
   * Calculates Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), and Mean Bias Error (MBE).
   * Uncovers systematic over- or under-forecasting tendencies and diurnal patterns across settlement periods.

---

## Slide 3 — Product Demonstration (Live Walkthrough)

*Presenter Action: Switch to browser view at `http://localhost:8000` (or deployed URL)*

### Walkthrough Narrative:
1. **Global Header & Health Status:**
   * Notice the live data connector badge: directly connected to Elexon BMRS streaming endpoints (`FUELHH` and `WINDFOR`).
   * Displays the active evaluation scope (**January 2026**) and the active day-ahead decision cutoff (**09:00 UTC**).
2. **Executive KPI Strip:**
   * **Latest Forecast vs Latest Realized Generation:** Instant insight into the most recent matched settlement period.
   * **Monthly MAE:** Highlights the average magnitude of volumetric forecast discrepancy across the portfolio.
   * **Monthly RMSE:** Highlights the dispersion penalty for extreme forecast misses.
   * **Mean Bias Error (MBE):** Instantly alerts the procurement desk whether the national model had a structural tendency to over- or under-predict wind.
3. **Interactive Forecast vs Actual Chart:**
   * Dual-trace visualization tracking national wind output in megawatts across January 2026.
   * Hover tooltips display the target settlement hour, forecasted MW, actual realized MW, forecast error, and the exact publication timestamp.
4. **Signed Error Over Time:**
   * Color-coded bars (amber for overforecasts, blue for underforecasts) relative to the zero-reference axis.
   * Demonstrates whether errors were sustained multi-day weather front mispredictions or isolated ramp errors.

---

## Slide 4 — Quantitative Accuracy & Error Formulations

### Transparent, Statistically Sound Energy Metrics

| Metric | Formulation | Unit | Procurement Desk Interpretation |
| :--- | :--- | :--- | :--- |
| **Signed Error** | $e_i = \text{Forecast}_i - \text{Actual}_i$ | MW | Positive = Overforecast (surplus); Negative = Underforecast (deficit risk). |
| **MAE** | $\frac{1}{N}\sum \|e_i\|$ | MW | Mean volumetric discrepancy magnitude. Essential for sizing reserve margin. |
| **RMSE** | $\sqrt{\frac{1}{N}\sum e_i^2}$ | MW | Heavily penalizes large swings. Reflects extreme physical balancing risk. |
| **MBE (Bias)** | $\frac{1}{N}\sum e_i$ | MW | Detects structural model optimism or conservatism. |
| **MAPE** | $\frac{1}{N_{\text{nonzero}}}\sum \frac{\|e_i\|}{\text{Actual}_i} \times 100\%$ | % | Normalized relative error. **Zero-actual hours strictly isolated** to prevent division-by-zero distortion. |

---

## Slide 5 — Trust, Provenance & Data Governance

### Why Procurement Leads Can Trust WindScope UK

* **Strict Elexon Data Scope:** Consumes only official Elexon BMRS datasets: `FUELHH` (fuelType = "WIND") and `WINDFOR`. No unverified third-party scraping or black-box weather inputs.
* **Resolution Alignment:** Harmonizes 30-minute settlement actuals into 60-minute blocks matching the hourly forecast horizon.
* **Auditability & Provenance Panel:**
  * Tracks total records ingested, duplicate actuals removed, and exact timestamp boundaries.
  * Explicitly counts and logs how many forecasts were excluded because they arrived after the procurement cutoff.
* **Zero Fabrication Guarantee:** Missing forecasts or actuals are represented explicitly as unavailable — never silently filled with zeros or synthetic estimates.
* **One-Click Audit Export:** Full dataset exportable to CSV with verified UTC timestamps for regulatory compliance and quantitative modeling.

---

## Slide 6 — Business Value & Procurement ROI

### Turning Forecast Intelligence into Commercial Advantage

* **Calibrated Day-Ahead Sizing:** Sizing day-ahead bilateral purchases against wind forecasts adjusted for known historical bias (MBE) prevents costly systematic imbalance.
* **Stress-Tested Buffer Margins:** Using empirical RMSE and MAE distributions to establish dynamic risk buffers rather than arbitrary rule-of-thumb safety margins.
* **Ramp & Peak Hour Protection:** The Diurnal Pattern chart reveals whether errors spike during morning demand ramps (07:00–09:00) or evening peaks (17:00–19:00).
* **Defensible Stakeholder Reporting:** Clear, unmanipulated metrics for executive risk committees and regulatory audits.
* *Governance Note:* WindScope UK is a forecast decision-support platform, not an algorithmic trading engine. Forecast errors do not directly equal cash-out imbalance costs.

---

## Slide 7 — Strategic Roadmap & Next Steps

### Planned Enhancements for Version 2.0

1. **Intraday Gate-Closure Tracking:** Evaluating intraday forecast revisions published at 1–4 hours before gate closure to assist within-day rebalancing.
2. **Regional & DNO Disaggregation:** Ingesting offshore vs onshore and regional zonal wind breakdowns (subject to data availability).
3. **Probabilistic Uncertainty Bands:** Visualizing P10/P50/P90 percentile forecast ensembles.
4. **Demand & Net-Load Synthesis:** Pairing wind forecast intelligence with national electricity demand forecasts to project net-imbalance exposure.

---

## Presenter Script & Suggested Demonstration Flow (6 Minutes)

* **[0:00 - 1:00] Intro & Problem Statement:** "Good morning. When procurement teams commit millions of pounds in the day-ahead power market, their exposure hinges on renewable forecasts. If wind underperforms, cash-out penalties bite. If wind overperforms, surplus power is dumped. WindScope UK answers two vital questions: What forecast was actually on your screen when you made the call, and how accurate was it?"
* **[1:00 - 2:30] Live Demo - Overview:** "Looking at January 2026 on our live dashboard, our system connects directly to Elexon BMRS. At our default 09:00 UTC day-ahead cutoff, we observe a monthly MAE of X MW, and our MBE shows whether the national forecast was structurally optimistic or conservative. On the main chart, you can clearly see the hourly forecast vs actual realization."
* **[2:30 - 3:45] Forecast Explorer & Cutoff Testing:** "Let's switch to the Forecast Explorer. If our trading policy shifted cutoff from 09:00 to 11:00 UTC, we can immediately re-evaluate the historical backtest. Notice the availability status badges: we never leak future revisions into past decisions."
* **[3:45 - 4:45] Accuracy Analytics & Diurnal Patterns:** "In the Accuracy Analysis tab, we see the error distribution histogram and the hourly diurnal pattern, revealing whether error spikes align with national peak demand hours."
* **[4:45 - 6:00] Conclusion & Q&A:** "WindScope UK provides defensible, audited, and mathematically sound forecast intelligence. We welcome your questions."
