import re
from typing import List, Dict, Any, Tuple, Optional, Set
from axiom_mem import config

OPTION_PREFIX_PATTERN = re.compile(r'^\s*([A-Za-z0-9][\.\)\:\-]\s*|\([A-Za-z0-9]\)\s*)')


def extract_option_keywords(option_text: str) -> Set[str]:
    """Clean option prefix and extract salient alphanumeric keywords."""
    clean_text = OPTION_PREFIX_PATTERN.sub('', option_text).lower()
    tokens = re.findall(r'[a-zA-Z0-9_\-\.]{3,}', clean_text)
    return set(tokens)


class OptionsDiscriminator:
    """
    Options-Aware Discriminative Re-ranker:
    Utilizes candidate multiple-choice options purely as ranking signal.
    Measures how strongly a memory discriminates between the candidate options,
    boosting grounded evidence while strictly never emitting synthetic answers.
    """
    def __init__(self, boost: float = config.OPTIONS_DISCRIMINATOR_BOOST):
        self.boost = boost

    def rerank_with_options(
        self,
        candidates: List[Tuple[Dict[str, Any], float]],
        options: Optional[List[str]]
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not candidates or not options:
            return candidates

        # Extract keyword sets per option
        option_token_sets = [extract_option_keywords(opt) for opt in options if opt]
        all_option_tokens = set().union(*option_token_sets) if option_token_sets else set()

        if not all_option_tokens:
            return candidates

        reranked: List[Tuple[Dict[str, Any], float]] = []
        for mem, score in candidates:
            content_lower = mem.get("content", "").lower()
            content_tokens = set(re.findall(r'[a-zA-Z0-9_\-\.]{3,}', content_lower))

            # Count overlap with individual options
            overlaps = [len(content_tokens.intersection(opt_set)) for opt_set in option_token_sets]
            max_overlap = max(overlaps) if overlaps else 0
            
            # Discrimination signal: does this memory strongly align with any specific option?
            if max_overlap > 0:
                # Degree of specificity
                overlap_ratio = min(max_overlap / 3.0, 1.0)
                multiplier = 1.0 + (self.boost - 1.0) * overlap_ratio
            else:
                multiplier = 1.0

            reranked.append((mem, score * multiplier))

        # Re-sort descending
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
