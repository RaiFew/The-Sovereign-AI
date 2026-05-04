import PyPDF2
try:
    reader = PyPDF2.PdfReader('d:/The Sovereign AI/plan_Soverign_agent.pdf')
    text = ''
    for page in reader.pages:
        text += page.extract_text()
    print("PDF TEXT EXTRACTED:")
    print(text[:3000])
except Exception as e:
    print(f"Error reading PDF: {e}")
