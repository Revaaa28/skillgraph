# Agent-consumer proof: an LLM answers with vs without a SkillGraph bundle

**The objection this closes:** "there is no agent — a script prints a bundle and nothing consumes it." Here the bundle is consumed by a real LLM, asked the same question twice: once bare, once with the bundle as its only context. Both answers below are verbatim from a single run of `agent_consumer.py` (no re-rolls; the script retries only on a hard API error).

- Run (UTC): 2026-11-14T04:57:34Z
- Model: gemini-3.5-flash-lite (via the Gemini API connector helper)
- Task type: verify_free_mint · Entity in question: Ink Koi (INKOI)
- Bundle fed to Run B: **1066 bytes** (compact JSON) — demo.py's `assemble_bundle("verify_free_mint")` output scoped to the entity the question names: the task's skills + tools, plus Ink Koi (INKOI) with its current verdict (label `indikasi`, ts 2026-11-14T04:26:46.175Z, provenance: Mint RedCeh autocheck - on-chain verification, board.json (BSC chain 56)).
- For scale: the unscoped verify_free_mint bundle (all entities) is 7856 bytes; preloading the entire graph catalog is 11,113 bytes (see METRICS.md).

## The question

> Can I still mint Ink Koi for free right now? How many free slots are left, and if I proceed, what exactly should I check before signing anything?

## Run A — no bundle (the question alone)

I do not have access to real-time blockchain data, so I cannot verify whether the free mint for Ink Koi is currently active, how many free slots remain, or the current state of their smart contract. 

Because the crypto and NFT space moves fast and is heavily targeted by phishing scams, **you should always verify the live status directly from official sources** (such as their verified Discord, official Twitter/X account, or the official minting website
) rather than relying on static guides or third-party links.

If you decide to proceed and attempt a mint, here is a strict safety checklist of what to check before connecting your wallet or signing any transaction:

### 1. Verify the Official Link
* **Scam risk:** Attackers frequently buy Google ads or create fake Twitter/X accounts mimicking popular projects to trick users into clicking phishing links.
* **What to do:** Double-check the URL character by character against the project’s verified official community channels. Never click links from direct messages (DMs).

### 2. Inspect the Wallet Permission / Transaction Prompt
When you click "Mint," your wallet (like MetaMask, Rabby, or Phantom) will pop up with a request. Carefully read what it is asking you to do:
* **"Connect" vs. "Sign" vs. "Set Approval for All":** Connecting your wallet is generally safe. However, be extremely wary of **"Set Approval for All"** (ERC-1155) or **"Approve"** (ERC-20) prompts if you are just trying to mint an NFT. These functions give a smart contract permission to drain *existing* assets from your wallet. A standard mint transaction should usually just be a direct interaction with the mint function, costing only network gas (or zero, if truly free, plus a nominal gas fee).
* **Check the Estimated Gas:** Even if the NFT is "free," you will almost always need to pay network gas fees. If the gas fee looks abnormally high, or if the wallet warns you that the interaction is interacting with an unverified or flagged contract, stop immediately.

### 3. Review the Contract on a Block Explorer
* If possible, look at the contract address associated with the mint button. Ensure it matches the contract address provided by the official team in their announcements channel. 

### Best Practices for Safety:
* **Use a burner/secondary wallet:** Never connect your primary vault wallet containing high-value assets to a minting site. Always use a fresh wallet with only enough funds to cover potential gas fees.
* **Revoke permissions later:** If you interact with unfamiliar smart contracts, use a tool like **Revoke.cash** afterward to cut off any lingering permissions.

## Run B — with the SkillGraph bundle as context

Prompt = a one-line framing, the bundle JSON (1066 bytes), then the same question.

Based on the live on-chain verification data for **Ink Koi (INKOI)** on BSC (Chain 56):

### 1. Can you still mint for free right now?
**No, the free lane is CLOSED.** 
* The free pool has been completely exhausted (`2,777 / 2,777` free mints claimed on-chain). 
* While the total collection supply has room (`2,786 / 5,555` minted so far), any new mints now fall under the **paid lane** (`0.0004 BNB` per mint, max 5 per wallet).

### 2. How many free slots are left?
**0 slots left.** 

---

### 3. What should you check if you proceed with a paid mint?
Before signing any transaction using tools like `baw` or `foundry` (`bsc_contract_call_construction`), you should programmatically verify the following fields on-chain:

1. **Contract Address & Integrity:** Confirm you are interacting with the verified INKOI contract (`0xbd4b4e7189ae9356514664146b0ed683601200a9`).
2. **Current Mint Price:** Ensure the active mint price matches the expected paid rate (`0.0004 BNB` per token) rather than an unexpected or modified fee.
3. **Wallet Mint Limit:** Verify your target wallet's current mint count against the `max 5 per wallet` rule to prevent transaction reverts.
4. **Remaining Total Supply:** Check that current total supply has not hit the hard cap of `5,555` INKOI.
5. **Transaction Payload Decoding:** Decode all parameters of the outgoing transaction data (such as quantity and native value attached) to ensure no malicious arguments or excess BNB values are passed.

## Reading

Same model, same question, one run each — the only difference is the bundle.
Run A has no source for today's mint state, so it cannot state the free-slot count; Run B's answer traces to a verdict timestamped 2026-11-14T04:26:46.175Z from an on-chain autocheck.
The bundle buys provenance and freshness, not IQ: a sourced, current fact the agent can cite, plus the verification skills' checks to apply before signing.
