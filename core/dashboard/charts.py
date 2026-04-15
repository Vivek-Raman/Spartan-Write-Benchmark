from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .models import DashboardRow, DashboardRun

_CHART_HEIGHT = 400
_PLOTLY_LAYOUT = dict(
    margin=dict(l=40, r=20, t=40, b=40),
    font=dict(size=12),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _flatten_runs(rows: list[DashboardRow]) -> list[dict[str, Any]]:
    """Build a flat list of dicts (one per non-null run) with extracted score fields."""
    flat: list[dict[str, Any]] = []
    for row in rows:
        summary = row.summary or ""
        category = "BASIC" if summary.upper().startswith("BASIC") else "LARGE"
        for run in row.runs:
            if run is None:
                continue
            scores = run.scores or {}
            tool_use = scores.get("tool_use", 0)
            total_tool_calls = (
                sum(tool_use.values()) if isinstance(tool_use, dict) else 0
            )
            flat.append(
                {
                    "model": row.model,
                    "job_id": row.job_id,
                    "summary": summary,
                    "category": category,
                    "run_index": run.index,
                    "status": run.status,
                    "error": run.error,
                    "chat_duration": scores.get("chat_duration"),
                    "input_tokens": scores.get("input_tokens"),
                    "output_tokens": scores.get("output_tokens"),
                    "reasoning_tokens": scores.get("reasoning_tokens"),
                    "tool_use": tool_use,
                    "total_tool_calls": total_tool_calls,
                }
            )
    return flat


def _completed_runs(flat: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in flat if r["status"] == "completed"]


def _chart_success_rate(flat: list[dict[str, Any]]) -> None:
    """Grouped bar: completed / failed / pending counts per model."""
    if not flat:
        return

    counts: dict[str, dict[str, int]] = {}
    for r in flat:
        model = r["model"]
        status = r["status"]
        counts.setdefault(model, {"completed": 0, "failed": 0, "pending": 0})
        bucket = status if status in ("completed", "failed") else "pending"
        counts[model][bucket] += 1

    models = sorted(counts)
    fig = go.Figure()
    colors = {"completed": "#2ecc71", "failed": "#e74c3c", "pending": "#95a5a6"}
    for status in ("completed", "failed", "pending"):
        vals = [counts[m][status] for m in models]
        if any(v > 0 for v in vals):
            fig.add_trace(
                go.Bar(
                    name=status.capitalize(),
                    x=models,
                    y=vals,
                    marker_color=colors[status],
                )
            )

    fig.update_layout(
        barmode="group",
        title="Run Status by Model",
        xaxis_title="Model",
        yaxis_title="Count",
        height=_CHART_HEIGHT,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, width="stretch")


def _chart_avg_duration(completed: list[dict[str, Any]]) -> None:
    """Bar per model showing mean chat_duration with individual run points overlaid."""
    runs_with_dur = [r for r in completed if r["chat_duration"] and r["chat_duration"] > 0]
    if not runs_with_dur:
        return

    from collections import defaultdict

    by_model: dict[str, list[float]] = defaultdict(list)
    for r in runs_with_dur:
        by_model[r["model"]].append(r["chat_duration"])

    models = sorted(by_model)
    means = [sum(by_model[m]) / len(by_model[m]) for m in models]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=models,
            y=means,
            name="Mean",
            marker_color="#3498db",
            opacity=0.7,
        )
    )
    for m in models:
        fig.add_trace(
            go.Scatter(
                x=[m] * len(by_model[m]),
                y=by_model[m],
                mode="markers",
                name=f"{m} runs",
                marker=dict(size=8, line=dict(width=1, color="white")),
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Average Chat Duration by Model",
        xaxis_title="Model",
        yaxis_title="Duration (seconds)",
        height=_CHART_HEIGHT,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, width="stretch")


def _chart_token_usage(completed: list[dict[str, Any]]) -> None:
    """Stacked bar per model: average input / reasoning / output tokens per run."""
    runs_with_tokens = [
        r
        for r in completed
        if r["input_tokens"] is not None and r["output_tokens"] is not None
    ]
    if not runs_with_tokens:
        return

    from collections import defaultdict

    sums: dict[str, dict[str, float]] = defaultdict(lambda: {"input": 0, "reasoning": 0, "output": 0})
    run_counts: dict[str, int] = defaultdict(int)

    for r in runs_with_tokens:
        m = r["model"]
        sums[m]["input"] += r["input_tokens"] or 0
        sums[m]["reasoning"] += r["reasoning_tokens"] or 0
        sums[m]["output"] += r["output_tokens"] or 0
        run_counts[m] += 1

    models = sorted(sums)
    fig = go.Figure()
    colors = {"Input": "#3498db", "Reasoning": "#e67e22", "Output": "#2ecc71"}
    for label, key in [("Input", "input"), ("Reasoning", "reasoning"), ("Output", "output")]:
        vals = [sums[m][key] / run_counts[m] for m in models]
        fig.add_trace(
            go.Bar(name=label, x=models, y=vals, marker_color=colors[label])
        )

    fig.update_layout(
        barmode="stack",
        title="Average Token Usage by Model",
        xaxis_title="Model",
        yaxis_title="Tokens (avg per run)",
        height=_CHART_HEIGHT,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, width="stretch")


def _chart_duration_per_job(completed: list[dict[str, Any]]) -> None:
    """Grouped bar: chat duration per job, comparing models side-by-side."""
    runs_with_dur = [r for r in completed if r["chat_duration"] and r["chat_duration"] > 0]
    if not runs_with_dur:
        return

    from collections import defaultdict

    by_job_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in runs_with_dur:
        by_job_model[r["job_id"]][r["model"]].append(r["chat_duration"])

    jobs = sorted(by_job_model)
    all_models = sorted({r["model"] for r in runs_with_dur})

    fig = go.Figure()
    for model in all_models:
        means = []
        for job in jobs:
            durations = by_job_model[job].get(model, [])
            means.append(sum(durations) / len(durations) if durations else 0)
        fig.add_trace(go.Bar(name=model, x=jobs, y=means))

    fig.update_layout(
        barmode="group",
        title="Chat Duration per Job",
        xaxis_title="Job",
        yaxis_title="Duration (seconds, avg)",
        height=_CHART_HEIGHT + 40,
        xaxis_tickangle=-30,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, width="stretch")


def _chart_tool_heatmap(completed: list[dict[str, Any]]) -> None:
    """Heatmap: models x tool names, values = avg calls per run."""
    from collections import defaultdict

    tool_sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    run_counts: dict[str, int] = defaultdict(int)

    for r in completed:
        m = r["model"]
        tu = r["tool_use"]
        run_counts[m] += 1
        if isinstance(tu, dict):
            for tool_name, count in tu.items():
                tool_sums[m][tool_name] += count

    if not tool_sums:
        return

    models = sorted(tool_sums)
    all_tools = sorted({t for m in tool_sums for t in tool_sums[m]})
    if not all_tools:
        return

    z = []
    for model in models:
        rc = run_counts[model] or 1
        z.append([tool_sums[model].get(t, 0) / rc for t in all_tools])

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=all_tools,
            y=models,
            colorscale="Blues",
            text=[[f"{v:.1f}" for v in row] for row in z],
            texttemplate="%{text}",
            textfont=dict(size=12),
            hovertemplate="Model: %{y}<br>Tool: %{x}<br>Avg calls: %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Tool Usage (avg calls per run)",
        height=max(250, 80 * len(models) + 100),
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, width="stretch")


