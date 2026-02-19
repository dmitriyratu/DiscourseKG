"""Registry mapping domains to extractor metadata."""

from typing import Dict, Optional

from src.scrape.models import DomainInfo

DOMAIN_REGISTRY: Dict[str, DomainInfo] = {
    "rollcall.com": DomainInfo(
        extractor_name="rollcall_transcript",
        instructions="Focus on extracting speaker dialogue",
    ),
}


def get_domain_info(domain: str) -> Optional[DomainInfo]:
    """Look up domain info from registry."""
    domain = domain.removeprefix("www.")
    return DOMAIN_REGISTRY.get(domain)
