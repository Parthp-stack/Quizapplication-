# PDF Quiz Setup Guide

## For Text-Based PDFs (Works Out of Box)
- Just upload any PDF with selectable text
- The app will automatically extract text and generate questions

## For Scanned PDFs (Image-Based)

### Option 1: Install Tesseract OCR (Recommended)

**Windows Users:**
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (choose default installation path)
3. In PowerShell/CMD, run:
   ```bash
   pip install pytesseract pdf2image pillow
   ```
4. Set the Tesseract path in your environment (it's usually automatic on Windows)

**Mac Users:**
```bash
brew install tesseract
pip install pytesseract pdf2image pillow
```

**Linux Users:**
```bash
sudo apt-get install tesseract-ocr
pip install pytesseract pdf2image pillow
```

After installation, scanned PDFs will work automatically!

### Option 2: Use AI Vision Extraction (If API Key Configured)
- If you don't want to install Tesseract, scanned PDFs can be converted to images
- The app can use the AI Vision API to extract text from the images
- No additional installation required!
- This is slower but works for most PDFs

### Option 3: Manual Text Entry
- Copy text from your PDF manually
- Use "Paste Text as PDF" feature (coming soon)

## Troubleshooting

**"Failed to extract text from PDF"**
- Ensure the PDF has text (not just images)
- For scanned PDFs, install Tesseract (Option 1)
- Check if PDF is password protected

**"No questions generated"**
- The extracted text might be too short (need at least 200 words)
- Try a different PDF with more content
- Check API key configuration

## FAQ

**Q: Does the app support encrypted PDFs?**
A: Yes, but only unencrypted PDFs or those without a password.

**Q: How many pages are processed?**
A: Text-based PDFs: All pages. Scanned PDFs: First 10 pages (for speed).

**Q: What file size limit?**
A: 50 MB maximum file size.

**Q: Can I use images instead of PDFs?**
A: Yes! Use the "AI Quiz from Photo" feature on the dashboard.
