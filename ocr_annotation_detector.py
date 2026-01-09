#!/usr/bin/env python3
"""
OCR Annotation Detector

This script uses OCR to detect text in a PDF that might be annotations.
It can help identify text that looks like it was added later (different fonts,
sizes, colors, or positioned in margins/empty areas).

Requirements:
    pip install PyMuPDF pillow pytesseract opencv-python numpy

Note: You also need to install tesseract:
    Ubuntu/Debian: sudo apt-get install tesseract-ocr
    macOS: brew install tesseract
    Windows: Download from https://github.com/tesseract-ocr/tesseract
"""

import fitz
import pytesseract
from PIL import Image
import cv2
import numpy as np
import sys
import os
from collections import defaultdict

def pdf_page_to_image(pdf_path, page_num, dpi=200):
    """Convert PDF page to high-res image for OCR."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("ppm")
    doc.close()

    from io import BytesIO
    img = Image.open(BytesIO(img_data))
    return img

def get_pdf_text_blocks(pdf_path, page_num):
    """Get text blocks directly from PDF structure."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    text_blocks = page.get_text("dict")
    doc.close()
    return text_blocks

def ocr_page(image):
    """Perform OCR on page image."""
    # Convert PIL to OpenCV
    opencv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Get detailed OCR data
    ocr_data = pytesseract.image_to_data(opencv_img, output_type=pytesseract.Output.DICT)

    return ocr_data

def analyze_text_characteristics(text_blocks):
    """Analyze text characteristics from PDF structure."""
    fonts = defaultdict(int)
    font_sizes = defaultdict(int)
    colors = defaultdict(int)

    for block in text_blocks["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                font = span["font"]
                size = round(span["size"], 1)
                color = span.get("color", 0)  # Default to black

                fonts[font] += 1
                font_sizes[size] += 1
                colors[color] += 1

    # Find most common characteristics (likely main document text)
    main_font = max(fonts.items(), key=lambda x: x[1])[0] if fonts else "unknown"
    main_size = max(font_sizes.items(), key=lambda x: x[1])[0] if font_sizes else 12
    main_color = max(colors.items(), key=lambda x: x[1])[0] if colors else 0

    return {
        'main_font': main_font,
        'main_size': main_size,
        'main_color': main_color,
        'all_fonts': dict(fonts),
        'all_sizes': dict(font_sizes),
        'all_colors': dict(colors)
    }

def find_potential_annotation_text(text_blocks, characteristics):
    """Find text that might be annotations based on characteristics."""
    potential_annotations = []

    for block in text_blocks["blocks"]:
        if "lines" not in block:
            continue

        for line in block["lines"]:
            for span in line["spans"]:
                font = span["font"]
                size = span["size"]
                color = span.get("color", 0)
                text = span.get("text", "").strip()
                bbox = span["bbox"]  # [x0, y0, x1, y1]

                if not text:
                    continue

                # Check if this text is different from main characteristics
                is_different_font = font != characteristics['main_font']
                is_different_size = abs(size - characteristics['main_size']) > 2
                is_different_color = color != characteristics['main_color']

                # Calculate position characteristics
                page_width = text_blocks.get("width", 595)  # Default A4 width
                page_height = text_blocks.get("height", 842)  # Default A4 height

                x_center = (bbox[0] + bbox[2]) / 2
                y_center = (bbox[1] + bbox[3]) / 2

                # Check if in margins
                left_margin = x_center < page_width * 0.1
                right_margin = x_center > page_width * 0.9
                top_margin = y_center < page_height * 0.1
                bottom_margin = y_center > page_height * 0.9
                in_margin = left_margin or right_margin or top_margin or bottom_margin

                # Score this text as potential annotation
                annotation_score = 0
                reasons = []

                if is_different_font:
                    annotation_score += 2
                    reasons.append("different font")

                if is_different_size:
                    annotation_score += 2
                    reasons.append("different size")

                if is_different_color:
                    annotation_score += 3
                    reasons.append("different color")

                if in_margin:
                    annotation_score += 2
                    reasons.append("in margin")

                # Small text blocks are often annotations
                if len(text) < 50:
                    annotation_score += 1
                    reasons.append("short text")

                # Very small or very large text
                if size < characteristics['main_size'] - 3:
                    annotation_score += 1
                    reasons.append("smaller text")
                elif size > characteristics['main_size'] + 5:
                    annotation_score += 1
                    reasons.append("larger text")

                if annotation_score >= 3:  # Threshold for potential annotation
                    potential_annotations.append({
                        'text': text,
                        'font': font,
                        'size': size,
                        'color': color,
                        'bbox': bbox,
                        'score': annotation_score,
                        'reasons': reasons,
                        'in_margin': in_margin
                    })

    return potential_annotations

def detect_annotation_text(pdf_path):
    """Main function to detect potential annotation text."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF '{pdf_path}' not found.")
        return False

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        print(f"Analyzing {total_pages} pages for potential annotation text...")

        all_annotations = []

        for page_num in range(total_pages):
            print(f"\nPage {page_num + 1}:")

            # Get PDF text structure
            text_blocks = get_pdf_text_blocks(pdf_path, page_num)

            # Analyze text characteristics
            characteristics = analyze_text_characteristics(text_blocks)
            print(f"  Main document characteristics:")
            print(f"    Font: {characteristics['main_font']}")
            print(f"    Size: {characteristics['main_size']}")
            print(f"    Color: {characteristics['main_color']}")

            # Find potential annotations
            potential_annotations = find_potential_annotation_text(text_blocks, characteristics)

            if potential_annotations:
                print(f"  Found {len(potential_annotations)} potential annotation texts:")

                for i, annot in enumerate(potential_annotations):
                    text_preview = annot['text'][:50] + "..." if len(annot['text']) > 50 else annot['text']
                    x0, y0, x1, y1 = annot['bbox']

                    print(f"    {i+1}. \"{text_preview}\"")
                    print(f"       Position: ({x0:.0f}, {y0:.0f}) to ({x1:.0f}, {y1:.0f})")
                    print(f"       Font: {annot['font']} | Size: {annot['size']} | Color: {annot['color']}")
                    print(f"       Score: {annot['score']} | Reasons: {', '.join(annot['reasons'])}")
                    print()

                all_annotations.extend(potential_annotations)
            else:
                print("  No potential annotation text found")

        print(f"\nSUMMARY: Found {len(all_annotations)} potential annotation texts")

        # Group by characteristics
        if all_annotations:
            print("\nMost common annotation characteristics:")
            annot_fonts = defaultdict(int)
            annot_sizes = defaultdict(int)

            for annot in all_annotations:
                annot_fonts[annot['font']] += 1
                annot_sizes[annot['size']] += 1

            print("  Fonts:", dict(annot_fonts))
            print("  Sizes:", dict(annot_sizes))

        return len(all_annotations) > 0

    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ocr_annotation_detector.py <pdf_file>")
        print("\nThis script analyzes a PDF to find text that might be annotations")
        print("(text with different fonts, sizes, colors, or in margins).")
        sys.exit(1)

    pdf_path = sys.argv[1]
    detect_annotation_text(pdf_path)

if __name__ == "__main__":
    main()