import re

SENTENCE_ENDS = re.compile(r"[。！？…….!?\n]")
QUOTE_PAIRS = [('"', '"'), ('"', '"'), ('「', '」'), ('『', '』'), ('（', '）'), ('(', ')')]
QUOTE_LEFT = set(p[0] for p in QUOTE_PAIRS)
QUOTE_RIGHT = set(p[1] for p in QUOTE_PAIRS)
QUOTE_MAP = dict(QUOTE_PAIRS)

NARRATION_SEPARATORS = {"说", "道", "问", "答", "喊", "叫", "骂", "笑", "哭", "叹", "想", "问", "答", "回", "讲", "念", "喝", "嚷", "吼", "呢", "吧", "啊"}


def count_chinese_words(text: str) -> int:
    count = 0
    for ch in text:
        if "一" <= ch <= "鿿":
            count += 1
    return count


def _is_paired(text: str) -> bool:
    """Check if all quotes/brackets are properly paired."""
    stack = []
    for ch in text:
        if ch in QUOTE_LEFT:
            stack.append(ch)
        elif ch in QUOTE_RIGHT:
            if not stack:
                return False
            expected = QUOTE_MAP.get(stack[-1])
            if expected != ch:
                return False
            stack.pop()
    return len(stack) == 0


def _is_dialogue_narration_boundary(text: str, pos: int) -> bool:
    """
    Detect patterns like 他说。  or 道。  — a period followed by narration verb.
    This means the sentence hasn't truly ended yet (dialogue attribution).
    Returns True if this is a false sentence boundary that should NOT be split on.
    """
    after = text[pos:pos + 4]
    after_stripped = after.lstrip()
    if after_stripped and after_stripped[0] in NARRATION_SEPARATORS:
        return True
    return False


def find_chapter_split_point(text: str, target_words: int) -> int:
    """
    Find the best natural sentence boundary to split a chapter.
    Enhanced rules:
    1. Prefer paragraph breaks (double newline) first
    2. Avoid splitting inside quotes/brackets
    3. Avoid splitting between dialogue and its attribution (e.g. 。他说道)
    4. Ellipsis only counts as sentence end when followed by newline
    5. Verify both resulting parts have balanced quotes
    6. Minimum valid: first part >= 60% target, second part >= 100 chars
    """
    if not text:
        return 0

    min_pos = max(1, int(len(text) * 0.6))
    max_pos = min(len(text), target_words * 2)
    search_end = min(len(text), max_pos)

    # Rule 1: paragraph break
    for i in range(search_end - 1, min_pos - 1, -1):
        if text[i:i + 2] == "\n\n":
            # Verify pairing on both sides
            left = text[:i + 2]
            right = text[i + 2:]
            if _is_paired(left) and _is_paired(right):
                return i + 2

    # Rule 2-4: scan for valid sentence endings
    candidates = []
    for i in range(search_end - 1, min_pos - 1, -1):
        ch = text[i]

        if ch == "…":
            if i + 1 < len(text) and text[i + 1] == "…":
                ch = "……"
                if i + 2 < len(text) and text[i + 2] in "\n ":
                    candidates.append((i + 2, "……"))
                continue

        if ch in "。！？":
            if i > min_pos and _is_dialogue_narration_boundary(text, i + 1):
                continue

            before_quote = text[i - 1] if i > 0 else ""
            if before_quote in (QUOTE_RIGHT - {"）", "）"}):
                candidates.append((i + 1, "quote_end"))
                continue

            if i + 1 < len(text):
                after = text[i + 1]
                if after == "\n":
                    candidates.append((i + 1, "newline_after"))
                elif after in QUOTE_RIGHT:
                    candidates.append((i + 2, "close_quote"))
                elif after == " " or after == "\t":
                    candidates.append((i + 1, "space"))
                else:
                    candidates.append((i + 1, "sentence_end"))

    # Rule 3: ellipsis (already handled above)

    # Evaluate candidates in priority order
    priority_order = ["newline_after", "……", "close_quote", "quote_end", "sentence_end", "space"]

    for priority in priority_order:
        for split_pos, cand_type in candidates:
            if cand_type != priority:
                continue
            left = text[:split_pos]
            right = text[split_pos:].lstrip()

            # Rule 5: minimum split size
            if len(right) < 100:
                continue
            if len(left) < int(len(text) * 0.5):
                continue

            # Rule 4: quote/bracket pairing
            if _is_paired(left) and _is_paired(right):
                return split_pos

    # Fallback: last-resort sweep — any sentence end that gives balanced halves
    for i in range(search_end - 1, min_pos - 1, -1):
        if text[i] in "。！？…":
            if i > min_pos and _is_dialogue_narration_boundary(text, i + 1):
                continue
            left = text[:i + 1]
            right = text[i + 1:].lstrip()
            if len(right) >= 100 and _is_paired(left) and _is_paired(right):
                return i + 1

    return search_end


def estimate_tokens(text: str, chars_per_token: float = 1.5) -> int:
    return int(len(text) / chars_per_token)

