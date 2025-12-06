from typing import List, Optional, Dict, Any, Callable, Type, Union
import os
import logging
import glob as glob_module
from spoon_ai.retrieval.chroma import Document

logger = logging.getLogger(__name__)

class BasicTextSplitter:
    """Simple text splitter to replace langchain's RecursiveCharacterTextSplitter"""
    
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        if not text:
            return []
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # If not the last chunk, try to split at whitespace
            if end < len(text):
                # Try to split at paragraph ends
                paragraph_end = text.rfind('\n\n', start, end)
                if paragraph_end > start:
                    end = paragraph_end + 2  # Include two newlines
                else:
                    # Try to split at sentence ends
                    sentence_end = max(
                        text.rfind('. ', start, end),
                        text.rfind('? ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('.\n', start, end),
                        text.rfind('?\n', start, end),
                        text.rfind('!\n', start, end)
                    )
                    if sentence_end > start:
                        end = sentence_end + 2  # Include separator and space
            
            chunks.append(text[start:end])
            start = end - self.chunk_overlap
            
        return chunks
        
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split document collection into smaller document chunks"""
        split_docs = []
        
        for doc in documents:
            splits = self.split_text(doc.page_content)
            
            for i, split in enumerate(splits):
                new_doc = Document(
                    page_content=split,
                    metadata=doc.metadata.copy() if doc.metadata else {}
                )
                
                # Add split information to metadata
                if 'chunk' not in new_doc.metadata:
                    new_doc.metadata['chunk'] = i
                    
                split_docs.append(new_doc)
                
        return split_docs

class DocumentLoader:
    def __init__(self):
        self.text_splitter = BasicTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Simplified loader implementation
        self.extension_loaders = {
            ".txt": self._load_text,
            ".pdf": self._load_text,  # Simplified implementation, should use PDF parsing library
            ".csv": self._load_text,
            ".html": self._load_text,
            ".htm": self._load_text,
            ".json": self._load_text
        }
    
    def _load_text(self, file_path: str) -> List[Document]:
        """Basic text file loader"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            metadata = {
                "source": file_path,
                "filename": os.path.basename(file_path)
            }
            
            return [Document(page_content=content, metadata=metadata)]
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return []
    
    def load_directory(self, directory_path: str, glob_pattern: Optional[str] = None) -> List[Document]:
        """Load documents from a directory"""
        # Check if the path is a file instead of a directory
        if os.path.isfile(directory_path):
            return self.load_file(directory_path)
            
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        documents = []
        
        # Use glob to match files
        if glob_pattern:
            file_paths = glob_module.glob(os.path.join(directory_path, glob_pattern), recursive=True)
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    docs = self.load_file(file_path)
                    documents.extend(docs)
        else:
            # Traverse directory to load all supported files
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    _, ext = os.path.splitext(file_path)
                    ext = ext.lower()
                    
                    if ext in self.extension_loaders:
                        try:
                            docs = self.load_file(file_path)
                            documents.extend(docs)
                            logger.info(f"Loaded document: {file_path}")
                        except Exception as e:
                            logger.error(f"Error loading {file_path}: {e}")
        
        # Split documents
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Split into {len(split_docs)} chunks")
        
        return split_docs
    
    def load_file(self, file_path: str) -> List[Document]:
        """Load a single file and return the documents"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext not in self.extension_loaders:
            raise ValueError(f"Unsupported file type: {ext}. Supported types are: {', '.join(self.extension_loaders.keys())}")
        
        try:
            # Call appropriate type loader
            loader_func = self.extension_loaders[ext]
            documents = loader_func(file_path)
            
            # Split documents
            split_docs = self.text_splitter.split_documents(documents)
            logger.info(f"Split {file_path} into {len(split_docs)} chunks")
            
            return split_docs
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise 