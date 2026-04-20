from __future__ import annotations

from collections import defaultdict
from typing import Any

import streamlit as st

from .charts import (
    _completed_runs,
    _flatten_runs,
    _order_models_by_mean_cost,
    render_charts,
)
from .models import DashboardRow, DashboardSummary


def _truncate(s: str, max_len: int = 96) -> str:
    s = s or ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _collect_score_keys(rows: list[DashboardRow]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        for r in row.runs:
            if r is None:
                continue
            if r.scores:
                keys.update(r.scores.keys())
            if r.tool_use:
                keys.add("tool_use")
    return sorted(keys)


def _filter_rows(
    rows: list[DashboardRow],
    selected_models: list[str],
    selected_statuses: list[str],
    show_errors_only: bool,
    job_query: str,
) -> list[DashboardRow]:
    q = job_query.strip().lower()
    out: list[DashboardRow] = []
    for row in rows:
        if row.model not in selected_models:
            continue
        if row.status not in selected_statuses:
            continue
        if show_errors_only and not row.error:
            continue
        if q:
            if q not in row.job_id.lower() and q not in (row.summary or "").lower():
                continue
        out.append(row)
    return out


@st.dialog("Chat result", width="large")
def _chat_result_dialog(
    model: str, job_id: str, run_index: int, chat_result: object
) -> None:
    st.caption(f"Model `{model}` · Job `{job_id}` · Run {run_index + 1}")
    if isinstance(chat_result, (dict, list)):
        st.json(chat_result, expanded=5)
        return
    st.code(str(chat_result), language="text")


def render_dashboard(summary: DashboardSummary) -> None:
    st.set_page_config(
        page_title="Benchmark Dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Benchmark Dashboard")
    st.caption(f"Directory: `{summary.base_dir}`")

    if not summary.rows:
        st.info(
            "No benchmark data found. Expected: `<dir>/benchmark.db`."
        )
        return

    flat_all = _flatten_runs(summary.rows)
    completed_all = _completed_runs(flat_all)
    model_options = _order_models_by_mean_cost(
        completed_all, {row.model for row in summary.rows}
    )
    selected_models = st.multiselect(
        "Models",
        options=model_options,
        default=model_options,
    )
    status_options = sorted({row.status for row in summary.rows})
    selected_statuses = st.multiselect(
        "Status",
        options=status_options,
        default=status_options,
    )
    show_errors_only = st.checkbox("Only rows with errors", value=False)
    job_query = st.text_input(
        "Search job id or summary",
        placeholder="Substring filter…",
        value="",
    )

    filtered_rows = _filter_rows(
        summary.rows,
        selected_models,
        selected_statuses,
        show_errors_only,
        job_query,
    )

    total_jobs = len(filtered_rows)
    completed = sum(1 for row in filtered_rows if row.status == "completed")
    failed = sum(1 for row in filtered_rows if row.status == "failed")
    pending = total_jobs - completed - failed
    total_runs = sum(row.non_null_run_count() for row in filtered_rows)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Jobs", total_jobs)
    m2.metric("Completed", completed)
    m3.metric("Failed", failed)
    m4.metric("Pending", pending)
    m5.metric("Recorded runs", total_runs)

    if not filtered_rows:
        st.warning("No rows match the current filters.")
        return

    render_charts(filtered_rows)

    st.header("Detailed Results")

    score_keys = _collect_score_keys(filtered_rows)

    flat_filtered = _flatten_runs(filtered_rows)
    completed_filtered = _completed_runs(flat_filtered)
    by_model: dict[str, list[DashboardRow]] = defaultdict(list)
    for row in filtered_rows:
        by_model[row.model].append(row)
    for model in _order_models_by_mean_cost(
        completed_filtered, by_model.keys()
    ):
        st.subheader(model)
        for row in sorted(by_model[model], key=lambda r: r.job_id):
            _render_job_section(row, score_keys)


def _render_job_section(row: DashboardRow, score_keys: list[str]) -> None:
    st.markdown(f"**`{row.job_id}`** · {row.status} · {row.non_null_run_count()} run(s)")
    if row.summary:
        st.caption(_truncate(row.summary, 200))

    table_rows: list[dict[str, Any]] = []
    for i, run in enumerate(row.runs):
        if run is None:
            table_rows.append(
                {
                    "Run": i + 1,
                    "Status": "—",
                    "Error": "",
                    **{f"score_{k}": None for k in score_keys},
                }
            )
            continue
        d: dict[str, Any] = {
            "Run": i + 1,
            "Status": run.status,
            "Error": _truncate(run.error, 120),
        }
        for k in score_keys:
            if k == "tool_use":
                d[f"score_{k}"] = dict(run.tool_use) if run.tool_use else None
            else:
                d[f"score_{k}"] = (run.scores or {}).get(k)
        table_rows.append(d)

    st.dataframe(table_rows, width="stretch", hide_index=True)

    chat_buttons = [
        run
        for run in row.runs
        if run is not None and run.chat_result is not None
    ]
    if not chat_buttons:
        return

    st.caption("Chat transcripts")
    n = len(chat_buttons)
    cols = st.columns(min(n, 6) or 1)
    for i, run in enumerate(chat_buttons):
        with cols[i % len(cols)]:
            safe_model = row.model.replace("/", "-").replace(" ", "_")
            key = f"chat-{safe_model}-{row.job_id}-{run.index}"
            if st.button(
                f"Run {run.index + 1}",
                key=key,
                type="secondary",
            ):
                _chat_result_dialog(
                    row.model,
                    row.job_id,
                    run.index,
                    run.chat_result,
                )
