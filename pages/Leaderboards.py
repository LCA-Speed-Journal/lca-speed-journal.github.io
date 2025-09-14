import streamlit as st
import pandas as pd
import numpy as np
import hashlib
import altair as alt
from pathlib import Path
from glob import glob
from utils import load_all_sessions, apply_filters, render_chart
import pandas as pd

st.title("📊 Leaderboards")

data, files = load_all_sessions()
if data.empty:
    st.warning("No data found.")
    st.stop()

filtered_data, top_n, show_gender_split = apply_filters(data)

# -------------------------------
# 3. Leaderboards
# -------------------------------
st.header("All-Time Leaderboards")
metric_categories = filtered_data['metric_category'].unique().tolist()
preferred_order = ["Speed", "X-Factor", "Lactic"]
metric_categories = [c for c in preferred_order if c in metric_categories] + \
                    [c for c in metric_categories if c not in preferred_order]

# -------------------------------
# Render Chart Function
# -------------------------------
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

    # Color mapping
    if "gender" in df.columns:
        color_scale = alt.Scale(domain=["M","F","Other"], range=["#89CFF0","#FFC0CB","#D3D3D3"])
    else:
        color_scale = alt.Scale(domain=["NA"], range=["#89CFF0"])

    # Dynamic axis
    min_val = df["display_value"].min()
    max_val = df["display_value"].max()
    pad = (max_val - min_val) * 0.05 if max_val != min_val else 1
    axis_min = min_val - 3*pad
    axis_max = max_val + pad

    # Bar labels
    df["bar_label"] = df.apply(
        lambda row: f"{row['display_value']:.2f} {display_unit} ({row['input_value']:.2f} {input_unit})", axis=1
    )

    # Base chart
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

    # Overlay text labels
    text = alt.Chart(df).mark_text(
        align="left", baseline="middle", dx=6, color="black"
    ).encode(
        x=alt.value(0),
        y=alt.Y("athlete_name:N", sort=df["athlete_name"].tolist()),
        text="bar_label:N"
    )

    chart_with_labels = chart + text

    # Streamlit layout
    col1, col2 = st.columns([2,1])
    with col1:
        st.altair_chart(chart_with_labels, use_container_width=True, key=chart_key)
    with col2:
        display_cols = ["athlete_name", f"Output ({display_unit})", f"Input ({input_unit})", "date"]
        existing_cols = [c for c in display_cols if c in df_renamed.columns]
        st.dataframe(df_renamed[existing_cols].style.format({
            f"Output ({display_unit})": "{:.2f}",
            f"Input ({input_unit})": "{:.2f}"
        }), key=table_key)


# -------------------------------
# Leaderboard Loops
# -------------------------------
if not metric_categories:
    st.info("No metrics available with current filters.")
