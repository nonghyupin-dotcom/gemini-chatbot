import streamlit as st
import requests
from pathlib import Path
import pypdf
import uuid
import json

# ==============================================================================
# 0. CONFIGURATION, CONSTANTS & DIRECTORIES
# ==============================================================================
API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={API_KEY}"
VERIFY_SSL = True  # 클라우드 환경이므로 SSL 검증을 켭니다.
DATA_FILE = Path("chatbot_data.json")

# Automatically create the knowledge base folder in the execution path
KNOWLEDGE_DIR = Path("knowledge_base")
KNOWLEDGE_DIR.mkdir(exist_ok=True)

# ==============================================================================
# 1. PERSISTENCE LAYER (JSON Save/Load)
# ==============================================================================
def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading saved data: {e}")
    return {}

def save_data():
    if "sessions" not in st.session_state or "active_session_id" not in st.session_state:
        return
    
    data = {
        "custom_instructions": st.session_state.get("custom_instructions", ""),
        "active_session_id": st.session_state.active_session_id,
        "sessions": st.session_state.sessions
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# ==============================================================================
# 2. SESSION MANAGEMENT
# ==============================================================================
def create_new_session():
    session_id = str(uuid.uuid4())
    st.session_state.sessions[session_id] = {
        "title": "New Chat",
        "messages": [],
        "mode": "general",          # "general" (일반 대화) or "master" (사규/법령 마스터)
        "selected_files": [],       # Selected file names in knowledge_base
    }
    st.session_state.active_session_id = session_id
    save_data()

def init_session_state():
    if "sessions" not in st.session_state:
        persisted = load_data()
        st.session_state.custom_instructions = persisted.get("custom_instructions", "")
        st.session_state.sessions = persisted.get("sessions", {})
        st.session_state.active_session_id = persisted.get("active_session_id", None)

    if not st.session_state.sessions:
        create_new_session()
    elif not st.session_state.active_session_id or st.session_state.active_session_id not in st.session_state.sessions:
        st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]

# ==============================================================================
# 3. PDF TEXT EXTRACTION (using pypdf)
# ==============================================================================
def extract_text_from_pdf(pdf_path: Path) -> str:
    text_list = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_list.append(extracted)
    except Exception as e:
        return f"\n[Error reading PDF {pdf_path.name}: {e}]\n"
    return "\n".join(text_list)

# ==============================================================================
# 4. LLM API CONNECTOR
# ==============================================================================
def query_gemini(prompt: str) -> str:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }
    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            verify=VERIFY_SSL,
            timeout=120,  # Elevated timeout for large document ingestion
        )
        response.raise_for_status()
        data = response.json()
        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except Exception as e:
        return f"Error contacting Gemini API: {e}"

