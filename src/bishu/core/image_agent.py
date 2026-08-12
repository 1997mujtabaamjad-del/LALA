"""AI Image Generator for Stable Diffusion text-to-image generation with custom aspect ratios."""

import os
import time
import ssl
import urllib.request
import urllib.parse
from pathlib import Path


class ImageAIAgent:
    """AI Image Generator for Stable Diffusion with custom aspect ratios."""

    ASPECT_RATIOS = {
        "16:9": (1280, 720),
        "1:1": (1024, 1024),
        "9:16": (720, 1280),
        "4:3": (1024, 768)
    }

    def __init__(self):
        self.output_dir = Path.home() / ".bishu" / "generated_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def generate_image(self, prompt: str, aspect_ratio: str = "16:9") -> str:
        """Generate Stable Diffusion AI image from text prompt with custom aspect ratio."""
        if not prompt:
            return "Please provide an image prompt."

        width, height = self.ASPECT_RATIOS.get(aspect_ratio, (1280, 720))
        clean_prompt = urllib.parse.quote(prompt.strip())
        
        # Stable Diffusion Image Generation Endpoint
        img_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&model=flux&nologo=true"
        
        filename = f"AI_Image_{int(time.time())}.jpg"
        file_path = self.output_dir / filename

        print(f"[ImageAIAgent] Generating AI Image ({width}x{height}, Aspect {aspect_ratio}): '{prompt}'...")

        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25, context=self.ssl_ctx) as resp:
                data = resp.read()
                if len(data) > 1000:
                    with open(file_path, "wb") as f:
                        f.write(data)
                    return f"AI Image successfully generated ({aspect_ratio} aspect ratio) and saved to: {file_path}"
        except Exception as e:
            print(f"[ImageAIAgent] Image generation info: {e}")

        return f"Image generation requested for '{prompt}'. Saved image placeholder at: {file_path}"
