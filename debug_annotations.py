#!/usr/bin/env python3
"""
PDF Annotation Debugger

This script helps diagnose why annotations might not be detected in a PDF.
It will show ALL annotations found (including highlights) and their types.
"""

import fitz  # PyMuPDF
import sys
import os

def debug_pdf_annotations(pdf_path):
    """Debug annotation detection in a PDF file."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        return False

    try:
        doc = fitz.open(pdf_path)
        print(f"PDF: {pdf_path}")
        print(f"Total pages: {len(doc)}")
        print("-" * 50)

        total_annotations = 0
        annotation_types = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_annotations = 0

            print(f"\nPage {page_num + 1}:")

            # Check if page has any annotations at all
            annot_list = list(page.annots())
            if not annot_list:
                print("  No annotations found on this page")
                continue

            for annot in annot_list:
                annot_type_num = annot.type[0]  # Numeric type
                annot_type_str = annot.type[1]  # String type
                content = annot.content
                rect = annot.rect

                print(f"  Found annotation:")
                print(f"    Type: {annot_type_str} (code: {annot_type_num})")
                print(f"    Content: '{content}'" if content else "    Content: (empty)")
                print(f"    Position: ({rect.x0:.1f}, {rect.y0:.1f}) to ({rect.x1:.1f}, {rect.y1:.1f})")
                print(f"    Size: {rect.width:.1f} x {rect.height:.1f}")

                # Track annotation types
                if annot_type_str in annotation_types:
                    annotation_types[annot_type_str] += 1
                else:
                    annotation_types[annot_type_str] = 1

                # Check if this would be filtered out by the main script
                if annot_type_str.lower() == 'highlight':
                    print(f"    --> This is a HIGHLIGHT (would be EXCLUDED by main script)")
                else:
                    print(f"    --> This is NOT a highlight (would be INCLUDED by main script)")

                page_annotations += 1
                total_annotations += 1
                print()

            print(f"  Page {page_num + 1} total: {page_annotations} annotations")

        doc.close()

        print("-" * 50)
        print(f"SUMMARY:")
        print(f"Total annotations found: {total_annotations}")
        print(f"Non-highlight annotations: {total_annotations - annotation_types.get('Highlight', 0)}")

        if annotation_types:
            print(f"Annotation types found:")
            for annot_type, count in annotation_types.items():
                status = "EXCLUDED" if annot_type.lower() == 'highlight' else "INCLUDED"
                print(f"  {annot_type}: {count} ({status})")
        else:
            print("No annotations detected in entire PDF!")
            print("\nPossible reasons:")
            print("1. The shapes/text were added as PDF content, not annotations")
            print("2. They were added as form fields, not annotations")
            print("3. The PDF viewer shows them but they're not stored as annotations")
            print("4. The annotations are in a format not recognized by PyMuPDF")

        return total_annotations > 0

    except Exception as e:
        print(f"Error reading PDF: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_annotations.py <pdf_file>")
        print("\nThis script will analyze a PDF and show all annotations it contains.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    debug_pdf_annotations(pdf_path)

if __name__ == "__main__":
    main()