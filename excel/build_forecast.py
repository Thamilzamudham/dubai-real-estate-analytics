"""
Builds Dubai_Sales_Forecast.xlsx  -  seasonal decomposition + linear trend forecast,
entirely with live Excel formulas (no Python-computed results are pasted in).

Method (classical multiplicative decomposition):
  1. Centered 12-month moving average (2x12 MA)  ->  trend-cycle estimate
  2. Ratio = Actual / CMA                         ->  seasonal ratios
  3. Average ratio per calendar month, normalised ->  seasonal index (mean = 1)
  4. Deseasonalised = Actual / Seasonal index
  5. Linear trend (SLOPE/INTERCEPT) on the last 36 deseasonalised months
  6. Forecast = Trend x Seasonal index, +/- z * residual SD band
  7. Backtest: refit using data only up to 12 months before the end, compare to a naive benchmark
"""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).parent
df = pd.read_csv(HERE.parent / "data" / "monthly_sales.csv", parse_dates=["month"])
n = len(df)                       # 106 months
FIRST, LAST = 2, n + 1            # data rows 2..107
FC_FIRST, FC_LAST = LAST + 1, LAST + 12   # forecast rows 108..119
WIN = 36
FIN_WIN = (LAST - WIN + 1, LAST)          # final trend window rows
BT_END = LAST - 12                        # backtest train end row
BT_WIN = (BT_END - WIN + 1, BT_END)

F = "Arial"
f_norm = Font(name=F, size=10)
f_bold = Font(name=F, size=10, bold=True)
f_in = Font(name=F, size=10, color="0000FF")
f_hdr = Font(name=F, size=10, bold=True, color="FFFFFF")
f_title = Font(name=F, size=14, bold=True, color="1F3864")
f_note = Font(name=F, size=9, italic=True, color="595959")
fill_hdr = PatternFill("solid", fgColor="1F3864")
fill_key = PatternFill("solid", fgColor="FFF2CC")
fill_fc = PatternFill("solid", fgColor="E2EFDA")
thin = Side(style="thin", color="BFBFBF")
box = Border(top=thin, bottom=thin, left=thin, right=thin)

wb = Workbook()


def header(ws, row, labels, widths=None):
    for i, t in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=t)
        c.font, c.fill, c.border = f_hdr, fill_hdr, box
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 32
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def style_range(ws, rng, font=f_norm, fmt=None, fill=None):
    for row in ws[rng]:
        for c in row:
            c.font = font
            if fmt:
                c.number_format = fmt
            if fill:
                c.fill = fill


# ------------------------------------------------------------------ Summary (first tab)
ws_s = wb.active
ws_s.title = "Summary"

# ------------------------------------------------------------------ Assumptions
ws_a = wb.create_sheet("Assumptions")
ws_a["A1"], ws_a["A1"].font = "Assumptions & Model Parameters", f_title
ws_a["A2"], ws_a["A2"].font = "Blue = input you can change. Black = formula. Parameters are computed from the Model sheet.", f_note
header(ws_a, 4, ["Item", "Value", "Notes"], [44, 16, 80])
rows_a = [
    ("Confidence multiplier (z)", 1.96, "Input. 1.96 ~ 95% band assuming roughly normal residuals."),
    ("Last actual month", f"=MAX(Data!A{FIRST}:A{LAST})", "Latest month in the Data sheet."),
    ("Backtest train-end month", "=EDATE(B6,-12)", "Backtest trains up to here, then predicts the final 12 months."),
    ("Backtest seasonal-ratio cutoff", "=EDATE(B7,-6)", "Seasonal ratios need 6 months of future data (centered MA), so use ratios up to this date only."),
    ("Trend window (months)", WIN, "Fixed at 36 inside SLOPE/INTERCEPT ranges (Model!F/M). Edit those ranges if you append data."),
    ("FINAL: trend slope (per month)", f"=SLOPE(Model!F{FIN_WIN[0]}:F{FIN_WIN[1]},Model!B{FIN_WIN[0]}:B{FIN_WIN[1]})", "AED bn added per month, on deseasonalised data."),
    ("FINAL: trend intercept", f"=INTERCEPT(Model!F{FIN_WIN[0]}:F{FIN_WIN[1]},Model!B{FIN_WIN[0]}:B{FIN_WIN[1]})", ""),
    ("BACKTEST: trend slope (per month)", f"=SLOPE(Model!M{BT_WIN[0]}:M{BT_WIN[1]},Model!B{BT_WIN[0]}:B{BT_WIN[1]})", "Fitted using training data only."),
    ("BACKTEST: trend intercept", f"=INTERCEPT(Model!M{BT_WIN[0]}:M{BT_WIN[1]},Model!B{BT_WIN[0]}:B{BT_WIN[1]})", ""),
    ("Residual SD (% of fitted, last 36m)", f"=STDEV(Model!N{FIN_WIN[0]}:N{FIN_WIN[1]})", "Drives the forecast band width. Band is constant over the horizon (simplification)."),
]
for i, (k, v, note) in enumerate(rows_a, start=5):
    ws_a.cell(row=i, column=1, value=k).font = f_norm
    c = ws_a.cell(row=i, column=2, value=v)
    c.font = f_in if i in (5, 9) else f_norm
    ws_a.cell(row=i, column=3, value=note).font = f_note
    for col in (1, 2, 3):
        ws_a.cell(row=i, column=col).border = box
