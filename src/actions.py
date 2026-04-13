"""
Playwright action wrappers - execution layer
"""
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserActions:
    def __init__(self, page, screenshot_dir: Path):
        self.page = page
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.step_count = 0
    
    async def screenshot(self, step_name: str = "") -> Path:
        """Take screenshot and save"""
        self.step_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"step_{self.step_count:03d}_{step_name}_{timestamp}.png"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        path = self.screenshot_dir / filename
        
        try:
            await self.page.screenshot(path=str(path), full_page=False)
            logger.info(f"Screenshot saved: {path}")
            return path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return path
    
    async def click(self, x: int, y: int, description: str = "") -> Dict:
        """Click at coordinates"""
        try:
            await self.page.mouse.click(x, y)
            logger.info(f"Clicked at ({x},{y}) - {description}")
            return {"success": True, "action": "click", "x": x, "y": y, "description": description}
        except Exception as e:
            logger.error(f"Click failed at ({x},{y}): {e}")
            return {"success": False, "error": str(e), "action": "click"}
    
    async def type_text(self, text: str, x: Optional[int] = None, y: Optional[int] = None, description: str = "") -> Dict:
        """Type text, optionally click first at x,y"""
        try:
            if x is not None and y is not None:
                await self.page.mouse.click(x, y)
                await self.page.wait_for_timeout(200)
            await self.page.keyboard.type(text)
            logger.info(f"Typed '{text[:30]}...' at ({x},{y}) - {description}")
            return {"success": True, "action": "type", "text": text, "x": x, "y": y}
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return {"success": False, "error": str(e), "action": "type"}
    
    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict:
        """Scroll page"""
        try:
            if direction == "down":
                await self.page.mouse.wheel(0, amount)
            elif direction == "up":
                await self.page.mouse.wheel(0, -amount)
            elif direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            await self.page.wait_for_timeout(500)
            logger.info(f"Scrolled {direction} {amount}")
            return {"success": True, "action": "scroll", "direction": direction, "amount": amount}
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def navigate(self, url: str) -> Dict:
        """Navigate to URL"""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self.page.wait_for_timeout(1000)
            logger.info(f"Navigated to {url}")
            return {"success": True, "action": "navigate", "url": url, "title": await self.page.title()}
        except Exception as e:
            logger.error(f"Navigate to {url} failed: {e}")
            return {"success": False, "error": str(e), "action": "navigate"}
    
    async def get_page_info(self) -> Dict:
        """Get current page info for agent context"""
        try:
            return {
                "url": self.page.url,
                "title": await self.page.title(),
                "viewport": self.page.viewport_size,
            }
        except Exception as e:
            return {"url": "unknown", "title": "unknown", "error": str(e)}
    
    async def wait(self, seconds: float = 1.0) -> Dict:
        """Wait"""
        try:
            await self.page.wait_for_timeout(int(seconds * 1000))
            return {"success": True, "action": "wait", "seconds": seconds}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Mock actions for demo without Playwright
class MockBrowserActions:
    def __init__(self, screenshot_dir: Path):
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.step_count = 0
        self.current_url = "file:///test-store/index.html"
        self.cart = []
        self.log = []
    
    async def screenshot(self, step_name: str = "") -> Path:
        self.step_count += 1
        # Create mock screenshot as text file
        path = self.screenshot_dir / f"step_{self.step_count:03d}_{step_name}_mock.png"
        # Create a simple image with PIL that says mock
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 600), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), f"Mock Screenshot Step {self.step_count}", fill=(0,0,0))
            draw.text((20, 50), f"Action: {step_name}", fill=(0,0,0))
            draw.text((20, 80), f"URL: {self.current_url}", fill=(0,0,0))
            draw.text((20, 110), f"Cart: {len(self.cart)} items", fill=(0,0,0))
            img.save(str(path))
        except:
            path.write_text(f"Mock screenshot step {self.step_count} - {step_name}")
        return path
    
    async def click(self, x: int, y: int, description: str = "") -> Dict:
        self.log.append(f"Click at ({x},{y}) - {description}")
        return {"success": True, "action": "click", "x": x, "y": y, "description": description, "mock": True}
    
    async def type_text(self, text: str, x: Optional[int] = None, y: Optional[int] = None, description: str = "") -> Dict:
        self.log.append(f"Type '{text}' at ({x},{y})")
        return {"success": True, "action": "type", "text": text, "mock": True}
    
    async def scroll(self, direction: str = "down", amount: int = 300) -> Dict:
        self.log.append(f"Scroll {direction} {amount}")
        return {"success": True, "action": "scroll", "direction": direction, "mock": True}
    
    async def navigate(self, url: str) -> Dict:
        self.current_url = url
        self.log.append(f"Navigate to {url}")
        return {"success": True, "action": "navigate", "url": url, "mock": True, "title": "Mock Demo Store"}
    
    async def get_page_info(self) -> Dict:
        return {"url": self.current_url, "title": "Mock Demo Store", "mock": True}
    
    async def wait(self, seconds: float = 1.0) -> Dict:
        return {"success": True, "action": "wait", "seconds": seconds, "mock": True}
