import sys
modules = [
    "langchain", "langchain_community", "langchain_google_genai",
    "faiss", "sentence_transformers", "easyocr", "PyPDF2", "fitz",
    "dotenv", "PIL", "streamlit", "google.generativeai"
]
for m in modules:
    try:
        __import__(m)
        print(f"✅ {m}")
    except ImportError as e:
        print(f"❌ {m}: {e}")
print("All imports done!")
