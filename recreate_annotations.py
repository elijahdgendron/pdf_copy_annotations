#!/usr/bin/env python3
"""
Manual Annotation Recreation Helper

This script helps manually recreate annotations on a PDF by providing
templates and guided creation. Useful when automated detection doesn't
work perfectly.

Requirements:
    pip install PyMuPDF

Usage Examples:
    # Interactive mode
    python3 recreate_annotations.py input.pdf output.pdf

    # Batch mode with predefined annotations
    python3 recreate_annotations.py input.pdf output.pdf --batch annotations.txt
"""

import fitz
import sys
import os
import json

class AnnotationRecreator:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.annotations = []

    def show_page_info(self, page_num):
        """Display information about a page to help with positioning."""
        if page_num >= len(self.doc):
            print(f"Error: Page {page_num + 1} doesn't exist (PDF has {len(self.doc)} pages)")
            return False

        page = self.doc[page_num]
        rect = page.rect
        print(f"\nPage {page_num + 1} Info:")
        print(f"  Dimensions: {rect.width:.0f} x {rect.height:.0f} points")
        print(f"  Coordinates: (0, 0) to ({rect.width:.0f}, {rect.height:.0f})")
        print(f"  Common positions:")
        print(f"    Top-left corner: (0, 0)")
        print(f"    Top-right corner: ({rect.width:.0f}, 0)")
        print(f"    Bottom-left corner: (0, {rect.height:.0f})")
        print(f"    Bottom-right corner: ({rect.width:.0f}, {rect.height:.0f})")
        print(f"    Center: ({rect.width/2:.0f}, {rect.height/2:.0f})")
        return True

    def add_text_annotation(self, page_num, x, y, text, author="User"):
        """Add a text (sticky note) annotation."""
        page = self.doc[page_num]
        point = fitz.Point(x, y)
        text_annot = page.add_annotation(fitz.ANNOT_TEXT, point)
        text_annot.set_content(text)
        text_annot.set_info(title=author)
        text_annot.update()

        self.annotations.append({
            'type': 'text',
            'page': page_num,
            'position': (x, y),
            'text': text,
            'author': author
        })

        print(f"✓ Added text annotation on page {page_num + 1} at ({x}, {y}): \"{text}\"")

    def add_freetext_annotation(self, page_num, x0, y0, x1, y1, text, fontsize=12):
        """Add a free text annotation (visible text on the page)."""
        page = self.doc[page_num]
        rect = fitz.Rect(x0, y0, x1, y1)
        freetext_annot = page.add_annotation(fitz.ANNOT_FREETEXT, rect)
        freetext_annot.set_content(text)
        freetext_annot.set_fontsize(fontsize)
        freetext_annot.update()

        self.annotations.append({
            'type': 'freetext',
            'page': page_num,
            'rect': (x0, y0, x1, y1),
            'text': text,
            'fontsize': fontsize
        })

        print(f"✓ Added free text on page {page_num + 1}: \"{text}\"")

    def add_rectangle_annotation(self, page_num, x0, y0, x1, y1, color=(1, 0, 0), width=2):
        """Add a rectangle/box annotation."""
        page = self.doc[page_num]
        rect = fitz.Rect(x0, y0, x1, y1)
        rect_annot = page.add_annotation(fitz.ANNOT_SQUARE, rect)
        rect_annot.set_colors(stroke=color)
        rect_annot.set_border(width=width)
        rect_annot.update()

        self.annotations.append({
            'type': 'rectangle',
            'page': page_num,
            'rect': (x0, y0, x1, y1),
            'color': color,
            'width': width
        })

        print(f"✓ Added rectangle on page {page_num + 1}: ({x0}, {y0}) to ({x1}, {y1})")

    def add_arrow_annotation(self, page_num, x0, y0, x1, y1, color=(0, 0, 1), width=2):
        """Add an arrow annotation."""
        page = self.doc[page_num]
        start_point = fitz.Point(x0, y0)
        end_point = fitz.Point(x1, y1)

        # Line annotation with arrow end
        line_annot = page.add_annotation(fitz.ANNOT_LINE, [start_point, end_point])
        line_annot.set_colors(stroke=color)
        line_annot.set_border(width=width)
        line_annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_CLOSED_ARROW)
        line_annot.update()

        self.annotations.append({
            'type': 'arrow',
            'page': page_num,
            'start': (x0, y0),
            'end': (x1, y1),
            'color': color,
            'width': width
        })

        print(f"✓ Added arrow on page {page_num + 1}: ({x0}, {y0}) → ({x1}, {y1})")

    def interactive_mode(self):
        """Interactive mode for creating annotations."""
        print(f"\n📄 PDF: {self.pdf_path}")
        print(f"📊 Pages: {len(self.doc)}")
        print("\n" + "="*50)
        print("INTERACTIVE ANNOTATION RECREATION")
        print("="*50)

        while True:
            print("\nOptions:")
            print("  1. Show page info")
            print("  2. Add text annotation (sticky note)")
            print("  3. Add free text (visible text)")
            print("  4. Add rectangle/box")
            print("  5. Add arrow")
            print("  6. Save and exit")
            print("  7. Exit without saving")

            try:
                choice = input("\nEnter choice (1-7): ").strip()

                if choice == "1":
                    page_num = int(input("Page number (1-based): ")) - 1
                    self.show_page_info(page_num)

                elif choice == "2":
                    page_num = int(input("Page number (1-based): ")) - 1
                    x = float(input("X position: "))
                    y = float(input("Y position: "))
                    text = input("Text content: ")
                    author = input("Author (optional): ") or "User"
                    self.add_text_annotation(page_num, x, y, text, author)

                elif choice == "3":
                    page_num = int(input("Page number (1-based): ")) - 1
                    x0 = float(input("Left X: "))
                    y0 = float(input("Top Y: "))
                    x1 = float(input("Right X: "))
                    y1 = float(input("Bottom Y: "))
                    text = input("Text content: ")
                    fontsize = float(input("Font size (12): ") or "12")
                    self.add_freetext_annotation(page_num, x0, y0, x1, y1, text, fontsize)

                elif choice == "4":
                    page_num = int(input("Page number (1-based): ")) - 1
                    x0 = float(input("Left X: "))
                    y0 = float(input("Top Y: "))
                    x1 = float(input("Right X: "))
                    y1 = float(input("Bottom Y: "))
                    width = float(input("Border width (2): ") or "2")
                    self.add_rectangle_annotation(page_num, x0, y0, x1, y1, width=width)

                elif choice == "5":
                    page_num = int(input("Page number (1-based): ")) - 1
                    x0 = float(input("Start X: "))
                    y0 = float(input("Start Y: "))
                    x1 = float(input("End X: "))
                    y1 = float(input("End Y: "))
                    width = float(input("Line width (2): ") or "2")
                    self.add_arrow_annotation(page_num, x0, y0, x1, y1, width=width)

                elif choice == "6":
                    return True  # Save

                elif choice == "7":
                    return False  # Don't save

                else:
                    print("Invalid choice. Please try again.")

            except ValueError as e:
                print(f"Invalid input: {e}")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return False

    def save_pdf(self, output_path):
        """Save the PDF with annotations."""
        self.doc.save(output_path)
        print(f"\n✅ Saved PDF with {len(self.annotations)} annotations to: {output_path}")

    def export_annotations_template(self, template_path):
        """Export current annotations as a template file."""
        template_data = {
            'annotations': self.annotations,
            'instructions': {
                'format': 'Each annotation needs: type, page, position/rect, and content',
                'types': ['text', 'freetext', 'rectangle', 'arrow'],
                'coordinates': 'PDF coordinates: (0,0) is top-left, (width, height) is bottom-right'
            }
        }

        with open(template_path, 'w') as f:
            json.dump(template_data, f, indent=2)

        print(f"✅ Exported annotation template to: {template_path}")

    def load_batch_annotations(self, batch_file):
        """Load annotations from a batch file."""
        try:
            with open(batch_file, 'r') as f:
                data = json.load(f)

            annotations = data.get('annotations', [])
            for annot in annotations:
                annot_type = annot['type']
                page_num = annot['page']

                if annot_type == 'text':
                    x, y = annot['position']
                    self.add_text_annotation(page_num, x, y, annot['text'], annot.get('author', 'User'))

                elif annot_type == 'freetext':
                    x0, y0, x1, y1 = annot['rect']
                    self.add_freetext_annotation(page_num, x0, y0, x1, y1, annot['text'], annot.get('fontsize', 12))

                elif annot_type == 'rectangle':
                    x0, y0, x1, y1 = annot['rect']
                    self.add_rectangle_annotation(page_num, x0, y0, x1, y1, annot.get('color', (1, 0, 0)), annot.get('width', 2))

                elif annot_type == 'arrow':
                    x0, y0 = annot['start']
                    x1, y1 = annot['end']
                    self.add_arrow_annotation(page_num, x0, y0, x1, y1, annot.get('color', (0, 0, 1)), annot.get('width', 2))

            print(f"✅ Loaded {len(annotations)} annotations from batch file")
            return True

        except Exception as e:
            print(f"❌ Error loading batch file: {e}")
            return False

    def close(self):
        """Close the PDF document."""
        self.doc.close()

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 recreate_annotations.py <input.pdf> <output.pdf> [--batch annotations.json]")
        print("\nThis script helps manually recreate annotations on a PDF.")
        print("\nModes:")
        print("  Interactive: python3 recreate_annotations.py input.pdf output.pdf")
        print("  Batch:       python3 recreate_annotations.py input.pdf output.pdf --batch annotations.json")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    if not os.path.exists(input_pdf):
        print(f"Error: Input PDF '{input_pdf}' not found.")
        sys.exit(1)

    try:
        recreator = AnnotationRecreator(input_pdf)

        # Check for batch mode
        if len(sys.argv) > 4 and sys.argv[3] == "--batch":
            batch_file = sys.argv[4]
            if recreator.load_batch_annotations(batch_file):
                recreator.save_pdf(output_pdf)
            else:
                sys.exit(1)
        else:
            # Interactive mode
            if recreator.interactive_mode():
                recreator.save_pdf(output_pdf)

                # Offer to export template
                export_choice = input("\nExport annotation template for reuse? (y/n): ").strip().lower()
                if export_choice == 'y':
                    template_name = output_pdf.replace('.pdf', '_template.json')
                    recreator.export_annotations_template(template_name)

        recreator.close()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()