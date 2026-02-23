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
        """
        Export translated segments to PDF.
        Attempts to preserve a clean layout with proper wrapping.
        """
        doc = fitz.open()
        
        margin = 72 # 1 inch
        page_width = 595
        page_height = 842
        width = page_width - 2*margin
        height = page_height - 2*margin
        
        fontsize = 12
        line_height = 1.5 * fontsize
        
        page = doc.new_page()
        y = margin
        
        # We use insert_htmlbox if available for better wrapping, 
        # but fitz.TextWriter or simple text wrapping is more portable.
        
        for seg in segments:
            text = seg.get('target_text', '')
            if not text:
                continue
                
            # Split into paragraphs if any
            paragraphs = text.split('\n')
            for para in paragraphs:
                if not para.strip():
                    y += line_height * 0.5
                    continue
                
                # Use TextWriter for auto-wrapping
                tw = fitz.TextWriter(page.rect)
                # We need to compute wrapping or use a high-level API
                # fitz.Page.insert_textbox is good for wrapping
                
                rect = fitz.Rect(margin, y, margin + width, page_height - margin)
                
                # insert_textbox returns the height used or -1 if overflow
                # We'll use a loop to handle overflows
                while True:
                    rc = page.insert_textbox(rect, para, fontsize=fontsize, fontname="helv", align=fitz.TEXT_ALIGN_JUSTIFY)
                    if rc < 0: # Overflow
                        page = doc.new_page()
                        y = margin
                        rect = fitz.Rect(margin, y, margin + width, page_height - margin)
                        continue
                    else:
                        y += rc + line_height
                        break
                
                if y > page_height - margin:
                    page = doc.new_page()
                    y = margin
        
        doc.save(file_path)
        doc.close()
    
    def get_supported_extensions(self):
        return ['.pdf']
