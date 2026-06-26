#!/usr/bin/env python3
"""Streamlit UI for PQE Phase 1 results and visual analysis.

The desktop launcher opens this page for non-technical users.
"""

from __future__ import annotations

import re
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pqe_phase1_mvp import (
    export_workbook,
    extract_parenthesized_parts,
    find_input_file_lists,
    group_cpk_spc_status,
    group_spc_status,
    parse_cpk_workbooks,
    parse_fai_workbooks,
    worst_cavity_rows,
)


DEFAULT_DIR = Path(__file__).resolve().parent
GROUP_FIELDS = ["cavity", "spc_no", "fai_no"]
DISPLAY_COLUMNS = [
    "source_file", "file_tag", "report_type", "sheet_kind", "sheet_name", "cavity", "spc_no", "fai_no", "description",
    "dimension_type", "nominal", "tol_plus", "tol_minus", "usl", "lsl", "mean", "stddev", "cpk",
    "proposed_tol_plus", "proposed_tol_minus", "proposed_usl", "proposed_lsl", "proposed_cpk", "status", "cpk_status",
]
NUMERIC_COLUMNS = ["mean", "stddev", "cpk", "proposed_cpk", "nominal", "usl", "lsl", "proposed_usl", "proposed_lsl"]


def natural_sort_key(value: object) -> List[object]:
    text = str(value)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def records_to_frame(records: List[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    for column in DISPLAY_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    for column in GROUP_FIELDS + ["source_file", "report_type", "sheet_kind"]:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    if "file_tag" not in df.columns and "source_file" in df.columns:
        df["file_tag"] = df["source_file"].apply(lambda value: " | ".join(extract_parenthesized_parts(str(value))))
    elif "file_tag" in df.columns:
        df["file_tag"] = df["file_tag"].fillna("").astype(str)
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def unique_values(df: pd.DataFrame, column: str) -> List[str]:
    if df.empty or column not in df.columns:
        return []
    return sorted(v for v in df[column].dropna().astype(str).unique().tolist() if v != "")


def apply_multiselect_filter(df: pd.DataFrame, column: str, values: Iterable[str]) -> pd.DataFrame:
    values = list(values)
    if not values or column not in df.columns:
        return df
    return df[df[column].astype(str).isin(values)]


def filter_by_fields(df: pd.DataFrame, cavity: List[str], spc_no: List[str], fai_no: List[str]) -> pd.DataFrame:
    filtered = apply_multiselect_filter(df, "cavity", cavity)
    filtered = apply_multiselect_filter(filtered, "spc_no", spc_no)
    filtered = apply_multiselect_filter(filtered, "fai_no", fai_no)
    return filtered


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Filtered_Data") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


def save_uploaded_file(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(uploaded_file.getbuffer())
    temp.flush()
    temp.close()
    return Path(temp.name)


def load_from_local(input_dir: Path, cpk_file: Optional[str], fai_file: Optional[str], target_cpk: float, include_cpk: bool = True, include_fai: bool = True) -> Tuple[List[dict], List[dict], List[Path], List[Path]]:
    if not include_cpk and not include_fai:
        raise FileNotFoundError("Please select CPK or FAI to parse.")
    cpk_paths, fai_paths = find_input_file_lists(input_dir, cpk_file, fai_file, require_cpk=False, require_fai=False)
    if not include_cpk:
        cpk_paths = []
    if not include_fai:
        fai_paths = []
    if not cpk_paths and not fai_paths:
        raise FileNotFoundError("No CPK or FAI Excel file found.")
    cpk_records, _ = parse_cpk_workbooks(cpk_paths, target_cpk)
    fai_records, _ = parse_fai_workbooks(fai_paths)
    return cpk_records, fai_records, cpk_paths, fai_paths


def load_from_uploads(cpk_uploads, fai_uploads, target_cpk: float) -> Tuple[List[dict], List[dict], List[Path], List[Path]]:
    cpk_records: List[dict] = []
    fai_records: List[dict] = []
    cpk_paths: List[Path] = []
    fai_paths: List[Path] = []
    for cpk_upload in cpk_uploads:
        cpk_path = save_uploaded_file(cpk_upload)
        cpk_paths.append(cpk_path)
        file_records, _ = parse_cpk_workbooks([cpk_path], target_cpk)
        for record in file_records:
            record["source_file"] = cpk_upload.name
            record["file_tag"] = " | ".join(extract_parenthesized_parts(cpk_upload.name))
        cpk_records.extend(file_records)
    for fai_upload in fai_uploads:
        fai_path = save_uploaded_file(fai_upload)
        fai_paths.append(fai_path)
        file_records, _ = parse_fai_workbooks([fai_path])
        for record in file_records:
            record["source_file"] = fai_upload.name
            record["file_tag"] = " | ".join(extract_parenthesized_parts(fai_upload.name))
        fai_records.extend(file_records)
    return cpk_records, fai_records, cpk_paths, fai_paths


def quality_metrics(fai_records: List[dict], cpk_records: List[dict], target_cpk: float) -> Tuple[int, int, int, int]:
    fai_ok = sum(1 for record in fai_records if record.get("status") == "OK")
    fai_ng = sum(1 for record in fai_records if record.get("status") == "NG")
    spc_rows = group_cpk_spc_status(cpk_records, target_cpk)
    spc_ok = sum(1 for row in spc_rows if row.get("spc_status") == "OK")
    spc_ng = sum(1 for row in spc_rows if row.get("spc_status") == "NG")
    return fai_ok, fai_ng, spc_ok, spc_ng


def render_export_tab(df: pd.DataFrame) -> None:
    st.subheader("按 source_file / 文件名括号字段 / cavity 筛选并导出表格")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        source_filter = st.multiselect("source_file", unique_values(df, "source_file"))
    with col2:
        file_tag_filter = st.multiselect("文件名括号字段", unique_values(df, "file_tag"))
    with col3:
        cavity_filter = st.multiselect("cavity", unique_values(df, "cavity"))
    with col4:
        report_filter = st.multiselect("report_type", unique_values(df, "report_type"))

    filtered = apply_multiselect_filter(df, "source_file", source_filter)
    filtered = apply_multiselect_filter(filtered, "file_tag", file_tag_filter)
    filtered = apply_multiselect_filter(filtered, "cavity", cavity_filter)
    filtered = apply_multiselect_filter(filtered, "report_type", report_filter)

    visible_columns = [c for c in DISPLAY_COLUMNS if c in filtered.columns]
    table = filtered[visible_columns] if visible_columns else filtered
    st.caption(f"筛选后记录数: {len(table)}")
    st.dataframe(table, use_container_width=True, height=520)

    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button(
            "下载 CSV",
            table.to_csv(index=False).encode("utf-8-sig"),
            file_name="PQE_Filtered_By_Source_Tag_Cavity.csv",
            mime="text/csv",
        )
    with col_xlsx:
        st.download_button(
            "下载 Excel",
            to_excel_bytes(table),
            file_name="PQE_Filtered_By_Source_Tag_Cavity.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def add_reference_lines(fig: go.Figure, data: pd.DataFrame) -> None:
    line_specs = [
        ("proposed_usl", "Proposed USL", "red", "dash"),
        ("usl", "Drawing USL", "red", "solid"),
        ("nominal", "Nominal", "green", "solid"),
        ("lsl", "Drawing LSL", "red", "solid"),
        ("proposed_lsl", "Proposed LSL", "red", "dash"),
    ]
    for column, label, color, dash in line_specs:
        if column not in data.columns:
            continue
        values = pd.to_numeric(data[column], errors="coerce").dropna()
        if values.empty:
            continue
        fig.add_hline(
            y=float(values.mean()),
            line_color=color,
            line_dash=dash,
            annotation_text=label,
            annotation_position="right",
        )


def build_control_chart_summary(plot_df: pd.DataFrame, x_field: str) -> pd.DataFrame:
    if plot_df.empty or x_field not in plot_df.columns:
        return pd.DataFrame()
    summary = plot_df.groupby(x_field, dropna=False, sort=False).agg(
        mean_value=("mean", "mean"),
        count=("mean", "size"),
        min_mean=("mean", "min"),
        max_mean=("mean", "max"),
        min_cpk=("cpk", "min"),
        nominal=("nominal", "mean"),
        ucl=("usl", "mean"),
        lcl=("lsl", "mean"),
    ).reset_index()
    summary[x_field] = summary[x_field].fillna("").astype(str)
    summary = summary.sort_values(x_field, key=lambda series: series.map(natural_sort_key))
    return summary


def draw_spc_control_chart(plot_df: pd.DataFrame, x_field: str, title: str, xaxis_title: str) -> None:
    if plot_df.empty:
        st.warning("当前筛选条件下没有数据。")
        return
    if x_field not in plot_df.columns:
        st.warning(f"当前数据缺少 {x_field} 字段，无法绘制控制图。")
        return
    summary = build_control_chart_summary(plot_df, x_field)
    if summary.empty:
        st.warning("当前筛选条件下没有可汇总的数据。")
        return

    chart_df = plot_df.copy()
    chart_df[x_field] = chart_df[x_field].fillna("").astype(str)
    categories = summary[x_field].astype(str).tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df[x_field],
        y=chart_df["mean"],
        mode="markers",
        name="Mean 明细点",
        marker=dict(color="rgba(31, 119, 180, 0.52)", size=8),
        customdata=chart_df[["source_file", "cavity", "spc_no", "fai_no"]].fillna("").to_numpy(),
        hovertemplate=(
            f"{xaxis_title}: %{{x}}<br>mean: %{{y:.6g}}"
            "<br>source_file: %{customdata[0]}"
            "<br>cavity: %{customdata[1]}"
            "<br>spc_no: %{customdata[2]}"
            "<br>fai_no: %{customdata[3]}<extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=summary[x_field],
        y=summary["mean_value"],
        mode="lines+markers",
        name="Mean 平均值",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=9),
        hovertemplate=f"{xaxis_title}: %{{x}}<br>平均 mean: %{{y:.6g}}<extra></extra>",
    ))
    limit_specs = [
        ("ucl", "UCL", "#d62728", "dash"),
        ("nominal", "Nominal", "#2ca02c", "solid"),
        ("lcl", "LCL", "#d62728", "dash"),
    ]
    for column, label, color, dash in limit_specs:
        values = pd.to_numeric(summary[column], errors="coerce")
        if values.dropna().empty:
            continue
        fig.add_trace(go.Scatter(
            x=summary[x_field],
            y=values,
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2, dash=dash),
            marker=dict(size=7, symbol="line-ew"),
            connectgaps=False,
            hovertemplate=f"{xaxis_title}: %{{x}}<br>{label}: %{{y:.6g}}<extra></extra>",
        ))
    fig.update_layout(
        title=title,
        height=620,
        xaxis_title=xaxis_title,
        yaxis_title="mean",
        showlegend=True,
        hovermode="x unified",
        plot_bgcolor="rgba(240, 250, 240, 0.55)",
        xaxis=dict(categoryorder="array", categoryarray=categories, tickangle=-35),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(summary, use_container_width=True)


def render_quadrant_tab(df: pd.DataFrame) -> None:
    st.subheader("统计过程控制图：按 SPC / FAI / cavity 汇总 mean")
    base = df.dropna(subset=["mean"]).copy()
    if base.empty:
        st.warning("没有可绘制的 mean 数据。")
        return

    mode = st.radio(
        "控制图模式",
        [
            "1. 指定 SPC → 不同 FAI 的 mean 控制图",
            "2. 指定 FAI → 不同 SPC 的 mean 控制图",
            "3. 指定 cavity → 不同文件名的 mean 控制图",
        ],
        horizontal=False,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        source_filter = st.multiselect("筛选 source_file", unique_values(base, "source_file"), key="quad_source")
    with c2:
        file_tag_filter = st.multiselect("筛选文件名括号字段", unique_values(base, "file_tag"), key="quad_file_tag")
    with c3:
        report_filter = st.multiselect("筛选 report_type", unique_values(base, "report_type"), key="quad_report_type")

    base = apply_multiselect_filter(base, "source_file", source_filter)
    base = apply_multiselect_filter(base, "file_tag", file_tag_filter)
    base = apply_multiselect_filter(base, "report_type", report_filter)

    if mode.startswith("1."):
        spc_options = unique_values(base, "spc_no")
        selected_spc = st.multiselect("指定 SPC（可多选）", spc_options, default=spc_options[:1], key="quad_mode1_spc")
        plot_df = apply_multiselect_filter(base, "spc_no", selected_spc)
        cavity_options = unique_values(plot_df, "cavity")
        selected_cavities = st.multiselect("筛选 cavity（可选）", cavity_options, key="quad_mode1_cavity")
        plot_df = apply_multiselect_filter(plot_df, "cavity", selected_cavities)
        title = "指定 SPC：%s → 不同 FAI 的 mean 控制图" % (", ".join(selected_spc) if selected_spc else "未选择")
        x_field = "fai_no"
        xaxis_title = "FAI"
    elif mode.startswith("2."):
        fai_options = unique_values(base, "fai_no")
        selected_fai = st.multiselect("指定 FAI（可多选）", fai_options, default=fai_options[:1], key="quad_mode2_fai")
        plot_df = apply_multiselect_filter(base, "fai_no", selected_fai)
        cavity_options = unique_values(plot_df, "cavity")
        selected_cavities = st.multiselect("筛选 cavity（可选）", cavity_options, key="quad_mode2_cavity")
        plot_df = apply_multiselect_filter(plot_df, "cavity", selected_cavities)
        title = "指定 FAI：%s → 不同 SPC 的 mean 控制图" % (", ".join(selected_fai) if selected_fai else "未选择")
        x_field = "spc_no"
        xaxis_title = "SPC"
    else:
        cavity_options = unique_values(base, "cavity")
        selected_cavities = st.multiselect("指定 cavity（可多选）", cavity_options, default=cavity_options[:1], key="quad_mode3_cavity")
        plot_df = apply_multiselect_filter(base, "cavity", selected_cavities)
        f1, f2 = st.columns(2)
        with f1:
            spc_filter = st.multiselect("筛选 SPC（可选）", unique_values(plot_df, "spc_no"), key="quad_mode3_spc")
        with f2:
            fai_filter = st.multiselect("筛选 FAI（可选）", unique_values(plot_df, "fai_no"), key="quad_mode3_fai")
        plot_df = apply_multiselect_filter(plot_df, "spc_no", spc_filter)
        plot_df = apply_multiselect_filter(plot_df, "fai_no", fai_filter)
        title = "指定 cavity：%s → 不同文件名的 mean 控制图" % (", ".join(selected_cavities) if selected_cavities else "未选择")
        x_field = "source_file"
        xaxis_title = "文件名"

    if plot_df.empty:
        st.warning("当前筛选条件下没有数据。")
        return
    draw_spc_control_chart(plot_df, x_field, title, xaxis_title)


def render_matrix_tab(df: pd.DataFrame) -> None:
    st.subheader("矩阵散点图：按 cavity / spc_no / fai_no 组合显示 mean")
    base = df.dropna(subset=["mean"]).copy()
    if base.empty:
        st.warning("没有可绘制的 mean 数据。")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        cavity_filter = st.multiselect("筛选 cavity", unique_values(base, "cavity"), key="matrix_cavity")
    with c2:
        spc_filter = st.multiselect("筛选 spc_no", unique_values(base, "spc_no"), key="matrix_spc")
    with c3:
        fai_filter = st.multiselect("筛选 fai_no", unique_values(base, "fai_no"), key="matrix_fai")
    base = filter_by_fields(base, cavity_filter, spc_filter, fai_filter)

    x_field = st.selectbox("X 轴", GROUP_FIELDS, index=0, key="matrix_x")
    y_field = st.selectbox("Y 轴", GROUP_FIELDS, index=1, key="matrix_y")
    if x_field == y_field:
        st.warning("X 轴和 Y 轴请选择不同字段。")
        return

    plot_df = base.groupby([x_field, y_field], dropna=False).agg(
        mean_value=("mean", "mean"),
        count=("mean", "size"),
        min_cpk=("cpk", "min"),
    ).reset_index()
    if plot_df.empty:
        st.warning("当前筛选条件下没有数据。")
        return

    fig = px.scatter(
        plot_df,
        x=x_field,
        y=y_field,
        size="count",
        color="mean_value",
        hover_data=["mean_value", "count", "min_cpk"],
        color_continuous_scale="RdYlGn",
        title=f"{x_field} × {y_field} 矩阵散点图 / 颜色值 = mean 平均值",
    )
    fig.update_traces(marker=dict(opacity=0.82, line=dict(width=1, color="DarkSlateGrey")))
    fig.update_layout(height=680)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(plot_df, use_container_width=True)


def render_line_tab(df: pd.DataFrame) -> None:
    st.subheader("折线图：固定 cavity / spc_no / fai_no 中任意两个，显示剩余维度的 mean")
    base = df.dropna(subset=["mean"]).copy()
    if base.empty:
        st.warning("没有可绘制的 mean 数据。")
        return

    fixed_fields = st.multiselect(
        "选择两个限制条件",
        GROUP_FIELDS,
        default=["cavity", "spc_no"],
        max_selections=2,
    )
    if len(fixed_fields) != 2:
        st.warning("请选择两个限制条件。")
        return

    remaining_fields = [field for field in GROUP_FIELDS if field not in fixed_fields]
    x_field = remaining_fields[0]
    filter_values = {}
    cols = st.columns(2)
    for idx, field in enumerate(fixed_fields):
        with cols[idx]:
            options = unique_values(base, field)
            default = options[:1]
            filter_values[field] = st.multiselect(f"限制 {field}", options, default=default, key=f"line_{field}")

    filtered = base.copy()
    for field, values in filter_values.items():
        filtered = apply_multiselect_filter(filtered, field, values)

    color_field = fixed_fields[1]
    plot_df = filtered.groupby([x_field, color_field], dropna=False).agg(
        mean_value=("mean", "mean"),
        count=("mean", "size"),
        min_cpk=("cpk", "min"),
    ).reset_index().sort_values([color_field, x_field])

    if plot_df.empty:
        st.warning("当前筛选条件下没有数据。")
        return

    fig = px.line(
        plot_df,
        x=x_field,
        y="mean_value",
        color=color_field,
        markers=True,
        hover_data=["count", "min_cpk"],
        title=f"固定 {fixed_fields[0]} / {fixed_fields[1]}，按 {x_field} 显示 mean",
    )
    fig.update_layout(height=620, yaxis_title="mean")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(plot_df, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="PQE Phase 1 Dashboard", layout="wide")
    st.title("PQE Phase 1 数据分析界面")

    with st.sidebar:
        st.header("数据来源")
        target_cpk = st.number_input("Target CPK", min_value=0.01, value=1.33, step=0.01)
        source_mode = st.radio("读取方式", ["工作目录自动读取", "上传文件"], horizontal=False)

        if source_mode == "工作目录自动读取":
            input_dir = Path(st.text_input("Input directory", str(DEFAULT_DIR))).expanduser().resolve()
            parse_col1, parse_col2 = st.columns(2)
            with parse_col1:
                include_cpk = st.checkbox("解析 CPK", value=True)
            with parse_col2:
                include_fai = st.checkbox("解析 FAI", value=True)
            cpk_file = st.text_input("CPK 文件名（可选）", "") or None
            fai_file = st.text_input("FAI 文件名（可选）", "") or None
            load_clicked = st.button("解析数据", type="primary", disabled=not (include_cpk or include_fai))
            load_args = ("local", input_dir, cpk_file, fai_file, target_cpk, include_cpk, include_fai)
        else:
            cpk_upload = st.file_uploader("上传 CPK Excel（可多选）", type=["xlsx", "xlsm"], accept_multiple_files=True)
            fai_upload = st.file_uploader("上传 FAI Excel（可多选）", type=["xlsx", "xlsm"], accept_multiple_files=True)
            load_clicked = st.button("解析上传文件", type="primary", disabled=not (cpk_upload or fai_upload))
            load_args = ("upload", cpk_upload, fai_upload, target_cpk)

    if load_clicked or "pqe_df" not in st.session_state:
        try:
            with st.spinner("正在解析 Excel 并计算指标..."):
                if load_args[0] == "local":
                    _, input_dir, cpk_file, fai_file, target_cpk, include_cpk, include_fai = load_args
                    cpk_records, fai_records, cpk_path, fai_path = load_from_local(input_dir, cpk_file, fai_file, target_cpk, include_cpk, include_fai)
                else:
                    _, cpk_upload, fai_upload, target_cpk = load_args
                    if not cpk_upload and not fai_upload:
                        st.info("请至少上传 CPK 或 FAI 文件。")
                        return
                    cpk_records, fai_records, cpk_path, fai_path = load_from_uploads(cpk_upload, fai_upload, target_cpk)
                df = records_to_frame(cpk_records + fai_records)
                worst_df = pd.DataFrame(worst_cavity_rows(cpk_records))
                st.session_state["pqe_df"] = df
                st.session_state["cpk_records"] = cpk_records
                st.session_state["fai_records"] = fai_records
                st.session_state["worst_df"] = worst_df
                st.session_state["target_cpk"] = target_cpk
                st.session_state["cpk_path"] = cpk_path
                st.session_state["fai_path"] = fai_path
        except Exception as exc:
            st.error(f"解析失败: {exc}")
            return

    df = st.session_state.get("pqe_df", pd.DataFrame())
    if df.empty:
        st.info("没有数据。请在左侧选择或上传文件后点击解析。")
        return

    cpk_records = st.session_state.get("cpk_records", [])
    fai_records = st.session_state.get("fai_records", [])
    target_cpk = st.session_state.get("target_cpk", 1.33)
    cpk_table_records = [record for record in cpk_records if record.get("sheet_kind") == "CPK"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总记录数", len(cpk_table_records) + len(fai_records))
    m2.metric("CPK记录数", len(cpk_table_records))
    m3.metric("FAI记录数", len(fai_records))
    m4.metric("低于目标CPK数", sum(1 for record in cpk_table_records if record.get("cpk") is not None and record.get("cpk") < target_cpk))

    fai_ok, fai_ng, spc_ok, spc_ng = quality_metrics(fai_records, cpk_records, target_cpk)
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("FAI编号尺寸OK数", fai_ok)
    q2.metric("FAI编号尺寸NG数", fai_ng)
    q3.metric("SPC编号OK个数", spc_ok)
    q4.metric("SPC编号NG个数", spc_ng)

    tab_export, tab_quad, tab_matrix, tab_line, tab_worst, tab_full_export = st.tabs([
        "筛选导出", "象限图", "矩阵散点图", "折线图", "Worst Cavity", "完整报告导出",
    ])
    with tab_export:
        render_export_tab(df)
    with tab_quad:
        render_quadrant_tab(df)
    with tab_matrix:
        render_matrix_tab(df)
    with tab_line:
        render_line_tab(df)
    with tab_worst:
        st.subheader("按 spc_no 筛选得到的最差 cavity")
        st.dataframe(st.session_state.get("worst_df", pd.DataFrame()), use_container_width=True, height=560)
    with tab_full_export:
        st.subheader("导出完整 Phase 1 Excel 报告")
        output = BytesIO()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_output:
            export_workbook(
                Path(temp_output.name),
                cpk_records,
                fai_records,
                target_cpk,
                st.session_state.get("cpk_path", [Path("CPK.xlsx")]),
                st.session_state.get("fai_path", [Path("FAI.xlsm")]),
            )
            output.write(Path(temp_output.name).read_bytes())
        st.download_button(
            "下载完整 Excel 报告",
            output.getvalue(),
            file_name="PQE_Phase1_UI_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
