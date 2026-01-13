import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- Page Configuration ---
st.set_page_config(page_title="Gemini PDF Chainer", layout="wide")
st.title("🔗 Gemini Step-by-Step PDF App")

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    # Button to clear everything and start fresh
    if st.button("Reset Chain"):
        st.session_state.clear()
        st.rerun()

# --- Session State Management ---
# This keeps your data alive as you click buttons
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "step1_result" not in st.session_state:
    st.session_state.step1_result = None
if "step2_result" not in st.session_state:
    st.session_state.step2_result = None
if "step3_result" not in st.session_state:
    st.session_state.step3_result = None

# --- Helper Function: Initialize Gemini & Upload File ---
def init_gemini(api_key, file_obj):
    try:
        genai.configure(api_key=api_key)
        # Use "gemini-1.5-pro" or "gemini-2.0-flash-exp" / "gemini-3-pro-preview" if available
        model = genai.GenerativeModel("gemini-3-pro") 
        
        # 1. Save uploaded file temporarily to disk
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        
        # 2. Upload to Google's Server
        with st.spinner("Uploading PDF to Gemini..."):
            uploaded_doc = genai.upload_file(tmp_path)
            
            # 3. Wait for processing (Crucial for large PDFs)
            while uploaded_doc.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_doc = genai.get_file(uploaded_doc.name)
                
        # 4. Clean up local file
        os.remove(tmp_path)
        
        # 5. Start Chat Session with the PDF loaded
        # We prime the history so the model knows it has the file
        return model.start_chat(history=[
            {"role": "user", "parts": [uploaded_doc, "Read this file."]},
            {"role": "model", "parts": ["I have read the file. Ready for instructions."]}
        ])
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# ==========================================
# STEP 1: BROCHURE (Input -> Output 1)
# ==========================================
st.divider()
st.subheader("Step 1: Brochure Generation")
prompt1 = st.text_area("Prompt 1", value="Create a detailed marketing brochure.", key="p1")

if st.button("Run Step 1"):
    if not (api_key and uploaded_file):
        st.error("Please provide API Key and upload a PDF.")
    else:
        # Initialize session if not already done
        if not st.session_state.chat_session:
            st.session_state.chat_session = init_gemini(api_key, uploaded_file)
        
        if st.session_state.chat_session:
            with st.spinner("Generating Brochure..."):
                response = st.session_state.chat_session.send_message(prompt1)
                st.session_state.step1_result = response.text
                # Reset future steps if we re-run Step 1
                st.session_state.step2_result = None
                st.session_state.step3_result = None

# Show Result 1
if st.session_state.step1_result:
    st.info("✅ Brochure Generated")
    st.write(st.session_state.step1_result)
else:
    st.stop() # Stop here if Step 1 isn't done

# ==========================================
# STEP 2: QUESTIONS (Input -> Output 2)
# ==========================================
st.divider()
st.subheader("Step 2: Question Generation")
prompt2 = st.text_area("Prompt 2", value="Generate 5 quiz questions based on the brochure.", key="p2")

if st.button("Run Step 2"):
    with st.spinner("Generating Questions..."):
        # The chat session inherently remembers Step 1, but we send a new prompt
        response = st.session_state.chat_session.send_message(prompt2)
        st.session_state.step2_result = response.text
        st.session_state.step3_result = None

# Show Result 2
if st.session_state.step2_result:
    st.info("✅ Questions Generated")
    st.write(st.session_state.step2_result)
else:
    st.stop() # Stop here if Step 2 isn't done

# ==========================================
# STEP 3: FINAL SYNTHESIS (Inputs 1+2 -> Output 3)
# ==========================================
st.divider()
st.subheader("Step 3: Final Compilation")
prompt3 = st.text_area("Prompt 3", value="Compile the brochure and questions into an HTML report.", key="p3")

if st.button("Run Step 3"):
    with st.spinner("Synthesizing Final Output..."):
        
        # --- CONTEXT INJECTION LOGIC ---
        # We explicitly paste the previous results into the prompt
        final_input = f"""
You are now in the Final Compilation step. Here is the data you generated in previous steps:

=== START STEP 1 OUTPUT (Brochure) ===
{st.session_state.step1_result}
=== END STEP 1 OUTPUT ===

=== START STEP 2 OUTPUT (Questions) ===
{st.session_state.step2_result}
=== END STEP 2 OUTPUT ===

=== YOUR INSTRUCTION ===
{prompt3}
"""
        response = st.session_state.chat_session.send_message(final_input)
        st.session_state.step3_result = response.text

# Show & Download Result 3
if st.session_state.step3_result:
    st.success("🎉 Chain Complete!")
    st.write(st.session_state.step3_result)
    
    st.download_button(
        label="Download Final Output (.txt)",
        data=st.session_state.step3_result,
        file_name="final_output.txt",
        mime="text/plain"
    )
