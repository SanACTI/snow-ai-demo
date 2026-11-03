import tiktoken
import json

# --- Token thresholds ---
MAX_TOKENS_DIRECT = 3000       # send directly to LLM under this
MAX_TOKENS_WITH_SUMMARY = 6000 # summarize first if between 3000-6000
MAX_TOKENS_HARD_LIMIT = 8000   # reject/route to batch above this

# --- Cost estimate (Mistral local = no cost, but track for when cloud is used) ---
# Based on gpt-4.1-mini pricing as reference: $0.40 per 1M input tokens
COST_PER_1K_TOKENS = 0.0004

def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in a string using tiktoken."""
    try:
        enc = tiktoken.get_encoding(model)
        return len(enc.encode(text))
    except Exception as e:
        print(f"[token_guard] ⚠️  Token counting failed: {e}")
        # Fallback: estimate 1 token per 4 chars
        return len(text) // 4

def estimate_cost(token_count: int) -> float:
    """Estimate cost based on token count."""
    return round((token_count / 1000) * COST_PER_1K_TOKENS, 6)

def build_full_prompt(facts: dict, summaries: list, warnings: list,
                      user_template: str, output_schema: str) -> str:
    """Build the full prompt string for token counting."""
    prompt = user_template.replace("{extracted_facts}", json.dumps(facts, indent=2))
    prompt = prompt.replace("{chunk_summaries}", "\n\n".join(summaries))
    prompt = prompt.replace("{validation_warnings}", "\n".join(warnings))
    prompt += f"\n\n## Required Output Schema\n{output_schema}"
    return prompt

def check_and_route(prompt: str, facts: dict) -> dict:
    """
    Check token count and decide how to route.
    Returns a dict with:
    - action: 'direct' | 'summarize_first' | 'batch_required'
    - token_count: int
    - cost_estimate: float
    - reason: str
    """
    token_count = count_tokens(prompt)
    cost = estimate_cost(token_count)
    incident = facts.get("incident_number", "UNKNOWN")
    priority = facts.get("priority", "Unknown")

    print(f"[token_guard] 📊 Token count for {incident}: {token_count} tokens")
    print(f"[token_guard] 💰 Estimated cost: ${cost}")

    if token_count <= MAX_TOKENS_DIRECT:
        print(f"[token_guard] ✅ Under threshold — sending directly to LLM")
        return {
            "action": "direct",
            "token_count": token_count,
            "cost_estimate": cost,
            "reason": f"Token count {token_count} is under direct limit {MAX_TOKENS_DIRECT}"
        }

    elif token_count <= MAX_TOKENS_WITH_SUMMARY:
        print(f"[token_guard] ⚠️  Over direct limit — will summarize work notes first")
        return {
            "action": "summarize_first",
            "token_count": token_count,
            "cost_estimate": cost,
            "reason": f"Token count {token_count} exceeds direct limit, summarizing first"
        }

    else:
        # Hard limit — route to batch for P3/P4, still process for P1/P2
        if priority in ["P1", "P2"]:
            print(f"[token_guard] 🔴 Over hard limit but P1/P2 — processing with truncation")
            return {
                "action": "truncate_and_send",
                "token_count": token_count,
                "cost_estimate": cost,
                "reason": f"Token count {token_count} over hard limit, truncating for P1/P2"
            }
        else:
            print(f"[token_guard] 🔴 Over hard limit — routing to batch queue")
            return {
                "action": "batch_required",
                "token_count": token_count,
                "cost_estimate": cost,
                "reason": f"Token count {token_count} exceeds hard limit {MAX_TOKENS_HARD_LIMIT}, route to batch"
            }

def truncate_prompt(prompt: str, max_tokens: int = MAX_TOKENS_HARD_LIMIT) -> str:
    """Truncate prompt to fit within max token limit."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(prompt)
        if len(tokens) > max_tokens:
            truncated = enc.decode(tokens[:max_tokens])
            print(f"[token_guard] ✂️  Truncated prompt from {len(tokens)} to {max_tokens} tokens")
            return truncated + "\n[NOTE: Input was truncated due to token limit]"
        return prompt
    except Exception:
        # Fallback char truncation
        char_limit = max_tokens * 4
        return prompt[:char_limit] + "\n[NOTE: Input was truncated]"