def _chart_duration_vs_tokens(completed: list[dict[str, Any]]) -> None:
    """Scatter: total tokens vs chat_duration, colored by model."""
    points = []
    for r in completed:
        dur = r["chat_duration"]
        inp = r["input_tokens"]
        out = r["output_tokens"]
        if dur and dur > 0 and inp is not None and out is not None:
            points.append(
                {
                    "model": r["model"],
                    "job_id": r["job_id"],
                    "total_tokens": (inp or 0) + (out or 0),
                    "chat_duration": dur,
                }
            )
    if not points:
        return

    fig = px.scatter(
        points,
        x="total_tokens",
        y="chat_duration",
        color="model",
        hover_data=["job_id"],
        title="Chat Duration vs Total Tokens",
        labels={
            "total_tokens": "Total Tokens (input + output)",
            "chat_duration": "Duration (seconds)",
        },
    )
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color="white")))
    fig.update_layout(height=_CHART_HEIGHT, **_PLOTLY_LAYOUT)
    st.plotly_chart(fig, width="stretch")


def render_charts(rows: list[DashboardRow]) -> None:
    """Render all benchmark visualizations. Called from render_dashboard."""
    flat = _flatten_runs(rows)
    if not flat:
        return

    completed = _completed_runs(flat)

    st.header("Visualizations")

    col_left, col_right = st.columns(2)
    with col_left:
        _chart_success_rate(flat)
    with col_right:
        _chart_avg_duration(completed)

    col_left2, col_right2 = st.columns(2)
    with col_left2:
        _chart_token_usage(completed)
    with col_right2:
        _chart_duration_vs_tokens(completed)

    _chart_duration_per_job(completed)
    _chart_tool_heatmap(completed)

    st.divider()
