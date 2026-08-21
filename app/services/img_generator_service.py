import aiohttp
import io
import logging
import itertools
from app.core.config import settings


class ImageGeneratorService:
    def __init__(self):
        self._counter = itertools.count()

    def _get_workers(self) -> list[tuple[str, str]]:
        """Return list of (url, token) pairs for all configured workers."""
        candidates = [
            (settings.ai_image_worker1, settings.ai_image_worker1_token),
            (settings.ai_image_worker2, settings.ai_image_worker2_token),
            (settings.ai_image_worker3, settings.ai_image_worker3_token),
            (settings.ai_image_worker4, settings.ai_image_worker4_token),
        ]
        return [(url, token) for url, token in candidates if url]

    async def _call_worker(self, url: str, token: str, payload: dict) -> io.BytesIO | None:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        return io.BytesIO(await resp.read())
                    logging.warning(f"Worker {url} returned {resp.status}: {await resp.text()}")
                    return None
        except Exception as e:
            logging.error(f"Worker {url} error: {e}")
            return None

    async def generate_image(self, prompt: str, image_b64: str = None) -> io.BytesIO | None:
        """
        Generate an image from a text prompt. If image_b64 is provided, it performs img2img.
        Rotates between workers in round-robin order; falls back to the other if one fails.
        """
        workers = self._get_workers()
        if not workers:
            logging.error("No image workers configured.")
            return None

        # Round-robin pick, then fall back to remaining workers
        start_idx = next(self._counter) % len(workers)
        ordered = workers[start_idx:] + workers[:start_idx]
        
        payload = {"prompt": prompt}
        if image_b64:
            payload["image_b64"] = image_b64

        for url, token in ordered:
            result = await self._call_worker(url, token, payload)
            if result:
                return result
            logging.warning(f"Worker {url} failed, trying next...")

        logging.error("All image workers failed.")
        return None


img_generator_service = ImageGeneratorService()
