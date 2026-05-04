import fitz
try:
    doc = fitz.open('d:/The Sovereign AI/plan_Soverign_agent.pdf')
    text = ""
    for page in doc:
        text += page.get_text()
    
    with open('d:/The Sovereign AI/pdf_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully extracted text to pdf_text.txt")
except Exception as e:
    print(f"Error: {e}")
