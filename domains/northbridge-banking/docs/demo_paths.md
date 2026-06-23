# Northbridge Banking Demo Paths

## Path 1: Public product-guidance cache

Goal: show an identity-free LangCache entry created by the first public-guidance answer, then reused across customers. This path should not vary by customer tier.

1. Start a fresh thread as any customer.
2. Prompt: `How do card controls work in the Northbridge app?`
3. Expected behavior:
   - `semantic_cache_search` checks group then public attributes and misses on a cleared cache
   - the agent uses shared product or support guidance, without identity or account tools
   - `semantic_cache_store` writes the final answer with public attributes:
     `{"domain": "northbridge-banking", "access_class": "public"}`
4. Start a second fresh thread as a different customer.
5. Prompt with the similar public-guidance variant:
   `How do the card controls in the Northbridge app work?`
6. Expected behavior:
   - `semantic_cache_search` returns the public cache hit
   - no identity or account tools are needed

To prove the match is symmetric, flush LangCache and run the same pair in reverse:
1. Prompt: `How do the card controls in the Northbridge app work?`
2. Prompt in a fresh thread: `How do card controls work in the Northbridge app?`
3. Expected behavior:
   - first prompt stores public cache
   - second prompt hits public cache

Optional follow-up:
- `Can I freeze and unfreeze my card there?`

## Path 2: Tier-scoped support guidance

Goal: show a cache entry created from cohort-safe context that stays within the signed-in support segment.

1. Start a fresh thread as `Maya Chen` (`Plus`).
2. Prompt: `What help do I usually get if something looks wrong with my card?`
3. Expected behavior:
   - `semantic_cache_search` first checks group attributes:
     `{"domain": "northbridge-banking", "access_class": "group", "cache_group_id": "plus_en"}`
   - the search misses on a cleared cache
   - the agent uses:
     `get_current_customer_support_context`
     `search_supportguidancedoc_by_text(value="card issue support routing")`
   - the answer says Maya is on `Plus Support` and mentions priority support routing or appointment-style follow-up
   - `semantic_cache_store` writes the final answer with `plus_en` group attributes
4. Start a fresh thread as `Jordan Lee` (`Plus`).
5. Prompt with the similar tier-scoped support variant:
   `What help do I normally get if something looks wrong with my card?`
6. Expected behavior:
   - the same `plus_en` LangCache hit is available because Jordan shares Maya's support cohort
7. Start a fresh thread as `Casey Alvarez` (`Standard`).
8. Repeat the same prompt.
9. Expected behavior:
   - the `plus_en` answer is not returned because the cohort is different
   - the agent falls through to public cache search and then normal tool use:
     `get_current_customer_support_context`
     `search_supportguidancedoc_by_text(value="card issue support routing")`
   - the answer says Casey is on `Standard Support` and mentions the standard app/phone support route
   - the final answer can be stored under `standard_en`

To prove the match is symmetric inside the same cohort, flush LangCache and run the Plus pair in reverse:
1. Start as `Maya Chen` and prompt:
   `What help do I normally get if something looks wrong with my card?`
2. Start a fresh thread as `Jordan Lee` and prompt:
   `What help do I usually get if something looks wrong with my card?`
3. Expected behavior:
   - first prompt stores a `plus_en` group cache entry
   - second prompt hits the `plus_en` cache entry

## Path 3: Flagship card-decline recovery

Goal: show full multi-entity reasoning over live customer records.

Use `Maya Chen`.

1. Prompt: `My card was declined. What happened?`
2. Expected behavior:
   - `get_current_user_profile`
   - `filter_depositaccount_by_customer_id`
   - `filter_debitcard_by_account_id`
   - `filter_cardauthorisation_by_card_id`
   - `filter_cardriskevent_by_linked_authorisation_id`
   - `filter_cardsupportintervention_by_risk_event_id`
3. Expected answer:
   - the declined merchant was `Harbor Tech Online`
   - Northbridge Bank temporarily blocked card ending `4812`

Continue on the same thread:

4. Prompt: `That temporary block does not work for me. What else can I do?`
5. Expected behavior:
   - `filter_cardrecoveryoption_by_account_id`

Then:

6. Prompt: `Unfreeze it after verification.`
7. Expected behavior:
   - `get_current_user_profile`
   - `filter_depositaccount_by_customer_id`
   - `submit_card_recovery_selection`

Accepted recovery selections in this demo:
- Plain-language labels such as `Unfreeze it after verification.`
- Stable option codes such as `UNFREEZE_AFTER_VERIFICATION`

Optional final follow-up:
- `Show me my current card status.`
