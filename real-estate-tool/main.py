"""Streamlit user interface for the real-estate research tool."""

import streamlit as st

from rag import generate_answer, process_urls

st.set_page_config(page_title="Real Estate Research Tool", page_icon="🏙️")
st.title("Real Estate Research Tool")

urls = [
    st.sidebar.text_input("URL 1"),
    st.sidebar.text_input("URL 2"),
    st.sidebar.text_input("URL 3"),
]
status = st.empty()

if st.sidebar.button("Process URLs", type="primary"):
    try:
        with st.spinner("Processing articles..."):
            for message in process_urls(urls):
                status.info(message)
    except Exception as exc:
        status.error(f"Could not process the URLs: {exc}")

query = st.text_input("Question", placeholder="Ask about the processed articles")
if query:
    try:
        with st.spinner("Generating an answer..."):
            answer, sources = generate_answer(query)
        st.header("Answer")
        st.write(answer)
        if sources:
            st.subheader("Sources")
            for source in sources:
                st.markdown(f"- [{source}]({source})")
    except Exception as exc:
        st.error(str(exc))