ws_a["B5"].fill = fill_key
ws_a["B5"].number_format = "0.00"
for r in (6, 7, 8):
    ws_a[f"B{r}"].number_format = "mmm-yyyy"
ws_a["B9"].number_format = "0"
for r in (10, 11, 12, 13):
    ws_a[f"B{r}"].number_format = "0.0000"
ws_a["B14"].number_format = "0.0%"
ws_a["A16"], ws_a["A16"].font = "Data note", f_bold
ws_a["A17"], ws_a["A17"].font = ("Data is SYNTHETIC (see README). Replace the Data sheet with real DLD / Dubai Pulse monthly figures; "
                                 "everything else recalculates."), f_note
SL_F, IC_F, SL_B, IC_B, SD, Z = "Assumptions!$B$10", "Assumptions!$B$11", "Assumptions!$B$12", "Assumptions!$B$13", "Assumptions!$B$14", "Assumptions!$B$5"

# ------------------------------------------------------------------ Data
ws_d = wb.create_sheet("Data")
header(ws_d, 1, ["Month", "Sales value (AED bn)", "Transactions", "Avg price (AED/sqft)", "t", "Month #",
                 "Centered 12m MA", "Ratio (Actual / CMA)"], [12, 16, 14, 16, 6, 9, 16, 16])
for i, row in enumerate(df.itertuples(index=False), start=FIRST):
    ws_d.cell(row=i, column=1, value=row.month.to_pydatetime()).number_format = "mmm-yy"
    ws_d.cell(row=i, column=2, value=float(row.sales_value_aed_bn)).number_format = "0.00"
    ws_d.cell(row=i, column=3, value=int(row.transactions)).number_format = "#,##0"
    ws_d.cell(row=i, column=4, value=int(row.avg_price_psf_aed)).number_format = "#,##0"
    ws_d.cell(row=i, column=5, value=f"=ROW()-1")
    ws_d.cell(row=i, column=6, value=f"=MONTH(A{i})")
    if i >= FIRST + 6 and i <= LAST - 6:
        ws_d.cell(row=i, column=7, value=f"=(SUM(B{i-5}:B{i+5})+0.5*(B{i-6}+B{i+6}))/12").number_format = "0.00"
        ws_d.cell(row=i, column=8, value=f"=B{i}/G{i}").number_format = "0.000"
    for col in range(1, 9):
        c = ws_d.cell(row=i, column=col)
        c.font = f_in if col in (1, 2, 3, 4) else f_norm
ws_d.freeze_panes = "B2"

# ------------------------------------------------------------------ Seasonality
ws_se = wb.create_sheet("Seasonality")
ws_se["A1"], ws_se["A1"].font = "Seasonal Index by Calendar Month", f_title
header(ws_se, 3, ["Month #", "Month", "Avg ratio (final)", "Seasonal index (final)",
                  "Avg ratio (backtest)", "Seasonal index (backtest)"], [10, 10, 16, 18, 18, 20])
