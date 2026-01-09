#!/usr/bin/env python3
"""
Flattened Annotation Detector

This script compares an original PDF with an annotated (flattened) PDF to detect
visual differences that were likely annotations. It can help identify:
- Added text
- New shapes/boxes
- Changes in content

Requirements:
    pip install PyMuPDF pillow opencv-python numpy
"""

import fitz
import numpy as np
from PIL import Image, ImageChops
import cv2
import sys
import os

def pdf_page_to_image(pdf_path, page_num, dpi=150):
    """Convert a PDF page to a PIL Image."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(dpi/72, dpi/72)  # Scale factor for DPI
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("ppm")
    doc.close()

    # Convert to PIL Image
    from io import BytesIO
    img = Image.open(BytesIO(img_data))
    return img

def find_differences(original_img, annotated_img):
    """Find visual differences between two images."""
    # Ensure same size
    if original_img.size != annotated_img.size:
        # Resize to match the smaller one
        min_width = min(original_img.width, annotated_img.width)
        min_height = min(original_img.height, annotated_img.height)
        original_img = original_img.resize((min_width, min_height))
        annotated_img = annotated_img.resize((min_width, min_height))

    # Calculate difference
    diff = ImageChops.difference(original_img, annotated_img)

    # Convert to numpy for analysis
    diff_np = np.array(diff)

    # Find significant differences (non-zero pixels)
    gray_diff = cv2.cvtColor(diff_np, cv2.COLOR_RGB2GRAY)

    # Threshold to find significant changes
    _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)

    # Find contours (potential annotation areas)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    return diff, contours, thresh

def analyze_contours(contours, min_area=100):
    """Analyze contours to classify potential annotations."""
    annotations = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)

        # Classify based on shape
        aspect_ratio = w / h
        annotation_type = "unknown"

        if aspect_ratio > 5 or aspect_ratio < 0.2:
            annotation_type = "line/arrow"
        elif 0.8 <= aspect_ratio <= 1.2:
            annotation_type = "square/circle"
        elif aspect_ratio > 2:
            annotation_type = "text/rectangle"
        else:
            annotation_type = "rectangle/shape"

        annotations.append({
            'type': annotation_type,
            'bbox': (x, y, w, h),
            'area': area,
            'aspect_ratio': aspect_ratio
        })

    return annotations

def detect_flattened_annotations(original_pdf, annotated_pdf, output_dir="annotation_analysis"):
    """Main function to detect flattened annotations."""
    if not os.path.exists(original_pdf):
        print(f"Error: Original PDF '{original_pdf}' not found.")
        return False

    if not os.path.exists(annotated_pdf):
        print(f"Error: Annotated PDF '{annotated_pdf}' not found.")
        return False

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Get page counts
        orig_doc = fitz.open(original_pdf)
        annot_doc = fitz.open(annotated_pdf)

        orig_pages = len(orig_doc)
        annot_pages = len(annot_doc)

        orig_doc.close()
        annot_doc.close()

        min_pages = min(orig_pages, annot_pages)
        print(f"Analyzing {min_pages} pages...")

        total_annotations = 0

        for page_num in range(min_pages):
            print(f"\nPage {page_num + 1}:")

            # Convert pages to images
            original_img = pdf_page_to_image(original_pdf, page_num)
            annotated_img = pdf_page_to_image(annotated_pdf, page_num)

            # Find differences
            diff_img, contours, thresh = find_differences(original_img, annotated_img)

            # Analyze contours
            annotations = analyze_contours(contours)

            if annotations:
                print(f"  Found {len(annotations)} potential annotations:")
                for i, annot in enumerate(annotations):
                    x, y, w, h = annot['bbox']
                    print(f"    {i+1}. {annot['type']}: position ({x}, {y}), size {w}x{h}, area {annot['area']:.0f}")

                # Save difference image
                diff_path = os.path.join(output_dir, f"page_{page_num+1}_differences.png")
                diff_img.save(diff_path)

                # Save threshold image
                thresh_path = os.path.join(output_dir, f"page_{page_num+1}_threshold.png")
                cv2.imwrite(thresh_path, thresh)

                print(f"  Saved analysis images: {diff_path}, {thresh_path}")
                total_annotations += len(annotations)
            else:
                print("  No significant differences found")

        print(f"\nSUMMARY: Found {total_annotations} potential annotations across {min_pages} pages")
        print(f"Analysis images saved in: {output_dir}/")

        return total_annotations > 0

    except Exception as e:
        print(f"Error analyzing PDFs: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 detect_flattened_annotations.py <original.pdf> <annotated.pdf> [output_dir]")
        print("\nThis script compares an original PDF with an annotated (flattened) PDF")
        print("to detect visual differences that were likely annotations.")
        print("\nExample:")
        print("  python3 detect_flattened_annotations.py clean.pdf annotated.pdf")
        sys.exit(1)

    original_pdf = sys.argv[1]
    annotated_pdf = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "annotation_analysis"

    detect_flattened_annotations(original_pdf, annotated_pdf, output_dir)

if __name__ == "__main__":
    main()