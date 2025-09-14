import streamlit as st
import pandas as pd
import re
from utils import load_all_sessions

st.title("📊 Performance Dashboard")

# -------------------------------
# Load data
# -------------------------------
data, files = load_all_sessions()
if data.empty:
    st.warning("No data found.")
    st.stop()

# Normalize
data["gender"] = data["gender"].str.strip().str.lower().map({
    "m": "male", "male": "male",
    "f": "female", "female": "female"
})
data["grade"] = pd.to_numeric(data["grade"], errors="coerce")
data["date"] = pd.to_datetime(data["date"], errors="coerce")
data["month_year"] = data["date"].dt.strftime("%B-%Y")

# Metrics of interest
metrics_to_keep = [
    "Max-Velocity (All Metrics)",
    "10m Acceleration",
    "Vertical Jump",
    "Triple Broad Jump",
    "Standing Triple Jump",
    "24/28s Drill"
]

# -------------------------------
# Helper: best performance
# -------------------------------
def best_performance(df, metric_label, grade_filter=None):
    if metric_label == "Max-Velocity (All Metrics)":
        subset = df[df["metric_family"].str.lower() == "maxv"].copy()
    else:
        subset = df[df["metric_name"] == metric_label].copy()

    if grade_filter:
        subset = subset[subset["grade"].isin(grade_filter)]
    if subset.empty:
        return None

    # Determine better direction
    display_unit = subset["display_unit"].dropna().iloc[0].lower()
    ascending = display_unit in ["s", "sec", "seconds"]

    # Best per athlete
    grouped = subset.loc[
        subset.groupby("athlete_name")["display_value"].idxmax()
    ]

    # Sort and take best
    best = grouped.sort_values("display_value", ascending=ascending).iloc[0]

    # Value string
    disp = f"{best['display_value']} {best['display_unit']}"
    if best['input_unit'] != best['display_unit']:
        disp += f" ({best['input_value']} {best['input_unit']})"

    return {
        "metric": metric_label,
        "athlete": best["athlete_name"],
        "value": disp,
        "date": best["month_year"]
    }

# -------------------------------
# Layout: All-Time Leaders
# -------------------------------
st.header("🏆 All-Time Leaders")
col_m, col_f = st.columns(2)

grade_bands = {
    "Overall (9–12)": [9, 10, 11, 12],
    "Freshman (9)": [9],
    "Fresh-Soph (9–10)": [9, 10]
}

for col, gender in zip([col_m, col_f], ["male", "female"]):
    with col:
        st.subheader(gender.capitalize())
        band_tabs = st.tabs(list(grade_bands.keys()))
        for i, (label, grades) in enumerate(grade_bands.items()):
            with band_tabs[i]:
                gdf = data[data["gender"] == gender]

                rows = []
                for metric_label in metrics_to_keep:
                    res = best_performance(gdf, metric_label, grade_filter=grades)
                    if res:
                        rows.append([res["metric"], res["athlete"], res["value"], res["date"]])
                    else:
                        rows.append([metric_label, "—", "—", "—"])

                df = pd.DataFrame(rows, columns=["Metric", "Athlete", "Value", "Date"])
                st.table(df)