names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
S0, S1 = 4, 15
for m in range(1, 13):
    r = S0 + m - 1
    ws_se.cell(row=r, column=1, value=m)
    ws_se.cell(row=r, column=2, value=names[m - 1])
    ws_se.cell(row=r, column=3, value=f"=AVERAGEIFS(Data!$H${FIRST}:$H${LAST},Data!$F${FIRST}:$F${LAST},A{r})")
    ws_se.cell(row=r, column=4, value=f"=C{r}/AVERAGE($C${S0}:$C${S1})")
    ws_se.cell(row=r, column=5, value=(f"=AVERAGEIFS(Data!$H${FIRST}:$H${LAST},Data!$F${FIRST}:$F${LAST},A{r},"
                                      f"Data!$A${FIRST}:$A${LAST},\"<=\"&Assumptions!$B$8)"))
    ws_se.cell(row=r, column=6, value=f"=E{r}/AVERAGE($E${S0}:$E${S1})")
style_range(ws_se, f"A{S0}:F{S1}", f_norm)
style_range(ws_se, f"C{S0}:F{S1}", f_norm, "0.000")
ws_se[f"A{S1+2}"], ws_se[f"A{S1+2}"].font = "Index > 1.00 means the month is seasonally stronger than the yearly average.", f_note
bar = BarChart()
bar.title, bar.y_axis.title, bar.height, bar.width = "Seasonal index (final model)", "Index", 8, 16
bar.add_data(Reference(ws_se, min_col=4, min_row=3, max_row=S1), titles_from_data=True)
bar.set_categories(Reference(ws_se, min_col=2, min_row=S0, max_row=S1))
bar.legend = None
bar.x_axis.delete = False
bar.y_axis.delete = False
bar.y_axis.scaling.min = 0.6
ws_se.add_chart(bar, "H3")

# ------------------------------------------------------------------ Model
ws_m = wb.create_sheet("Model")
header(ws_m, 1, ["Month", "t", "Month #", "Actual (AED bn)", "Seasonal idx (final)", "Deseasonalised",
                 "Trend line", "Fitted (36m window)", "FORECAST", "Lower band", "Upper band",
                 "Seasonal idx (backtest)", "Deseasonalised (backtest)", "% error (Actual/Fitted-1)"],
       [11, 6, 8, 14, 14, 15, 11, 14, 12, 12, 12, 15, 17, 16])
for r in range(FIRST, FC_LAST + 1):
    hist = r <= LAST
    if hist:
        ws_m.cell(row=r, column=1, value=f"=Data!A{r}")
        ws_m.cell(row=r, column=4, value=f"=Data!B{r}")
    else:
        ws_m.cell(row=r, column=1, value=f"=EDATE(A{r-1},1)")
    ws_m.cell(row=r, column=2, value=f"=ROW()-1")
    ws_m.cell(row=r, column=3, value=f"=MONTH(A{r})")
    ws_m.cell(row=r, column=5, value=f"=INDEX(Seasonality!$D${S0}:$D${S1},C{r})")
    if r >= FIN_WIN[0]:       # trend/fitted only where the trend was actually fitted (+ forecast)
        ws_m.cell(row=r, column=7, value=f"={IC_F}+{SL_F}*B{r}")
    if hist:
        ws_m.cell(row=r, column=6, value=f"=D{r}/E{r}")
        if r >= FIN_WIN[0]:
            ws_m.cell(row=r, column=8, value=f"=G{r}*E{r}")
        ws_m.cell(row=r, column=12, value=f"=INDEX(Seasonality!$F${S0}:$F${S1},C{r})")
        ws_m.cell(row=r, column=13, value=f"=D{r}/L{r}")
        if r >= FIN_WIN[0]:
            ws_m.cell(row=r, column=14, value=f"=D{r}/H{r}-1")
    else:
        ws_m.cell(row=r, column=9, value=f"=G{r}*E{r}")
        ws_m.cell(row=r, column=10, value=f"=I{r}*(1-{Z}*{SD})")
        ws_m.cell(row=r, column=11, value=f"=I{r}*(1+{Z}*{SD})")
    fmts = {1: "mmm-yy", 4: "0.00", 5: "0.000", 6: "0.00", 7: "0.00", 8: "0.00", 9: "0.00",
            10: "0.00", 11: "0.00", 12: "0.000", 13: "0.00", 14: "0.0%"}
    for col in range(1, 15):
        c = ws_m.cell(row=r, column=col)
        c.font = f_norm
        if col in fmts:
            c.number_format = fmts[col]
        if not hist:
            c.fill = fill_fc
