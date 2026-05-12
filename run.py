#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.browser_agent import run_sync
import json

if __name__ == "__main__":
    task = "Check availability and price of Wireless Headphones Pro Max on demo store, if in stock add to cart and report total with delivery"
    
    # Test with headphones
    print("=== Test 1: Headphones ===")
    result = run_sync(task, use_mock=True, max_steps=5)
    print(f"Steps: {result['total_steps']}, Cost: ${result['total_cost_usd']}, Done: {result['is_done']}")
    print(f"Final: {result['final_answer']}")
    
    # Test with powerbank
    print("\n=== Test 2: Powerbank ===")
    task2 = "Search for powerbank on demo store, check price and stock, add to cart if available, report total with delivery"
    result2 = run_sync(task2, use_mock=True, max_steps=6)
    print(f"Steps: {result2['total_steps']}, Cost: ${result2['total_cost_usd']}, Done: {result2['is_done']}")
    print(f"Final: {result2['final_answer']}")
