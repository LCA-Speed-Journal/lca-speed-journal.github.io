import streamlit as st
import pandas as pd
import numpy as np
import hashlib
import altair as alt
from pathlib import Path
from glob import glob

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "sessions"

st.set_page_config(layout="wide")

@st.cache_data
def load_all_sessions():
    files = glob(str(DATA_DIR / "*.csv"))
    if not files:
        return pd.DataFrame(), []
    df_list = [pd.read_csv(f) for f in files]
    return pd.concat(df_list, ignore_index=True), files

def apply_filters(data):
    st.sidebar.header("Filters")

    # Leaderboard size
    top_n = st.sidebar.slider(
        "Number of leaderboard entries to show",
        min_value=3, max_value=30, value=10, step=1,
        help="Show only the top-N athletes for each leaderboard."
    )

    # Year filter
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data["year"] = data["date"].dt.year
        year_options = sorted(data["year"].dropna().unique())
        year_filter = st.sidebar.multiselect("Select Year(s)", options=year_options)
    else:
        year_filter = []
        st.sidebar.info("No date column found in dataset.")

    athlete_filter = st.sidebar.multiselect("Select Athlete(s)", options=data['athlete_name'].unique())
    metric_filter = st.sidebar.multiselect("Select Metric(s)", options=data['metric_name'].unique())
    season_phase_filter = st.sidebar.multiselect("Season Phase(s)", options=data['season_phase'].unique())

    # Grade filter
    if "grade" in data.columns:
        grade_options = sorted(data['grade'].dropna().unique())
        grade_filter = st.sidebar.multiselect("Select Grade(s)", options=grade_options)
    else:
        grade_filter = []
        st.sidebar.info("No grade column found in dataset.")

    # Week filter
    if "week_number" in data.columns:
        try:
            data["week_number"] = pd.to_numeric(data["week_number"], errors="coerce").astype("Int64")
        except Exception:
            pass

    week_min = int(data['week_number'].min()) if "week_number" in data.columns and pd.notna(data['week_number'].min()) else 0
    week_max = int(data['week_number'].max()) if "week_number" in data.columns and pd.notna(data['week_number'].max()) else 52

    week_range = st.sidebar.slider(
        "Week Number Range", min_value=week_min, max_value=week_max, value=(week_min, week_max)
    )

    show_gender_split = st.sidebar.checkbox("Show Gender-Split Leaderboards", value=True)

    if "gender" in data.columns:
        gender_options = data['gender'].unique()
        gender_filter = st.sidebar.multiselect("Gender", options=gender_options)
    else:
        gender_filter = []
        st.sidebar.info("No gender column found in dataset.")

    # Apply filters
    filtered = data[
        (data['athlete_name'].isin(athlete_filter) if athlete_filter else True) &
        (data['metric_name'].isin(metric_filter) if metric_filter else True) &
        (data['season_phase'].isin(season_phase_filter) if season_phase_filter else True) &
        (data['week_number'].between(*week_range)) &
        (data['gender'].isin(gender_filter) if ("gender" in data.columns and gender_filter) else True) &
        (data['year'].isin(year_filter) if year_filter else True) &
        (data['grade'].isin(grade_filter) if grade_filter else True)
    ].copy()

    return filtered, top_n, show_gender_split

# chart rendering function (copied from your original, unchanged)
def render_chart(df, title_suffix="", gendered=False, label="Metric", unit="", input_unit="", ascending=True):
    df = df.copy().reset_index(drop=True)
    df = df.sort_values("display_value", ascending=not ascending).reset_index(drop=True)
    df["rank"] = range(len(df))

    display_unit = unit
    input_unit = input_unit

    # Table renaming
    df_renamed = df.rename(columns={
        "display_value": f"Output ({display_unit})",
        "input_value": f"Input ({input_unit})"
    })
    if "date" in df_renamed.columns:
        df_renamed["date"] = pd.to_datetime(df_renamed["date"]).dt.date

    df_hash = hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()[:8]
    gender_suffix = f"-{gendered}" if gendered else ""
    chart_key = f"chart-{label}{title_suffix}{gender_suffix}-{df_hash}"
    table_key = f"table-{label}{title_suffix}{gender_suffix}-{df_hash}"

    if "gender" in df.columns:
        color_scale = alt.Scale(domain=["M","F","Other"], range=["#89CFF0","#FFC0CB","#D3D3D3"])
    else:
        color_scale = alt.Scale(domain=["NA"], range=["#89CFF0"])

    min_val = df["display_value"].min()
    max_val = df["display_value"].max()
    pad = (max_val - min_val) * 0.05 if max_val != min_val else 1
    axis_min = min_val - 3*pad
    axis_max = max_val + pad

    df["bar_label"] = df.apply(
        lambda row: f"{row['display_value']:.2f} {display_unit} ({row['input_value']:.2f} {input_unit})", axis=1
    )

    chart = alt.Chart(df).mark_bar(clip=True).encode(
        x=alt.X("display_value:Q", title=f"{label} ({display_unit})").scale(domain=(axis_min, axis_max)),
        y=alt.Y("athlete_name:N", sort=df["athlete_name"].tolist()),
        color=alt.Color("gender:N", scale=color_scale, legend=alt.Legend(title="Gender")) 
            if "gender" in df.columns else alt.value("#89CFF0"),
        tooltip=[
            alt.Tooltip("athlete_name:N", title="Athlete"),
            alt.Tooltip("metric_name:N", title="Metric"),
            alt.Tooltip("display_value:Q", title=f"Output ({display_unit})", format=".2f"),
            alt.Tooltip("input_value:Q", title=f"Input ({input_unit})", format=".2f"),
            alt.Tooltip("date:T", title="Date")
        ]
    ).properties(
        height=max(300, len(df)*40),
        width="container"
    )

    text = alt.Chart(df).mark_text(
        align="left", baseline="middle", dx=6, color="black"
    ).encode(
        x=alt.value(0),
        y=alt.Y("athlete_name:N", sort=df["athlete_name"].tolist()),
        text="bar_label:N"
    )
