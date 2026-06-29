import streamlit as st
from datetime import datetime

ITEMS_PER_PAGE = 15


def render(api_get, api_post):
    st.title("Tickets")

    status_filter = st.selectbox("Status", ["All", "open", "resolved", "escalated"])
    search = st.text_input("Search", placeholder="Search by name, email, or ID...")

    page = st.session_state.get("tickets_page", 1)

    params = {"page": page, "per_page": ITEMS_PER_PAGE}
    if status_filter != "All":
        params["status"] = status_filter
    if search:
        params["search"] = search

    data = api_get("/api/admin/tickets", params=params)
    if data is None:
        st.warning("Could not load tickets.")
        return

    tickets = data.get("items", [])
    total = data.get("total", 0)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    st.markdown(f"**{total} tickets** · Page {page} of {total_pages}")

    if not tickets:
        st.info("No tickets found.")
        return

    rows = []
    for t in tickets:
        status_label = t.get("status", "open")
        rows.append(f"""
        <tr>
          <td>{t.get("id", "")}</td>
          <td>{t.get("customer_name", "")}</td>
          <td>{t.get("customer_email", "")}</td>
          <td>{t.get("subject", "")[:60]}</td>
          <td><span class="status-badge {status_label}">{status_label}</span></td>
          <td>{t.get("created_at", "")[:10]}</td>
          <td>
            <a href="?page=Conversation&ticket_id={t.get("id", "")}" target="_self">
              <button class="btn btn-sm btn-outline">View</button>
            </a>
          </td>
        </tr>
        """)

    st.markdown(
        f"""
    <style>
    .ticket-table {{ width: 100%; border-collapse: collapse; }}
    .ticket-table th {{ text-align: left; padding: 0.6rem 0.5rem; border-bottom: 2px solid var(--border-color); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); }}
    .ticket-table td {{ padding: 0.5rem; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }}
    .ticket-table tr:hover {{ background: var(--bg-secondary); }}
    </style>
    <table class="ticket-table">
      <thead><tr>
        <th>ID</th><th>Name</th><th>Email</th><th>Subject</th><th>Status</th><th>Date</th><th></th>
      </tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if page > 1 and st.button("← Previous"):
            st.session_state.tickets_page = page - 1
            st.rerun()
    with col3:
        if page < total_pages and st.button("Next →"):
            st.session_state.tickets_page = page + 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Export CSV", use_container_width=False):
        all_data = api_get("/api/admin/tickets", params={"per_page": 10000, "page": 1})
        if all_data and all_data.get("items"):
            import csv, io

            items = all_data["items"]
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=items[0].keys())
            w.writeheader()
            w.writerows(items)
            st.download_button(
                "Download CSV", buf.getvalue(), "tickets.csv", "text/csv"
            )
