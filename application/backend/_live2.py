import asyncio, sys, time
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from app.services.competitor import COMPETITOR_CONFIGS, generate_competitor_analysis, resolve_inputs

async def main():
    cfg = COMPETITOR_CONFIGS["competitor_analysis_lead_magnet"]
    inputs = resolve_inputs(cfg, {
        "client_website_url": "https://www.acmedental.com.au/",
        "industry": "dental implants",
        "region_location": "Melbourne, Australia",
    })
    print("inputs:", inputs, flush=True)
    t = time.time()
    out = await generate_competitor_analysis("competitor_analysis_lead_magnet", inputs)
    print(f"--- {len(out)} chars in {time.time()-t:.1f}s ---")
    print(out[:900])

asyncio.run(main())
