"""
Main browser agent loop - screenshot -> decision -> action -> new screenshot
Simple Python loop, no LangChain needed for MVP (as per brief)
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .config import MAX_STEPS, SCREENSHOT_DIR, COST_PER_1K_VISION_TOKENS, TOKENS_PER_SCREENSHOT, TEST_STORE_PATH, HEADLESS, SLOW_MO, USE_MOCK_LLM
from .actions import BrowserActions, MockBrowserActions
from .computer_use import llm_computer_use, ComputerUseAction

logger = logging.getLogger(__name__)

class BrowserAgent:
    def __init__(self, task: str, headless: bool = HEADLESS, slow_mo: int = SLOW_MO, max_steps: int = MAX_STEPS, use_mock: bool = None):
        self.task = task
        self.headless = headless
        self.slow_mo = slow_mo
        self.max_steps = max_steps
        self.use_mock = use_mock if use_mock is not None else USE_MOCK_LLM
        
        self.steps: List[Dict] = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = None
        self.end_time = None
        
        # For loop detection
        self.recent_actions: List[str] = []
    
    def _check_loop(self, action: ComputerUseAction) -> bool:
        """Detect if agent is stuck looping same action 3+ times"""
        action_key = f"{action.action}_{action.x}_{action.y}_{action.text}"
        self.recent_actions.append(action_key)
        # Keep last 5
        if len(self.recent_actions) > 5:
            self.recent_actions.pop(0)
        
        # Check if last 3 are same
        if len(self.recent_actions) >= 3:
            last_three = self.recent_actions[-3:]
            if len(set(last_three)) == 1:
                logger.warning(f"Loop detected: same action 3 times: {last_three[0]}")
                return True
        return False
    
    def _calculate_cost(self, steps: int) -> tuple[int, float]:
        """Calculate cost: each screenshot = vision tokens"""
        tokens = steps * TOKENS_PER_SCREENSHOT
        cost = (tokens / 1000) * COST_PER_1K_VISION_TOKENS
        return tokens, cost
    
    async def run(self, start_url: Optional[str] = None) -> Dict:
        """
        Main loop
        """
        self.start_time = datetime.now(timezone.utc)
        logger.info(f"Starting browser agent task: {self.task}")
        logger.info(f"Mock mode: {self.use_mock}, Headless: {self.headless}, Max steps: {self.max_steps}")
        
        # Setup browser
        if self.use_mock:
            actions = MockBrowserActions(SCREENSHOT_DIR)
            page = None
            browser = None
            playwright = None
            logger.info("Using Mock Browser (no Playwright)")
        else:
            try:
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                actions = BrowserActions(page, SCREENSHOT_DIR)
                logger.info("Playwright browser launched")
            except Exception as e:
                logger.error(f"Failed to launch Playwright, fallback to mock: {e}")
                actions = MockBrowserActions(SCREENSHOT_DIR)
                page = None
                browser = None
                playwright = None
                self.use_mock = True
        
        # Navigate to start URL
        if start_url is None:
            # Use local test store
            if TEST_STORE_PATH.exists():
                start_url = f"file://{TEST_STORE_PATH.resolve()}"
            else:
                start_url = "https://books.toscrape.com/"  # Fallback public demo store
        
        try:
            nav_result = await actions.navigate(start_url)
            screenshot_path = await actions.screenshot("initial")
            
            self.steps.append({
                "step": 0,
                "action": "navigate",
                "url": start_url,
                "reasoning": f"Initial navigation to {start_url}",
                "screenshot": str(screenshot_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "page_info": await actions.get_page_info()
            })
            
            # Main loop
            for step_num in range(1, self.max_steps + 1):
                logger.info(f"\n=== Step {step_num}/{self.max_steps} ===")
                
                # Get page info
                page_info = await actions.get_page_info()
                
                # Take screenshot
                screenshot_path = await actions.screenshot(f"step_{step_num}_before_decision")
                
                # Call computer use model
                history = [{"action": s["action"], "x": s.get("x"), "y": s.get("y"), "reasoning": s.get("reasoning","")} for s in self.steps]
                decision: ComputerUseAction = llm_computer_use(
                    task=self.task,
                    screenshot_path=screenshot_path,
                    page_info=page_info,
                    history=history
                )
                
                logger.info(f"Decision: {decision.action} - {decision.reasoning}")
                logger.info(f"Progress: {decision.task_progress}")
                
                # Check loop
                if self._check_loop(decision):
                    logger.warning("Stopping due to loop detection")
                    self.steps.append({
                        "step": step_num,
                        "action": "loop_detected",
                        "reasoning": f"Loop detected - same action 3 times, stopping. Last action: {decision.action}",
                        "screenshot": str(screenshot_path),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "is_loop": True
                    })
                    break
                
                # Check if done
                if decision.is_done or decision.action == "done":
                    logger.info(f"Task marked as done: {decision.reasoning}")
                    self.steps.append({
                        "step": step_num,
                        "action": "done",
                        "reasoning": decision.reasoning,
                        "task_progress": decision.task_progress,
                        "screenshot": str(screenshot_path),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "is_done": True,
                        "final_answer": decision.reasoning
                    })
                    break
                
                # Execute action
                result = {}
                if decision.action == "click":
                    result = await actions.click(decision.x or 0, decision.y or 0, decision.reasoning)
                elif decision.action == "type":
                    result = await actions.type_text(decision.text or "", decision.x, decision.y, decision.reasoning)
                elif decision.action == "scroll":
                    result = await actions.scroll(decision.direction or "down", 300)
                elif decision.action == "navigate":
                    result = await actions.navigate(decision.text or start_url)
                elif decision.action == "wait":
                    result = await actions.wait(1.0)
                else:
                    logger.warning(f"Unknown action {decision.action}")
                    result = {"success": False, "error": f"Unknown action {decision.action}"}
                
                # Screenshot after action
                await asyncio.sleep(0.5)
                after_screenshot = await actions.screenshot(f"step_{step_num}_after_{decision.action}")
                
                # Log step
                self.steps.append({
                    "step": step_num,
                    "action": decision.action,
                    "x": decision.x,
                    "y": decision.y,
                    "text": decision.text,
                    "direction": decision.direction,
                    "reasoning": decision.reasoning,
                    "task_progress": decision.task_progress,
                    "screenshot_before": str(screenshot_path),
                    "screenshot_after": str(after_screenshot),
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "page_info": page_info
                })
                
                # Cost tracking
                self.total_tokens, self.total_cost = self._calculate_cost(step_num)
                
                # Small delay
                await asyncio.sleep(0.5)
            
            self.end_time = datetime.now(timezone.utc)
            duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
            
            # Final summary
            final_answer = ""
            for s in reversed(self.steps):
                if s.get("is_done") and s.get("final_answer"):
                    final_answer = s["final_answer"]
                    break
                if s.get("reasoning") and "total" in s.get("reasoning","").lower():
                    final_answer = s["reasoning"]
            
            summary = {
                "task": self.task,
                "start_url": start_url,
                "total_steps": len(self.steps),
                "total_tokens": self.total_tokens,
                "total_cost_usd": round(self.total_cost, 4),
                "cost_per_step": round(self.total_cost / len(self.steps), 4) if self.steps else 0,
                "duration_seconds": round(duration, 2),
                "is_done": any(s.get("is_done") for s in self.steps),
                "is_loop": any(s.get("is_loop") for s in self.steps),
                "final_answer": final_answer or "Task completed (mock)",
                "steps": self.steps,
                "mock": self.use_mock,
                "start_time": self.start_time.isoformat() if self.start_time else "",
                "end_time": self.end_time.isoformat() if self.end_time else ""
            }
            
            # Save trace
            trace_path = SCREENSHOT_DIR / f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with open(trace_path, 'w', encoding='utf-8') as f:
                # Convert datetime objects to string for JSON
                json.dump(summary, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"\n=== Task Finished ===")
            logger.info(f"Steps: {len(self.steps)}, Cost: ${summary['total_cost_usd']}, Duration: {duration}s")
            logger.info(f"Final answer: {final_answer}")
            logger.info(f"Trace saved to {trace_path}")
            
            return summary
        
        finally:
            # Cleanup
            if not self.use_mock and 'browser' in locals() and browser:
                try:
                    await browser.close()
                    await playwright.stop()
                except:
                    pass

def run_sync(task: str, start_url: str = None, max_steps: int = MAX_STEPS, use_mock: bool = True) -> Dict:
    """Sync wrapper for async run"""
    agent = BrowserAgent(task=task, max_steps=max_steps, use_mock=use_mock)
    return asyncio.run(agent.run(start_url=start_url))

if __name__ == "__main__":
    # Test with mock
    task = "Check availability and price of Wireless Headphones Pro Max on demo store, if in stock add to cart and report total with delivery"
    result = run_sync(task, use_mock=True, max_steps=5)
    print(json.dumps(result, indent=2, default=str))
