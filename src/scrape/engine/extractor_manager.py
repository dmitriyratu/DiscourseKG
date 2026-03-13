"""Extractor lifecycle: registry lookup, load cached, or generate via LLM."""

import ast
import importlib
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup

from src.scrape.config import scraper_config
from src.scrape.engine.prompts import build_extractor_prompts
from src.scrape.engine.registry import get_domain_info
from src.scrape.models import ExtractorScript
from src.shared.llm import create_client
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ExtractorManager:
    """Resolves extractors by domain: loads cached or generates via LLM."""

    DOMAINS_DIR = Path(__file__).parent.parent / "domains"

    def fetch_html(self, url: str) -> str:
        """Fetch raw HTML from URL via trafilatura."""
        return trafilatura.fetch_url(url)

    def get_or_create_extractor(self, url: str) -> Callable[[str], str]:
        """Get cached extractor or generate a new one. Domain must be in registry."""
        domain = urlparse(url).netloc
        domain_info = get_domain_info(domain)
        if not domain_info:
            raise ValueError(f"Domain '{domain}' not supported. Add to src/scrape/engine/registry.py")

        path = self.DOMAINS_DIR / f"{domain_info.extractor_name}.py"
        if path.is_file():
            return self._load_extractor(domain_info.extractor_name)

        instructions = domain_info.instructions or scraper_config.DEFAULT_INSTRUCTIONS
        code = self._generate_extractor_code(url, instructions)

        header = textwrap.dedent(f"""
            # Generated extractor for {domain}
            # Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            # Sample URL: {url}
            # Instructions: {instructions or 'default'}
        """).lstrip() + "\n"
        path.write_text(header + code, encoding="utf-8")
        logger.info(f"Saved extractor: {path}")

        return self._load_extractor(domain_info.extractor_name)

    def _load_extractor(self, extractor_name: str) -> Callable[[str], str]:
        module = importlib.import_module(f"src.scrape.domains.{extractor_name}")
        return module.extract

    def _generate_extractor_code(self, url: str, instructions: str, html: str | None = None) -> str:
        logger.info(f"Generating extractor for URL: {url}")
        html = html or self.fetch_html(url)
        html_sample = self._get_sample_html(html)

        client = create_client(scraper_config.LLM_MODEL)
        system, user_content = build_extractor_prompts(instructions, html_sample)

        result = client.create(
            response_model=ExtractorScript,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )

        ast.parse(result.code)
        logger.info("Extractor code generated and validated successfully")
        return result.code

    def _get_sample_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["head", "script", "style", "nav", "footer"]):
            tag.decompose()

        body_html = str(soup.body or soup)
        length = len(body_html)
        start_idx = int(0.25 * length)
        end_idx = min(start_idx + scraper_config.HTML_SAMPLE_MAX_CHARS, int(0.75 * length))
        logger.info(f"Sample HTML length: {end_idx - start_idx} characters out of {length} characters")

        return body_html[start_idx:end_idx]
