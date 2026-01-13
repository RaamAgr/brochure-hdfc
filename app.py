import streamlit as st
import google.generativeai as genai
import tempfile
import os

# --- Page Config ---
st.set_page_config(page_title="Gemini 3 Pro | Step-by-Step Chain", layout="wide")

st.title("🔗 Gemini 3 Pro: Step-by-Step Chain")
st.markdown("""
**Workflow:**
1. Upload PDF → Run Step 1 (Analysis)
2. Review Output 1 → Run Step 2 (Risk Assessment)
3. Review Output 2 → Run Step 3 (Final Report)
""")

# --- Sidebar: Setup ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    # Reset button to clear state and start over
    if st.button("Reset Chain"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- Session State Initialization ---
# This "memory" keeps data alive between button clicks
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "step1_result" not in st.session_state:
    st.session_state.step1_result = None
if "step2_result" not in st.session_state:
    st.session_state.step2_result = None
if "step3_result" not in st.session_state:
    st.session_state.step3_result = None

# --- Helper: Initialize Chat ---
def init_gemini(api_key, file_obj):
    try:
        genai.configure(api_key=api_key)
        # Using the latest Gemini 3 model ID
        model = genai.GenerativeModel("gemini-3-pro-preview") 
        
        # Upload file to Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("Uploading PDF to Gemini 3 context window..."):
            uploaded_doc = genai.upload_file(tmp_path)
            # Wait for processing if necessary (Gemini 3 is usually instant)
            import time
            while uploaded_doc.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_doc = genai.get_file(uploaded_doc.name)
                
        os.remove(tmp_path)
        
        # Start chat with the file
        chat = model.start_chat(history=[
            {"role": "user", "parts": [uploaded_doc, "Analyze this file."]},
            {"role": "model", "parts": ["I have analyzed the file. Ready for your prompts."]}
        ])
        return chat
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# ==========================================
# STEP 1: INITIAL ANALYSIS
# ==========================================
st.divider()
st.subheader("Step 1: Initial Extraction")

prompt1 = st.text_area("Prompt 1", value="Summarize the key technical requirements in this document.", height=100)

# Button 1 only runs if we haven't done Step 1 yet, or if we want to re-run it
if st.button("Run Step 1", type="primary"):
    if not api_key or not uploaded_file:
        st.warning("Please provide API Key and File.")
    else:
        # Initialize session if needed
        if st.session_state.chat_session is None:
            st.session_state.chat_session = init_gemini(api_key, uploaded_file)
        
        if st.session_state.chat_session:
            with st.spinner("Gemini 3 is thinking..."):
                response = st.session_state.chat_session.send_message(prompt1)
                st.session_state.step1_result = response.text
                # Clear future steps if we re-run step 1
                st.session_state.step2_result = None
                st.session_state.step3_result = None

# Display Output 1 if it exists
if st.session_state.step1_result:
    st.info("✅ Step 1 Output Generated")
    st.write(st.session_state.step1_result)
else:
    st.stop() # Stop execution here until Step 1 is done

# ==========================================
# STEP 2: REFINEMENT
# ==========================================
st.divider()
st.subheader("Step 2: Risk Analysis")
st.markdown("*Proceed only after reviewing Step 1.*")

prompt2 = st.text_area("Prompt 2", value="Based on the summary above, list the top 5 high-priority risks.", height=100)

if st.button("Run Step 2"):
    with st.spinner("Analyzing risks..."):
        # The chat session already knows what happened in Step 1
        response = st.session_state.chat_session.send_message(prompt2)
        st.session_state.step2_result = response.text
        st.session_state.step3_result = None

# Display Output 2 if it exists
if st.session_state.step2_result:
    st.info("✅ Step 2 Output Generated")
    st.write(st.session_state.step2_result)
else:
    st.stop()

# ==========================================
# STEP 3: FINAL FORMAT
# ==========================================
st.divider()
st.subheader("Step 3: JSON Conversion")

prompt3 = st.text_area("Prompt 3", value="Convert the risk list into a strict JSON format.", height=100)

if st.button("Run Step 3"):
    with st.spinner("Formatting..."):
        response = st.session_state.chat_session.send_message(prompt3)
        st.session_state.step3_result = response.text

# Display Output 3 if it exists
if st.session_state.step3_result:
    st.success("✅ Chain Complete!")
    st.code(st.session_state.step3_result, language='json')
    
    st.download_button(
        label="Download Final JSON",
        data=st.session_state.step3_result,
        file_name="gemini3_output.json",
        mime="application/json"
    )
