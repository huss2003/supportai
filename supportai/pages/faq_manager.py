import streamlit as st


def render(api_get, api_post, api_delete):
    st.title("FAQ Manager")

    search_query = st.text_input(
        "Search FAQs", placeholder="Search by question or answer..."
    )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        category_filter = st.selectbox(
            "Category",
            [
                "All",
                "general",
                "billing",
                "technical",
                "account",
                "shipping",
                "returns",
                "other",
            ],
        )
    with col2:
        if st.button("+ New FAQ", type="primary"):
            st.session_state.show_faq_form = True

    data = api_get("/api/admin/faqs")
    if data is None:
        st.warning("Could not load FAQs.")
        return

    faqs = data.get("items", [])
    if search_query:
        sq = search_query.lower()
        faqs = [
            f
            for f in faqs
            if sq in f.get("question", "").lower() or sq in f.get("answer", "").lower()
        ]
    if category_filter != "All":
        faqs = [f for f in faqs if f.get("category") == category_filter]

    if not faqs:
        st.info("No FAQs found.")

    for faq in faqs:
        q = faq.get("question", "")
        a = faq.get("answer", "")
        cat = faq.get("category", "general")
        faq_id = faq.get("id", "")

        with st.container():
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(
                    f'<div class="card" style="margin-bottom:0.5rem;">'
                    f'<span class="status-badge open">{cat}</span> '
                    f"<strong>{q}</strong>"
                    f'<p style="color:var(--text-secondary);margin-top:0.3rem;font-size:0.9rem;">{a[:200]}{"..." if len(a) > 200 else ""}</p>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_b:
                if st.button("Edit", key=f"edit_{faq_id}"):
                    st.session_state.editing_faq = faq
                if st.button("Delete", key=f"del_{faq_id}"):
                    r = api_delete(f"/api/admin/faqs/{faq_id}")
                    if r is not None:
                        st.success("Deleted")
                        st.rerun()

        st.markdown("<hr style='margin:0.2rem 0;opacity:0.3;'>", unsafe_allow_html=True)

    # --- new / edit modal ---
    show_form = (
        st.session_state.get("show_faq_form", False)
        or st.session_state.get("editing_faq") is not None
    )
    editing = st.session_state.get("editing_faq", None)

    if show_form:
        with st.container():
            st.markdown(
                '<div class="modal-overlay"><div class="modal-content">',
                unsafe_allow_html=True,
            )
            st.subheader("Edit FAQ" if editing else "New FAQ")

            question = st.text_input(
                "Question", value=editing.get("question", "") if editing else ""
            )
            answer = st.text_area(
                "Answer", value=editing.get("answer", "") if editing else "", height=200
            )
            category = st.selectbox(
                "Category",
                [
                    "general",
                    "billing",
                    "technical",
                    "account",
                    "shipping",
                    "returns",
                    "other",
                ],
                index=[
                    "general",
                    "billing",
                    "technical",
                    "account",
                    "shipping",
                    "returns",
                    "other",
                ].index(editing.get("category", "general"))
                if editing
                and editing.get("category")
                in [
                    "general",
                    "billing",
                    "technical",
                    "account",
                    "shipping",
                    "returns",
                    "other",
                ]
                else 0,
            )

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("Save"):
                    if question and answer:
                        payload = {
                            "question": question,
                            "answer": answer,
                            "category": category,
                        }
                        if editing:
                            r = api_post(f"/api/admin/faqs/{editing['id']}", payload)
                        else:
                            r = api_post("/api/admin/faqs", payload)
                        if r is not None:
                            st.success("Saved")
                            st.session_state.show_faq_form = False
                            st.session_state.editing_faq = None
                            st.rerun()
                    else:
                        st.warning("Question and answer are required.")
            with col_s2:
                if st.button("Cancel"):
                    st.session_state.show_faq_form = False
                    st.session_state.editing_faq = None
                    st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)
