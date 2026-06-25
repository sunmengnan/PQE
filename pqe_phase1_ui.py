#!/usr/bin/env python3
"""Streamlit UI for PQE Phase 1 results and visual analysis.

The desktop launcher opens this page for non-technical users.
"""

from __future__ import annotations

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
    find_input_files,
    group_spc_status,
    parse_cpk_workbook,
    parse_fai_workbook,
    worst_cavity_rows,
)


DEFAULT_DIR = Path(__file__).resolve().parent
GROUP_FIELDS = ["cavity", "spc_no", "fai_no"]
DISPLAY_COLUMNS = [
    "source_file", "file_tag", "report_type", "sheet_kind", "sheet_name", "cavity", "spc_no", "fai_no", "description",
    "dimension_type", "nominal", "tol_plus", "tol_minus", "usl", "lsl", "mean", "stddev", "cpk",
    "proposed_tol_plus", "proposed_tol_minus", "proposed_usl", "proposed_lsl", "proposed_cpk", "status", "cpk_status",
]


def records_to_frame(records: List[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    for column in GROUP_FIELDS + ["source_file", "report_type", "sheet_kind"]:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    if "file_tag" not in df.columns and "source_file" in df.columns:
        df["file_tag"] = df["source_file"].apply(lambda value: " | ".join(extract_parenthesized_parts(str(value))))
    elif "file_tag" in df.columns:
        df["file_tag"] = df["file_tag"].fillna("").astype(str)
    for column in ["mean", "stddev", "cpk", "proposed_cpk", "nominal", "usl", "lsl", "proposed_usl", "proposed_lsl"]:
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


def load_from_local(input_dir: Path, cpk_file: Optional[str], fai_file: Optional[str], target_cpk: float) -> Tuple[List[dict], List[dict], Path, Path]:
    cpk_path, fai_path = find_input_files(input_dir, cpk_file, fai_file)
    cpk_records, _ = parse_cpk_workbook(cpk_path, target_cpk)
    fai_records, _ = parse_fai_workbook(fai_path)
    return cpk_records, fai_records, cpk_path, fai_path


def load_from_uploads(cpk_upload, fai_upload, target_cpk: float) -> Tuple[List[dict], List[dict], Path, Path]:
    cpk_path = save_uploaded_file(cpk_upload)
    fai_path = save_uploaded_file(fai_upload)
    cpk_records, _ = parse_cpk_workbook(cpk_path, target_cpk)
    fai_records, _ = parse_fai_workbook(fai_path)
    for record in cpk_records:
        record["source_file"] = cpk_upload.name
        record["file_tag"] = " | ".join(extract_parenthesized_parts(cpk_upload.name))
    for record in fai_records:
        record["source_file"] = fai_upload.name
        record["file_tag"] = " | ".join(extract_parenthesized_parts(fai_upload.name))
    return cpk_records, fai_records, cpk_path, fai_path


def quality_metrics(fai_records: List[dict]) -> Tuple[int, int, int, int]:
    fai_ok = sum(1 for record in fai_records if record.get("status") == "OK")
    fai_ng = sum(1 for record in fai_records if record.get("status") == "NG")
    spc_rows = group_spc_status(fai_records)
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


def draw_fai_mean_chart(plot_df: pd.DataFrame, title: str) -> None:
    if plot_df.empty:
        st.warning("当前筛选条件下没有数据。")
        return
    fig = go.Figure()
    for fai_no in unique_values(plot_df, "fai_no"):
        values = plot_df.loc[plot_df["fai_no"].astype(str) == str(fai_no), "mean"]
        fig.add_trace(go.Box(
            y=values,
            x=[f"FAI {fai_no}"] * len(values),
            name=f"FAI {fai_no}",
            boxpoints="all",
            jitter=0.35,
            pointpos=0,
        ))
    add_reference_lines(fig, plot_df)
    fig.update_layout(
        title=title,
        height=560,
        xaxis_title="FAI No",
        yaxis_title="mean",
        showlegend=False,
        plot_bgcolor="rgba(240, 250, 240, 0.55)",
    )
    st.plotly_chart(fig, use_container_width=True)

    summary = plot_df.groupby("fai_no", dropna=False).agg(
        mean_value=("mean", "mean"),
        count=("mean", "size"),
        min_cpk=("cpk", "min"),
        nominal=("nominal", "mean"),
        drawing_usl=("usl", "mean"),
        drawing_lsl=("lsl", "mean"),
        proposed_usl=("proposed_usl", "mean"),
        proposed_lsl=("proposed_lsl", "mean"),
    ).reset_index()
    st.dataframe(summary, use_container_width=True)


def render_quadrant_tab(df: pd.DataFrame) -> None:
    st.subheader("象限图：指定 spc_no，显示不同 fai_no 的 mean 分布")
    base = df.dropna(subset=["mean"]).copy()
    if base.empty:
        st.warning("没有可绘制的 mean 数据。")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        source_filter = st.multiselect("筛选 source_file", unique_values(base, "source_file"), key="quad_source")
    with c2:
        file_tag_filter = st.multiselect("筛选文件名括号字段", unique_values(base, "file_tag"), key="quad_file_tag")
    with c3:
        spc_options = unique_values(base, "spc_no")
        selected_spc = st.selectbox("指定 spc_no", spc_options, index=0 if spc_options else None, key="quad_spc_single")
    with c4:
        use_cavity_dimension = st.checkbox("增加 cavity 维度", value=True)

    base = apply_multiselect_filter(base, "source_file", source_filter)
    base = apply_multiselect_filter(base, "file_tag", file_tag_filter)
    if selected_spc:
        base = base[base["spc_no"].astype(str) == str(selected_spc)]

    fai_filter = st.multiselect("筛选 fai_no（不选则显示该 spc_no 下全部 fai_no）", unique_values(base, "fai_no"), key="quad_fai")
    base = apply_multiselect_filter(base, "fai_no", fai_filter)

    if use_cavity_dimension:
        cavity_values = unique_values(base, "cavity")
        selected_cavities = st.multiselect("选择 cavity 图层", cavity_values, default=cavity_values, key="quad_cavity_layers")
        base = apply_multiselect_filter(base, "cavity", selected_cavities)

    if base.empty:
        st.warning("当前筛选条件下没有数据。")
        return

    if use_cavity_dimension:
        for cavity in unique_values(base, "cavity"):
            cavity_df = base[base["cavity"].astype(str) == str(cavity)]
            draw_fai_mean_chart(cavity_df, f"SPC {selected_spc} - {cavity} 不同 FAI 的 mean 分布")
    else:
        draw_fai_mean_chart(base, f"SPC {selected_spc} 不同 FAI 的 mean 分布")


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
            cpk_file = st.text_input("CPK 文件名（可选）", "") or None
            fai_file = st.text_input("FAI 文件名（可选）", "") or None
            load_clicked = st.button("解析数据", type="primary")
            load_args = ("local", input_dir, cpk_file, fai_file, target_cpk)
        else:
            cpk_upload = st.file_uploader("上传 CPK Excel", type=["xlsx", "xlsm"])
            fai_upload = st.file_uploader("上传 FAI Excel", type=["xlsx", "xlsm"])
            load_clicked = st.button("解析上传文件", type="primary", disabled=not (cpk_upload and fai_upload))
            load_args = ("upload", cpk_upload, fai_upload, target_cpk)

    if load_clicked or "pqe_df" not in st.session_state:
        try:
            with st.spinner("正在解析 Excel 并计算指标..."):
                if load_args[0] == "local":
                    _, input_dir, cpk_file, fai_file, target_cpk = load_args
                    cpk_records, fai_records, cpk_path, fai_path = load_from_local(input_dir, cpk_file, fai_file, target_cpk)
                else:
                    _, cpk_upload, fai_upload, target_cpk = load_args
                    if not cpk_upload or not fai_upload:
                        st.info("请先上传 CPK 和 FAI 文件。")
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

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总记录数", len(df))
    m2.metric("CPK记录数", len(cpk_records))
    m3.metric("FAI记录数", len(fai_records))
    m4.metric("低于目标CPK数", int(((df.get("cpk") < target_cpk) & df.get("cpk").notna()).sum()) if "cpk" in df.columns else 0)

    fai_ok, fai_ng, spc_ok, spc_ng = quality_metrics(fai_records)
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
                Path(st.session_state.get("cpk_path", "CPK.xlsx")),
                Path(st.session_state.get("fai_path", "FAI.xlsm")),
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
