# R-Mobile Demo Paths

## Path 1: Bill Higher Than Expected (Context Retriever)

1. **User**: "Why is my bill higher than last month?"
   → Agent calls get_current_user_profile → filter_bill_by_customer_id → filter_billcharge_by_bill_id (BILL_001) → filter_billcharge_by_bill_id (BILL_002)
   → Identifies two one-time charges: $29 international roaming in Canada + $5 insurance deductible
   → Shows: May bill is **$187.43** vs April's **$153.22** — a **$34.21** increase

2. **User**: "How can I avoid that roaming charge next time?"
   → Agent calls search_policydoc_by_text("international roaming")
   → Recommends Travel Pass at $5/day for Canada/Mexico, notes Go5G Plus already includes international data in 215+ countries but not voice

## Path 2: Device Upgrade + Memory (Context Retriever + Memory)

1. **User**: "Am I eligible to upgrade my phone?"
   → Agent calls get_current_user_profile → filter_device_by_customer_id → get_current_time
   → Shows: Jamie's iPhone 16 Pro has 1 installment left ($3.47), eligible next month. Pat's Galaxy S24 is fully paid off and eligible now. Riley's iPhone 15 has 18 months remaining.

2. **User**: "Please remember that I prefer managing everything through the app and that I'm interested in international travel plans."
   → Agent calls remember_customer_detail
   → Confirms preferences saved

3. **User**: "Based on what you know about my preferences and account, what plans or add-ons would you recommend?"
   → Agent calls search_customer_memory → filter_line_by_customer_id → filter_device_by_customer_id
   → Recommends: since Jamie prefers app management, suggests adding Travel Pass via the app for the upcoming Europe trip. Notes Pat's Galaxy S24 is upgrade-eligible and could get trade-in credit.

## Path 3: Cached Response (LangCache)

1. **User**: "What is your device trade-in policy?"
   → Returns cached response with trade-in terms: condition requirements, 24-month bill credits, 30-day mail-in window, up to $800 for recent iPhones
   → Demonstrates instant cached response vs full agent pipeline
