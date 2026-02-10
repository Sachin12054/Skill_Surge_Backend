import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple
import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text from a PDF."""
    text: str
    page: int
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]


class PDFProcessor:
    """Service for processing PDF documents."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract all text from a PDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        return text
    
    async def extract_text_by_page(self, pdf_bytes: bytes) -> List[Tuple[int, str]]:
        """Extract text from each page of a PDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        
        for i, page in enumerate(doc):
            pages.append((i + 1, page.get_text()))
        
        doc.close()
        return pages
    
    async def chunk_text(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks."""
        chunks = []
        
        # Clean text
        text = self._clean_text(text)
        
        # Split into sentences first
        sentences = self._split_sentences(text)
        
        current_chunk = ""
        current_start = 0
        chunk_start = 0
        
        for i, sentence in enumerate(sentences):
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(TextChunk(
                        text=current_chunk.strip(),
                        page=0,  # Can be enhanced with page tracking
                        start_pos=chunk_start,
                        end_pos=current_start,
                        metadata={}
                    ))
                
                # Find overlap point
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                overlap_text = current_chunk[overlap_start:]
                
                current_chunk = overlap_text + sentence
                chunk_start = current_start - len(overlap_text)
            else:
                current_chunk += sentence
            
            current_start += len(sentence)
        
        # Add last chunk
        if current_chunk.strip():
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                page=0,
                start_pos=chunk_start,
                end_pos=current_start,
                metadata={}
            ))
        
        return chunks
    
    async def extract_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract metadata from a PDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "keywords": doc.metadata.get("keywords", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "page_count": len(doc),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
        }
        
        doc.close()
        return metadata
    
    async def extract_images(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract images from a PDF."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        
        for page_num, page in enumerate(doc):
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                
                images.append({
                    "page": page_num + 1,
                    "index": img_index,
                    "width": base_image["width"],
                    "height": base_image["height"],
                    "ext": base_image["ext"],
                    "data": base_image["image"],
                })
        
        doc.close()
        return images
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers (common patterns)
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s + ' ' for s in sentences if s.strip()]


def get_pdf_processor(chunk_size: int = 1000, chunk_overlap: int = 200) -> PDFProcessor:
    """Get PDF processor instance."""
    return PDFProcessor(chunk_size, chunk_overlap)
