import sys, os

def main():
    if len(sys.argv) < 3:
        print("Expected at least 2 file paths (Excel + PDFs)")
        return

    excel_path = sys.argv[1]
    pdf_paths = sys.argv[2:]

    print("Excel file:", excel_path)
    print("PDF files:")
    for pdf in pdf_paths:
        print("-", pdf)

    print("\nExistence check:")
    print(f"{excel_path} exists:", os.path.exists(excel_path))
    for pdf in pdf_paths:
        print(f"{pdf} exists:", os.path.exists(pdf))

if __name__ == "__main__":
    main()
