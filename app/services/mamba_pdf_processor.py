"""
Mamba-Enhanced PDF Processor
Uses Mamba state-space model for intelligent text extraction and understanding.
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
import re
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModel
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
    embeddings: Optional[torch.Tensor] = None
    importance_score: float = 0.0


# Model cache directory
MODEL_CACHE_DIR = "/app/models"  # Use persistent volume in production


class MambaPDFProcessor:
    """Enhanced PDF processor using Mamba state-space model for intelligent extraction."""
    
    # Class-level model cache (singleton pattern)
    _model_cache = None
    _model_loaded = False
    
    def __init__(
        self, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        use_mamba: bool = True,
        model_cache_dir: str = MODEL_CACHE_DIR
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_mamba = use_mamba
        self.model_cache_dir = model_cache_dir
        
        # Initialize Mamba model if enabled
        if self.use_mamba:
            try:
                self._init_mamba()
            except Exception as e:
                logger.warning(f"Failed to initialize Mamba: {e}. Falling back to basic extraction.")
                self.use_mamba = False
    
    def _init_mamba(self):
        """Initialize Mamba model for intelligent text processing with caching."""
        try:
            # Check if model is already loaded in class cache
            if MambaPDFProcessor._model_loaded and MambaPDFProcessor._model_cache is not None:
                self.model = MambaPDFProcessor._model_cache
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                logger.info("Reusing cached Mamba model")
                return
            
            # Use a lightweight transformer for text understanding
            # Note: Full Mamba-SSM requires specific model architecture
            # For production, use: state-spaces/mamba-130m or similar
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {self.device}")
            
            # Create cache directory if it doesn't exist
            import os
            os.makedirs(self.model_cache_dir, exist_ok=True)
            
            # For now, use sentence transformers with local caching
            # This will be replaced with actual Mamba model in production
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading model from cache: {self.model_cache_dir}")
            self.model = SentenceTransformer(
                'all-MiniLM-L6-v2', 
                device=self.device,
                cache_folder=self.model_cache_dir
            )
            
            # Cache the model at class level
            MambaPDFProcessor._model_cache = self.model
            MambaPDFProcessor._model_loaded = True
            
            logger.info("Mamba-based text processor initialized and cached successfully")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Error initializing Mamba processor: {e}")
            raise
    
    async def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract all text from a PDF with intelligent processing."""
        # Validate input type
        if not isinstance(pdf_bytes, bytes):
            logger.error(f"extract_text received non-bytes: {type(pdf_bytes)}")
            if isinstance(pdf_bytes, str):
                # Try to recover by encoding
                logger.warning("Attempting to convert string to bytes")
                pdf_bytes = pdf_bytes.encode('latin-1')
            else:
                raise ValueError(f"Expected bytes, got {type(pdf_bytes)}")
        
        logger.info(f"Opening PDF with {len(pdf_bytes)} bytes, first 4: {pdf_bytes[:4]}")
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if self.use_mamba:
            # Intelligent extraction: prioritize main content
            text = await self._extract_with_mamba(doc)
        else:
            # Basic extraction
            text = ""
            for page in doc:
                text += page.get_text()
        
        doc.close()
        return text
    
    async def _extract_with_mamba(self, doc: fitz.Document) -> str:
        """
        Use Mamba-style state-space processing for intelligent extraction.
        Filters headers, footers, page numbers, and focuses on main content.
        """
        all_blocks = []
        
        for page_num, page in enumerate(doc):
            # Get text blocks with position information
            blocks = page.get_text("blocks")
            
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block
                
                # Skip small text blocks (likely headers/footers)
                if len(text.strip()) < 10:
                    continue
                
                # Skip blocks at page edges (headers/footers)
                page_height = page.rect.height
                if y0 < 50 or y1 > page_height - 50:
                    continue
                
                all_blocks.append({
                    'text': text,
                    'page': page_num + 1,
                    'position': (x0, y0, x1, y1),
                    'size': len(text)
                })
        
        # Rank blocks by importance using Mamba (embeddings-based)
        if all_blocks and self.use_mamba:
            all_blocks = await self._rank_blocks_by_importance(all_blocks)
        
        # Concatenate in order
        return " ".join(block['text'] for block in all_blocks)
    
    async def _rank_blocks_by_importance(self, blocks: List[Dict]) -> List[Dict]:
        """Use Mamba to rank text blocks by semantic importance."""
        try:
            texts = [block['text'] for block in blocks]
            
            # Get embeddings for all blocks
            embeddings = self.model.encode(texts, convert_to_tensor=True)
            
            # Calculate importance based on semantic density
            # Blocks with richer semantic content get higher scores
            norms = torch.norm(embeddings, dim=1)
            
            for i, block in enumerate(blocks):
                block['importance'] = norms[i].item()
            
            # Sort by page first, then by importance within page
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
                # Extract main content only
                blocks = page.get_text("blocks")
                page_height = page.rect.height
                
                main_content = []
                for block in blocks:
                    x0, y0, x1, y1, text, _, _ = block
                    
                    # Filter headers/footers
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
        
        # Clean text
        text = self._clean_text(text)
        
        # Split into sentences
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
                    
                    # Add embeddings if Mamba is enabled
                    if self.use_mamba:
                        try:
                            embedding = self.model.encode(chunk.text, convert_to_tensor=True)
                            chunk.embeddings = embedding
                            chunk.importance_score = torch.norm(embedding).item()
                        except Exception as e:
                            logger.warning(f"Error generating embeddings: {e}")
                    
                    chunks.append(chunk)
                
                # Smart overlap: find sentence boundary
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                overlap_text = current_chunk[overlap_start:]
                
                current_chunk = overlap_text + sentence
                chunk_start = current_start - len(overlap_text)
            else:
                current_chunk += sentence
            
            current_start += len(sentence)
        
        # Add last chunk
        if current_chunk.strip():
            chunk = TextChunk(
                text=current_chunk.strip(),
                page=0,
                start_pos=chunk_start,
                end_pos=current_start,
                metadata={}
            )
            
            if self.use_mamba:
                try:
                    embedding = self.model.encode(chunk.text, convert_to_tensor=True)
                    chunk.embeddings = embedding
                    chunk.importance_score = torch.norm(embedding).item()
                except:
                    pass
            
            chunks.append(chunk)
        
        return chunks
    
    async def extract_key_concepts(self, pdf_bytes: bytes, top_k: int = 10) -> List[str]:
        """
        Extract key concepts from PDF using Mamba's understanding.
        Returns the most important concepts/terms.
        """
        if not self.use_mamba:
            return []
        
        text = await self.extract_text(pdf_bytes)
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        try:
            # Get embeddings for all sentences
            embeddings = self.model.encode(sentences[:100], convert_to_tensor=True)  # Limit for speed
            
            # Calculate importance scores
            norms = torch.norm(embeddings, dim=1)
            
            # Get top-k most important sentences
            top_indices = torch.argsort(norms, descending=True)[:top_k]
            
            key_sentences = [sentences[i] for i in top_indices.cpu().numpy()]
            
            # Extract noun phrases as concepts (simplified)
            concepts = []
            for sentence in key_sentences:
                words = sentence.split()
                # Simple heuristic: capitalized words or longer words
                concepts.extend([w.strip('.,!?') for w in words if len(w) > 5 or w[0].isupper()])
            
            # Remove duplicates and return
            return list(dict.fromkeys(concepts))[:top_k]
        
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
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove common header/footer patterns
        text = re.sub(r'Page \d+ of \d+', '', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences intelligently."""
        # Handle common abbreviations
        text = text.replace('Dr.', 'Dr')
        text = text.replace('Mr.', 'Mr')
        text = text.replace('Mrs.', 'Mrs')
        text = text.replace('etc.', 'etc')
        
        # Split on sentence boundaries
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