ws_m.freeze_panes = "B2"

# ------------------------------------------------------------------ Backtest
ws_b = wb.create_sheet("Backtest")
ws_b["A1"], ws_b["A1"].font = "Backtest - train on data up to 12 months ago, predict the last 12", f_title
ws_b["A2"], ws_b["A2"].font = "Benchmark = 'naive seasonal': same month last year. The model should beat it to be worth using.", f_note
header(ws_b, 4, ["Month", "Actual", "Seasonal idx", "Trend", "Model forecast", "Error (Act-Fcst)",
                 "Abs % error", "Naive (same month LY)", "Naive abs % error", "Signed % error"],
       [11, 11, 12, 11, 14, 15, 12, 18, 16, 14])
B0 = 5
for k in range(12):
    r = B0 + k
    mr = BT_END + 1 + k           # model row for the test month
    ws_b.cell(row=r, column=1, value=f"=Model!A{mr}").number_format = "mmm-yy"
    ws_b.cell(row=r, column=2, value=f"=Model!D{mr}")
    ws_b.cell(row=r, column=3, value=f"=Model!L{mr}")
    ws_b.cell(row=r, column=4, value=f"={IC_B}+{SL_B}*Model!B{mr}")
    ws_b.cell(row=r, column=5, value=f"=D{r}*C{r}")
    ws_b.cell(row=r, column=6, value=f"=B{r}-E{r}")
    ws_b.cell(row=r, column=7, value=f"=ABS(F{r})/B{r}")
    ws_b.cell(row=r, column=8, value=f"=Model!D{mr-12}")
    ws_b.cell(row=r, column=9, value=f"=ABS(B{r}-H{r})/B{r}")
    ws_b.cell(row=r, column=10, value=f"=F{r}/B{r}")
    for col in range(1, 11):
        c = ws_b.cell(row=r, column=col)
        c.font = f_norm
        c.border = box
        c.number_format = {1: "mmm-yy", 3: "0.000", 7: "0.0%", 9: "0.0%", 10: "0.0%"}.get(col, "0.00")
B1 = B0 + 11
ws_b[f"A{B1+2}"], ws_b[f"A{B1+2}"].font = "Results", f_bold
res = [
    ("Model MAPE", f"=AVERAGE(G{B0}:G{B1})", "0.0%"),
    ("Naive-seasonal MAPE", f"=AVERAGE(I{B0}:I{B1})", "0.0%"),
    ("Model bias (+ = under-forecast)", f"=AVERAGE(J{B0}:J{B1})", "0.0%"),
    ("Verdict", f'=IF(B{B1+3}<B{B1+4},"Model beats naive benchmark","Naive benchmark is better - revisit model")', "General"),
]
for i, (k, fm, nf) in enumerate(res, start=B1 + 3):
    ws_b.cell(row=i, column=1, value=k).font = f_norm
    c = ws_b.cell(row=i, column=2, value=fm)
    c.font, c.number_format = f_bold, nf
    c.fill = fill_key
MAPE_M, MAPE_N, BIAS = f"Backtest!$B${B1+3}", f"Backtest!$B${B1+4}", f"Backtest!$B${B1+5}"
VERDICT = f"Backtest!$B${B1+6}"
ws_b.column_dimensions["A"].width = 30

# ------------------------------------------------------------------ Summary content
ws_s["A1"], ws_s["A1"].font = "Dubai Real Estate Sales - 12-Month Forecast", f_title
ws_s["A2"], ws_s["A2"].font = ("Seasonal decomposition + linear trend, built with live Excel formulas. "
                               "Data is synthetic (see README)."), f_note
