"""Engine HTTP bersama untuk semua adapter."""
import httpx

from app.config import get_settings

settings = get_settings()


async def make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": settings.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*;q=0.8",
        },
        follow_redirects=True,
        timeout=60.0,
        verify=False,
    )


class BrowserEngine:
    """Wrapper kecil Playwright; diluncurkan malas (lazy) saat pertama dipakai."""

    def __init__(self):
        self._pw = None
        self._browser = None

    async def page(self, url: str, wait_selector: str | None = None, timeout_ms: int = 30000):
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=True)
        page = await self._browser.new_page(user_agent=settings.user_agent)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout_ms)
            return page
        except Exception:
            await page.close()
            raise

    async def html(self, url: str, wait_selector: str | None = None, timeout_ms: int = 30000) -> str:
        page = await self.page(url, wait_selector, timeout_ms)
        try:
            return await page.content()
        finally:
            await page.close()

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
