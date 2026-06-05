# Gemini File‑Based Chatbot

This **Streamlit** application lets you upload a **.txt** or **.pdf** document, stores its contents, and answers questions using the **Gemini 1.5‑flash** model. The model is forced to answer **only** from the uploaded document.

## 📦 Prerequisites
- Python 3.9+ (recommended 3.10 or later)
- An active internet connection that can reach `generativeai.googleapis.com`
- Your **Gemini API Key** (generated from Google AI Studio)

## 🚀 Quick‑start
1. **Open a PowerShell terminal** and navigate to the project folder:
   ```powershell
   cd "C:\Users\한국서부발전(인터넷망)\.gemini\antigravity\scratch\gemini_file_chatbot"
   ```
2. **Create a virtual environment** (optional but recommended):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Run the Streamlit app** (default port 8501):
   ```powershell
   streamlit run app.py
   ```
   The app will be reachable at `http://localhost:8501`. To allow teammates on the intranet to connect using your machine’s IP, add the `--server.enableCORS false` flag:
   ```powershell
   streamlit run app.py --server.enableCORS false --server.port 8501
   ```

## 🛡️ Security note
- The request to the Gemini API disables SSL verification (`verify=False`) to bypass corporate firewalls, mirroring the pattern used in your previous Naver news scraper. This is **not recommended** for production environments because it makes the TLS handshake vulnerable to MITM attacks. If you can whitelist the API endpoint instead, remove the `verify=False` argument.

## 📂 Project layout
```
gemini_file_chatbot/
├─ app.py              # Streamlit UI & Gemini integration
├─ requirements.txt   # Python dependencies
└─ README.md          # This file
```

## 🎯 Next steps
- Add more sophisticated document chunking for large PDFs.
- Persist conversation history to a file or database.
- Deploy behind your corporate reverse‑proxy for easier access.

---
*Created by Antigravity – your AI‑powered coding partner.*
