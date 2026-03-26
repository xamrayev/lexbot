import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")

st.set_page_config(page_title="Mehnat Kodeksi Chat", page_icon="⚖️")
st.title("⚖️ O'zbekiston Mehnat Kodeksi")
st.caption("GraphRAG AI Yordamchisi")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Savolingizni bering..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Qidirilmoqda..."):
            try:
                resp = requests.post(f"{API_URL}/query", json={"query": prompt})
                if resp.status_code == 200:
                    data = resp.json()
                    st.markdown(data["answer"])

                    if data["sources"]:
                        with st.expander("📚 Manbalar"):
                            for src in data["sources"]:
                                st.write(
                                    f"**{src['code']} {src['modda_number']}-modda**: {src['modda_title']}"
                                )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": data["answer"]}
                    )
                else:
                    st.error("Xatolik yuz berdi")
            except Exception as e:
                st.error(f"Xatolik: {str(e)}")
