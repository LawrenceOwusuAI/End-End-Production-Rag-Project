import re
from typing import Optional
from nemoguardrails.actions import action
from nemoguardrails.actions.rail_outcome import RailOutcome

# INPUT PROMPT-INJECTION PATTERNS
BLOCKED_INPUT_PATTERNS = [

    # SYSTEM PROMPT EXTRACTION
    r"\breveal\s+(the\s+)?system\s+prompt\b",

    r"\bshow\s+(me\s+)?(the\s+)?system\s+prompt\b",

    r"\bprint\s+(the\s+)?system\s+prompt\b",

    r"\bdisplay\s+(the\s+)?system\s+prompt\b",

    r"\breveal\s+(the\s+)?developer\s+(message|instructions)\b",

    r"\bshow\s+(me\s+)?(the\s+)?hidden\s+instructions\b",

    # PROMPT INJECTION
    r"\bignore\s+(all\s+)?previous\s+instructions\b",

    r"\bignore\s+(all\s+)?prior\s+instructions\b",

    r"\bforget\s+(all\s+)?previous\s+instructions\b",

    r"\bdisregard\s+(all\s+)?previous\s+instructions\b",

    r"\boverride\s+(the\s+)?system\s+instructions\b",

    r"\bdisregard\s+(the\s+)?system\s+prompt\b",

    # SECURITY BYPASS
    r"\bdisable\s+(the\s+)?guardrails\b",

    r"\bbypass\s+(the\s+)?guardrails\b",

    r"\bdisable\s+(the\s+)?safety\s+checks\b",

    r"\bbypass\s+(the\s+)?safety\s+controls\b",

    r"\bturn\s+off\s+(the\s+)?moderation\b",

    r"\bremove\s+(the\s+)?security\s+rules\b",
]

# OUTPUT SECRET PATTERNS
SECRET_OUTPUT_PATTERNS = [
    # OPENAI-LIKE API KEY
    r"\bsk-[A-Za-z0-9_-]{16,}\b",

    # GITHUB TOKENS
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",

    # AWS ACCESS KEY
    r"\bAKIA[0-9A-Z]{16}\b",

    # PRIVATE KEY
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",

    r"""
    \b
    (
        api[_-]?key
        |
        secret[_-]?key
        |
        password
        |
        access[_-]?token
        |
        auth[_-]?token
        |
        bearer[_-]?token
    )
    \s*
    [:＝=]
    \s*
    ["']?
    [^\s"']{8,}
    """
]

# CUSTOM INPUT RAIL ACTION
@action(name="custom_block_input", is_system_action=True)

async def custom_block_input(context: Optional[dict] = None):
    context = (context or {})
    user_text = str(context.get("user_message","") or context.get("user_input","") or "")
    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern,user_text,flags=re.IGNORECASE):
            return RailOutcome.block(reason=("Prompt injection or security bypass detected."))
    return RailOutcome.allow()

# CUSTOM OUTPUT SECRET-LEAKAGE ACTION
@action(name="custom_block_output_secrets",is_system_action=True)
async def custom_block_output_secrets(context: Optional[dict] = None):
    context = (context or {})
    bot_text = str(context.get("bot_message","") or context.get("bot_response","") or "")
    for pattern in SECRET_OUTPUT_PATTERNS:
        if re.search(pattern,bot_text, flags=(re.IGNORECASE | re.VERBOSE)):
            return RailOutcome.block(reason=("Potential credential or secret leakage detected."))
    return RailOutcome.allow()