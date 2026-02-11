"""
Mamba-Enhanced PDF Processor
Uses intelligent heuristic-based text extraction and understanding.
Optimized for low-memory environments (no local ML models).
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
import re
from dataclasses import dataclass
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text from a PDF."""
    text: str
    page: int
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]
    importance_score: float = 0.0


class MambaPDFProcessor:
    """Enhanced PDF processor using intelligent heuristic extraction.
    
    Provides the same API as before but without heavy ML model dependencies.
    Text ranking uses TF-IDF-like heuristics instead of sentence-transformers.
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        use_mamba: bool = True,
        model_cache_dir: str = "/app/models"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_mamba = use_mamba
        logger.info("PDF processor initialized (lightweight mode)")
    
    async def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract all text from a PDF with intelligent processing."""
        # Validate input type
        if not isinstance(pdf_bytes, bytes):
            logger.error(f"extract_text received non-bytes: {type(pdf_bytes)}")
            if isinstance(pdf_bytes, str):
                logger.warning("Attempting to convert string to bytes")
                pdf_bytes = pdf_bytes.encode('latin-1')
            else:
                raise ValueError(f"Expected bytes, got {type(pdf_bytes)}")
        
        logger.info(f"Opening PDF with {len(pdf_bytes)} bytes, first 4: {pdf_bytes[:4]}")
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if self.use_mamba:
            text = await self._extract_with_mamba(doc)
        else:
            text = ""
            for page in doc:
                text += page.get_text()
        
        doc.close()
        return text
    
    async def _extract_with_mamba(self, doc: fitz.Document) -> str:
        """
        Use heuristic-based processing for intelligent extraction.
        Filters headers, footers, page numbers, and focuses on main content.
        """
        all_blocks = []
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("blocks")
            
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block
                
                if len(text.strip()) < 10:
                    continue
                
                page_height = page.rect.height
                if y0 < 50 or y1 > page_height - 50:
                    continue
                
                all_blocks.append({
                    'text': text,
                    'page': page_num + 1,
                    'position': (x0, y0, x1, y1),
                    'size': len(text)
                })
        
        if all_blocks and self.use_mamba:
            all_blocks = self._rank_blocks_by_importance(all_blocks)
        
        return " ".join(block['text'] for block in all_blocks)
    
    def _rank_blocks_by_importance(self, blocks: List[Dict]) -> List[Dict]:
        """Rank text blocks by importance using text heuristics (no ML model needed)."""
        try:
            for block in blocks:
                text = block['text']
                score = 0.0
                # Longer blocks are typically more important
                score += min(len(text) / 500.0, 1.0) * 0.3
                # Blocks with more unique words score higher
                words = set(text.lower().split())
                score += min(len(words) / 50.0, 1.0) * 0.3
                # Blocks with numbers/data
                if re.search(r'\d+\.?\d*', text):
                    score += 0.1
                # Blocks with academic indicators
                if any(w in text.lower() for w in ['result', 'method', 'conclusion', 'abstract', 'hypothesis', 'study', 'analysis']):
                    score += 0.2
                # Penalize very short blocks
                if len(text.strip()) < 30:
                    score -= 0.3
                block['importance'] = max(0.0, score)
            
            blocks.sort(key=lambda x: (x['page'], -x.get('importance', 0)))
            return blocks
        except Exception as e:
            logger.warning(f"Error ranking blocks: {e}. Returning original order.")
            return blocks
    
    async def extract_text_by_page(self, pdf_bytes: bytes) -> List[Tuple[int, str]]:
        """Extract text from each page with intelligent processing."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        
        for i, page in enumerate(doc):
            if self.use_mamba:
                blocks = page.get_text("blocks")
                page_height = page.rect.height
                
                main_content = []
                for block in blocks:
                    x0, y0, x1, y1, text, _, _ = block
                    if len(text.strip()) > 10 and 50 < y0 < page_height - 50:
                        main_content.append(text)
                
                text = " ".join(main_content)
            else:
                text = page.get_text()
            
            pages.append((i + 1, text))
        
        doc.close()
        return pages
    
    async def chunk_text(self, text: str) -> List[TextChunk]:
        """Split text into intelligent, semantically-aware chunks."""
        chunks = []
        text = self._clean_text(text)
        sentences = self._split_sentences(text)
        
        current_chunk = ""
        current_start = 0
        chunk_start = 0
        
        for i, sentence in enumerate(sentences):
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunk = TextChunk(
                        text=current_chunk.strip(),
                        page=0,
                        start_pos=chunk_start,
                        end_pos=current_start,
                        metadata={}
                    )
                    
                    if self.use_mamba:
                        chunk.importance_score = self._compute_importance(chunk.text)
                    
                    chunks.append(chunk)
                
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                overlap_text = current_chunk[overlap_start:]
                current_chunk = overlap_text + sentence
                chunk_start = current_start - len(overlap_text)
            else:
                current_chunk += sentence
            
            current_start += len(sentence)
        
        if current_chunk.strip():
            chunk = TextChunk(
                text=current_chunk.strip(),
                page=0,
                start_pos=chunk_start,
                end_pos=current_start,
                metadata={}
            )
            if self.use_mamba:
                chunk.importance_score = self._compute_importance(chunk.text)
            chunks.append(chunk)
        
        return chunks
    
    def _compute_importance(self, text: str) -> float:
        """Compute importance score using text heuristics."""
        words = text.lower().split()
        if not words:
            return 0.0
        unique_ratio = len(set(words)) / len(words)
        length_score = min(len(text) / 500.0, 1.0)
        return (unique_ratio * 0.5 + length_score * 0.5)
    
    async def extract_key_concepts(self, pdf_bytes: bytes, top_k: int = 10) -> List[str]:
        """
        Extract key concepts from PDF using text analysis.
        Returns the most important concepts/terms.
        """
        if isinstance(pdf_bytes, str):
            text = pdf_bytes
        else:
            text = await self.extract_text(pdf_bytes)
        
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        
        try:
            # TF-IDF-like heuristic: find important words
            from collections import Counter
            all_words = []
            for s in sentences[:100]:
                words = re.findall(r'\b[A-Za-z]{4,}\b', s)
                all_words.extend([w.lower() for w in words])
            
            word_counts = Counter(all_words)
            # Remove very common words
            stopwords = {'with', 'that', 'this', 'from', 'have', 'been', 'were', 'will',
                         'they', 'their', 'which', 'would', 'could', 'should', 'about',
                         'also', 'more', 'than', 'some', 'into', 'other', 'these', 'most',
                         'such', 'when', 'what', 'each', 'make', 'like', 'does', 'made',
                         'after', 'before', 'between', 'through', 'over', 'under', 'only'}
            for sw in stopwords:
                word_counts.pop(sw, None)
            
            # Score by frequency * length (longer technical terms are more important)
            scored = [(word, count * math.log(len(word))) for word, count in word_counts.items()]
            scored.sort(key=lambda x: x[1], reverse=True)
            
            return [word for word, score in scored[:top_k]]
        except Exception as e:
            logger.error(f"Error extracting concepts: {e}")
            return []
    
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
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\d+\n', '\n', text)
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences intelligently."""
        text = text.replace('Dr.', 'Dr')
        text = text.replace('Mr.', 'Mr')
        text = text.replace('Mrs.', 'Mrs')
        text = text.replace('etc.', 'etc')
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() + ' ' for s in sentences if s.strip()]


# Singleton instance
_processor_instance = None


def get_pdf_processor(
    chunk_size: int = 1000, 
    chunk_overlap: int = 200,
    use_mamba: bool = True
) -> MambaPDFProcessor:
    """Get PDF processor instance with optional Mamba enhancement."""
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = MambaPDFProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            use_mamba=use_mamba
        )
    
    return _processor_instance
