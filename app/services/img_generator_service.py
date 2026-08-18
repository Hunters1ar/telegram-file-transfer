import aiohttp
import io
import logging

class ImageGeneratorService:
    def __init__(self):
        self.url = "https://image-generator.yeslichto09.workers.dev/"
        self.token = "152634879"

    async def generate_image(self, prompt: str) -> io.BytesIO | None:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return io.BytesIO(image_data)
                    else:
                        error_text = await response.text()
                        logging.error(f"Image generation failed: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logging.error(f"Error during image generation: {e}")
            return None

img_generator_service = ImageGeneratorService()
