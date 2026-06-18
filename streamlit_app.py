import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from pathlib import Path

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataBot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', 'Inter', sans-serif;
}

/* Background */
.stApp {
    background: #0f1117;
    color: #e8eaf6;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #161b27;
    border-right: 1px solid #1e2d45;
}
[data-testid="stSidebar"] * {
    color: #c8d6f0 !important;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1a2340 0%, #1e2d45 100%);
    border: 1px solid #2a3f62;
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #3d8ef8, #7b5ea7, #3d8ef8);
    background-size: 200% 100%;
    animation: shimmer 3s linear infinite;
}
@keyframes shimmer {
    0% { background-position: 0% 0%; }
    100% { background-position: 200% 0%; }
}
.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba(61,142,248,0.18);
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 900;
    color: #60a5fa;
    line-height: 1.1;
    margin-bottom: 6px;
}
.metric-label {
    font-size: 0.85rem;
    color: #8ba3cc;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Insight bar */
.insight-bar {
    background: linear-gradient(135deg, #1a2a1a 0%, #1a2d1e 100%);
    border: 1px solid #2a4a2e;
    border-left: 4px solid #4ade80;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 20px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.insight-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
}
.insight-text {
    color: #a7f3d0;
    font-size: 1rem;
    line-height: 1.6;
    font-weight: 500;
}

/* Section headers */
.section-header {
    color: #e2e8f0;
    font-size: 1.15rem;
    font-weight: 700;
    margin: 32px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2d45;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* File title */
.file-title {
    background: linear-gradient(135deg, #1a2340, #1e2d45);
    border: 1px solid #2a3f62;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.file-icon { font-size: 2.5rem; }
.file-name {
    font-size: 1.6rem;
    font-weight: 900;
    color: #e2e8f0;
    margin: 0;
}
.file-meta {
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 4px;
}

/* Plotly charts background */
.js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2d45;
    border-radius: 12px;
    overflow: hidden;
}

/* Selectbox / multiselect */
[data-baseweb="select"] {
    background: #161b27 !important;
}

/* Divider */
hr {
    border-color: #1e2d45;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

REPORTS_DIR = "reports"
PLOTLY_TEMPLATE = "plotly_dark"
CHART_BG = "rgba(0,0,0,0)"
CHART_PAPER_BG = "rgba(22,27,39,0.0)"
COLOR_SEQ = ["#3d8ef8", "#7b5ea7", "#4ade80", "#fb923c", "#f472b6", "#facc15", "#38bdf8"]


# ─── Helpers ────────────────────────────────────────────────────────────────────

def load_report(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_value(val):
    if isinstance(val, float):
        if val >= 1_000_000:
            return f"{val/1_000_000:.2f}M"
        if val >= 1_000:
            return f"{val/1_000:.1f}K"
        return f"{val:,.2f}"
    if isinstance(val, int):
        if val >= 1_000_000:
            return f"{val/1_000_000:.2f}M"
        if val >= 1_000:
            return f"{val/1_000:.1f}K"
        return f"{val:,}"
    return str(val)


def apply_plotly_style(fig):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family="Cairo, Inter, sans-serif", color="#c8d6f0"),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
        xaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45"),
        yaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45"),
    )
    return fig


def make_chart(chart_cfg: dict, df: pd.DataFrame):
    chart_type = chart_cfg.get("type", "bar")
    title = chart_cfg.get("title", "")
    x_col = chart_cfg.get("x_column")
    y_col = chart_cfg.get("y_column")
    color_col = chart_cfg.get("color_column")

    # Validate columns exist
    for col in [x_col, y_col, color_col]:
        if col and col not in df.columns:
            return None

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                         title=title, color_discrete_sequence=COLOR_SEQ)
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, color=color_col,
                          title=title, color_discrete_sequence=COLOR_SEQ,
                          markers=True)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col,
                         title=title, color_discrete_sequence=COLOR_SEQ,
                         hole=0.35)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                             title=title, color_discrete_sequence=COLOR_SEQ,
                             size_max=14)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_col, color=color_col,
                               title=title, color_discrete_sequence=COLOR_SEQ)
        elif chart_type == "area":
            fig = px.area(df, x=x_col, y=y_col, color=color_col,
                          title=title, color_discrete_sequence=COLOR_SEQ)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title,
                         color_discrete_sequence=COLOR_SEQ)

        return apply_plotly_style(fig)
    except Exception:
        return None


# ─── Sidebar ─────────────────────────────────────────────────────────────────────

def get_available_reports() -> list[str]:
    if not os.path.exists(REPORTS_DIR):
        return []
    return sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")], reverse=True)


with st.sidebar:
    st.markdown("## 📊 DataBot")
    st.markdown("---")

    reports = get_available_reports()

    # Allow URL param to pre-select a report
    query_report = st.query_params.get("report", "")

    if not reports:
        st.warning("لا توجد تقارير بعد.\nأرسل ملف CSV/Excel للبوت.")
        st.stop()

    default_idx = 0
    if query_report and query_report in reports:
        default_idx = reports.index(query_report)

    selected_report = st.selectbox(
        "اختر التقرير",
        options=reports,
        index=default_idx,
        format_func=lambda x: x.replace("report_", "").replace(".json", ""),
    )

    st.markdown("---")
    st.markdown(f"**عدد التقارير:** {len(reports)}")
    st.markdown(
        '<p style="color:#4a5568;font-size:0.75rem;margin-top:32px;">DataBot • Powered by Claude AI</p>',
        unsafe_allow_html=True,
    )

