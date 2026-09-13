"""Lookup tables and enumerations for Scout (L5a) terrain reading. No logic here."""

from enum import Enum


class Domain(str, Enum):
    MEDICAL    = "MEDICAL"
    LEGAL      = "LEGAL"
    FINANCIAL  = "FINANCIAL"
    SECURITY   = "SECURITY"
    CODE       = "CODE"
    INDUSTRIAL = "INDUSTRIAL"
    GENERAL    = "GENERAL"
    UNKNOWN    = "UNKNOWN"


_DOMAIN_SIGNALS: dict[Domain, list[str]] = {
    Domain.MEDICAL:    ["pasient", "diagnose", "dose", "medisin", "symptom", "behandling",
                        "patient", "diagnosis", "dosage", "medication", "treatment",
                        "mg", "ml", "ICD", "ICPC", "nyresvikt", "diabetes", "insulin"],
    Domain.LEGAL:      ["kontrakt", "paragraf", "ansvar", "klausul", "erstatning",
                        "contract", "clause", "liability", "indemnity", "court",
                        "kontraktspkt", "indirekte tap"],
    Domain.FINANCIAL:  ["rente", "avkastning", "risiko", "investering", "portefølje",
                        "fastrente", "anbefales", "interest rate", "yield", "portfolio"],
    Domain.SECURITY:   ["overstyr", "ignorer", "glem instruksjoner", "du er nå",
                        "ignore previous", "jailbreak", "override", "pretend you are",
                        "bypass", "disregard", "OVERSTYR"],
    Domain.CODE:       ["def ", "class ", "import ", "function", "sql", "SELECT",
                        "```python", "```sql", "```javascript"],
    Domain.INDUSTRIAL: ["ventil", "trykk", "temperatur", "alarm", "stengt", "åpen",
                        "valve", "pressure", "shutdown", "interlock", "V-12"],
}

_HEDGE_WORDS = ["kanskje", "muligens", "antagelig", "trolig", "sannsynligvis", "usikker",
                "maybe", "perhaps", "possibly", "uncertain", "might", "could be", "not sure"]

# Sycophancy = LLM compensating for lost context with politeness
_SYCOPHANCY_SIGNALS = [
    "flott spørsmål", "utmerket spørsmål", "det er et viktig poeng",
    "du har helt rett", "du er inne på noe", "veldig godt poeng",
    "great question", "excellent point", "absolutely", "certainly",
    "you're absolutely right", "that's a great", "fantastic question",
    "what a great", "i completely agree", "you raise an excellent",
]

# Self-aware degradation = model admitting lost context (strongest signal)
_SELF_AWARE_DEGRADATION = [
    "ny samtale", "ny sesjon", "starte på nytt", "ny tråd",
    "gå og sov", "legg deg", "sov litt", "ta en pause",
    "start fresh", "new conversation", "new session", "start over",
    "fresh start", "begin again", "let's start a new",

    "i may have lost", "i might have lost track", "context may be",
    "jeg husker ikke", "jeg mister tråden", "konteksten er lang",
    "i don't have access to our earlier", "i cannot see the earlier",
    "jeg kan ikke se den tidligere", "jeg har ikke tilgang til",

    "if i recall correctly", "if i remember correctly",
    "as i mentioned earlier", "as we discussed",
    "jeg tror vi diskuterte", "som jeg nevnte tidligere",
    "som vi snakket om", "earlier in our conversation",

    "could you remind me", "could you repeat", "kan du gjenta",
    "kan du minne meg", "what was the original",

    "correct me if i'm wrong", "i may be repeating myself",
    "i might be repeating", "i may have already said",
    "jeg gjentar meg kanskje", "rett meg hvis jeg tar feil",

    "as mentioned", "as noted above", "as discussed above",
    "based on what you've said so far", "from what i understand so far",
]

_FACTUAL_MARKERS = ["er det slik at", "hva er", "hvem er", "når ble", "hvor mange",
                    "what is", "who is", "when was", "how many", "according to"]

# OWASP Top 10 for Agentic AI 2026 — mapping from VAIG risk_type
_OWASP_MAPPING: dict[str, str] = {
    "injection":       "ASI01",  # Agent Goal Hijack
    "hallucination":   "ASI03",  # Memory Poisoning / false recall
    "structure":       "ASI02",  # Tool Misuse (strukturfeil i output)
    "safety_critical": "ASI08",  # Cascading Failures
    "unknown":         "ASI09",  # Human-Agent Trust Exploitation (fallback)
}

_NO_WORDS = ["og", "er", "det", "ikke", "jeg", "du", "vi", "de", "en", "et",
             "med", "til", "for", "på", "som", "av", "har", "kan", "vil", "skal",
             "dette", "disse", "også", "men", "hvis", "når", "eller", "hva", "hvem",
             "hvordan", "hvor", "hvorfor", "nei", "ja", "her", "der", "nå", "da"]

_EN_WORDS = ["the", "and", "is", "not", "you", "we", "they", "with", "for",
             "that", "this", "are", "have", "can", "will", "should", "from",
             "what", "who", "how", "where", "why", "yes", "no", "here", "there"]

# Minimum word-frequency ratio to count a language as present / mixed
_LANG_MIN_RATIO = 0.02
_LANG_MIX_RATIO = 0.05
