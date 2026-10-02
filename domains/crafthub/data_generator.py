"""Generate sample data for the CraftHub arts & crafts retail demo."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import openai
from dotenv import load_dotenv

from backend.app.core.domain_contract import GeneratedDataset

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "output" / "crafthub"
STORE_TZ = ZoneInfo("America/Chicago")


def ts(dt: datetime) -> str:
    return dt.isoformat()


now = datetime.now(timezone.utc)


def upcoming(weekday: int, hour: int, minute: int = 0) -> datetime:
    """Next occurrence of a local store time (Mon=0 ... Sun=6), always in the future."""
    local_now = now.astimezone(STORE_TZ)
    days_ahead = (weekday - local_now.weekday()) % 7
    candidate = (local_now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=7)
    return candidate


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    client = openai.OpenAI()
    response = client.embeddings.create(
        input=texts,
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return [item.embedding for item in response.data]


def product(
    product_id: str,
    sku: str,
    name: str,
    brand: str,
    category: str,
    subcategory: str,
    craft_type: str,
    price: float,
    sale_price: float,
    rating: float,
    availability_status: str,
    details_summary: str,
    project_uses: str,
    project_fit_summary: str,
    search_text: str,
    *,
    pickup_eligible: bool = True,
    shipping_eligible: bool = True,
) -> dict[str, object]:
    return {
        "product_id": product_id,
        "sku": sku,
        "name": name,
        "brand": brand,
        "category": category,
        "subcategory": subcategory,
        "craft_type": craft_type,
        "price": price,
        "sale_price": sale_price,
        "rating": rating,
        "availability_status": availability_status,
        "pickup_eligible": pickup_eligible,
        "shipping_eligible": shipping_eligible,
        "details_summary": details_summary,
        "project_uses": project_uses,
        "project_fit_summary": project_fit_summary,
        "search_text": search_text,
    }


def inventory(
    inventory_id: str,
    store_id: str,
    product_id: str,
    quantity_available: int,
    pickup_status: str,
    pickup_eta_hours: int,
    aisle_location: str | None,
) -> dict[str, object]:
    return {
        "inventory_id": inventory_id,
        "store_id": store_id,
        "product_id": product_id,
        "store_name": STORE_NAME_BY_ID[store_id],
        "product_name": PRODUCT_NAME_BY_ID[product_id],
        "quantity_available": quantity_available,
        "pickup_status": pickup_status,
        "pickup_eta_hours": pickup_eta_hours,
        "aisle_location": aisle_location,
    }


DEMO_CUSTOMER = {
    "customer_id": "CUST_MI_001",
    "name": "Emily Carter",
    "email": "emily.carter@example.com",
    "city": "Irving",
    "state": "TX",
    "member_tier": "rewards_plus",
    "rewards_points": 2340,
    "home_store_id": "STORE_001",
    "home_store_name": "CraftHub Las Colinas",
    "account_created_at": ts(now - timedelta(days=940)),
}

CUSTOMERS = [
    DEMO_CUSTOMER,
    {
        "customer_id": "CUST_MI_002",
        "name": "Marcus Reyes",
        "email": "marcus.reyes@example.com",
        "city": "Dallas",
        "state": "TX",
        "member_tier": "rewards",
        "rewards_points": 410,
        "home_store_id": "STORE_002",
        "home_store_name": "CraftHub Preston Royal",
        "account_created_at": ts(now - timedelta(days=260)),
    },
    {
        "customer_id": "CUST_MI_003",
        "name": "Hannah Brooks",
        "email": "hannah.brooks@example.com",
        "city": "Frisco",
        "state": "TX",
        "member_tier": "pro",
        "rewards_points": 5120,
        "home_store_id": "STORE_003",
        "home_store_name": "CraftHub Frisco Stonebriar",
        "account_created_at": ts(now - timedelta(days=1430)),
    },
    {
        "customer_id": "CUST_MI_004",
        "name": "Olivia Nguyen",
        "email": "olivia.nguyen@example.com",
        "city": "Plano",
        "state": "TX",
        "member_tier": "rewards",
        "rewards_points": 875,
        "home_store_id": "STORE_004",
        "home_store_name": "CraftHub Plano Legacy",
        "account_created_at": ts(now - timedelta(days=615)),
    },
]

STORES = [
    {
        "store_id": "STORE_001",
        "name": "CraftHub Las Colinas",
        "city": "Irving",
        "state": "TX",
        "zip_code": "75039",
        "address": "5120 N MacArthur Blvd, Irving, TX 75039",
        "phone": "+1-972-555-0141",
        "pickup_supported": True,
        "curbside_supported": True,
        "custom_framing": True,
        "services": "Custom framing counter, classroom, curbside pickup, Cricut demo station, balloon and party counter",
        "hours_summary": "Mon-Sat 9am-9pm, Sun 10am-7pm",
    },
    {
        "store_id": "STORE_002",
        "name": "CraftHub Preston Royal",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75230",
        "address": "6010 Royal Ln, Dallas, TX 75230",
        "phone": "+1-214-555-0142",
        "pickup_supported": True,
        "curbside_supported": True,
        "custom_framing": True,
        "services": "Custom framing counter, classroom, curbside pickup, expanded yarn wall",
        "hours_summary": "Mon-Sat 9am-9pm, Sun 10am-7pm",
    },
    {
        "store_id": "STORE_003",
        "name": "CraftHub Frisco Stonebriar",
        "city": "Frisco",
        "state": "TX",
        "zip_code": "75034",
        "address": "2640 Preston Rd, Frisco, TX 75034",
        "phone": "+1-469-555-0143",
        "pickup_supported": True,
        "curbside_supported": False,
        "custom_framing": False,
        "services": "Classroom, Cricut demo station, seasonal décor shop",
        "hours_summary": "Mon-Sat 9am-9pm, Sun 10am-7pm",
    },
    {
        "store_id": "STORE_004",
        "name": "CraftHub Plano Legacy",
        "city": "Plano",
        "state": "TX",
        "zip_code": "75024",
        "address": "7300 Dallas Pkwy, Plano, TX 75024",
        "phone": "+1-972-555-0144",
        "pickup_supported": True,
        "curbside_supported": True,
        "custom_framing": True,
        "services": "Custom framing counter, curbside pickup, fine art paint department",
        "hours_summary": "Mon-Sat 9am-9pm, Sun 10am-7pm",
    },
]

PRODUCTS = [
    # --- Cricut & Machines ---
    product(
        "PRD_001", "CRI-MAKER3-CHAMP", "Cricut Maker 3 Smart Cutting Machine", "Cricut", "Cricut & Machines", "Cutting Machines", "vinyl",
        429.99, 349.99, 4.8, "limited_stock",
        "Cuts 300+ materials including vinyl, cardstock, iron-on, felt, leather, and basswood. Works with Smart Materials up to 12 ft without a mat.",
        "Vinyl decals, custom t-shirts, home signs, party décor, felt projects, leather earrings.",
        "Top pick for makers who want the widest material range and plan to grow into wood, leather, and fabric.",
        "Cricut Maker 3 smart cutting machine, vinyl, iron-on, cardstock, fabric, felt, leather, wood, matless cutting, custom shirts, decals, signs.",
    ),
    product(
        "PRD_002", "CRI-EXPLORE3", "Cricut Explore 3 Smart Cutting Machine", "Cricut", "Cricut & Machines", "Cutting Machines", "vinyl",
        299.99, 249.99, 4.7, "in_stock",
        "Cuts 100+ materials including vinyl, iron-on, and cardstock. Matless cutting with Smart Materials.",
        "Vinyl decals, t-shirts, labels, cards, party banners.",
        "Best value for vinyl and iron-on crafters who don't need fabric or wood cutting.",
        "Cricut Explore 3 cutting machine, vinyl decals, iron-on shirts, cardstock, labels, cards, beginner friendly.",
    ),
    product(
        "PRD_003", "CRI-JOYXTRA", "Cricut Joy Xtra", "Cricut", "Cricut & Machines", "Cutting Machines", "vinyl",
        199.99, 149.99, 4.6, "in_stock",
        "Compact cutting machine for projects up to 8.5 in wide; prints-then-cuts stickers.",
        "Stickers, labels, cards, mug decals, small vinyl projects.",
        "Great starter or gift machine for small projects and sticker making.",
        "Cricut Joy Xtra compact cutting machine, stickers, labels, cards, mug decals, small vinyl, beginner, gift.",
    ),
    product(
        "PRD_004", "CRI-VINYL-PERM-BRT", "Cricut Premium Permanent Vinyl Sampler, Brights", "Cricut", "Cricut & Machines", "Vinyl", "vinyl",
        29.99, 22.49, 4.7, "in_stock",
        "Ten 12 in x 12 in sheets of outdoor-rated permanent adhesive vinyl in bright colors.",
        "Mugs, tumblers, car decals, outdoor signs, water bottles.",
        "Use for anything that gets washed or lives outdoors.",
        "Cricut permanent vinyl sampler brights, mugs, tumblers, outdoor decals, water bottles, dishwasher safe projects.",
    ),
    product(
        "PRD_005", "CRI-IRONON-SMPL", "Cricut Everyday Iron-On Sampler, Basics", "Cricut", "Cricut & Machines", "Iron-On", "vinyl",
        24.99, 18.74, 4.6, "in_stock",
        "Six 12 in x 12 in sheets of heat-transfer vinyl for cotton and poly blends.",
        "Custom t-shirts, tote bags, team shirts, baby onesies.",
        "Pair with EasyPress for shirts and totes.",
        "Cricut iron-on heat transfer vinyl sampler, custom t-shirts, tote bags, onesies, fabric projects.",
    ),
    product(
        "PRD_006", "CRI-EASYPRESS3-12", "Cricut EasyPress 3, 12 in x 10 in", "Cricut", "Cricut & Machines", "Heat Presses", "vinyl",
        199.99, 159.99, 4.8, "in_stock",
        "Bluetooth-enabled heat press with precise temperature control up to 400°F.",
        "Iron-on shirts, totes, pillows, infusible ink projects.",
        "Recommended add-on for anyone doing iron-on with a Cricut.",
        "Cricut EasyPress 3 heat press, iron-on, t-shirts, tote bags, pillows, infusible ink, bluetooth.",
    ),
    # --- Paint & Fine Art ---
    product(
        "PRD_007", "EC-ACRYLIC-24", "Easel & Co. Acrylic Paint Set, 24 Colors", "Easel & Co.", "Art Supplies", "Acrylic Paint", "painting",
        19.99, 11.99, 4.5, "in_stock",
        "Twenty-four 0.75 fl oz tubes of fast-drying acrylic paint.",
        "Canvas painting, pumpkin painting, rock painting, crafts, paint nights.",
        "Budget-friendly all-purpose acrylic set for beginners and kids' projects with supervision.",
        "Easel & Co. acrylic paint set 24 colors, canvas painting, pumpkin painting, rocks, beginner, paint night.",
    ),
    product(
        "PRD_008", "EC-CANVAS-1114-10", "Easel & Co. Stretched Canvas Value Pack, 11 in x 14 in, 10 ct", "Easel & Co.", "Art Supplies", "Canvas", "painting",
        39.99, 19.99, 4.4, "in_stock",
        "Ten pre-primed, triple-gessoed cotton canvases on wood stretcher bars.",
        "Acrylic and oil painting, paint parties, classroom art.",
        "Best value when painting in bulk or hosting a paint night.",
        "Easel & Co. stretched canvas 11x14 value pack, acrylic painting, oil painting, paint party, classroom.",
    ),
    product(
        "PRD_009", "LQX-BASICS-48", "Liquitex BASICS Acrylic Paint Set, 48 Colors", "Liquitex", "Art Supplies", "Acrylic Paint", "painting",
        79.99, 55.99, 4.8, "in_stock",
        "Forty-eight 22 ml tubes of student-grade heavy body acrylic paint.",
        "Canvas painting, mixed media, art students.",
        "Step-up acrylic set for serious hobby painters.",
        "Liquitex BASICS acrylic paint set 48 colors, heavy body, canvas, mixed media, art student, step up quality.",
    ),
    product(
        "PRD_010", "WN-COTMAN-POCKET", "Winsor & Newton Cotman Watercolor Sketchers' Pocket Box", "Winsor & Newton", "Art Supplies", "Watercolor", "watercolor",
        26.99, 21.59, 4.7, "in_stock",
        "Twelve half pans, travel brush, and mixing palette in a compact box.",
        "Watercolor florals, travel sketching, journaling.",
        "Perfect first watercolor kit for florals classes and travel.",
        "Winsor Newton Cotman watercolor pocket box, half pans, florals, travel sketching, beginner watercolor.",
    ),
    product(
        "PRD_011", "CANSON-XL-WC-912", "Canson XL Watercolor Pad, 9 in x 12 in", "Canson", "Art Supplies", "Paper Pads", "watercolor",
        14.99, 10.49, 4.6, "in_stock",
        "Thirty sheets of 140 lb cold-press watercolor paper.",
        "Watercolor florals, lettering, class practice.",
        "Standard paper for watercolor classes.",
        "Canson XL watercolor paper pad 9x12, 140 lb cold press, florals, practice, class supplies.",
    ),
    product(
        "PRD_012", "CRAYOLA-WASH-10", "Crayola Washable Kids' Paint, 10 ct", "Crayola", "Kids' Crafts", "Kids' Paint", "painting",
        9.99, 7.99, 4.8, "in_stock",
        "Ten 2 oz bottles of non-toxic, washable tempera paint.",
        "Kids' pumpkin painting, classroom art, preschool crafts.",
        "Best pick for classrooms and young kids — washes out of clothes and skin.",
        "Crayola washable kids paint, non toxic, classroom, preschool, kids pumpkin painting, teacher supplies.",
    ),
    # --- Yarn & Needlecraft ---
    product(
        "PRD_013", "BERNAT-BLANKET-105", "Bernat Blanket Yarn, 10.5 oz", "Bernat", "Yarn & Needlecraft", "Yarn", "knitting",
        12.99, 8.44, 4.7, "in_stock",
        "Super bulky (weight 6) polyester chenille yarn, 220 yd per skein.",
        "Chunky knit blankets, throws, hand-knit blankets, amigurumi.",
        "Go-to yarn for chunky blankets; a 50 in x 60 in throw typically needs 5-6 skeins.",
        "Bernat Blanket yarn super bulky chenille, chunky knit blanket, throw, hand knitting, arm knitting, cozy.",
    ),
    product(
        "PRD_014", "YB-IMPECCABLE-45", "Yarnbury Impeccable Yarn, 4.5 oz", "Yarnbury", "Yarn & Needlecraft", "Yarn", "knitting",
        5.99, 4.19, 4.5, "in_stock",
        "Medium (weight 4) acrylic worsted yarn, 285 yd per skein.",
        "Scarves, hats, dishcloths, beginner crochet and knitting.",
        "Affordable everyday worsted yarn for learning and quick gifts.",
        "Yarnbury Impeccable worsted yarn weight 4 acrylic, scarves, hats, beginner crochet, knitting.",
    ),
    product(
        "PRD_015", "LB-WOOLEASE-TQ", "Lion Brand Wool-Ease Thick & Quick Yarn", "Lion Brand", "Yarn & Needlecraft", "Yarn", "knitting",
        9.99, 7.49, 4.6, "in_stock",
        "Super bulky (weight 6) wool-acrylic blend, 106 yd per skein.",
        "Chunky scarves, hats, quick blankets.",
        "Warmer wool-blend alternative to chenille blanket yarn.",
        "Lion Brand Wool-Ease Thick and Quick super bulky yarn, chunky scarf, hat, blanket, wool blend.",
    ),
    product(
        "PRD_016", "CLOVER-AMOUR-SET", "Clover Amour Crochet Hook Set", "Clover", "Yarn & Needlecraft", "Hooks & Needles", "crochet",
        49.99, 39.99, 4.9, "in_stock",
        "Ten ergonomic aluminum hooks, sizes B through J, in a zip case.",
        "Crochet blankets, amigurumi, garments.",
        "Premium comfort-grip set for frequent crocheters.",
        "Clover Amour crochet hook set, ergonomic, sizes B to J, amigurumi, blankets, crochet gifts.",
    ),
    product(
        "PRD_017", "YB-BAMBOO-CIRC-13", "Yarnbury Bamboo Circular Knitting Needles, US 13", "Yarnbury", "Yarn & Needlecraft", "Hooks & Needles", "knitting",
        9.99, 6.99, 4.4, "in_stock",
        "29 in bamboo circular needles, US size 13 (9 mm).",
        "Chunky blankets, bulky cowls, flat knitting in rows.",
        "Right size for super bulky blanket yarn.",
        "Yarnbury bamboo circular knitting needles US 13 9mm, chunky blanket, bulky yarn, cowl.",
    ),
    # --- Floral & Seasonal ---
    product(
        "PRD_018", "HH-GRAPEVINE-24", "Hearth & Harvest 24 in Grapevine Wreath Base", "Hearth & Harvest", "Floral & Seasonal", "Wreath Bases", "wreaths",
        14.99, 8.99, 4.6, "in_stock",
        "Natural twisted grapevine wreath form, 24 in diameter.",
        "Fall front-door wreaths, holiday wreaths, rustic home décor.",
        "Best base for a full, natural-looking front-door wreath.",
        "Hearth & Harvest grapevine wreath base 24 inch, fall wreath, front door, rustic décor, DIY wreath.",
    ),
    product(
        "PRD_019", "HH-FALL-MAPLE-PICK", "Hearth & Harvest Fall Maple Leaf & Berry Pick", "Hearth & Harvest", "Floral & Seasonal", "Fall Floral", "wreaths",
        5.99, 3.59, 4.5, "in_stock",
        "18 in faux maple leaf and berry pick in orange, burgundy, and gold.",
        "Fall wreaths, centerpieces, mantel arrangements.",
        "Plan on 6-8 picks for a full 24 in wreath.",
        "Hearth & Harvest fall maple leaf berry pick, autumn floral, wreath, centerpiece, mantel, orange burgundy gold.",
    ),
    product(
        "PRD_020", "HH-VELVET-PUMPKIN-3", "Hearth & Harvest Faux Velvet Pumpkins, 3 ct", "Hearth & Harvest", "Floral & Seasonal", "Fall Décor", "home_decor",
        24.99, 14.99, 4.7, "in_stock",
        "Set of three plush velvet pumpkins with natural stems in cream, rust, and sage.",
        "Fall tablescapes, mantels, porch décor, wreath accents.",
        "Popular seasonal décor that pairs with any fall wreath.",
        "Hearth & Harvest velvet pumpkins set, fall décor, tablescape, mantel, porch, autumn.",
    ),
    product(
        "PRD_021", "HH-BURLAP-RIB-25", "Hearth & Harvest Wired Burlap Ribbon, 2.5 in x 10 yd", "Hearth & Harvest", "Floral & Seasonal", "Ribbon", "wreaths",
        7.99, 5.59, 4.5, "in_stock",
        "Natural burlap ribbon with wired edges that hold their shape.",
        "Wreath bows, gift wrapping, rustic décor.",
        "Wired edges make it easy to shape a full wreath bow.",
        "Hearth & Harvest wired burlap ribbon, wreath bow, fall décor, rustic, gift wrap.",
    ),
    product(
        "PRD_022", "ADTECH-PRO200", "Ad Tech Pro 200 Dual-Temp Hot Glue Gun", "Ad Tech", "Craft Basics", "Glue & Adhesives", "general",
        14.99, 11.99, 4.6, "in_stock",
        "Full-size dual-temperature glue gun with stand; uses standard 7/16 in glue sticks.",
        "Wreaths, floral arranging, home décor, general crafting.",
        "Essential for attaching picks and ribbon to wreath bases.",
        "Ad Tech hot glue gun dual temp, wreaths, floral, décor, glue sticks, craft essential.",
    ),
    product(
        "PRD_023", "HH-HALLOWEEN-SKEL", "Hearth & Harvest Light-Up Halloween Skeleton Wreath", "Hearth & Harvest", "Floral & Seasonal", "Halloween", "home_decor",
        49.99, 29.99, 4.3, "limited_stock",
        "Ready-made 22 in black twig wreath with LED skeleton and timer.",
        "Halloween front door, spooky porch décor.",
        "Ready-made option for shoppers who don't want to DIY.",
        "Hearth & Harvest Halloween skeleton wreath light up LED, spooky décor, front door, ready made.",
    ),
    # --- Framing, Paper, Jewelry, Basics ---
    product(
        "PRD_024", "FW-GALLERY-1114", "Frameworks Gallery Frame with Mat, 11 in x 14 in", "Frameworks", "Frames", "Wall Frames", "framing",
        29.99, 14.99, 4.5, "in_stock",
        "Black wood-look frame with white mat that displays an 8 in x 10 in print.",
        "Photos, art prints, gallery walls, kids' art.",
        "Ready-made framing option when custom framing isn't needed.",
        "Frameworks gallery frame 11x14 with mat, 8x10 print, photos, gallery wall, ready made frame.",
    ),
    product(
        "PRD_025", "PAP-CARDSTOCK-100", "Paperie Cardstock Paper, 12 in x 12 in, 100 Sheets", "Paperie", "Paper Crafts", "Cardstock", "paper_crafts",
        24.99, 14.99, 4.6, "in_stock",
        "One hundred 65 lb sheets in 50 assorted solid colors.",
        "Scrapbooking, card making, Cricut paper projects, party décor.",
        "Works in every Cricut machine for card and paper projects.",
        "Paperie cardstock 12x12 100 sheets, scrapbooking, card making, Cricut paper, party décor.",
    ),
    product(
        "PRD_026", "BC-JEWELRY-KIT", "Bead Cove Jewelry Making Starter Kit", "Bead Cove", "Jewelry Making", "Kits", "jewelry",
        24.99, 17.49, 4.3, "in_stock",
        "Beads, findings, wire, and pliers to make 20+ bracelets and earrings.",
        "Bracelets, earrings, friendship jewelry, birthday parties.",
        "All-in-one kit for beginners and teen parties.",
        "Bead Cove jewelry making kit, beads, pliers, bracelets, earrings, beginner, teen party.",
    ),
    product(
        "PRD_027", "MODPODGE-MATTE-16", "Mod Podge Matte, 16 oz", "Mod Podge", "Craft Basics", "Glue & Adhesives", "general",
        12.99, 9.09, 4.8, "in_stock",
        "All-in-one glue, sealer, and finish that dries clear with a matte finish.",
        "Decoupage, photo transfers, sealing painted projects.",
        "Classic finish for decoupage and sealing painted pumpkins.",
        "Mod Podge matte decoupage glue sealer finish, photo transfer, seal paint, craft basics.",
    ),
    product(
        "PRD_028", "MSC-MASON-6", "Maker Supply Co. Clear Glass Mason Jars, 16 oz, 6 ct", "Maker Supply Co.", "Craft Basics", "Jars & Containers", "home_decor",
        14.99, 10.49, 4.5, "in_stock",
        "Six regular-mouth glass jars with silver lids.",
        "Candles, centerpieces, gift jars, vinyl-decal gifts.",
        "Popular blank for vinyl decals and fall centerpieces.",
        "Maker Supply Co. mason jars 16 oz, candles, centerpiece, gift jar, vinyl decal blank, home décor.",
    ),
]

PRODUCT_NAME_BY_ID = {row["product_id"]: row["name"] for row in PRODUCTS}
STORE_NAME_BY_ID = {row["store_id"]: row["name"] for row in STORES}


STORE_INVENTORY = [
    # Las Colinas (demo home store) — note the Cricut Maker 3 is sold out here.
    inventory("INV_001", "STORE_001", "PRD_001", 0, "sold_out", 72, "Cricut shop, aisle 3"),
    inventory("INV_002", "STORE_001", "PRD_002", 4, "pickup_today", 2, "Cricut shop, aisle 3"),
    inventory("INV_003", "STORE_001", "PRD_003", 6, "pickup_today", 1, "Cricut shop, aisle 3"),
    inventory("INV_004", "STORE_001", "PRD_004", 18, "pickup_today", 1, "Cricut shop, aisle 3"),
    inventory("INV_005", "STORE_001", "PRD_005", 14, "pickup_today", 1, "Cricut shop, aisle 3"),
    inventory("INV_006", "STORE_001", "PRD_006", 3, "pickup_today", 2, "Cricut shop, aisle 3"),
    inventory("INV_007", "STORE_001", "PRD_007", 22, "pickup_today", 1, "Fine art, aisle 9"),
    inventory("INV_008", "STORE_001", "PRD_008", 9, "pickup_today", 1, "Fine art, aisle 10"),
    inventory("INV_009", "STORE_001", "PRD_012", 30, "pickup_today", 1, "Kids' crafts, aisle 14"),
    inventory("INV_010", "STORE_001", "PRD_013", 26, "pickup_today", 1, "Yarn wall, aisle 17"),
    inventory("INV_011", "STORE_001", "PRD_014", 40, "pickup_today", 1, "Yarn wall, aisle 17"),
    inventory("INV_012", "STORE_001", "PRD_017", 5, "pickup_today", 1, "Yarn wall, aisle 18"),
    inventory("INV_013", "STORE_001", "PRD_018", 11, "pickup_today", 1, "Seasonal floral, front of store"),
    inventory("INV_014", "STORE_001", "PRD_019", 48, "pickup_today", 1, "Seasonal floral, front of store"),
    inventory("INV_015", "STORE_001", "PRD_020", 7, "pickup_today", 1, "Fall décor shop, front of store"),
    inventory("INV_016", "STORE_001", "PRD_021", 2, "pickup_today", 1, "Ribbon wall, aisle 6"),
    inventory("INV_017", "STORE_001", "PRD_022", 12, "pickup_today", 1, "Craft basics, aisle 5"),
    inventory("INV_018", "STORE_001", "PRD_023", 1, "pickup_today", 2, "Halloween shop, front of store"),
    inventory("INV_019", "STORE_001", "PRD_024", 15, "pickup_today", 1, "Frame shop, aisle 1"),
    inventory("INV_020", "STORE_001", "PRD_025", 8, "pickup_today", 1, "Paper crafting, aisle 7"),
    inventory("INV_021", "STORE_001", "PRD_027", 16, "pickup_today", 1, "Craft basics, aisle 5"),
    inventory("INV_022", "STORE_001", "PRD_028", 10, "pickup_today", 1, "Craft basics, aisle 4"),
    # Preston Royal
    inventory("INV_023", "STORE_002", "PRD_001", 3, "pickup_today", 2, "Cricut shop, aisle 2"),
    inventory("INV_024", "STORE_002", "PRD_013", 34, "pickup_today", 1, "Yarn wall, aisle 15"),
    inventory("INV_025", "STORE_002", "PRD_015", 12, "pickup_today", 1, "Yarn wall, aisle 15"),
    inventory("INV_026", "STORE_002", "PRD_016", 4, "pickup_today", 1, "Yarn wall, aisle 16"),
    inventory("INV_027", "STORE_002", "PRD_021", 9, "pickup_today", 1, "Ribbon wall, aisle 6"),
    inventory("INV_028", "STORE_002", "PRD_010", 5, "pickup_today", 1, "Fine art, aisle 11"),
    # Frisco Stonebriar
    inventory("INV_029", "STORE_003", "PRD_001", 2, "pickup_today", 3, "Cricut shop, aisle 4"),
    inventory("INV_030", "STORE_003", "PRD_018", 6, "pickup_today", 1, "Seasonal floral, front of store"),
    inventory("INV_031", "STORE_003", "PRD_023", 4, "pickup_today", 1, "Halloween shop, front of store"),
    inventory("INV_032", "STORE_003", "PRD_026", 7, "pickup_today", 1, "Jewelry making, aisle 12"),
    # Plano Legacy
    inventory("INV_033", "STORE_004", "PRD_009", 6, "pickup_today", 1, "Fine art, aisle 9"),
    inventory("INV_034", "STORE_004", "PRD_010", 8, "pickup_today", 1, "Fine art, aisle 9"),
    inventory("INV_035", "STORE_004", "PRD_011", 14, "pickup_today", 1, "Fine art, aisle 10"),
]


def workshop(
    workshop_id: str,
    store_id: str,
    title: str,
    craft_type: str,
    skill_level: str,
    age_group: str,
    start: datetime,
    duration_minutes: int,
    price: float,
    seats_available: int,
    supplies_included: bool,
    supply_list: str | None,
    description: str,
) -> dict[str, object]:
    return {
        "workshop_id": workshop_id,
        "store_id": store_id,
        "store_name": STORE_NAME_BY_ID[store_id],
        "title": title,
        "craft_type": craft_type,
        "skill_level": skill_level,
        "age_group": age_group,
        "start_time": ts(start),
        "duration_minutes": duration_minutes,
        "price": price,
        "seats_available": seats_available,
        "supplies_included": supplies_included,
        "supply_list": supply_list,
        "description": description,
    }


SATURDAY, SUNDAY = 5, 6

WORKSHOPS = [
    workshop(
        "WS_001", "STORE_001", "Fall Grapevine Wreath Workshop", "wreaths", "beginner", "adults",
        upcoming(SATURDAY, 10), 120, 25.00, 5, False,
        "24 in grapevine wreath base, 6-8 fall floral picks, 2.5 in wired ribbon, hot glue gun and glue sticks",
        "Design and build a full fall front-door wreath with a hand-tied bow. Instructor provides wire and floral tape.",
    ),
    workshop(
        "WS_002", "STORE_001", "Kids' Club: Pumpkin Painting", "painting", "all_levels", "kids",
        upcoming(SATURDAY, 13), 60, 5.00, 9, True, None,
        "Kids ages 5-12 paint and decorate their own mini pumpkin with washable paint. All supplies included.",
    ),
    workshop(
        "WS_003", "STORE_001", "Cricut Basics: Your First Vinyl Decal", "vinyl", "beginner", "adults",
        upcoming(SUNDAY, 14), 90, 15.00, 0, True, None,
        "Learn Design Space, cut and weed permanent vinyl, and apply a decal to a mason jar you take home. Class is full.",
    ),
    workshop(
        "WS_004", "STORE_001", "Chunky Knit Blanket Workshop", "knitting", "beginner", "adults",
        upcoming(SUNDAY, 11), 150, 35.00, 4, True, None,
        "Knit a 30 in x 40 in chunky throw with Bernat Blanket yarn and US 13 needles. Yarn and needles included.",
    ),
    workshop(
        "WS_005", "STORE_002", "Watercolor Florals for Beginners", "watercolor", "beginner", "adults",
        upcoming(SATURDAY, 11), 120, 20.00, 7, False,
        "Watercolor pocket set, 9 in x 12 in watercolor pad, round brush",
        "Paint loose roses and eucalyptus in watercolor. Great first class for new painters.",
    ),
    workshop(
        "WS_006", "STORE_003", "Cricut Basics: Your First Vinyl Decal", "vinyl", "beginner", "adults",
        upcoming(SATURDAY, 14), 90, 15.00, 6, True, None,
        "Learn Design Space, cut and weed permanent vinyl, and apply a decal to a mason jar you take home.",
    ),
]

current_order_date = now - timedelta(days=6, hours=2)
current_promised_date = now - timedelta(days=1, hours=5)

ORDERS = [
    {
        "order_id": "ORD_MI_1001",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "status": "shipped_delayed",
        "fulfillment_type": "shipping",
        "store_id": None,
        "store_name": None,
        "order_total": 394.97,
        "order_date": ts(current_order_date),
        "promised_date": ts(current_promised_date),
        "delivered_at": None,
        "tracking_number": "772896104315",
        "shipping_address": "4210 N O'Connor Rd, Irving, TX 75062",
        "summary": "Cricut Maker 3, Premium Permanent Vinyl Sampler, and Everyday Iron-On Sampler",
    },
    {
        "order_id": "ORD_MI_1002",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "status": "completed",
        "fulfillment_type": "pickup",
        "store_id": "STORE_001",
        "store_name": "CraftHub Las Colinas",
        "order_total": 57.63,
        "order_date": ts(now - timedelta(days=24)),
        "promised_date": ts(now - timedelta(days=24) + timedelta(hours=2)),
        "delivered_at": ts(now - timedelta(days=24) + timedelta(hours=3)),
        "tracking_number": None,
        "shipping_address": None,
        "summary": "Six skeins of Bernat Blanket Yarn and US 13 bamboo circular needles for a chunky knit throw",
    },
    {
        "order_id": "ORD_MI_1003",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "status": "in_production",
        "fulfillment_type": "custom_framing",
        "store_id": "STORE_001",
        "store_name": "CraftHub Las Colinas",
        "order_total": 168.40,
        "order_date": ts(now - timedelta(days=9)),
        "promised_date": ts(now + timedelta(days=2, hours=3)),
        "delivered_at": None,
        "tracking_number": None,
        "shipping_address": None,
        "summary": "Custom framing: 16 in x 20 in watercolor print, walnut frame, double white mat, conservation glass",
    },
    {
        "order_id": "ORD_MI_1004",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "status": "completed",
        "fulfillment_type": "shipping",
        "store_id": None,
        "store_name": None,
        "order_total": 55.99,
        "order_date": ts(now - timedelta(days=66)),
        "promised_date": ts(now - timedelta(days=61)),
        "delivered_at": ts(now - timedelta(days=62)),
        "tracking_number": "9400111899562210458731",
        "shipping_address": "4210 N O'Connor Rd, Irving, TX 75062",
        "summary": "Liquitex BASICS Acrylic Paint Set, 48 Colors",
    },
    {
        "order_id": "ORD_MI_2001",
        "customer_id": "CUST_MI_002",
        "status": "ready_for_pickup",
        "fulfillment_type": "pickup",
        "store_id": "STORE_002",
        "store_name": "CraftHub Preston Royal",
        "order_total": 39.99,
        "order_date": ts(now - timedelta(hours=6)),
        "promised_date": ts(now - timedelta(hours=4)),
        "delivered_at": None,
        "tracking_number": None,
        "shipping_address": None,
        "summary": "Clover Amour Crochet Hook Set",
    },
]

ORDER_ITEMS = [
    {
        "order_item_id": "ITEM_MI_001",
        "order_id": "ORD_MI_1001",
        "product_id": "PRD_001",
        "product_name": PRODUCT_NAME_BY_ID["PRD_001"],
        "quantity": 1,
        "unit_price": 349.99,
        "fulfillment_status": "in_transit",
    },
    {
        "order_item_id": "ITEM_MI_002",
        "order_id": "ORD_MI_1001",
        "product_id": "PRD_004",
        "product_name": PRODUCT_NAME_BY_ID["PRD_004"],
        "quantity": 1,
        "unit_price": 22.49,
        "fulfillment_status": "in_transit",
    },
    {
        "order_item_id": "ITEM_MI_003",
        "order_id": "ORD_MI_1001",
        "product_id": "PRD_005",
        "product_name": PRODUCT_NAME_BY_ID["PRD_005"],
        "quantity": 1,
        "unit_price": 22.49,
        "fulfillment_status": "in_transit",
    },
    {
        "order_item_id": "ITEM_MI_004",
        "order_id": "ORD_MI_1002",
        "product_id": "PRD_013",
        "product_name": PRODUCT_NAME_BY_ID["PRD_013"],
        "quantity": 6,
        "unit_price": 8.44,
        "fulfillment_status": "picked_up",
    },
    {
        "order_item_id": "ITEM_MI_005",
        "order_id": "ORD_MI_1002",
        "product_id": "PRD_017",
        "product_name": PRODUCT_NAME_BY_ID["PRD_017"],
        "quantity": 1,
        "unit_price": 6.99,
        "fulfillment_status": "picked_up",
    },
    {
        "order_item_id": "ITEM_MI_006",
        "order_id": "ORD_MI_1003",
        "product_id": "SVC_CUSTOM_FRAMING",
        "product_name": "Custom Framing — 16 in x 20 in, walnut frame, double white mat, conservation glass",
        "quantity": 1,
        "unit_price": 168.40,
        "fulfillment_status": "in_production",
    },
    {
        "order_item_id": "ITEM_MI_007",
        "order_id": "ORD_MI_1004",
        "product_id": "PRD_009",
        "product_name": PRODUCT_NAME_BY_ID["PRD_009"],
        "quantity": 1,
        "unit_price": 55.99,
        "fulfillment_status": "delivered",
    },
    {
        "order_item_id": "ITEM_MI_008",
        "order_id": "ORD_MI_2001",
        "product_id": "PRD_016",
        "product_name": PRODUCT_NAME_BY_ID["PRD_016"],
        "quantity": 1,
        "unit_price": 39.99,
        "fulfillment_status": "ready_for_pickup",
    },
]

SHIPMENTS = [
    {
        "shipment_id": "SHIP_MI_001",
        "order_id": "ORD_MI_1001",
        "carrier": "FedEx",
        "tracking_number": "772896104315",
        "shipment_status": "delay_in_transit",
        "shipped_at": ts(now - timedelta(days=5, hours=16)),
        "estimated_delivery": ts(now + timedelta(days=1, hours=5)),
        "last_scan_at": ts(now - timedelta(hours=5)),
        "current_location": "FedEx hub, Memphis, TN",
        "delay_reason": "Severe thunderstorms at the Memphis hub caused a missed outbound flight to Dallas-Fort Worth.",
    },
    {
        "shipment_id": "SHIP_MI_002",
        "order_id": "ORD_MI_1004",
        "carrier": "USPS",
        "tracking_number": "9400111899562210458731",
        "shipment_status": "delivered",
        "shipped_at": ts(now - timedelta(days=65)),
        "estimated_delivery": ts(now - timedelta(days=61)),
        "last_scan_at": ts(now - timedelta(days=62)),
        "current_location": "Irving, TX",
        "delay_reason": None,
    },
]

SHIPMENT_EVENTS = [
    {
        "event_id": "SEVT_MI_001",
        "shipment_id": "SHIP_MI_001",
        "order_id": "ORD_MI_1001",
        "event_type": "label_created",
        "timestamp": ts(now - timedelta(days=6)),
        "location": "Jacksonville, FL",
        "description": "Shipping label created at the CraftHub distribution center.",
    },
    {
        "event_id": "SEVT_MI_002",
        "shipment_id": "SHIP_MI_001",
        "order_id": "ORD_MI_1001",
        "event_type": "picked_up",
        "timestamp": ts(now - timedelta(days=5, hours=16)),
        "location": "Jacksonville, FL",
        "description": "FedEx picked up the package from the CraftHub distribution center.",
    },
    {
        "event_id": "SEVT_MI_003",
        "shipment_id": "SHIP_MI_001",
        "order_id": "ORD_MI_1001",
        "event_type": "arrival_scan",
        "timestamp": ts(now - timedelta(days=2, hours=21)),
        "location": "Memphis, TN",
        "description": "Package arrived at the FedEx Memphis hub.",
    },
    {
        "event_id": "SEVT_MI_004",
        "shipment_id": "SHIP_MI_001",
        "order_id": "ORD_MI_1001",
        "event_type": "delay",
        "timestamp": ts(now - timedelta(hours=5)),
        "location": "Memphis, TN",
        "description": "Weather delay: severe thunderstorms grounded the outbound flight to Dallas-Fort Worth.",
    },
    {
        "event_id": "SEVT_MI_005",
        "shipment_id": "SHIP_MI_002",
        "order_id": "ORD_MI_1004",
        "event_type": "delivered",
        "timestamp": ts(now - timedelta(days=62)),
        "location": "Irving, TX",
        "description": "Package delivered to front porch.",
    },
]

SUPPORT_CASES = [
    {
        "case_id": "CASE_MI_001",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "order_id": "ORD_MI_1001",
        "category": "shipment_delay",
        "status": "open",
        "opened_at": ts(now - timedelta(hours=3)),
        "summary": "Customer reports Cricut Maker 3 order not received by the original promise date.",
        "resolution": None,
    },
    {
        "case_id": "CASE_MI_002",
        "customer_id": DEMO_CUSTOMER["customer_id"],
        "order_id": "ORD_MI_1002",
        "category": "pickup_question",
        "status": "resolved",
        "opened_at": ts(now - timedelta(days=24, hours=2)),
        "summary": "Asked whether a yarn order could be picked up curbside.",
        "resolution": "Confirmed curbside pickup at CraftHub Las Colinas; order was brought out to the car.",
    },
]

GUIDE_TEXT = [
    {
        "guide_id": "GUIDE_MI_001",
        "title": "Returns and Exchanges",
        "category": "return_policy",
        "content": (
            "Most unused items in original condition can be returned within 60 days of purchase with a receipt or order "
            "confirmation, in store or by mail. Cricut machines and other electronics must be returned within 30 days and include "
            "all original packaging. Custom framing, cut fabric, and personalized items are final sale. Returns without a receipt "
            "are refunded as store credit at the lowest recent selling price."
        ),
    },
    {
        "guide_id": "GUIDE_MI_002",
        "title": "Buy Online, Pick Up In Store and Curbside",
        "category": "pickup_policy",
        "content": (
            "Buy online, pick up in store orders are usually ready within 2 hours during store hours. Curbside pickup is available at "
            "participating stores: tap 'I'm here' in the app and an associate brings the order to your car. Orders are held for 5 "
            "days. Store inventory is the source of truth for same-day pickup, so always check the local store before promising it."
        ),
    },
    {
        "guide_id": "GUIDE_MI_003",
        "title": "Custom Framing Turnaround",
        "category": "custom_framing",
        "content": (
            "Custom framing orders are typically ready in 10-14 days. Rush service may be available for an additional fee. You'll get "
            "a text and email when your frame is ready for pickup at the store where you placed the order. Conservation glass blocks "
            "99% of UV light and is recommended for original art and watercolors."
        ),
    },
    {
        "guide_id": "GUIDE_MI_004",
        "title": "Shipment Delays",
        "category": "shipping_policy",
        "content": (
            "When a shipment is delayed, the latest carrier scan and revised estimate are the best current signal. Once the original "
            "promise date has passed, the support team can review the order and offer a replacement or refund if the package does "
            "not arrive within 3 business days of the revised estimate."
        ),
    },
    {
        "guide_id": "GUIDE_MI_005",
        "title": "Choosing the Right Cricut Vinyl",
        "category": "project_guide",
        "content": (
            "Use permanent vinyl for mugs, tumblers, and anything outdoors or washed often. Use removable vinyl for wall decals and "
            "seasonal window clings. Use iron-on (heat transfer vinyl) for t-shirts, totes, and fabric, applied with an EasyPress or "
            "household iron. Always mirror your design before cutting iron-on."
        ),
    },
    {
        "guide_id": "GUIDE_MI_006",
        "title": "Fall Front-Door Wreath Supply Checklist",
        "category": "project_guide",
        "content": (
            "For a full 24 in fall wreath you'll need a grapevine or foam wreath base, 6-8 fall floral picks, about 3 yd of 2.5 in "
            "wired ribbon for the bow, floral wire, and a hot glue gun with glue sticks. Add faux pumpkins or a wood sign as a focal "
            "point. Hang with an over-the-door hook to avoid scratching the door."
        ),
    },
    {
        "guide_id": "GUIDE_MI_007",
        "title": "CraftHub Rewards",
        "category": "rewards",
        "content": (
            "CraftHub Rewards members earn points on every purchase and get members-only coupons. Rewards Plus members also get free "
            "standard shipping on qualifying orders and early access to seasonal sales. Teachers and small businesses can join "
            "CraftHub Pro for additional everyday discounts."
        ),
    },
]


def write_jsonl(output_dir: Path, filename: str, rows: list[dict[str, object]]) -> None:
    path = output_dir / filename
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  {path.name}: {len(rows)} records")


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    safe_value = f'"{value}"' if " " in value else value
    if not env_path.exists():
        env_path.write_text(f"{key}={safe_value}\n")
        return
    lines = env_path.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = f"{key}={safe_value}"
            break
    else:
        lines.append(f"{key}={safe_value}")
    env_path.write_text("\n".join(lines) + "\n")


def generate_demo_data(
    *,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
    transform: Callable[[Any], Any] | None = None,
) -> GeneratedDataset:
    """Write the demo dataset.

    ``transform`` receives each JSON-like record set (lists/dicts of strings) before
    embedding and writing, so a white-label overlay can rename stores and brands.
    """
    del seed
    t = transform or (lambda value: value)
    resolved_output_dir = output_dir or OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    customer = t(DEMO_CUSTOMER)

    print("Generating embeddings for guides...")
    guide_text = t(GUIDE_TEXT)
    embeddings = embed([guide["content"] for guide in guide_text])
    guides = [{**guide, "content_embedding": embedding} for guide, embedding in zip(guide_text, embeddings)]

    print("Writing JSONL files:")
    write_jsonl(resolved_output_dir, "customers.jsonl", t(CUSTOMERS))
    write_jsonl(resolved_output_dir, "stores.jsonl", t(STORES))
    write_jsonl(resolved_output_dir, "products.jsonl", t(PRODUCTS))
    write_jsonl(resolved_output_dir, "store_inventory.jsonl", t(STORE_INVENTORY))
    write_jsonl(resolved_output_dir, "workshops.jsonl", t(WORKSHOPS))
    write_jsonl(resolved_output_dir, "orders.jsonl", t(ORDERS))
    write_jsonl(resolved_output_dir, "order_items.jsonl", t(ORDER_ITEMS))
    write_jsonl(resolved_output_dir, "shipments.jsonl", t(SHIPMENTS))
    write_jsonl(resolved_output_dir, "shipment_events.jsonl", t(SHIPMENT_EVENTS))
    write_jsonl(resolved_output_dir, "support_cases.jsonl", t(SUPPORT_CASES))
    write_jsonl(resolved_output_dir, "guides.jsonl", guides)

    env_updates = {
        "DEMO_USER_ID": customer["customer_id"],
        "DEMO_USER_NAME": customer["name"],
        "DEMO_USER_EMAIL": customer["email"],
        "DEMO_USER_MEMBER_TIER": customer["member_tier"],
        "DEMO_USER_CITY": customer["city"],
        "DEMO_USER_STATE": customer["state"],
        "DEMO_USER_HOME_STORE_ID": customer["home_store_id"],
        "DEMO_USER_HOME_STORE_NAME": customer["home_store_name"],
    }
    if update_env_file:
        for key, value in env_updates.items():
            update_env(key, value)

    print(f"\nDemo user: {customer['name']} ({customer['customer_id']})")
    print(f"Home store: {customer['home_store_name']} ({customer['home_store_id']})")
    print("Done.")

    return GeneratedDataset(
        output_dir=str(resolved_output_dir),
        env_updates=env_updates,
        summary={
            "customers": len(CUSTOMERS),
            "stores": len(STORES),
            "products": len(PRODUCTS),
            "store_inventory": len(STORE_INVENTORY),
            "workshops": len(WORKSHOPS),
            "orders": len(ORDERS),
            "order_items": len(ORDER_ITEMS),
            "shipments": len(SHIPMENTS),
            "shipment_events": len(SHIPMENT_EVENTS),
            "support_cases": len(SUPPORT_CASES),
            "guides": len(GUIDE_TEXT),
        },
    )


if __name__ == "__main__":
    generate_demo_data(update_env_file=True)
