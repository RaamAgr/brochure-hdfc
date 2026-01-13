import streamlit as st
import google.generativeai as genai
import tempfile
import os

st.set_page_config(page_title="Gemini 3 PDF Chain", layout="wide")

# --- UI Header ---
st.title("🔗 Gemini 3 Pro PDF Chain")
st.info("Step-by-step processing: PDF -> Prompt 1 -> Prompt 2 -> Prompt 3")

# --- Configuration ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

# --- Step Prompts ---
p1 = st.text_area("Step 1: Initial Prompt", "Extract the executive summary and key metrics.")
p2 = st.text_area("Step 2: Analysis Prompt", "Based on those metrics, provide a SWOT analysis.")
p3 = st.text_area("Step 3: Final Refinement", "Write a 3-bullet executive email based on that SWOT.")

if st.button("Start Processing"):
    if not (api_key and uploaded_file):
        st.error("Missing API Key or PDF file.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-3-pro") # Using Gemini 3 Pro

            # 1. Upload File to Google Cloud (Gemini 3 handles larger files better)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            with st.spinner("Uploading and analyzing PDF..."):
                doc_file = genai.upload_file(path=tmp_path)
                # Chat session keeps the state across your 3 steps
                chat = model.start_chat(history=[])

                # STEP 1
                st.subheader("Step 1 Output")
                res1 = chat.send_message([doc_file, p1])
                st.write(res1.text)

                # STEP 2
                st.subheader("Step 2 Output")
                res2 = chat.send_message(p2)
                st.write(res2.text)

                # STEP 3
                st.subheader("Step 3 Output")
                res3 = chat.send_message(p3)
                st.markdown("---")
                st.success("Final Result Ready!")
                st.write(res3.text)

                # DOWNLOAD
                st.download_button(
                    label="Download Result (.txt)",
                    data=res3.text,
                    file_name="gemini_3_final_output.txt",
                    mime="text/plain"
                )

            os.remove(tmp_path) # Cleanup
        except Exception as e:
            st.error(f"Error: {e}")
