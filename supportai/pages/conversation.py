import streamlit as st
import requests


def render(api_get):
    st.title("Conversation Viewer")

    ticket_id = st.text_input("Ticket ID", placeholder="Enter ticket ID...")
    if not ticket_id:
        st.info("Enter a ticket ID to view the conversation.")
        return

    data = api_get(f"/api/admin/tickets/{ticket_id}")
    if data is None:
        st.warning("Ticket not found or API unreachable.")
        return

    ticket = data.get("ticket", data)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"#{ticket.get('id', '')} — {ticket.get('subject', 'No Subject')}")

        status = ticket.get("status", "open")
        st.markdown(
            f'<span class="status-badge {status}">{status}</span>',
            unsafe_allow_html=True,
        )

        messages = ticket.get("messages", [])
        if not messages:
            st.info("No messages.")
            return

        st.markdown(
            '<div style="display:flex;flex-direction:column;gap:0;">',
            unsafe_allow_html=True,
        )
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            ts = msg.get("created_at", "")[:19]
            method = msg.get("method", None)

            badge = ""
            if method:
                badge = f'<span class="method-badge {method}">{method}</span>'

            bubble_class = "user" if role == "user" else "agent"
            st.markdown(
                f'<div class="chat-bubble {bubble_class}">'
                f"{badge}{content}"
                f'<div class="timestamp">{ts}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Details")
        meta = ticket.get("metadata", {})
        details = {
            "Customer": ticket.get("customer_name", "—"),
            "Email": ticket.get("customer_email", "—"),
            "Status": status,
            "Priority": ticket.get("priority", "—"),
            "Category": ticket.get("category", "—"),
            "Created": ticket.get("created_at", "")[:10]
            if ticket.get("created_at")
            else "—",
            "Resolved": ticket.get("resolved_at", "")[:10]
            if ticket.get("resolved_at")
            else "—",
            "LLM Model": meta.get("llm_model", "—"),
            "Sentiment": f"{meta.get('sentiment', 0):.2f}"
            if meta.get("sentiment")
            else "—",
            "Resolution": ticket.get("resolution_summary", "—"),
        }
        for label, val in details.items():
            st.markdown(f"**{label}**  \n{val}")
            st.markdown("---")
