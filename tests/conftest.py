import sys
from unittest.mock import MagicMock

# Mock sentence_transformers and faiss to prevent torch and CUDA loading during tests
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()

import backend.app.rag
# Set HAS_SEMANTIC_LIBS to False to force fallback keyword matching in tests
backend.app.rag.HAS_SEMANTIC_LIBS = False
