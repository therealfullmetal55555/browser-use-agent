"""
Computer use - GPT-6 Sol native computer use or OpenAI vision fallback
Model gets screenshot, decides where to click/what to type

For portfolio: uses OpenAI vision (gpt-4o) if API key set, else mock deterministic
"""
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from typing import Literal

from .config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, USE_MOCK_LLM

logger = logging.getLogger(__name__)

class ComputerUseAction(BaseModel):
    action: Literal["click", "type", "scroll", "navigate", "wait", "done"] = Field(description="Action to take")
    x: Optional[int] = Field(default=None, description="X coordinate for click/type")
    y: Optional[int] = Field(default=None, description="Y coordinate for click/type")
    text: Optional[str] = Field(default=None, description="Text to type, or URL to navigate")
    direction: Optional[str] = Field(default=None, description="Scroll direction: up/down/top/bottom")
    reasoning: str = Field(description="Reasoning for this action, what you see and why you choose this")
    task_progress: str = Field(default="", description="Current progress on task")
    is_done: bool = Field(default=False, description="True if task is complete")

COMPUTER_USE_SYSTEM_PROMPT = """You are a browser automation agent with computer use ability (like GPT-6 Sol native computer use).

You get a screenshot of current browser page and a task. You must decide next action.

Task examples:
- "Check availability and price of Wireless Headphones Pro Max on demo store, if in stock add to cart and report total with delivery"
- "Search for powerbank on demo store"

Available actions:
- click: click at x,y coordinates (you must estimate coordinates from screenshot, 0-1000 range)
- type: type text (optionally at x,y first)
- scroll: scroll up/down/top/bottom
- navigate: go to URL
- wait: wait 1-2 seconds
- done: task complete, provide final answer

Rules:
- Look carefully at screenshot - identify products, prices, stock, buttons
- For search: type in search box
- For add to cart: click Add to Cart button
- For cart total: click cart icon, read total with delivery
- Never enter payment data - stop before payment (final boundary)
- If stuck (same action 3+ times without progress), try different approach or say done with explanation
- Be precise with coordinates - estimate based on layout
- Always provide reasoning

Return JSON with action, x, y, text, reasoning, is_done.

Example:
Screenshot shows demo store with headphones at 89 EUR in stock, Add to Cart button visible at bottom of product card.

Task: Check headphones price and add to cart if in stock

You should:
{
  "action": "click",
  "x": 150,
  "y": 350,
  "text": null,
  "direction": null,
  "reasoning": "I see Wireless Headphones Pro Max at 89 EUR, in stock (15 available), Add to Cart button visible. I will click it to add to cart.",
  "task_progress": "Found product, price 89 EUR, in stock, adding to cart",
  "is_done": false
}
"""

