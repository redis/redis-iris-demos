# Demo Paths

Scripted paths for the CraftHub arts & crafts retail demo. The signed-in customer is
**Emily Carter** (Rewards Plus, 2,340 points), home store **CraftHub Las Colinas** (Irving, TX).

> Tip: Run an opening question once in Context Surfaces mode, then repeat it in Simple RAG
> mode to show that generic RAG can explain policies but can't see live inventory, classes,
> or Emily's orders.

Class times are generated for the *upcoming* Saturday/Sunday, so "this weekend" always works.

## Path 1: Project Supplies to Weekend Class (Context Retriever)

1. Ask: "I want to make a fall wreath for my front door. What do I need, and is it in stock at my store?"
   → `get_current_user_profile`, several `search_product_by_text`, `filter_storeinventory` (STORE_001)
   → Supply list with sale prices, aisle locations, and live quantities: **Hearth & Harvest 24 in Grapevine
   Wreath Base**, **Fall Maple Leaf & Berry Picks** (6-8), **Wired Burlap Ribbon** (only 2 left),
   **Ad Tech Pro 200 Hot Glue Gun**.
2. Follow with: "Is there a class for that this weekend?"
   → `get_current_time`, `filter_workshop`
   → **Fall Grapevine Wreath Workshop**, Saturday 10:00 AM, $25, 5 seats, supplies not included
   (the supply list matches what was just found in stock).

RAG contrast: Simple RAG can return the wreath checklist guide, but not stock, aisles, or class seats.

## Path 2: Sold Out Locally, Available Nearby

1. Ask: "Do you have a Cricut Maker 3 in stock at my store?"
   → **Sold out at Las Colinas**; agent checks all stores and offers **Preston Royal (3)** or
   **Frisco Stonebriar (2)** for pickup today.

## Path 3: Shipment Delay Investigation

1. Ask: "I haven't received my Cricut order yet."
   → `filter_order`, `get_current_time`, `filter_shipment`, `filter_shipmentevent`
   → `ORD_MI_1001` (Cricut Maker 3 + vinyl + iron-on) is delayed at the **FedEx Memphis hub** by
   severe thunderstorms; original promise date passed, new estimate is tomorrow.
2. Follow with: "Has support already opened a case?"
   → `filter_supportcase` → `CASE_MI_001` is open for the shipment delay.

## Path 4: Custom Framing Status

1. Ask: "When will my custom frame be ready?"
   → `ORD_MI_1003`: 16 in x 20 in watercolor print, walnut frame, double white mat, conservation
   glass — **in production** at Las Colinas, ready in ~2 days.

## Path 5: Agent Memory

Seeded long-term memories:
- "Crafting interests: knits chunky blankets and is getting into Cricut vinyl projects"
- "Shopping preference: prefers curbside pickup at the CraftHub Las Colinas store"

1. Ask: "Please remember that I prefer curbside pickup at Las Colinas and I'm really into Cricut vinyl projects."
   → `remember_customer_detail` (acknowledged; writes are blocked in demo mode)
2. Click **Memory** to show short-term session events and long-term memories.
3. Ask: "Given what you know about me, what should I check out next time I visit?"
   → Uses the memories, checks Emily's orders and Las Colinas inventory, and recommends in-stock
   blanket yarn and vinyl, referencing her curbside preference.

## Path 6: LangCache and Guardrails

1. Ask: "What's your return policy?" → cache hit on the seeded LangCache entry (60 days; Cricut
   machines 30 days; custom framing final sale).
2. Ask: "Tell me a joke" → blocked by semantic routing before reaching the LLM.

Policies, prices, and store details are illustrative demo data.
