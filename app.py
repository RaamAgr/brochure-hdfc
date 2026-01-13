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
    
    st.divider()
    
    # === NEW FEATURE: DEBUG TOGGLE ===
    # If True: Show steps one by one. If False: Run everything at once.
    debug_mode = st.toggle("Debug / Manual Mode", value=True)
    
    st.divider()
    
    # Button to clear everything and start fresh
    if st.button("Reset Chain"):
        st.session_state.clear()
        st.rerun()

# --- Session State Management ---
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
        
        # 1. SAFETY SETTINGS (Keep these to allow "rebuttal" arguments)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # 2. GENERATION CONFIG (Temp=0 + Thinking)
        # Gemini 3 Pro defaults to "High" thinking, but we set temp=0 as requested.
        generation_config = genai.types.GenerationConfig(
            temperature=0.3, # Deterministic output
            candidate_count=1
        )

        model = genai.GenerativeModel(
            "gemini-3-pro-preview", 
            safety_settings=safety_settings,
            generation_config=generation_config
        ) 
        
        # Standard File Upload Logic...
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("Uploading PDF to Gemini..."):
            uploaded_doc = genai.upload_file(tmp_path)
            while uploaded_doc.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_doc = genai.get_file(uploaded_doc.name)
                
        os.remove(tmp_path)
        
        return model.start_chat(history=[
            {"role": "user", "parts": [uploaded_doc, "Read this file."]},
            {"role": "model", "parts": ["I have read the file. Ready for instructions."]}
        ])
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# ==========================================
# DEFAULT PROMPTS
# ==========================================
default_p1 = """Read the entire PDF brochure thoroughly, page by page, without skipping any content.

Extract all information exactly as presented, including but not limited to:

• All statements, claims, promises, and assertions
• All factual data, numbers, percentages, measurements, and comparisons
• All descriptions of products, services, processes, and methodologies
• All benefits, advantages, differentiators, and selling points
• All assumptions, conditions, limitations, exclusions, and disclaimers
• All testimonials, quotes, endorsements, or implied guarantees
• All timelines, dates, milestones, and projections
• All references to standards, certifications, partners, or authorities

Do not summarize, paraphrase, soften, or improve wording.
Preserve original language verbatim wherever possible.

Organize the output strictly by page number and section heading, so each extracted item can be traced back to its source.

Convert tables, charts, footnotes, captions, and callouts into text while preserving structure.

If a statement is vague, ambiguous, or unsupported, mark it clearly as such without interpretation.

If claims appear absolute, comparative, or superlative, label them explicitly.

Do not add analysis, opinions, or conclusions.

The goal is a complete, auditable raw information dump suitable for later rebuttal and cross examination."""

default_p2 = """From the provided brochure text, generate customer facing questions suitable for rebuttal, retention, and grievance handling.

Internally ensure the questions cover ALL of the following categories (do not label categories in output):
	1.	General understanding and informative questions
• overall plan purpose
• who the plan is for
• how the plan helps in the long term
	2.	Customer doubts and confusion after purchase
• misunderstanding of benefits
• expectations versus reality
	3.	Policy status and continuation scenarios
• lapsed, paid up, discontinued situations
• impact of stopping premiums
	4.	Regret, sunk cost, and continuation dilemma
• customer has already paid for some time
• what is lost if the policy is stopped now
• whether continuing still makes sense
	5.	Dissatisfaction and trust concerns
• miss selling perception
• unhappiness or loss of confidence

STRICTLY EXCLUDE:
• illustration based or example based questions
• questions containing specific numbers, percentages, ages, amounts, or years
• feature by feature, option listing, rider, or fund mechanics questions
• operational or administrative queries

Write questions in simple, natural, first person language used by Indian policyholders.

Write questions as if spoken by a non technical Indian customer in a real call or complaint.

Prefer short, direct sentences over complex ones.

Generate multiple simple variations when the same concern can be expressed differently, as long as the meaning is not identical.

Do NOT answer the questions.

Output only a clean list of questions."""

default_p3 = """Using only the brochure content provided, answer each question below.

Follow these rules strictly:

• Repeat the question exactly as written, including the *  at the beginning and  * at the end
• Write the answer immediately below the question
• Write as if you are speaking directly to the customer, not referring to documents
• Never mention the brochure, policy document, or terms text explicitly
• Use simple, non technical, customer friendly language
• Respond as a customer support and retention executive
• Always start by reassuring and explaining why the plan still has value
• Convince the customer calmly before offering any next steps
• You may mention customer support or helpline only as optional assistance, not as an exit
• Never ask the customer to complain, escalate, or raise a grievance
• Do not use legal or compliance heavy phrases
• Do not introduce information not present in the brochure
• Keep answers short, clear, and benefit focused

If a question cannot be fully answered using the brochure alone, provide reassurance first, then gently suggest reaching customer support for personalised help.


 FORMATTING RULES:
        - DEFAULT FORMAT (Q&A):
           Q: {{Question/Heading}}
           A: {{answer}}
           Separator: '###'


"""



