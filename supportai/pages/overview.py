import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def render(api_get):
    st.title("Overview")
    data = api_get("/api/admin/overview")
    if data is None:
        st.warning("Could not load overview data.")
        return

    kpis = data.get("kpis", {})
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        val = kpis.get("total_conversations", 0)
        delta = kpis.get("conversations_delta", None)
        st.markdown(
            f'<div class="card kpi-card"><div class="kpi-value">{val:,}</div>'
            f'<div class="kpi-label">Total Conversations</div>'
            + (
                f'<div class="kpi-delta positive">↑ {delta}%</div>'
                if delta and delta > 0
                else f'<div class="kpi-delta negative">↓ {abs(delta)}%</div>'
                if delta and delta < 0
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    with col2:
        val = kpis.get("resolution_rate", 0)
        st.markdown(
            f'<div class="card kpi-card"><div class="kpi-value">{val:.1f}%</div>'
            f'<div class="kpi-label">Resolution Rate</div></div>',
            unsafe_allow_html=True,
        )

    with col3:
        val = kpis.get("avg_sentiment", 0)
        st.markdown(
            f'<div class="card kpi-card"><div class="kpi-value">{val:.2f}</div>'
            f'<div class="kpi-label">Avg Sentiment</div></div>',
            unsafe_allow_html=True,
        )

    with col4:
        val = kpis.get("llm_calls", 0)
        delta = kpis.get("llm_calls_delta", None)
        st.markdown(
            f'<div class="card kpi-card"><div class="kpi-value">{val:,}</div>'
            f'<div class="kpi-label">LLM Calls (today)</div>'
            + (
                f'<div class="kpi-delta positive">↑ {delta}%</div>'
                if delta and delta > 0
                else f'<div class="kpi-delta negative">↓ {abs(delta)}%</div>'
                if delta and delta < 0
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Conversations over Time")
        timeline = data.get("timeline", [])
        if timeline:
            dates = [t.get("date") for t in timeline]
            counts = [t.get("count", 0) for t in timeline]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=counts,
                    mode="lines+markers",
                    line=dict(color="#6366f1", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(99,102,241,0.12)",
                )
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis=dict(title=None),
                yaxis=dict(title="Conversations"),
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timeline data.")

        st.subheader("Sentiment Distribution")
        sentiment = data.get("sentiment_distribution", {})
        if sentiment:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=list(sentiment.keys()),
                        values=list(sentiment.values()),
                        marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]),
                        hole=0.45,
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                height=280,
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sentiment data.")

    with col2:
        st.subheader("Resolution Rate (7-day)")
        resolution = data.get("resolution_timeline", [])
        if resolution:
            dates = [r.get("date") for r in resolution]
            rates = [r.get("rate", 0) * 100 for r in resolution]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=rates,
                    mode="lines+markers",
                    line=dict(color="#10b981", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(16,185,129,0.12)",
                )
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis=dict(title=None),
                yaxis=dict(title="%", range=[0, 100]),
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No resolution timeline.")

        st.subheader("LLM Usage by Model")
        llm = data.get("llm_model_breakdown", {})
        if llm:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=list(llm.keys()), y=list(llm.values()), marker_color="#3b82f6"
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis=dict(title=None),
                yaxis=dict(title="Calls"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No LLM usage data.")