def build_user_prompt(task: str, screenshot_path: Optional[Path] = None, page_info: Dict = None, history: list = None) -> tuple[str, Optional[str]]:
    """
    Build prompt for computer use model
    Returns (text_prompt, base64_image_or_none)
    """
    page_info_str = ""
    if page_info:
        page_info_str = f"\nCurrent page: {page_info.get('url')} - {page_info.get('title')}"
    
    history_str = ""
    if history:
        # Last 3 actions
        recent = history[-3:]
        history_str = "\nRecent actions:\n" + "\n".join([f"- {h.get('action')} at ({h.get('x')},{h.get('y')}) - {h.get('reasoning','')[:100]}" for h in recent])
    
    text_prompt = f"""
Task: {task}
{page_info_str}
{history_str}

Analyze screenshot and decide next action. Return JSON.

If task is "Check availability and price of product X":
1. Search for product if not visible
2. Check price and stock
3. If in stock, add to cart
4. Go to cart and report total with delivery
5. Then done

Remember: stop before payment, don't enter card data.
"""
    
    # Encode screenshot if exists
    image_b64 = None
    if screenshot_path and screenshot_path.exists() and screenshot_path.suffix.lower() in ['.png','.jpg','.jpeg']:
        try:
            # Check if file is actually image (not mock text)
            if screenshot_path.stat().st_size > 1000:
                with open(screenshot_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to encode screenshot {screenshot_path}: {e}")
    
    return text_prompt, image_b64

def mock_computer_use(task: str, step: int, page_info: Dict = None, history: list = None) -> ComputerUseAction:
    """
    Mock computer use that simulates deterministic actions for demo store
    This allows portfolio demo without real vision API and without Playwright browser
    """
    task_lower = task.lower()
    
    # Simulate a successful trace for "headphones" task
    # Step 0: initial page, need to search or find product
    # Step 1: click product or add to cart
    # Step 2: go to cart
    # Step 3: report total and done
    
    # For headphones task
    if "headphone" in task_lower:
        if step == 0:
            return ComputerUseAction(
                action="click",
                x=200,
                y=300,
                reasoning="I see demo store with 8 products. Wireless Headphones Pro Max is visible at top left, price 89 EUR, in stock. I will click Add to Cart button.",
                task_progress="Found headphones, price 89 EUR, in stock: 15",
                is_done=False
            )
        elif step == 1:
            return ComputerUseAction(
                action="click",
                x=750,
                y=50,
                reasoning="Headphones added to cart (button changed to Added!). Now I need to click cart icon at top right to see total with delivery.",
                task_progress="Added headphones to cart, now checking cart total",
                is_done=False
            )
        elif step == 2:
            return ComputerUseAction(
                action="done",
                reasoning="I am in cart page. I see subtotal 89.00 EUR, delivery 5.99 EUR, total 94.99 EUR. Task complete: headphones available at 89 EUR, in stock, added to cart, total with delivery 94.99 EUR. Stopping before payment as required.",
                task_progress="Task complete: price 89 EUR, in stock, cart total 94.99 EUR with delivery",
                is_done=True
            )
    
    # For powerbank task
    if "powerbank" in task_lower:
        if step == 0:
            return ComputerUseAction(
                action="type",
                x=200,
                y=120,
                text="powerbank",
                reasoning="I need to search for powerbank. I'll type 'powerbank' in search box at top.",
                task_progress="Searching for powerbank",
                is_done=False
            )
        elif step == 1:
            return ComputerUseAction(
                action="click",
                x=250,
                y=200,
                reasoning="Search results show Powerbank 20000mAh at 39 EUR, in stock. Clicking Add to Cart.",
                task_progress="Found powerbank 39 EUR, in stock, adding to cart",
                is_done=False
            )
        elif step == 2:
            return ComputerUseAction(
                action="click",
                x=750,
                y=50,
                reasoning="Added to cart, now going to cart to get total",
                task_progress="Added to cart, checking total",
                is_done=False
            )
        elif step == 3:
            return ComputerUseAction(
                action="done",
                reasoning="Cart shows powerbank 39 EUR + delivery 5.99 = total 44.99 EUR. Task complete, stopping before payment.",
                task_progress="Complete: powerbank 39 EUR, total 44.99 with delivery",
                is_done=True
            )
    
    # Default - try to add first product and done
    if step == 0:
        return ComputerUseAction(
            action="click",
            x=200,
            y=300,
            reasoning="I see demo store. I'll add first product to cart as example.",
            task_progress="Adding first product",
            is_done=False
        )
    elif step == 1:
        return ComputerUseAction(
            action="click",
            x=750,
            y=50,
            reasoning="Added product, going to cart",
            task_progress="Checking cart",
            is_done=False
        )
    else:
        return ComputerUseAction(
            action="done",
            reasoning="Task complete in mock mode. Cart total with delivery would be shown here. Stopping before payment.",
            task_progress="Mock task complete",
            is_done=True
        )

def llm_computer_use(task: str, screenshot_path: Path, page_info: Dict = None, history: list = None) -> ComputerUseAction:
    """
    Real computer use via OpenAI vision / GPT-6 Sol
    """
    if USE_MOCK_LLM:
        # Extract step from history length
        step = len(history) if history else 0
        return mock_computer_use(task, step, page_info, history)
    
    try:
        from openai import OpenAI
        
        client_kwargs = {}
        if OPENAI_BASE_URL:
            client_kwargs["base_url"] = OPENAI_BASE_URL
        client_kwargs["api_key"] = OPENAI_API_KEY
        client = OpenAI(**client_kwargs)
        
        text_prompt, image_b64 = build_user_prompt(task, screenshot_path, page_info, history)
        
        # Build message with image
        if image_b64:
            user_content = [
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        else:
            user_content = text_prompt
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": COMPUTER_USE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        action = ComputerUseAction(**data)
        logger.info(f"LLM computer use: {action.action} at ({action.x},{action.y}) - {action.reasoning[:100]}...")
        return action
    
    except Exception as e:
        logger.error(f"LLM computer use failed, fallback to mock: {e}")
        step = len(history) if history else 0
        mock_action = mock_computer_use(task, step, page_info, history)
        mock_action.reasoning += f" (fallback mock due to LLM error: {e})"
        return mock_action

if __name__ == "__main__":
    # Test mock
    for step in range(3):
        action = mock_computer_use("Check availability and price of Wireless Headphones Pro Max, if in stock add to cart and report total with delivery", step)
        print(f"Step {step}: {action.action} - {action.reasoning}")