# ==============================================================================
# 5. UI COMPONENTS & RENDERING
# ==============================================================================
def render_sidebar():
    with st.sidebar:
        st.title("🤖 Chat Control Panel")
        
        # New Chat Button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            create_new_session()
            st.rerun()
            
        st.markdown("---")
        
        active_sess = st.session_state.sessions[st.session_state.active_session_id]
        
        # Mode Selection
        st.subheader("⚙️ Chat Mode")
        current_mode = active_sess.get("mode", "general")
        mode_index = 0 if current_mode == "general" else 1
        
        selected_mode = st.radio(
            "Select operation mode:",
            options=["💬 일반 대화 모드", "📜 사규/법령 마스터 모드"],
            index=mode_index,
            key=f"mode_select_{st.session_state.active_session_id}"
        )
        
        new_mode = "general" if "일반 대화" in selected_mode else "master"
        if new_mode != current_mode:
            active_sess["mode"] = new_mode
            save_data()
            st.rerun()
            
        st.markdown("---")
        
        # 1. Custom Settings (User Profile)
        with st.expander("👤 User Settings", expanded=False):
            st.text_area(
                "Custom Instructions:",
                placeholder="e.g., I work at KOWEPO and I am interested in power plant operations...",
                height=120,
                key="custom_instructions",
                on_change=save_data
            )
            st.caption("These instructions will guide Gemini's responses globally.")

        # 2. Rules/Regulations Knowledge Base File Uploader & Checklist
        if active_sess["mode"] == "master":
            st.markdown("### 📜 Knowledge Base Management")
            
            # File Uploader
            uploaded_file = st.file_uploader(
                "Upload reference PDF",
                type=["pdf"],
                key=f"kb_uploader_{st.session_state.active_session_id}"
            )
            if uploaded_file:
                target_path = KNOWLEDGE_DIR / uploaded_file.name
                try:
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"Saved: {uploaded_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save file: {e}")

            # Checklist of uploaded files
            pdf_files = sorted([f.name for f in KNOWLEDGE_DIR.glob("*.pdf")])
            
            if pdf_files:
                st.markdown("#### 🗂️ Active Documents")
                
                # Check for list key in session dictionary
                if "selected_files" not in active_sess:
                    active_sess["selected_files"] = []
                
                for filename in pdf_files:
                    col1, col2 = st.columns([0.82, 0.18])
                    
                    with col1:
                        is_checked = filename in active_sess["selected_files"]
                        checked = st.checkbox(
                            filename,
                            value=is_checked,
                            key=f"check_{filename}_{st.session_state.active_session_id}"
                        )
                        
                        # Sync check values
                        if checked and filename not in active_sess["selected_files"]:
                            active_sess["selected_files"].append(filename)
                            save_data()
                        elif not checked and filename in active_sess["selected_files"]:
                            active_sess["selected_files"].remove(filename)
                            save_data()
                            
                    with col2:
                        if st.button("🗑️", key=f"del_kb_{filename}_{st.session_state.active_session_id}"):
                            filepath = KNOWLEDGE_DIR / filename
                            if filepath.exists():
                                filepath.unlink()
                            
                            # Clean up lists in all sessions
                            for s in st.session_state.sessions.values():
                                if "selected_files" in s and filename in s["selected_files"]:
                                    s["selected_files"].remove(filename)
                                    
                            save_data()
                            st.success(f"Deleted {filename}")
                            st.rerun()
            else:
                st.info("No documents uploaded yet. Upload a PDF above.")

        st.markdown("---")
        st.subheader("💬 Chat Sessions")
        
        # Render lists of past chat sessions
        for sess_id, sess in list(st.session_state.sessions.items()):
            col1, col2 = st.columns([0.8, 0.2])
            
            is_active = (sess_id == st.session_state.active_session_id)
            btn_label = f"💬 {sess['title']}"
            
            with col1:
                if st.button(
                    btn_label,
                    key=f"select_{sess_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.active_session_id = sess_id
                    save_data()
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{sess_id}", use_container_width=True):
                    del st.session_state.sessions[sess_id]
                    if st.session_state.active_session_id == sess_id:
                        remaining = list(st.session_state.sessions.keys())
                        if remaining:
                            st.session_state.active_session_id = remaining[0]
                        else:
                            create_new_session()
                    save_data()
                    st.rerun()

def render_chat_interface():
    active_sess = st.session_state.sessions[st.session_state.active_session_id]
    
    st.title("Gemini File-Based Chatbot Workspace")
    
    # Active document indicators in Master Mode
    if active_sess.get("mode", "general") == "master":
        active_files = active_sess.get("selected_files", [])
        if active_files:
            st.info(f"📂 **Active Rules Master Context**: Using {len(active_files)} document(s): `{', '.join(active_files)}`")
        else:
            st.warning("⚠️ **Rules Master Mode Active**: Please upload and select at least one reference document from the sidebar to query.")
    else:
        st.success("💬 **General Chat Mode Active**: Feel free to ask Gemini anything.")

    # Render conversation
    for msg in active_sess["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User Input
    user_input = st.chat_input("Upload a file or ask Gemini anything...")
    
    if user_input:
        # In master mode, ensure files are selected
        if active_sess.get("mode", "general") == "master" and not active_sess.get("selected_files", []):
            st.error("Please select or upload at least one PDF file in the sidebar before asking questions.")
            st.stop()

        # Save message
        active_sess["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Dynamic renaming of session
        if active_sess["title"] == "New Chat":
            clean_title = user_input.strip()
            active_sess["title"] = clean_title[:20] + "..." if len(clean_title) > 20 else clean_title

        # Build Prompt Context
        system_instructions = []
        
        # 1. Append User Profile Context
        custom_inst = st.session_state.get("custom_instructions", "")
        if custom_inst.strip():
            system_instructions.append(
                f"[User Profile / Background Context]\n{custom_inst.strip()}"
            )
            
        # 2. Append Mode Context
        if active_sess.get("mode", "general") == "master":
            # Extract content from checked PDFs
            context_pieces = []
            for filename in active_sess.get("selected_files", []):
                file_path = KNOWLEDGE_DIR / filename
                if file_path.exists():
                    text = extract_text_from_pdf(file_path)
                    context_pieces.append(f"--- START DOCUMENT: {filename} ---\n{text}\n--- END DOCUMENT: {filename} ---")
            
            system_instructions.append(
                "[System Persona & Response Rules]\n"
                "너는 사내 규정 전문가(사규 비서)이다. "
                "철저히 제공된 문서 내용에만 기반하여 답변하라. "
                "문서 외에 외부 정보를 사용하거나 지어내지 말라. "
                "답변의 끝에는 어떤 파일을 참고했는지 반드시 '출처: [참고한 파일명]' 형태로 명시하라."
            )
            
            documents_str = "\n\n".join(context_pieces)
            full_prompt = (
                f"{chr(10).join(system_instructions)}\n\n"
                f"[Document Content Context]\n{documents_str}\n\n"
                f"[User Question]\n{user_input}"
            )
        else:
            # General Chat Mode
            if system_instructions:
                full_prompt = (
                    f"{chr(10).join(system_instructions)}\n\n"
                    f"[User Question]\n{user_input}"
                )
            else:
                full_prompt = user_input

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = query_gemini(full_prompt)
                st.markdown(answer)
                
        active_sess["messages"].append({"role": "assistant", "content": answer})
        save_data()
        st.rerun()

# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    st.set_page_config(page_title="Gemini File Chatbot", page_icon="🤖", layout="wide")
    init_session_state()
    render_sidebar()
    render_chat_interface()

if __name__ == "__main__":
    main()