# ==========================================
#  MODE 1: AUTOMATIC (DEBUG OFF)
# ==========================================
if not debug_mode:
    st.info("⚡ Automatic Mode Enabled. Upload a PDF and click Run.")
    
    if st.button("🚀 Run Full Chain", type="primary"):
        if not (api_key and uploaded_file):
            st.error("Please provide API Key and upload a PDF.")
        else:
            # 1. Init Session
            if not st.session_state.chat_session:
                st.session_state.chat_session = init_gemini(api_key, uploaded_file)
            
            if st.session_state.chat_session:
                # Use st.status for a cool expandable progress log
                with st.status("Running AI Agent Workflow...", expanded=True) as status:
                    
                    # STEP 1
                    st.write("📝 Generating Brochure...")
                    response1 = st.session_state.chat_session.send_message(default_p1)
                    st.session_state.step1_result = response1.text
                    
                    # STEP 2
                    st.write("❓ Generating Questions...")
                    response2 = st.session_state.chat_session.send_message(default_p2)
                    st.session_state.step2_result = response2.text
                    
                    # STEP 3
                    st.write("📑 Compiling Final Report...")
                    final_input = f"""
                    You are now in the Final Compilation step. 
                    === START STEP 1 OUTPUT ===
                    {st.session_state.step1_result}
                    === START STEP 2 OUTPUT ===
                    {st.session_state.step2_result}
                    === INSTRUCTION ===
                    {default_p3}
                    """
                    response3 = st.session_state.chat_session.send_message(final_input)
                    st.session_state.step3_result = response3.text
                    
                    status.update(label="✅ Workflow Complete!", state="complete", expanded=False)

    # Show Final Output Only
    if st.session_state.step3_result:
        st.subheader("Final Output")
        st.write(st.session_state.step3_result)
        st.download_button(
  		  label="Download Report", 
  		  data=st.session_state.step3_result, 
   		  file_name="report.txt", 
 	      mime="text/plain"
)

# ==========================================
# MODE 2: DEBUG / MANUAL (DEBUG ON)
# ==========================================
else:
    st.warning("🛠️ Debug Mode Enabled. You have full control over every step.")

    # --- STEP 1 ---
    st.divider()
    st.subheader("Step 1: Brochure Generation")
    prompt1 = st.text_area("Prompt 1", value=default_p1, key="p1")

    if st.button("Run Step 1"):
        if not (api_key and uploaded_file):
            st.error("Missing Keys/File")
        else:
            if not st.session_state.chat_session:
                st.session_state.chat_session = init_gemini(api_key, uploaded_file)
            
            if st.session_state.chat_session:
                with st.spinner("Generating..."):
                    response = st.session_state.chat_session.send_message(prompt1)
                    st.session_state.step1_result = response.text
    
    if st.session_state.step1_result:
        with st.expander("View Step 1 Result", expanded=False):
            st.write(st.session_state.step1_result)

    # --- STEP 2 ---
    st.divider()
    st.subheader("Step 2: Question Generation")
    prompt2 = st.text_area("Prompt 2", value=default_p2, key="p2")

    if st.button("Run Step 2"):
        if not st.session_state.step1_result:
            st.error("Run Step 1 first!")
        else:
            with st.spinner("Generating..."):
                response = st.session_state.chat_session.send_message(prompt2)
                st.session_state.step2_result = response.text

    if st.session_state.step2_result:
        with st.expander("View Step 2 Result", expanded=False):
            st.write(st.session_state.step2_result)

    # --- STEP 3 ---
    st.divider()
    st.subheader("Step 3: Final Compilation")
    prompt3 = st.text_area("Prompt 3", value=default_p3, key="p3")

    if st.button("Run Step 3"):
        if not st.session_state.step2_result:
            st.error("Run Step 2 first!")
        else:
            with st.spinner("Synthesizing..."):
                final_input = f"""
                Previous outputs:
                {st.session_state.step1_result}
                {st.session_state.step2_result}
                Instruction: {prompt3}
                """
                response = st.session_state.chat_session.send_message(final_input)
                st.session_state.step3_result = response.text
    
    if st.session_state.step3_result:
        st.success("Done!")
        st.write(st.session_state.step3_result)
