import re

SENTENCE_ENDS = re.compile(r"[。！？…….!?\n]")


def count_chinese_words(text: str) -> int:
    """Count Chinese characters (excluding punctuation, spaces, newlines)."""
    count = 0
    for ch in text:
        if "一" <= ch <= "鿿":
            count += 1
    return count


def find_chapter_split_point(text: str, min_position: int | None = None) -> int:
    """
    Find the best split point in text that ends at a natural sentence boundary.
    Searches backwards from min_position (or text end) for the nearest valid break.
    Returns the character index AFTER the break (i.e., where to split).
    """
    if min_position is None or min_position >= len(text):
        min_position = len(text)

    search_end = min(len(text), min_position)

    paragraph_break = text.rfind("\n\n", 0, search_end)
    if paragraph_break > 0:
        return paragraph_break + 2

    for i in range(search_end - 1, max(0, search_end - 500), -1):
        ch = text[i]
        if ch in "。！？…\n" and i < len(text) - 1:
            next_ch = text[i + 1]
            if next_ch == "\n" or next_ch == "”" or next_ch == "'" or next_ch == " ":
                return i + 2 if next_ch == "”" or next_ch == "'" else i + 1
        if ch == "。”" or ch == "！”" or ch == "？”":
            return i + 2

    for i in range(search_end - 1, max(0, search_end - 2000), -1):
        if text[i] in "。！？…":
            return i + 1

    return search_end


def estimate_tokens(text: str, chars_per_token: float = 1.5) -> int:
    """Rough token estimation for Chinese text. ~1.5 chars per token on average."""
    return int(len(text) / chars_per_token)
