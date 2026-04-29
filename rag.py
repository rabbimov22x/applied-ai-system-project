"""
Pet care knowledge base for Retrieval-Augmented Generation (RAG).

The knowledge base is a curated list of factual pet care guidelines.
Each entry has a category, plain-text content, and keyword tags.

retrieve(query, top_k) scores every entry against the query using
Jaccard term-overlap (no external dependencies) and returns the
top-k most relevant entries.

format_context(docs) formats retrieved entries into a block of text
that is injected into the agent's system prompt before each API call,
so Claude can ground its scheduling advice in real care guidelines
rather than relying on general training knowledge alone.
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
# Each entry: {"id": str, "category": str, "text": str, "tags": List[str]}

KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    # General feeding
    {
        "id": "feed-001",
        "category": "Feeding",
        "text": "Adult dogs should be fed 1-2 times per day at consistent times. "
                "Irregular feeding schedules can cause digestive upset.",
        "tags": ["dog", "feeding", "meal", "schedule", "daily"],
    },
    {
        "id": "feed-002",
        "category": "Feeding",
        "text": "Puppies under 6 months need 3-4 small meals per day; "
                "puppies 6-12 months need 2-3 meals.",
        "tags": ["puppy", "dog", "feeding", "meal", "young"],
    },
    {
        "id": "feed-003",
        "category": "Feeding",
        "text": "Cats are obligate carnivores. Most adult cats do well with "
                "2 meals per day, roughly 12 hours apart.",
        "tags": ["cat", "feeding", "meal", "schedule", "nutrition"],
    },
    {
        "id": "feed-004",
        "category": "Feeding",
        "text": "Fresh water must be available at all times for both dogs and cats. "
                "Change water at least once per day.",
        "tags": ["dog", "cat", "water", "hydration", "daily"],
    },

    # Exercise
    {
        "id": "exer-001",
        "category": "Exercise",
        "text": "Golden Retrievers are high-energy dogs that need at least "
                "1 to 2 hours of vigorous exercise daily, split into two sessions.",
        "tags": ["golden retriever", "dog", "walk", "exercise", "daily", "energy"],
    },
    {
        "id": "exer-002",
        "category": "Exercise",
        "text": "Most adult dogs need 30 minutes to 2 hours of exercise per day "
                "depending on breed, age, and health status.",
        "tags": ["dog", "walk", "exercise", "daily"],
    },
    {
        "id": "exer-003",
        "category": "Exercise",
        "text": "Senior dogs (7 years and older) benefit from shorter, more frequent "
                "walks rather than a single long outing, to reduce joint stress.",
        "tags": ["dog", "senior", "old", "walk", "exercise", "joint"],
    },
    {
        "id": "exer-004",
        "category": "Exercise",
        "text": "Siamese cats are active and social. Daily interactive play sessions "
                "of 15-20 minutes prevent boredom and behavioural issues.",
        "tags": ["siamese", "cat", "play", "exercise", "enrichment", "daily"],
    },

    # Grooming
    {
        "id": "groom-001",
        "category": "Grooming",
        "text": "Golden Retrievers require brushing 2-3 times per week "
                "to prevent matting and reduce shedding.",
        "tags": ["golden retriever", "dog", "brushing", "grooming", "weekly"],
    },
    {
        "id": "groom-002",
        "category": "Grooming",
        "text": "Nail trimming should occur every 3-4 weeks for most dogs. "
                "Overgrown nails cause joint pain and affect posture.",
        "tags": ["dog", "nails", "grooming", "monthly", "trimming"],
    },
    {
        "id": "groom-003",
        "category": "Grooming",
        "text": "Litter boxes must be scooped at least once daily. Cats often "
                "refuse to use dirty boxes, which can cause health problems.",
        "tags": ["cat", "litter", "litter box", "daily", "hygiene"],
    },
    {
        "id": "groom-004",
        "category": "Grooming",
        "text": "Dental care should include brushing or dental chews daily. "
                "Professional cleaning is typically needed once a year.",
        "tags": ["dog", "cat", "teeth", "dental", "daily", "grooming"],
    },

    # Medication
    {
        "id": "med-001",
        "category": "Medication",
        "text": "Medications should be given at consistent times each day to maintain "
                "stable blood levels. Set a reminder rather than relying on memory.",
        "tags": ["medication", "medicine", "daily", "consistent", "schedule"],
    },
    {
        "id": "med-002",
        "category": "Medication",
        "text": "Never skip a pet's prescribed medication without consulting a vet, "
                "even if the pet appears healthy.",
        "tags": ["medication", "medicine", "prescription", "health"],
    },
    {
        "id": "med-003",
        "category": "Medication",
        "text": "Flea and tick preventatives are typically applied monthly. "
                "Missing a dose can leave a window of vulnerability.",
        "tags": ["flea", "tick", "medication", "monthly", "prevention"],
    },

    # Scheduling and timing
    {
        "id": "sched-001",
        "category": "Scheduling",
        "text": "Morning walks before feeding are recommended for large-breed dogs "
                "to reduce the risk of bloat (gastric dilatation-volvulus).",
        "tags": ["dog", "walk", "morning", "feeding", "large breed", "bloat"],
    },
    {
        "id": "sched-002",
        "category": "Scheduling",
        "text": "Feeding, walks, and medication should occur at the same time each day. "
                "Pets adapt quickly to consistent routines and may become anxious without them.",
        "tags": ["routine", "consistent", "schedule", "daily", "feeding", "walk"],
    },

    # Vet care
    {
        "id": "vet-001",
        "category": "Vet Care",
        "text": "Most healthy adult pets need a vet checkup once per year. "
                "Senior pets (7 years and older) should visit every 6 months.",
        "tags": ["vet", "checkup", "annual", "yearly", "senior", "health"],
    },
    {
        "id": "vet-002",
        "category": "Vet Care",
        "text": "Vaccinations are typically given annually or every 3 years depending "
                "on the vaccine type and local regulations.",
        "tags": ["vaccine", "vaccination", "vet", "annual", "yearly"],
    },
]


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> set:
    """Lowercase, split on whitespace and punctuation, return unique words."""
    import re
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Return the top-k knowledge base entries most relevant to the query.

    Scoring uses Jaccard similarity between the query token set and the
    union of the entry's text and tag tokens. This requires no external
    libraries and runs in O(n) time over the knowledge base.

    Args:
        query:  The user's input or a summary of it.
        top_k:  Maximum number of entries to return.

    Returns:
        List of knowledge base entries, each with an added "score" key,
        ordered from most to least relevant. Entries with score 0 are
        excluded.
    """
    query_tokens = _tokenise(query)
    scored: List[Dict[str, Any]] = []

    for entry in KNOWLEDGE_BASE:
        doc_tokens = _tokenise(entry["text"]) | set(entry["tags"])
        intersection = query_tokens & doc_tokens
        union = query_tokens | doc_tokens
        score = len(intersection) / len(union) if union else 0.0
        if score > 0:
            scored.append({**entry, "score": round(score, 4)})

    scored.sort(key=lambda e: e["score"], reverse=True)
    return scored[:top_k]


def format_context(docs: List[Dict[str, Any]]) -> str:
    """
    Format retrieved knowledge base entries into a block of text
    suitable for injection into a system prompt.

    Args:
        docs: List of entries returned by retrieve().

    Returns:
        A formatted string, or an empty string if docs is empty.
    """
    if not docs:
        return ""
    lines = ["## Retrieved pet care guidelines (use these to inform your response)"]
    for doc in docs:
        lines.append(f"[{doc['category']}] {doc['text']}")
    return "\n".join(lines)
