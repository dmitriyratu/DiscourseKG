"""JS code builders for crawl4ai page actions."""

import json

SCROLL_WAIT_MS = 1000
SCROLL_POLL_MS = 150


def _jump_wait_js() -> str:
    """Scroll progressively to bottom and wait for DOM to potentially grow."""
    return f"""
        const delay = ms => new Promise(r => setTimeout(r, ms));
        await delay(100);
        
        const target = document.body.scrollHeight;
        const viewport = window.innerHeight;
        let current = window.scrollY;
        
        while (current < target) {{
            current = Math.min(current + viewport, target);
            window.scrollTo(0, current);
            await delay(300);
        }}
        
        const prevHeight = document.body.scrollHeight;
        let elapsed = 0;
        while (elapsed < {SCROLL_WAIT_MS}) {{
            await delay({SCROLL_POLL_MS});
            elapsed += {SCROLL_POLL_MS};
            if (document.body.scrollHeight > prevHeight) break;
        }}
    """


def build_scroll_js() -> str:
    """Build JS for scroll action."""
    return f"""
        (async () => {{
            {_jump_wait_js()}
        }})();
        """


def build_click_js(selector: str) -> str:
    """Build JS for click action. Selector must be JSON-encoded."""
    selector_js = json.dumps(selector)
    return f"""
        (async () => {{
            const delay = ms => new Promise(r => setTimeout(r, ms));
            await delay(100);
            
            let el = document.querySelector({selector_js});
            if (!el && {selector_js}.includes(':contains("')) {{
                const text = {selector_js}.split(':contains("')[1].split('")')[0];
                el = Array.from(document.querySelectorAll('a, button, span, div'))
                    .find(e => e.textContent.trim() === text);
            }}
            if (el) {{
                el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                await delay(200);
                el.click();
            }}
            
            await delay(1000);
            {_jump_wait_js()}
        }})();
        """
