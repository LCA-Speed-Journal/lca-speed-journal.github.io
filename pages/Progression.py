import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import re
from utils import load_all_sessions, apply_filters

st.title("📈 Progression")

data, files = load_all_sessions()
if data.empty:
    st.warning("No data found.")
    st.stop()

filtered_data, top_n, show_gender_split = apply_filters(data)

# -------------------------------
# Progression Section
# -------------------------------
st.header("Progression")

prog_data = filtered_data.copy()
if prog_data.empty:
    st.info("No data available for progression charts with current filters.")
else:
    metric_categories = prog_data['metric_category'].dropna().unique().tolist()
    preferred_order = ["Speed", "X-Factor", "Lactic"]
    metric_categories = [c for c in preferred_order if c in metric_categories] + \
                        [c for c in metric_categories if c not in preferred_order]

    cat_tabs = st.tabs(metric_categories)

    for i, category in enumerate(metric_categories):
        with cat_tabs[i]:
            category_data = prog_data[prog_data['metric_category'] == category]

            # =======================
            # SPEED CATEGORY
            # =======================
            if category.lower() == "speed":
                speed_families = ["maxv", "acceleration"]
                sub_tabs = st.tabs(["Max-Velocity", "Acceleration"])

                # ---- Max Velocity ----
                with sub_tabs[0]:
                    family_data = category_data[category_data['metric_family'].str.lower() == "maxv"].copy()
                    if family_data.empty:
                        st.info("No Max-Velocity data.")
                    else:
                        # Extract build distance from metric name
                        def get_build_distance(metric_name: str) -> int:
                            match = re.match(r"(\d+)\s*-\s*\d+", str(metric_name))
                            if match:
                                return int(match.group(1))
                            return 0

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

                                gender_tabs = st.tabs(sorted(working_data['gender'].dropna().unique()))
                                for g_i, g in enumerate(sorted(working_data['gender'].dropna().unique())):
                                    with gender_tabs[g_i]:
                                        team_df = working_data[working_data['gender'] == g].copy()
                                        if team_df.empty:
                                            st.info(f"No {g} data available.")
                                            continue

                                        # Jitter weeks for scatter
                                        team_df["week_jitter"] = team_df["week_number"] + np.random.uniform(-0.2, 0.2, size=len(team_df))

                                        min_val = team_df["display_value"].min()
                                        max_val = team_df["display_value"].max()
                                        pad = (max_val - min_val) * 0.05 if max_val != min_val else 1
                                        y_domain = (min_val - pad, max_val + pad)

                                        scatter = alt.Chart(team_df).mark_point(filled=True, size=80, opacity=0.75).encode(
                                            x=alt.X("week_jitter:Q", title="Week",
                                                    scale=alt.Scale(zero=False),
                                                    axis=alt.Axis(values=sorted(team_df["week_number"].unique()))),
                                            y=alt.Y("display_value:Q", title="Value",
                                                    scale=alt.Scale(domain=y_domain)),
                                            color=alt.Color("athlete_name:N",
                                                            legend=alt.Legend(title="Athlete"),
                                                            scale=alt.Scale(scheme="turbo")),
                                            shape=alt.Shape("year:N", legend=alt.Legend(title="Year")),
                                            tooltip=[
                                                alt.Tooltip('athlete_name:N', title='Athlete'),
                                                alt.Tooltip('metric_name:N', title='Metric'),
                                                alt.Tooltip('week_number:Q', title='Week'),
                                                alt.Tooltip('display_value:Q', title='Value', format=".3f"),
                                                alt.Tooltip('year:O', title='Year')
                                            ]
                                        )

                                        box = alt.Chart(team_df).mark_boxplot(extent=1, size=55, opacity=0.4).encode(
                                            x=alt.X("week_number:Q", title="Week",
                                                    scale=alt.Scale(zero=False)),
                                            y=alt.Y("display_value:Q", title="Value",
                                                    scale=alt.Scale(domain=y_domain)),
                                            color=alt.value("gray")
                                        )

                                        if len(team_df) >= 5:
                                            iqr_band = alt.Chart(team_df).mark_errorband(extent='iqr', color='darkgray', opacity=0.2).encode(
                                                x="week_number:Q", y="display_value:Q"
                                            )
                                            chart = (box + iqr_band + scatter).properties(width='container', height=600)
                                        else:
                                            chart = (box + scatter).properties(width='container', height=600)

                                        st.altair_chart(chart, use_container_width=True)

                # ---- Acceleration ----
                with sub_tabs[1]:
                    family_data = category_data[category_data['metric_family'].str.lower() == "acceleration"].copy()
                    if family_data.empty:
                        st.info("No Acceleration data available.")
                    else:
                        acc_metrics = sorted(family_data['metric_name'].dropna().unique())
                        acc_tabs = st.tabs(acc_metrics)

                        for j, label in enumerate(acc_metrics):
                            with acc_tabs[j]:
                                working_data = family_data[family_data["metric_name"] == label]
                                if working_data.empty:
                                    st.info(f"No data for {label}.")
                                    continue

                                gender_tabs = st.tabs(sorted(working_data['gender'].dropna().unique()))
                                for g_i, g in enumerate(sorted(working_data['gender'].dropna().unique())):
                                    with gender_tabs[g_i]:
                                        team_df = working_data[working_data['gender'] == g].copy()
                                        if team_df.empty:
                                            st.info(f"No {g} data available.")
                                            continue

                                        team_df["week_jitter"] = team_df["week_number"] + np.random.uniform(-0.2, 0.2, size=len(team_df))

                                        min_val = team_df["display_value"].min()
                                        max_val = team_df["display_value"].max()
                                        pad = (max_val - min_val) * 0.05 if max_val != min_val else 1
                                        y_domain = (min_val - pad, max_val + pad)

                                        scatter = alt.Chart(team_df).mark_point(filled=True, size=80, opacity=0.75).encode(
                                            x=alt.X("week_jitter:Q", title="Week",
                                                    scale=alt.Scale(zero=False),
                                                    axis=alt.Axis(values=sorted(team_df["week_number"].unique()))),
                                            y=alt.Y("display_value:Q", title="Value",
                                                    scale=alt.Scale(domain=y_domain)),
                                            color=alt.Color("athlete_name:N", legend=alt.Legend(title="Athlete")),
                                            shape=alt.Shape("year:N", legend=alt.Legend(title="Year")),
                                            tooltip=[
                                                alt.Tooltip('athlete_name:N', title='Athlete'),
                                                alt.Tooltip('metric_name:N', title='Metric'),
                                                alt.Tooltip('week_number:Q', title='Week'),
                                                alt.Tooltip('display_value:Q', title='Value', format=".3f"),
                                                alt.Tooltip('year:O', title='Year')
                                            ]
                                        )

                                        box = alt.Chart(team_df).mark_boxplot(extent=1, size=55, opacity=0.4).encode(
                                            x=alt.X("week_number:Q", title="Week",
                                                    scale=alt.Scale(zero=False)),
                                            y=alt.Y("display_value:Q", title="Value",
                                                    scale=alt.Scale(domain=y_domain)),
                                            color=alt.value("gray")
                                        )

                                        if len(team_df) >= 5:
                                            iqr_band = alt.Chart(team_df).mark_errorband(extent='iqr', color='darkgray', opacity=0.2).encode(
                                                x="week_number:Q", y="display_value:Q"
                                            )
                                            chart = (box + iqr_band + scatter).properties(width='container', height=600)
                                        else:
                                            chart = (box + scatter).properties(width='container', height=600)

                                        st.altair_chart(chart, use_container_width=True)

            # =======================
            # NON-SPEED CATEGORIES
            # =======================
            else:
                metrics = sorted(category_data['metric_name'].dropna().unique())
                if not metrics:
                    st.info(f"No {category} metrics available.")
                else:
                    metric_tabs = st.tabs(metrics)
                    for j, label in enumerate(metrics):
                        with metric_tabs[j]:
                            working_data = category_data[category_data['metric_name'] == label]
                            if working_data.empty:
                                st.info(f"No data for {label}.")
                                continue

                            gender_tabs = st.tabs(sorted(working_data['gender'].dropna().unique()))
                            for g_i, g in enumerate(sorted(working_data['gender'].dropna().unique())):
                                with gender_tabs[g_i]:
                                    team_df = working_data[working_data['gender'] == g].copy()
                                    if team_df.empty:
                                        st.info(f"No {g} data available.")
                                        continue

                                    team_df["week_jitter"] = team_df["week_number"] + np.random.uniform(-0.25, 0.25, size=len(team_df))

                                    min_val = team_df["display_value"].min()
                                    max_val = team_df["display_value"].max()
                                    pad = (max_val - min_val) * 0.05 if max_val != min_val else 1
                                    y_domain = (min_val - pad, max_val + pad)

                                    scatter = alt.Chart(team_df).mark_point(filled=True, size=80, opacity=0.75).encode(
                                        x=alt.X("week_jitter:Q", title="Week",
                                                scale=alt.Scale(zero=False),
                                                axis=alt.Axis(values=sorted(team_df["week_number"].unique()))),
                                        y=alt.Y("display_value:Q", title="Value",
                                                scale=alt.Scale(domain=y_domain)),
                                        color=alt.Color("athlete_name:N",
                                                        legend=alt.Legend(title="Athlete"),
                                                        scale=alt.Scale(scheme="turbo")),
                                        shape=alt.Shape("year:N", legend=alt.Legend(title="Year")),
                                        tooltip=[
                                            alt.Tooltip('athlete_name:N', title='Athlete'),
                                            alt.Tooltip('metric_name:N', title='Metric'),
                                            alt.Tooltip('week_number:Q', title='Week'),
                                            alt.Tooltip('display_value:Q', title='Value', format=".3f"),
                                            alt.Tooltip('year:O', title='Year')
                                        ]
                                    )

                                    box = alt.Chart(team_df).mark_boxplot(extent=1, opacity=0.4, clip=True).encode(
                                        x=alt.X("week_number:Q", title="Week",
                                                scale=alt.Scale(zero=False)),
                                        y=alt.Y("display_value:Q", title="Value",
                                                scale=alt.Scale(domain=y_domain)),
                                        color=alt.value("gray")
                                    )

                                    if len(team_df) >= 5:
                                        iqr_band = alt.Chart(team_df).mark_errorband(extent='iqr', color='darkgray', opacity=0.2).encode(
                                            x="week_number:Q", y="display_value:Q"
                                        )
                                        chart = (box + iqr_band + scatter).properties(width='container', height=600)
                                    else:
                                        chart = (box + scatter).properties(width='container', height=600)

                                    st.altair_chart(chart, use_container_width=True)
