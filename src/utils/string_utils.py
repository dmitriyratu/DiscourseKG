"""String manipulation utilities."""

import re
from typing import Optional


def slugify(text: str, max_length: Optional[int] = None) -> str:
    """
    Convert text to URL-safe slug.
    
    Args:
        text: Text to slugify
        max_length: Optional maximum length to truncate to
        
    Returns:
        URL-safe slug
        
    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Trump Announces New Policy", max_length=20)
        'trump-announces-new'
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    slug = text.strip('-')
    return slug[:max_length] if max_length else slug