header(ws_s, 4, ["Key metric", "Value"], [46, 18])
kp = [
    ("Last 12 months actual (AED bn)", f"=SUM(Model!D{LAST-11}:D{LAST})", "#,##0.0"),
    ("Next 12 months forecast (AED bn)", f"=SUM(Model!I{FC_FIRST}:I{FC_LAST})", "#,##0.0"),
    ("Forecast growth vs last 12 months", "=B6/B5-1", "0.0%"),
    ("Strongest forecast month", f"=INDEX(Model!A{FC_FIRST}:A{FC_LAST},MATCH(MAX(Model!I{FC_FIRST}:I{FC_LAST}),Model!I{FC_FIRST}:I{FC_LAST},0))", "mmm-yy"),
    ("Weakest forecast month", f"=INDEX(Model!A{FC_FIRST}:A{FC_LAST},MATCH(MIN(Model!I{FC_FIRST}:I{FC_LAST}),Model!I{FC_FIRST}:I{FC_LAST},0))", "mmm-yy"),
    ("Backtest MAPE (model)", f"={MAPE_M}", "0.0%"),
    ("Backtest MAPE (naive benchmark)", f"={MAPE_N}", "0.0%"),
    ("Backtest verdict", f"={VERDICT}", "General"),
    ("Backtest bias (+ = under-forecast)", f"={BIAS}", "0.0%"),
    ("Bias-adjusted next-12m forecast (AED bn)", "=B6/(1-B13)", "#,##0.0"),
    ("Bias-adjusted growth vs last 12 months", "=B14/B5-1", "0.0%"),
]
for i, (k, fm, nf) in enumerate(kp, start=5):
    ws_s.cell(row=i, column=1, value=k).font = f_norm
    c = ws_s.cell(row=i, column=2, value=fm)
    c.font, c.number_format, c.alignment = f_bold, nf, Alignment(horizontal="right")
    for col in (1, 2):
        ws_s.cell(row=i, column=col).border = box
ws_s.column_dimensions["B"].width = 38

ws_s["A17"], ws_s["A17"].font = "How to read this workbook", f_bold
guide = ["Data -> raw monthly series + centered moving average + seasonal ratios",
         "Seasonality -> seasonal index per calendar month (final and backtest versions)",
         "Assumptions -> inputs (z-value) and trend parameters computed from the data",
         "Model -> deseasonalised series, trend, fitted values, 12-month forecast and bands",
         "Backtest -> honest out-of-sample test vs naive same-month-last-year benchmark"]
for i, t in enumerate(guide, start=18):
    ws_s.cell(row=i, column=1, value=t).font = f_norm

ch = LineChart()
ch.title, ch.height, ch.width = "Monthly sales value: actual, fitted and forecast (AED bn)", 10, 26
ch.y_axis.title = "AED bn"
for col, name in ((4, "Actual"), (8, "Fitted"), (9, "Forecast"), (10, "Lower band"), (11, "Upper band")):
    ch.add_data(Reference(ws_m, min_col=col, min_row=1, max_row=FC_LAST), titles_from_data=True)
ch.set_categories(Reference(ws_m, min_col=1, min_row=2, max_row=FC_LAST))
ch.x_axis.number_format = "mmm-yy"
ch.x_axis.tickLblSkip = 6
ch.x_axis.delete = False
ch.y_axis.delete = False
for s in ch.series:
    s.smooth = False
    s.marker.symbol = "none"
ch.series[0].graphicalProperties.line.solidFill = "1F3864"
ch.series[1].graphicalProperties.line.solidFill = "A6A6A6"
ch.series[2].graphicalProperties.line.solidFill = "C00000"
ch.series[2].graphicalProperties.line.width = 28000
for s in ch.series[3:]:
    s.graphicalProperties.line.solidFill = "F4B183"
    s.graphicalProperties.line.dashStyle = "dash"
ws_s["A24"], ws_s["A24"].font = ("Note: the trend window covers the 2023-25 boom, so a straight-line trend can overstate current momentum. "
                                 "The backtest bias line quantifies this; the bias-adjusted row is the more cautious view."), f_note
ws_s.add_chart(ch, "D4")

out = HERE / "Dubai_Sales_Forecast.xlsx"
wb.save(out)
print("saved", out)
