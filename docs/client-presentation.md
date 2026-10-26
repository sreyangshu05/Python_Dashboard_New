# WindScope UK — Client Presentation & Demonstration Deck

**UK Wind Forecast Review Dashboard**

*Audience: Electricity Procurement and Analytics Teams*
*Duration: 5–7 Minutes Pitch & Interactive Demonstration*

---

## Slide 1 — The Business Challenge

### Reviewing Wind Forecasts for Day-Ahead Analysis

* Wind generation is variable, and forecast error can be relevant to operational and commercial analysis.
* A retrospective comparison is useful only when its selection rule, data quality, and limitations are visible.
* WindScope provides a reproducible view of returned forecast publications and measured differences from realized generation. It does not estimate market exposure or recommend a procurement position.

---

## Slide 2 — Introducing WindScope UK

### "See the latest available wind forecast. Measure its accuracy. Make better-informed procurement decisions."

WindScope UK is a forecast-intelligence and decision-support web application for UK day-ahead power buyers.

### Core Capabilities
1. **Decision-Time Forecast Visibility:**
   * Selects the newest forecast revision returned by Elexon or captured in the local archive at or before the configured cutoff (default: 09:00 UTC on the preceding day).
   * Excludes known revisions published after that cutoff. Completeness of historical source records is not guaranteed.
2. **Quantitative Error Analytics:**
   * Calculates Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), and Mean Bias Error (MBE).
   * Summarizes errors and bias in the matched observations available for the selected period.

---

## Slide 3 — Product Demonstration (Live Walkthrough)

*Presenter Action: Start the local application using the README instructions, then open `http://localhost:8000`. This is a local address, not a public deployment URL.*

### Walkthrough Narrative:
1. **Global Header & Health Status:**
   * The dashboard requests Elexon BMRS `FUELHH` and `WINDFOR` data when loaded or refreshed.
   * Displays the active evaluation scope (**January 2026**) and the active day-ahead decision cutoff (**09:00 UTC**).
2. **Executive KPI Strip:**
   * **Latest Forecast vs Latest Realized Generation:** Shows the most recent matched observation in the selected response.
   * **MAE and RMSE:** Summarize absolute error for the matched observations in the selected period.
   * **Mean Bias Error (MBE):** Positive values indicate overforecasting on average; negative values indicate underforecasting.
3. **Interactive Forecast vs Actual Chart:**
   * Dual-trace visualization tracking national wind output in megawatts across January 2026.
   * Hover tooltips show the available target, forecast, actual, error, and publication details.
4. **Signed Error Over Time:**
   * Color-coded bars (amber for overforecasts, blue for underforecasts) relative to the zero-reference axis.
   * Displays signed error over time; it does not attribute errors to weather events or forecast causes.

---

## Slide 4 — Quantitative Accuracy & Error Formulations

### Transparent, Statistically Sound Energy Metrics

| Metric | Formulation | Unit | Procurement Desk Interpretation |
| :--- | :--- | :--- | :--- |
| **Signed Error** | $e_i = \text{Forecast}_i - \text{Actual}_i$ | MW | Positive = overforecast; negative = underforecast. |
| **MAE** | $\frac{1}{N}\sum \|e_i\|$ | MW | Mean absolute error over finite matched pairs. |
| **RMSE** | $\sqrt{\frac{1}{N}\sum e_i^2}$ | MW | Gives larger errors greater weight; not a direct balancing-risk measure. |
| **MBE (Bias)** | $\frac{1}{N}\sum e_i$ | MW | Summarizes average signed error across the matched pairs. |
| **MAPE** | $\frac{1}{N_{\text{nonzero}}}\sum \frac{\|e_i\|}{|\text{Actual}_i|} \times 100\%$ | % | Mean absolute percentage error; zero actuals are excluded from its denominator. |

---

## Slide 5 — Data Handling & Limitations

### What the dashboard does and does not establish

* **Strict Elexon Data Scope:** Consumes only official Elexon BMRS datasets: `FUELHH` (fuelType = "WIND") and `WINDFOR`. No unverified third-party scraping or black-box weather inputs.
* **Resolution Alignment:** Harmonizes 30-minute settlement actuals into 60-minute blocks matching the hourly forecast horizon.
* Missing forecasts and actuals are represented as unavailable; incomplete FUELHH hour pairs are not filled with zero.
* CSV export follows the active evaluation filters and uses UTC timestamps.
* SQLite retains successfully retrieved WINDFOR revisions from first capture onward; it cannot recover earlier revisions that were already absent from Elexon's response.
* Every evaluation still needs successful upstream Elexon requests. The archive is not a complete offline data source.

---

## Slide 6 — Appropriate Use

### A retrospective analytical aid, not a financial forecast

* Compare observed forecast error across the selected dates and available matched hours.
* Use bias and error summaries as inputs to further analysis, with suitable review and controls.
* Do not translate these metrics directly into reserve sizing, savings, cash-out cost, or procurement ROI. The dashboard does not include demand, contracts, market prices, or a validated cost model.

---

## Slide 7 — Strategic Roadmap & Next Steps

### Planned Enhancements for Version 2.0

1. **Intraday Gate-Closure Tracking:** Evaluating intraday forecast revisions published at 1–4 hours before gate closure to assist within-day rebalancing.
2. **Regional & DNO Disaggregation:** Ingesting offshore vs onshore and regional zonal wind breakdowns (subject to data availability).
3. **Probabilistic Uncertainty Bands:** Visualizing P10/P50/P90 percentile forecast ensembles.
4. **Demand & Net-Load Synthesis:** Pairing wind forecast intelligence with national electricity demand forecasts to project net-imbalance exposure.

---

## Presenter Script & Suggested Demonstration Flow (6 Minutes)

* **[0:00 - 1:00] Context:** "WindScope compares returned UK wind forecasts with later realized generation and makes the historical selection rule and data limitations visible."
* **[1:00 - 2:30] Overview:** "The dashboard requests January 2026 Elexon data and applies the configured prior-day 09:00 UTC cutoff. Interpret displayed metrics for the matched observations in the selected response."
* **[2:30 - 3:45] Forecast Explorer:** "Explore availability, dates, cutoff, and exported records. The selector excludes known post-cutoff revisions, but cannot prove that the source returned every historical revision."
* **[3:45 - 4:45] Accuracy Analytics:** "Review the error distribution and hourly summaries. These describe the observed data; they do not establish financial impact or causation."
* **[4:45 - 6:00] Conclusion:** "WindScope is an analytical aid for reviewing wind forecast performance, not a trading or cost-optimization system."
