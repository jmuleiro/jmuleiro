import pdfplumber
import sys

if __name__ == "__main__":
  # Take the first argument passed and try to open the pdf
  pdf_path = sys.argv[1]
  print(pdf_path)
  with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
      text = page.extract_text()
      print("Lines: " + "{0}".format(text.count('\n')))
      #print(text)  