# ─── Load Data ───────────────────────────────────────────────────────────────────

report_path = os.path.join(REPORTS_DIR, selected_report)
try:
    report = load_report(report_path)
except Exception as e:
    st.error(f"خطأ في تحميل التقرير: {e}")
    st.stop()

raw_data = report.get("raw_data", [])
df_full = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
file_name = report.get("file_name", selected_report)
insights = report.get("insights", "")
metrics = report.get("metrics", [])
charts = report.get("charts", [])

# Compute metric values from raw_data if not stored
for m in metrics:
    if "value" not in m or m["value"] is None:
        col = m.get("column")
        op = m.get("operation", "sum")
        if col and col in df_full.columns:
            try:
                series = pd.to_numeric(df_full[col], errors="coerce")
                if op == "sum":
                    m["value"] = series.sum()
                elif op == "mean":
                    m["value"] = series.mean()
                elif op == "max":
                    m["value"] = series.max()
                elif op == "min":
                    m["value"] = series.min()
                elif op == "count":
                    m["value"] = series.count()
            except Exception:
                m["value"] = "—"

# ─── File Title ──────────────────────────────────────────────────────────────────

ext = Path(file_name).suffix.lower()
icon = "📊" if ext in [".xlsx", ".xls"] else "📋"

row_count = len(df_full)
col_count = len(df_full.columns)

st.markdown(f"""
<div class="file-title">
  <div class="file-icon">{icon}</div>
  <div>
    <div class="file-name">{file_name}</div>
    <div class="file-meta">{row_count:,} صف &nbsp;·&nbsp; {col_count} عمود &nbsp;·&nbsp; {len(charts)} رسم بياني</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Metric Cards ────────────────────────────────────────────────────────────────

if metrics:
    st.markdown('<div class="section-header">📈 المقاييس الرئيسية</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(metrics), 4))
    for i, m in enumerate(metrics[:4]):
        val = m.get("value", "—")
        label = m.get("label", m.get("column", "—"))
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{format_value(val)}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

# ─── Insight Bar ─────────────────────────────────────────────────────────────────

if insights:
    st.markdown(f"""
    <div class="insight-bar">
        <div class="insight-icon">🤖</div>
        <div class="insight-text">{insights}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── Interactive Filters ─────────────────────────────────────────────────────────

df = df_full.copy()

if not df.empty:
    st.markdown('<div class="section-header">🔽 الفلاتر التفاعلية</div>', unsafe_allow_html=True)

    cat_cols = [c for c in df.columns if df[c].dtype == object and df[c].nunique() <= 50]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    filter_applied = False

    if cat_cols:
        fcols = st.columns(min(len(cat_cols), 3))
        for i, col in enumerate(cat_cols[:3]):
            options = sorted(df[col].dropna().unique().tolist())
            selected = fcols[i].multiselect(
                f"تصفية: {col}",
                options=options,
                default=[],
                key=f"filter_{col}",
            )
            if selected:
                df = df[df[col].isin(selected)]
                filter_applied = True

    if num_cols:
        ncols = st.columns(min(len(num_cols), 2))
        for i, col in enumerate(num_cols[:2]):
            min_val = float(df_full[col].min())
            max_val = float(df_full[col].max())
            if min_val < max_val:
                rng = ncols[i].slider(
                    f"نطاق: {col}",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val),
                    key=f"range_{col}",
                )
                df = df[(df[col] >= rng[0]) & (df[col] <= rng[1])]
                if rng != (min_val, max_val):
                    filter_applied = True

    if filter_applied:
        st.caption(f"✅ يعرض {len(df):,} صف من أصل {len(df_full):,}")

# ─── Charts ──────────────────────────────────────────────────────────────────────

if charts and not df.empty:
    st.markdown('<div class="section-header">📉 الرسوم البيانية</div>', unsafe_allow_html=True)

    # Pair charts in rows of 2
    for i in range(0, len(charts), 2):
        pair = charts[i: i + 2]
        chart_cols = st.columns(len(pair))
        for j, chart_cfg in enumerate(pair):
            fig = make_chart(chart_cfg, df)
            if fig:
                with chart_cols[j]:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                with chart_cols[j]:
                    st.warning(f"تعذّر رسم: {chart_cfg.get('title', '')}")

# ─── Data Table ──────────────────────────────────────────────────────────────────

if not df.empty:
    st.markdown('<div class="section-header">🗂️ جدول البيانات</div>', unsafe_allow_html=True)

    # Optional ranking column
    num_cols_available = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    rank_col = None
    if num_cols_available:
        tcol1, tcol2 = st.columns([3, 1])
        rank_col = tcol2.selectbox(
            "ترتيب حسب",
            options=["— بدون —"] + num_cols_available,
            key="rank_select",
        )
        search_term = tcol1.text_input("🔍 بحث في البيانات", key="table_search")
    else:
        search_term = st.text_input("🔍 بحث في البيانات", key="table_search")

    display_df = df.copy()

    if search_term:
        mask = display_df.apply(
            lambda col: col.astype(str).str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        display_df = display_df[mask]

    if rank_col and rank_col != "— بدون —":
        display_df = display_df.sort_values(rank_col, ascending=False).reset_index(drop=True)
        display_df.index = display_df.index + 1  # 1-based rank
        display_df.index.name = "#"

    st.dataframe(
        display_df,
        use_container_width=True,
        height=420,
    )

    # Download button
    csv_bytes = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ تحميل البيانات CSV",
        data=csv_bytes,
        file_name=f"{Path(file_name).stem}_filtered.csv",
        mime="text/csv",
    )
