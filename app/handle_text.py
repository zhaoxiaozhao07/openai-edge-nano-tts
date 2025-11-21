# handle_text.py

import re
import emoji

def prepare_tts_input_with_context(text: str) -> str:
    """
    Prepares text for a TTS API by cleaning Markdown and adding minimal contextual hints
    for certain Markdown elements like headers. Preserves paragraph separation.

    Args:
        text (str): The raw text containing Markdown or other formatting.

    Returns:
        str: Cleaned text with contextual hints suitable for TTS input.
    """

    # Remove emojis
    text = emoji.replace_emoji(text, replace='')

    # Add context for headers
    def header_replacer(match):
        level = len(match.group(1))  # Number of '#' symbols
        header_text = match.group(2).strip()
        if level == 1:
            return f"Title — {header_text}\n"
        elif level == 2:
            return f"Section — {header_text}\n"
        else:
            return f"Subsection — {header_text}\n"

    text = re.sub(r"^(#{1,6})\s+(.*)", header_replacer, text, flags=re.MULTILINE)

    # Announce links (currently commented out for potential future use)
    # text = re.sub(r"\[([^\]]+)\]\((https?:\/\/[^\)]+)\)", r"\1 (link: \2)", text)

    # Remove links while keeping the link text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # Describe inline code
    text = re.sub(r"`([^`]+)`", r"code snippet: \1", text)

    # Remove bold/italic symbols but keep the content
    text = re.sub(r"(\*\*|__|\*|_)", '', text)

    # Remove code blocks (multi-line) with a description
    text = re.sub(r"```([\s\S]+?)```", r"(code block omitted)", text)

    # Remove image syntax but add alt text if available
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"Image: \1", text)

    # Remove HTML tags
    text = re.sub(r"</?[^>]+(>|$)", '', text)

    # Normalize line breaks
    text = re.sub(r"\n{2,}", '\n\n', text)  # Ensure consistent paragraph separation

    # Replace multiple spaces within lines
    text = re.sub(r" {2,}", ' ', text)

    # Trim leading and trailing whitespace from the whole text
    text = text.strip()

    return text

def clean_text(text, options):
    """
    Cleans the text based on the provided options.
    Mirroring logic from speech.js cleanText function.
    """
    cleaned_text = text

    # Stage 1: Structural content removal
    if options.get('remove_urls'):
        # Remove URLs
        cleaned_text = re.sub(r'https?://\S+|www\.\S+', '', cleaned_text)
    
    if options.get('remove_markdown'):
        # Remove Markdown syntax
        # Remove images
        cleaned_text = re.sub(r'!\[.*?\]\(.*?\)', '', cleaned_text)
        # Remove links (keep text)
        cleaned_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned_text)
        # Remove bold/italic
        cleaned_text = re.sub(r'(\*\*|__|\*|_)', '', cleaned_text)
        # Remove code blocks
        cleaned_text = re.sub(r'```[\s\S]*?```', '', cleaned_text)
        # Remove inline code
        cleaned_text = re.sub(r'`.*?`', '', cleaned_text)
        # Remove headers
        cleaned_text = re.sub(r'#+\s', '', cleaned_text)
        # Remove blockquotes
        cleaned_text = re.sub(r'>\s', '', cleaned_text)

    # Stage 2: Custom content removal
    custom_keywords = options.get('custom_keywords', [])
    if custom_keywords:
        for keyword in custom_keywords:
            cleaned_text = cleaned_text.replace(keyword, '')

    # Stage 3: Character removal
    if options.get('remove_emoji'):
        cleaned_text = emoji.replace_emoji(cleaned_text, replace='')

    # Stage 4: Context-aware formatting cleaning
    if options.get('remove_citation_numbers'):
        # Remove citation numbers like [1], [2]
        cleaned_text = re.sub(r'\[\d+\]', '', cleaned_text)

    # Stage 5: General format cleaning
    if options.get('remove_line_breaks'):
        # Replace multiple newlines with a single space
        cleaned_text = re.sub(r'\n+', ' ', cleaned_text)
        # Normalize whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    # Stage 6: Final cleanup
    return cleaned_text.strip()
