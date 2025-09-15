import streamlit as st
import pandas as pd
from utils import load_all_sessions
from datetime import datetime

st.title("📊 Performance Dashboard")

# -------------------------------
# Load and preprocess data
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
data["year"] = data["date"].dt.year

# Metrics of interest
preferred_metrics = [
    "Max-Velocity (All Metrics)",
    "10m Acceleration",
    "Vertical Jump",
    "Triple Broad Jump",
    "Standing Triple Jump",
    "24/28s Drill"
]

grade_bands = {
    "Overall (9–12)": [9, 10, 11, 12],
    "Freshman (9)": [9],
    "Fresh-Soph (9–10)": [9, 10]
}

current_year = datetime.now().year
season_data = data[data["year"] == current_year]

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

    # Determine direction
    display_unit = subset["display_unit"].dropna().iloc[0].lower()
    ascending = display_unit in ["s", "sec", "seconds"]

    grouped = subset.loc[
        subset.groupby("athlete_name")["display_value"].idxmax()
    ]

    best = grouped.sort_values("display_value", ascending=ascending).iloc[0]

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
# Section 1: All-Time Leaders
# -------------------------------
st.header("🏆 All-Time Leaders")
col_m, col_f = st.columns(2)

for col, gender in zip([col_m, col_f], ["male", "female"]):
    with col:
        st.subheader(gender.capitalize())
        band_tabs = st.tabs(list(grade_bands.keys()))
        for i, (label, grades) in enumerate(grade_bands.items()):
            with band_tabs[i]:
                gdf = data[data["gender"] == gender]

                rows = []
                for metric_label in preferred_metrics:
                    res = best_performance(gdf, metric_label, grade_filter=grades)
                    if res:
                        rows.append([res["metric"], res["athlete"], res["value"], res["date"]])
                    else:
                        rows.append([metric_label, "—", "—", "—"])

                df = pd.DataFrame(rows, columns=["Metric", "Athlete", "Value", "Date"])
                st.table(df)

# -------------------------------
# Detect offseason
# -------------------------------
from datetime import date

today = date.today()
year = today.year

# Season runs from 2nd week of March (≈ March 8) to 2nd week of June (≈ June 14)
season_start = date(year, 3, 10)   # adjust to your exact "second week" rule if needed
season_end   = date(year, 6, 14)

offseason = not (season_start <= today <= season_end)

# -------------------------------
# Year in Review Mode
# -------------------------------
if offseason:
    st.header(f"📅 Year in Review ({current_year})")

    # Helper: Top 3 per metric
    def top_performances(df, metric_label, grades):
        if metric_label == "Max-Velocity (All Metrics)":
            subset = df[df["metric_family"].str.lower() == "maxv"].copy()
        else:
            subset = df[df["metric_name"] == metric_label].copy()

        subset = subset[subset["grade"].isin(grades)]
        if subset.empty:
            return pd.DataFrame(columns=["Athlete", "Value", "Date"])

        display_unit = subset["display_unit"].dropna().iloc[0].lower()
        ascending = display_unit in ["s", "sec", "seconds"]

        grouped = subset.loc[
            subset.groupby("athlete_name")["display_value"].idxmax()
        ]

        top3 = grouped.sort_values("display_value", ascending=ascending).head(3)
        rows = []
        for _, row in top3.iterrows():
            val = f"{row['display_value']} {row['display_unit']}"
            if row["input_unit"] != row["display_unit"]:
                val += f" ({row['input_value']} {row['input_unit']})"
            rows.append([row["athlete_name"], val, row["date"].strftime("%B-%Y")])

        return pd.DataFrame(rows, columns=["Athlete", "Value", "Date"])

    # Two-column layout
    col_left, col_right = st.columns([2, 1])

    # -------------------------------
    # Left Column: Top Performances
    # -------------------------------
    with col_left:
        st.subheader("🏅 Top Performances of the Season")

        gender_tabs = st.tabs(["Male", "Female"])
        for g_idx, gender in enumerate(["male", "female"]):
            with gender_tabs[g_idx]:
                band_tabs = st.tabs(list(grade_bands.keys()))
                for i, (label, grades) in enumerate(grade_bands.items()):
                    with band_tabs[i]:
                        gdf = season_data[season_data["gender"] == gender]
                        for metric_label in preferred_metrics:
                            st.markdown(f"**{metric_label}**")
                            df = top_performances(gdf, metric_label, grades)
                            if df.empty:
                                st.info("No data")
                            else:
                                st.dataframe(
                                    df,
                                    use_container_width=True,
                                    hide_index=True
                                )

    # -------------------------------
    # Right Column: Participation + Consistency
    # -------------------------------
    with col_right:
        st.subheader("📊 Participation")
        counts = (
            season_data.groupby("metric_name")["athlete_name"]
            .nunique()
            .reset_index()
            .rename(columns={"athlete_name": "Unique Athletes"})
            .sort_values("Unique Athletes", ascending=False)
        )
        st.table(counts)

        st.subheader("⏱️ Consistency")
        consistency = (
            season_data.groupby("athlete_name")["date"]
            .count()
            .reset_index()
            .rename(columns={"date": "Sessions"})
            .sort_values("Sessions", ascending=False)
            .head(10)
        )
        st.table(consistency)

# -------------------------------
# Section 2: Recent Session Highlights (In-Season)
# -------------------------------
else:
    st.header("⏱️ Recent Session Highlights")

    this_year = data[data["date"].dt.year == current_year]
    if this_year.empty:
        st.info("No data available for the current year.")
    else:
        latest_week = this_year["week_number"].max()
        recent = this_year[this_year["week_number"] == latest_week]

        # Figure out top metrics if preferred ones missing
        metric_counts = recent["metric_name"].value_counts().to_dict()
        selected_metrics = []
        for m in preferred_metrics:
            if m == "Max-Velocity (All Metrics)":
                if not recent[recent["metric_family"].str.lower() == "maxv"].empty:
                    selected_metrics.append(m)
                else:
                    if metric_counts:
                        alt = max(metric_counts, key=metric_counts.get)
                        selected_metrics.append(alt)
                        metric_counts.pop(alt, None)
            else:
                if m in metric_counts:
                    selected_metrics.append(m)
                    metric_counts.pop(m, None)
                else:
                    if metric_counts:
                        alt = max(metric_counts, key=metric_counts.get)
                        selected_metrics.append(alt)
                        metric_counts.pop(alt, None)

        col_m2, col_f2 = st.columns(2)
        for col, gender in zip([col_m2, col_f2], ["male", "female"]):
            with col:
                st.subheader(gender.capitalize())
                band_tabs = st.tabs(list(grade_bands.keys()))
                for i, (label, grades) in enumerate(grade_bands.items()):
                    with band_tabs[i]:
                        gdf = recent[recent["gender"] == gender]

                        rows = []
                        for metric_label in selected_metrics:
                            res = best_performance(gdf, metric_label, grade_filter=grades)
                            if res:
                                rows.append([res["metric"], res["athlete"], res["value"], res["date"]])
                            else:
                                rows.append([metric_label, "—", "—", "—"])

                        df = pd.DataFrame(rows, columns=["Metric", "Athlete", "Value", "Date"])
                        st.table(df)
