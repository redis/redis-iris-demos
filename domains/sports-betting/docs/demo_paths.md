# Demo Paths

Four scripted conversation paths for the sports-betting domain. Each path
uses the same UI components as Reddash while changing the business story to
live sportsbook support: Context Retriever for structured bet/account data,
LangCache for common settlement policy answers, and Agent Memory for durable
player preferences.

> Tip: After running a path in Context Surfaces mode, toggle to Simple RAG and
> ask the same opening question to show the contrast.

---

## Path 1 - Delayed Bet Settlement (Flagship)

Shows: player identity, live bet context, bet legs, settlement timeline, wallet
movement, and policy retrieval.

| # | You say | What the agent does | Key data surfaced |
|---|---------|--------------------|-------------------|
| 1 | **"Why has my football bet not settled yet?"** | get_user -> bets -> time -> bet legs -> settlement events -> wallet -> policy search | Maya has a GBP 20 football accumulator. All three legs show winning outcomes, but the match-winner leg is in trading review after a late official-feed correction. No payout transaction exists yet. |
| 2 | **"So has it paid out?"** | Re-checks wallet transactions for the bet | Finds only the stake transaction. No payout has been credited. |
| 3 | **"How long should this take?"** | Searches settlement policy or uses LangCache for common settlement timing | Policy says accumulators wait for every verified leg, and reviewed results usually resolve within 60 minutes of official confirmation. |

RAG contrast: Simple RAG can explain settlement policy generically but cannot see Maya's bet legs, settlement queue, stake, or wallet state.

---

## Path 2 - Wallet and Payout Review

Shows: wallet ledger, bet history, payout status, and account context.

| # | You say | What the agent does | Key data surfaced |
|---|---------|--------------------|-------------------|
| 1 | **"Show me my recent wallet activity."** | get_user -> wallet transactions | GBP 75 deposit, stakes for four bets, one GBP 28 payout, and current balance after the latest stake. |
| 2 | **"Which bet paid out?"** | Links wallet payout to the settled bet | The GBP 28 payout came from the earlier football single that settled as won. |
| 3 | **"Can I withdraw the payout?"** | Searches withdrawal policy and checks account context | KYC is verified; withdrawal checks may still apply, but no open payout hold exists for the settled single. |

RAG contrast: Simple RAG can describe withdrawal checks but cannot connect the payout to a specific wallet transaction.

---

## Path 3 - Cash Out and Market Status

Shows: open bet lookup, market state, cash-out policy, and safer support tone.

| # | You say | What the agent does | Key data surfaced |
|---|---------|--------------------|-------------------|
| 1 | **"Can I cash out my open slip?"** | get_user -> bets -> bet legs -> market status -> policy search | Maya has a GBP 12 open single on North London. Cash out is available at GBP 11.40 before kickoff. |
| 2 | **"Why can't I cash out the accumulator?"** | Checks accumulator status and searches cash-out policy | The accumulator is pending final settlement review, so cash out is not available. |
| 3 | **"Should I place another bet while I wait?"** | Uses safer-gambling guidance and memory if available | The assistant avoids nudging a new bet and suggests waiting for verified settlement. |

RAG contrast: Simple RAG can explain cash out eligibility but cannot tell which of Maya's bets currently has a cash-out value.

---

## Path 4 - Memory-Aware Player Preference

Shows: durable Agent Memory plus fresh Context Retriever data.

| # | You say | What the agent does | Key data surfaced |
|---|---------|--------------------|-------------------|
| 1 | **"Please remember that I prefer football accumulators and keep stakes under GBP 25."** | remember_customer_detail | Stores a durable preference with football, accumulator, and stake-preference topics. |
| 2 | **"Given what you know about me, review my recent bets."** | get_user -> memory -> bets -> bet legs | The GBP 20 accumulator fits Maya's stored stake style; the GBP 12 single is also under the preference threshold. |
| 3 | **"What should I do about the pending one?"** | Uses settlement context and safer-gambling policy | Recommends waiting for the reviewed result rather than placing another bet to make up for the delay. |

RAG contrast: Simple RAG cannot recall Maya's stake preference or combine it with her live bet history.
