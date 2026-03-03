"""
Text summarization for knowledge graph analysis.

This module provides summarization that preserves original content
by selecting the most important sentences based on semantic similarity.
Optimized for speech/communication content analysis.
"""

import numpy as np
import tiktoken
from sentence_transformers import SentenceTransformer, util
from nltk.tokenize import sent_tokenize
from typing import List, Optional

from src.summarize.models import SummarizationResult, SummarizationData, SummarizeContext, SummarizeStageMetadata
from src.summarize.config import summarization_config
from src.shared.pipeline_definitions import StageResult


class Summarizer:
    """
    Summarizer optimized for speech content analysis.
    Selects the most important sentences while preserving original content
    and targeting specific word counts for knowledge graph processing.
    """
    
    WINDOW_SIZE = 3

    def __init__(self) -> None:
        self.tokenizer = tiktoken.get_encoding(summarization_config.SUMMARIZER_TOKENIZER)
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(summarization_config.SUMMARIZER_MODEL)
        return self._model

    def summarize_content(self, processing_context: SummarizeContext) -> StageResult:
        """Summarize text to target token count."""
        id = processing_context.id
        text = processing_context.text
        target_tokens = processing_context.target_tokens
        
        original_tokens = len(self.tokenizer.encode(text))
        
        if not text or not text.strip():
            return self._create_result(id, text, "", 0.0)
        
        summary_text = text if original_tokens <= target_tokens else self._do_summarization(text, target_tokens)
        orig_words = len(text.split()) if text else 0
        sum_words = len(summary_text.split()) if summary_text else 0
        compression_of_original = sum_words / orig_words if orig_words else 1.0
        output_text = None if compression_of_original >= 1.0 else summary_text
        return self._create_result(id, text, output_text, compression_of_original)

    
    def _do_summarization(self, text: str, target_tokens: int) -> str:
        """Select highest-centrality sentences until target token count."""
        sentences = sent_tokenize(text)
        if len(sentences) < self.WINDOW_SIZE:
            return text

        centrality_scores = self._compute_hybrid_scores(sentences)
        ranked_indices = centrality_scores.argsort()[::-1]

        selected_sentences = []
        token_count = 0
        max_tokens = int(target_tokens * 1.15) 
        
        for rank_index in ranked_indices:
            sentence = sentences[rank_index]
            sentence_tokens = len(self.tokenizer.encode(sentence))
            if token_count + sentence_tokens <= max_tokens:
                selected_sentences.append(rank_index)
                token_count += sentence_tokens
            else:
                break

        top_sentences = [sentences[i] for i in sorted(selected_sentences)]
        summary_text = ' '.join(top_sentences)
        
        return summary_text

    def _compute_hybrid_scores(self, sentences: List[str]) -> np.ndarray:
        """Compute semantic similarity scores for sentence ranking."""
        num_sentences = len(sentences)
        
        embeddings = self.model.encode(
            sentences,
            batch_size=num_sentences,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        all_similarities = util.pytorch_cos_sim(embeddings, embeddings).cpu().numpy()
        
        # Calculate length weights for each sentence
        sentence_lengths = np.array([len(sent.split()) for sent in sentences])
        length_weights = np.minimum(sentence_lengths/np.quantile(sentence_lengths, 0.9), 1)
        
        # Apply weights directly to similarity matrix rows
        weighted_similarities = all_similarities * length_weights.reshape(-1, 1)
        
        # Global scores
        global_scores = np.median(weighted_similarities, axis=1)
        
        # Vectorized local scores computation
        window_size = min(self.WINDOW_SIZE, num_sentences - 1)
        local_scores = np.array([
            np.concatenate([
                weighted_similarities[i, max(0, i - window_size):i],
                weighted_similarities[i, i + 1:min(i + window_size + 1, num_sentences)]
            ]).mean()
            for i in range(num_sentences)
        ])
        
        standardized_global_scores = (global_scores - global_scores.min()) / (global_scores.max() - global_scores.min() + 1e-8)
        standardized_local_scores = (local_scores - local_scores.min()) / (local_scores.max() - local_scores.min() + 1e-8)
        
        final_scores = 0.7 * standardized_global_scores + 0.3 * standardized_local_scores
        return final_scores
    
    def _create_result(
        self, id: str, original: str, summary: Optional[str], compression_of_original: float
    ) -> StageResult:
        """Helper to create StageResult with separated artifact and metadata."""
        orig_words = len(original.split())
        sum_words = len(summary.split()) if summary else 0
        summarization_data = SummarizationData(
            summarize=summary,
            compression_of_original=compression_of_original,
            original_word_count=orig_words if compression_of_original < 1 else None,
            summary_word_count=sum_words if compression_of_original < 1 else None,
        )
        
        # Build artifact (what gets persisted)
        artifact = SummarizationResult(
            id=id,
            success=True,
            data=summarization_data,
            error_message=None
        )
        
        metadata = SummarizeStageMetadata(compression_of_original=compression_of_original).model_dump()
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)