"""Segment the novel into tokenized sentences for later analysis.

Pipeline
--------
1. Load data/novel.txt (UTF-8).
2. Convert the whole text to simplified Chinese with OpenCC
   (jieba's dictionaries are trained on simplified characters).
3. Split the text into sentences on Chinese sentence-ending punctuation (。！？).
4. Tokenize each sentence with jieba, discarding punctuation marks.
5. Keep only sentences with at least 5 words.
6. Write sentences.txt: one sentence per line, words separated by a single space.
"""

import jieba
import opencc

INPUT_PATH = "data/novel.txt"
OUTPUT_PATH = "sentences.txt"
SENTENCE_ENDINGS = "。！？"
MIN_WORDS = 5


def split_sentences(text):
    """Split text on Chinese sentence-ending punctuation (。！？)."""
    sentences = []
    start = 0
    for i, ch in enumerate(text):
        if ch in SENTENCE_ENDINGS:
            piece = text[start:i]
            if piece.strip():
                sentences.append(piece)
            start = i + 1
    tail = text[start:]
    if tail.strip():
        sentences.append(tail)
    return sentences


def tokenize(sentence):
    """Tokenize a sentence with jieba, dropping punctuation and whitespace.

    A token is kept only if it contains at least one alphanumeric character
    (letters, digits, CJK characters), which filters out all-punctuation
    tokens such as 「」，。！？…—— and whitespace-only tokens.
    """
    return [word for word in jieba.cut(sentence) if any(ch.isalnum() for ch in word)]


def main():
    # utf-8-sig transparently handles files with or without a BOM.
    with open(INPUT_PATH, "r", encoding="utf-8-sig") as f:
        text = f.read()

    converter = opencc.OpenCC("t2s")
    text = converter.convert(text)

    kept = 0
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        for sentence in split_sentences(text):
            words = tokenize(sentence)
            if len(words) >= MIN_WORDS:
                out.write(" ".join(words) + "\n")
                kept += 1

    print(f"Saved {kept} sentences (>= {MIN_WORDS} words) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
