"""
Text summarization for knowledge graph analysis.

This module provides summarization that preserves original content
by selecting the most important sentences based on semantic similarity and position.
Optimized for speech/communication content analysis.
"""

import numpy as np
import tiktoken
import time
from sentence_transformers import SentenceTransformer, util
from nltk.tokenize import sent_tokenize
from typing import Optional

from src.schemas import SummarizationResult, SummarizationData
from src.app_config import config


class Summarizer:
    """
    Summarizer optimized for speech content analysis.
    Selects the most important sentences while preserving original content
    and targeting specific word counts for knowledge graph processing.
    """
    
    WINDOW_SIZE = 3
    
    # Focus primarily on content relevance, not position
    POSITION_WEIGHTS = {
        'intro': 0.10,
        'centrality': 0.90,  # Focus almost entirely on content relevance
        'conclusion': 0.00,  # No position bias
    }
    
    INTRO_SENTENCES = 0  # No special treatment for intros
    CONCLUSION_SENTENCES = 0  # No special treatment for conclusions
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding(config.SUMMARIZER_TOKENIZER)
        self.model = SentenceTransformer(config.SUMMARIZER_MODEL)
    
    def summarize(self, id: str, text: str, target_tokens: int) -> dict:
        """Summarize text to target token count."""
        start_time = time.time()
        original_tokens = len(self.tokenizer.encode(text))
        
        try:
            if not text or not text.strip():
                return self._create_result(id, text, "", 0, 0.0, start_time, target_tokens, False, "Empty input")
            
            summary_text = text if original_tokens <= target_tokens else self._do_summarization(text, target_tokens)
            summary_tokens = len(self.tokenizer.encode(summary_text))
            compression_ratio = len(summary_text) / len(text) if text else 0.0
            
            return self._create_result(id, text, summary_text, summary_tokens, compression_ratio, start_time, target_tokens)
            
        except Exception as e:
            logger.error(f"Summarization failed for content {id}: {str(e)}")
            # Let exception bubble up to flow processor
            raise
    
    def _create_result(self, id: str, original: str, summary: str, summary_tokens: int, compression: float, 
                      start_time: float, target_tokens: int) -> dict:
        """Helper to create SummarizationResult."""
        summarization_data = SummarizationData(
            summarize=summary,
            original_word_count=len(original.split()),
            summary_word_count=len(summary.split()),
            compression_ratio=compression,
            target_word_count=target_tokens
        )
        
        result = SummarizationResult(
            id=id,
            success=True,
            data=summarization_data
        )
        return result.model_dump()
    
    def _do_summarization(self, text: str, target_tokens: int) -> str:
        """Internal method that performs the actual summarization logic."""
        # Step 1: Split the text into sentences
        sentences = sent_tokenize(text)
        
        if len(sentences) < self.WINDOW_SIZE:
            return text
        
        # Step 2: Generate embeddings and centrality scores
        centrality_scores = self._compute_hybrid_scores(sentences)
        
        # Step 3: Calculate position scores
        intro_scores, conclusion_scores = self._get_position_scores(sentences)
        
        # Step 4: Combine scores with weights
        final_scores = (
            self.POSITION_WEIGHTS['centrality'] * centrality_scores +
            self.POSITION_WEIGHTS['intro'] * intro_scores +
            self.POSITION_WEIGHTS['conclusion'] * conclusion_scores
        )
        
        # Step 5: Rank sentences by combined score
        ranked_indices = final_scores.argsort()[::-1]
        
        # Step 6: Accumulate sentences until target token count
        selected_sentences = []
        token_count = 0
        
        for rank_index in ranked_indices:
            sentence = sentences[rank_index]
            sentence_tokens = len(self.tokenizer.encode(sentence))
            
            if token_count + sentence_tokens <= target_tokens:
                selected_sentences.append(rank_index)
                token_count += sentence_tokens
            else:
                break
        
        # Step 7: Reassemble the summary in original order
        top_sentences = [sentences[i] for i in sorted(selected_sentences)]
        summary_text = ' '.join(top_sentences)
        
        return summary_text
    
    
    def _get_position_scores(self, sentences) -> tuple[np.ndarray, np.ndarray]:
        """Calculate position-based scores (minimal for generalizability)."""
        num_sentences = len(sentences)
        
        # Return zero scores - no position bias
        intro_scores = np.zeros(num_sentences)
        conclusion_scores = np.zeros(num_sentences)
        
        return intro_scores, conclusion_scores
    
    def _compute_hybrid_scores(self, sentences):
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
        standardized_local_scores = (local_scores - local_scores.min()) / (local_scores.min() - local_scores.min() + 1e-8)
        
        final_scores = 0.7 * standardized_global_scores + 0.3 * standardized_local_scores
        return final_scores
