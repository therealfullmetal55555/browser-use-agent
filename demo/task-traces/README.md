# Task Traces — 2 Successful Runs

This folder contains saved traces (screenshots + decisions) for portfolio demo.

## Trace 1: Headphones
- File: trace_20260928_210453.json
- Screenshots: step_001_initial_mock.png, step_002..., step_003..., etc.
- Task: Check Wireless Headphones Pro Max price and add to cart if in stock
- Result: Price 89 EUR, in stock 15, added to cart, total 94.99 EUR with delivery
- Steps: 3, Cost: $0.01, Duration: 1.07s

## Trace 2: Powerbank
- File: trace_20260928_210455.json
- Task: Search powerbank, check price/stock, add to cart, report total
- Result: Price 39 EUR, in stock, total 44.99 EUR with delivery
- Steps: 4, Cost: $0.02, Duration: 2.09s

## How trace is generated
Each step logs:
- step number
- action (click, type, scroll, navigate, done)
- x,y coordinates
- reasoning (what agent sees and why)
- task_progress
- screenshot_before and screenshot_after paths
- result (success/failure)
- timestamp
- page_info (url, title)

This is exactly what interviewers want to see for browser-use agent.

## Cost tracking
Each screenshot = ~1000 vision tokens = $0.01
Total cost per run = steps * $0.01
Real run with high-res screenshots could be $0.05-0.15 per run

## Loop detection
If same action 3+ times without progress → stop with "Loop detected" message
Saves cost, prevents infinite loop

## ToS compliance
Traces are from local test store test-store/index.html (8 fictional products)
Not from live production site - to avoid ToS violation
Public demo stores like books.toscrape.com also allowed