else:
    category_tabs = st.tabs(metric_categories)

    for i, category in enumerate(metric_categories):
        with category_tabs[i]:
            category_data = filtered_data[filtered_data['metric_category']==category]

            # -------------------------------
            # Inside the Speed section (Max-Velocity + Acceleration)
            # -------------------------------
            if category.lower() == "speed":
                speed_families = ["maxv", "acceleration"]
                sub_tabs = st.tabs(["Max-Velocity", "Acceleration"])

                for sf_i, sf in enumerate(speed_families):
                    with sub_tabs[sf_i]:
                        family_data = category_data[
                            category_data['metric_family'].str.lower() == sf
                        ]

                        # -------------------------------
                        # Max-Velocity Bucketing
                        # -------------------------------
                        if sf == "maxv":
                            import re

                            def get_build_distance(metric_name: str) -> int:
                                """Extract build distance from metric name like '10-20m Split' or '30-50m Zone'."""
                                match = re.match(r"(\d+)\s*-\s*\d+", str(metric_name))
                                if match:
                                    return int(match.group(1))
                                return 0  # fallback if parsing fails

                            family_data = family_data.copy()
                            family_data["build"] = family_data["metric_name"].apply(get_build_distance)

                            def assign_bucket(build: int) -> str:
                                if build <= 18:
                                    return "Early-Acceleration"
                                elif 19 <= build <= 35:
                                    return "Medium-Build"
                                elif build >= 36:
                                    return "Late-Velocity"
                                return "Uncategorized"

                            family_data["bucket"] = family_data["build"].apply(assign_bucket)

                            # Four tabs: All Metrics, Early, Medium, Late
                            bucket_tabs_labels = [
                                "Max-Velocity (All Metrics)",
                                "Early-Acceleration",
                                "Medium-Build",
                                "Late-Velocity"
                            ]
                            bucket_tabs = st.tabs(bucket_tabs_labels)

                            for j, label in enumerate(bucket_tabs_labels):
                                with bucket_tabs[j]:
                                    if label == "Max-Velocity (All Metrics)":
                                        working_data = family_data
                                    else:
                                        working_data = family_data[family_data["bucket"] == label]

                                    if working_data.empty:
                                        st.info(f"No data for {label}.")
                                        continue

                                    # Grab units explicitly
                                    display_unit_val = working_data['display_unit'].iloc[0].strip() \
                                        if pd.notna(working_data['display_unit'].iloc[0]) else ""
                                    input_unit_val = working_data['input_unit'].iloc[0].strip() \
                                        if pd.notna(working_data['input_unit'].iloc[0]) else ""

                                    # Build leaderboard
                                    if 'gender' in working_data.columns:
                                        composite_leaderboard = working_data.loc[
                                            working_data.groupby("athlete_name")["display_value"].idxmax()
                                        ][["athlete_name","display_value","input_value","date","gender","metric_name"]]
                                        gendered=True
                                    else:
                                        composite_leaderboard = working_data.loc[
                                            working_data.groupby("athlete_name")["display_value"].idxmax()
                                        ][["athlete_name","display_value","input_value","date","metric_name"]]
                                        gendered=False

                                    ascending = False if display_unit_val.lower() in ["s","sec","seconds"] else True
                                    composite_leaderboard = composite_leaderboard.sort_values(
                                        "display_value", ascending=not ascending
                                    ).head(top_n)

                                    render_chart(
                                        composite_leaderboard,
                                        title_suffix="-composite",
                                        gendered=gendered,
                                        label=label,
                                        unit=display_unit_val,
                                        input_unit=input_unit_val,
                                        ascending=ascending
                                    )

                                    if show_gender_split and 'gender' in working_data.columns:
                                        gendered_leaderboard = working_data.loc[
                                            working_data.groupby(["athlete_name","gender"])["display_value"].idxmax()
                                        ][["athlete_name","display_value","input_value","date","gender","metric_name"]]

                                        for g in gendered_leaderboard['gender'].unique():
                                            g_df = gendered_leaderboard[gendered_leaderboard['gender']==g]
                                            g_df = g_df.sort_values("display_value", ascending=not ascending).head(top_n)
                                            render_chart(
                                                g_df,
                                                title_suffix=f"-{g}",
                                                gendered=True,
                                                label=label,
                                                unit=display_unit_val,
                                                input_unit=input_unit_val,
                                                ascending=ascending
                                            )

                        # -------------------------------
                        # Acceleration family (standard leaderboard loop)
                        # -------------------------------
                        elif sf == "acceleration":
                            metrics = family_data['metric_name'].unique().tolist()
                            if not metrics:
                                st.info("No Acceleration metrics available.")
                            else:
                                metric_tabs = st.tabs(metrics)
                                for j, label in enumerate(metrics):
                                    with metric_tabs[j]:
                                        working_data = family_data[family_data['metric_name']==label]
                                        if working_data.empty:
                                            st.info(f"No data for {label}.")
                                            continue

                                        display_unit_val = working_data['display_unit'].iloc[0].strip() \
                                            if pd.notna(working_data['display_unit'].iloc[0]) else ""
                                        input_unit_val = working_data['input_unit'].iloc[0].strip() \
                                            if pd.notna(working_data['input_unit'].iloc[0]) else ""

                                        ascending = False if display_unit_val.lower() in ["s","sec","seconds"] else True

                                        if 'gender' in working_data.columns:
                                            composite_leaderboard = working_data.loc[
                                                working_data.groupby("athlete_name")["display_value"].idxmax()
                                            ][["athlete_name","display_value","input_value","date","gender"]]
                                            gendered=True
                                        else:
                                            composite_leaderboard = working_data.loc[
                                                working_data.groupby("athlete_name")["display_value"].idxmax()
                                            ][["athlete_name","display_value","input_value","date"]]
                                            gendered=False

                                        composite_leaderboard = composite_leaderboard.sort_values(
                                            "display_value", ascending=not ascending
                                        ).head(top_n)

                                        render_chart(
                                            composite_leaderboard,
                                            title_suffix="-composite",
                                            gendered=gendered,
                                            label=label,
                                            unit=display_unit_val,
                                            input_unit=input_unit_val,
                                            ascending=ascending
                                        )

                                        if show_gender_split and 'gender' in working_data.columns:
                                            gendered_leaderboard = working_data.loc[
                                                working_data.groupby(["athlete_name","gender"])["display_value"].idxmax()
                                            ][["athlete_name","display_value","input_value","date","gender"]]

                                            for g in gendered_leaderboard['gender'].unique():
                                                g_df = gendered_leaderboard[gendered_leaderboard['gender']==g]
                                                g_df = g_df.sort_values("display_value", ascending=not ascending).head(top_n)
                                                render_chart(
                                                    g_df,
                                                    title_suffix=f"-{g}",
                                                    gendered=True,
                                                    label=label,
                                                    unit=display_unit_val,
                                                    input_unit=input_unit_val,
                                                    ascending=ascending
                                                )

            else:  # Non-speed categories
                metrics = category_data['metric_name'].unique().tolist()
                metric_tabs = st.tabs(metrics)

                for j, label in enumerate(metrics):
                    with metric_tabs[j]:
                        working_data = category_data[category_data['metric_name']==label]
                        if working_data.empty:
                            st.info(f"No data for {label}.")
                            continue

                        display_unit_val = working_data['display_unit'].iloc[0].strip() if pd.notna(working_data['display_unit'].iloc[0]) else ""
                        input_unit_val = working_data['input_unit'].iloc[0].strip() if pd.notna(working_data['input_unit'].iloc[0]) else ""

                        ascending = False if display_unit_val.lower() in ["s","sec","seconds"] else True

                        if 'gender' in working_data.columns:
                            composite_leaderboard = working_data.loc[
                                working_data.groupby("athlete_name")["display_value"].idxmax()
                            ][["athlete_name","display_value","input_value","date","gender"]]
                            gendered=True
                        else:
                            composite_leaderboard = working_data.loc[
                                working_data.groupby("athlete_name")["display_value"].idxmax()
                            ][["athlete_name","display_value","input_value","date"]]
                            gendered=False

                        composite_leaderboard = composite_leaderboard.sort_values("display_value", ascending=not ascending).head(top_n)

                        render_chart(composite_leaderboard, title_suffix="-composite", gendered=gendered,
                                     label=label, unit=display_unit_val, input_unit=input_unit_val, ascending=ascending)

                        if show_gender_split and 'gender' in working_data.columns:
                            gendered_leaderboard = working_data.loc[
                                working_data.groupby(["athlete_name","gender"])["display_value"].idxmax()
                            ][["athlete_name","display_value","input_value","date","gender"]]

                            for g in gendered_leaderboard['gender'].unique():
                                g_df = gendered_leaderboard[gendered_leaderboard['gender']==g]
                                g_df = g_df.sort_values("display_value", ascending=not ascending).head(top_n)
                                render_chart(g_df, title_suffix=f"-{g}", gendered=True,
                                             label=label, unit=display_unit_val, input_unit=input_unit_val, ascending=ascending)