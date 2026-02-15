from src.formats.format_handler import FormatHandler
import fitz # PyMuPDF

class PdfHandler(FormatHandler):
    def read(self, file_path):
        doc = fitz.open(file_path)
        segments = []
        global_index = 0
        
        for page_num, page in enumerate(doc):
            # get_text("blocks") returns list of (x0, y0, x1, y1, "lines", block_no, block_type)
            blocks = page.get_text("blocks")
            for b in blocks:
                # b[4] is the text content
                text = b[4].strip()
                if text:
                    segments.append({
                        'index': global_index,
                        'source_text': text,
                        'metadata': {
                            'page': page_num,
                            'bbox': b[:4] # store bbox for potential future use
                        }
                    })
                    global_index += 1
        return segments

    def write(self, file_path, segments, original_file_path=None):
        # Create a new PDF or modify existing?
        # Since PDF editing is complex to preserve layout while changing text length,
        # we act as "Simple Export" here: Create a new PDF with standard simple layout.
        
        doc = fitz.open()
        
        # Simple text placement constants
        margin = 50
        fontsize = 11
        lineheight = 14
        width = 595 - 2*margin # A4 width approx
        height = 842 - 2*margin # A4 height approx
        
        current_page = doc.new_page()
        y = margin
        
        # Create a font
        font = fitz.Font("helv")
        
        for seg in segments:
            text = seg.get('target_text', '')
            if not text:
                continue
                
            # We add text line by line or block by block
            # This is very basic and won't handle complex formatting
            # TODO: Improve with better text wrapping logic
            
            # Simple text insertion
            rc = current_page.insert_text((margin, y), text, fontsize=fontsize, fontname="helv")
            y += lineheight * (text.count('\n') + 1.5) # Estimate height
            
            if y > height:
                current_page = doc.new_page()
                y = margin

        doc.save(file_path)
    
    def get_supported_extensions(self):
        return ['.pdf']
