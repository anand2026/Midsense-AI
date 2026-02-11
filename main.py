import streamlit as st
import requests

st.set_page_config(page_title="MediSense AI", page_icon="🩺")
st.title("🩺 MediSense AI — Agentic Medical Assistant")

st.markdown("Ask any medical question and get answers retrieved from trusted documents and AI reasoning.")

user_question = st.text_input("Type your medical question here:")

if st.button("Ask MediSense AI"):
    if user_question.strip() != "":
        with st.spinner("MediSense AI is thinking..."):
            try:
                response = requests.post(
                    "https://medisenseai.onrender.com/process/",
                    json={"question": user_question}
                )
                if response.status_code == 200:
                    result = response.json()
                    # Adapt to your backend response structure
                    answer = result.get("generation")
                    st.success("Answer:")
                    st.write(answer)
                    st.success("Agent flow")
                    st.write(result.get("flow"))
                else:
                    st.error(f"Something went wrong! Status code: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a question before submitting.")
