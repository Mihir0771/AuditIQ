"""Content readability and text length distribution checks (CONT-*)."""

import re

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


def count_syllables(word: str) -> int:
    """Estimates syllable count of an English word using phonetic vowel clusters."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove silent trailing 'e'
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel

    return max(1, count)


def calculate_flesch_reading_ease(words: list[str], sentences: list[str]) -> float:
    """Computes standard Flesch Reading Ease score:

    206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
    90-100: Very Easy (5th grade)
    60-70: Standard (8th-9th grade)
    0-30: Very Confusing (College graduate)
    """
    total_words = len(words)
    total_sentences = max(1, len(sentences))
    if total_words == 0:
        return 0.0

    total_syllables = sum(count_syllables(w) for w in words)
    asl = total_words / total_sentences
    asw = total_syllables / total_words

    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return round(max(0.0, min(100.0, score)), 1)


class ReadabilityCheck(BaseCheck):
    id = "CONT-READABILITY-SCORE"
    layer = AuditLayer.CONTENT
    title = "Flesch Reading Ease & Comprehension Level"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "Content that is unnecessarily convoluted or dense scores poorly with human readers and "
        "increases the risk that AI models hallucinate or misinterpret factual claims."
    )
    fix_guidance = (
        "Aim for a Flesch Reading Ease score of 50–70 (accessible to general audiences) by shortening "
        "sentences and replacing bureaucratic jargon with plain language."
    )
    references = ["https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 100:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        body = parser.css_first("body")
        if not body:
            return []

        # Extract clean text from paragraphs or semantic content containers
        paragraphs = [p.text(strip=True) for p in body.css("p") if len(p.text(strip=True)) > 20]
        if paragraphs:
            full_text = " ".join(paragraphs)
        else:
            # Fallback for modern SPAs and documentation layouts lacking standard <p> wrappers
            content_nodes = body.css(
                "article, main, section, [role='main'], div.content, div.post, div.markdown-body"
            )
            candidate_text = [
                n.text(strip=True) for n in content_nodes if len(n.text(strip=True)) > 50
            ]
            full_text = " ".join(candidate_text) if candidate_text else body.text(strip=True)

        if not full_text or len(full_text.split()) < 30:
            return []

        words = re.findall(r"\b[a-zA-Z]+\b", full_text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", full_text) if len(s.strip()) > 5]

        score = calculate_flesch_reading_ease(words, sentences)

        if score < 30.0:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "flesch_reading_ease": score,
                            "classification": "Very Difficult / Academic (College Graduate)",
                            "avg_sentence_length_words": round(
                                len(words) / max(1, len(sentences)), 1
                            ),
                        }
                    ],
                    title_override=f"Low readability score ({score:.0f}/100): Content is very difficult to read",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"flesch_reading_ease": score, "classification": "Accessible"}],
            )
        ]


class SentenceVarietyCheck(BaseCheck):
    id = "CONT-SENTENCE-VARIETY"
    layer = AuditLayer.CONTENT
    title = "Paragraph & Sentence Length Hygiene"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 2
    why_it_matters = (
        "Walls of text (paragraphs >150 words) fatigue mobile readers and prevent LLM chunking algorithms "
        "from cleanly isolating quotable passages."
    )
    fix_guidance = "Break long paragraphs (>150 words) into digestible 2-3 sentence chunks and add bullet lists."
    references = ["https://web.dev/articles/content-best-practices"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        long_paragraphs = []

        for p in parser.css("p"):
            text = p.text(strip=True)
            words = text.split()
            if len(words) > 150:
                long_paragraphs.append({"word_count": len(words), "snippet": text[:80] + "..."})

        if long_paragraphs:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "long_paragraphs_count": len(long_paragraphs),
                            "samples": long_paragraphs[:3],
                        }
                    ],
                    title_override=f"Detected {len(long_paragraphs)} wall-of-text paragraph(s) (>150 words)",
                )
            ]
        return []


class ThinContentCheck(BaseCheck):
    id = "CONT-THIN-CONTENT"
    layer = AuditLayer.CONTENT
    title = "Thin Content Pages (<250 Words)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Pages with less than 250 words offer little unique value to users, are flagged as low-quality "
        "under Google's Helpful Content guidelines, and are ignored by generative AI answer engines."
    )
    fix_guidance = "Expand thin pages with comprehensive answers, examples, or consolidate into parent category pages."
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or "text/html" not in snap.content_type:
            return []

        if snap.word_count < 250:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"word_count": snap.word_count, "minimum_recommended": 250}],
                    title_override=f"Thin content: Page contains only {snap.word_count} words (<250 words)",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"word_count": snap.word_count}],
            )
        ]
