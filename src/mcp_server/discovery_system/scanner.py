"""
Discovery System Scanner - Script-Based Markdown Extraction

Scans CLAUDE.md, wiki/, and docs/ directories to extract knowledge patterns
using simple markdown parsing (no LLM required for P05 MVP).
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiscoveredSection:
    """A discovered section from a knowledge source."""

    source_file: str
    source_type: str  # CLAUDE_MD, WIKI, DOCS
    section_title: str | None
    section_content: str
    content_hash: str
    keywords: list[str] = field(default_factory=list)


class DiscoveryScanner:
    """Script-based scanner for repository knowledge patterns."""

    # Common folder names for wiki and docs
    WIKI_FOLDER_NAMES = ["wiki", "Wiki", ".wiki"]
    DOCS_FOLDER_NAMES = ["docs", "Docs", "documentation", "Documentation"]

    # Minimum section content length to consider (avoid empty sections)
    MIN_SECTION_LENGTH = 50

    # Common words to exclude from keywords
    STOP_WORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "we",
        "us",
        "our",
        "you",
        "your",
        "he",
        "she",
        "him",
        "her",
        "his",
        "if",
        "then",
        "else",
        "when",
        "where",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "why",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "not",
        "only",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "here",
        "there",
        "any",
        "into",
    }

    def __init__(self, project_root: Path):
        """
        Initialize scanner for a project.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root)

    def scan_all(self) -> list[DiscoveredSection]:
        """
        Scan all knowledge sources and return discovered sections.

        Returns:
            List of DiscoveredSection objects
        """
        discoveries = []

        # Scan CLAUDE.md
        claude_md = self.project_root / "CLAUDE.md"
        if claude_md.exists():
            discoveries.extend(self._scan_markdown_file(claude_md, "CLAUDE_MD"))

        # Scan wiki folder
        wiki_path = self._find_folder(self.WIKI_FOLDER_NAMES)
        if wiki_path:
            discoveries.extend(self._scan_folder(wiki_path, "WIKI"))

        # Scan docs folder
        docs_path = self._find_folder(self.DOCS_FOLDER_NAMES)
        if docs_path:
            discoveries.extend(self._scan_folder(docs_path, "DOCS"))

        return discoveries

    def scan_claude_md(self) -> list[DiscoveredSection]:
        """Scan CLAUDE.md file only."""
        claude_md = self.project_root / "CLAUDE.md"
        if claude_md.exists():
            return self._scan_markdown_file(claude_md, "CLAUDE_MD")
        return []

    def scan_wiki(self) -> list[DiscoveredSection]:
        """Scan wiki folder only."""
        wiki_path = self._find_folder(self.WIKI_FOLDER_NAMES)
        if wiki_path:
            return self._scan_folder(wiki_path, "WIKI")
        return []

    def scan_docs(self) -> list[DiscoveredSection]:
        """Scan docs folder only."""
        docs_path = self._find_folder(self.DOCS_FOLDER_NAMES)
        if docs_path:
            return self._scan_folder(docs_path, "DOCS")
        return []

    def _find_folder(self, folder_names: list[str]) -> Path | None:
        """Find first existing folder from list of candidates."""
        for name in folder_names:
            candidate = self.project_root / name
            if candidate.is_dir():
                return candidate
        return None

    def _scan_folder(self, folder: Path, source_type: str) -> list[DiscoveredSection]:
        """Scan all markdown files in a folder recursively."""
        discoveries = []
        for md_file in folder.rglob("*.md"):
            # Skip hidden files and directories
            if any(part.startswith(".") for part in md_file.parts):
                continue
            discoveries.extend(self._scan_markdown_file(md_file, source_type))
        return discoveries

    def _scan_markdown_file(
        self, file_path: Path, source_type: str
    ) -> list[DiscoveredSection]:
        """
        Scan a markdown file and extract sections by H2/H3 headers.

        Returns:
            List of DiscoveredSection objects
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        relative_path = str(file_path.relative_to(self.project_root))
        discoveries = []

        # Split content by H2/H3 headers
        sections = self._split_by_headers(content)

        for title, section_content in sections:
            # Skip sections that are too short
            if len(section_content.strip()) < self.MIN_SECTION_LENGTH:
                continue

            # Calculate content hash
            content_hash = hashlib.sha256(section_content.encode()).hexdigest()

            # Extract keywords
            keywords = self._extract_keywords(title, section_content)

            discoveries.append(
                DiscoveredSection(
                    source_file=relative_path,
                    source_type=source_type,
                    section_title=title,
                    section_content=section_content.strip(),
                    content_hash=content_hash,
                    keywords=keywords,
                )
            )

        return discoveries

    def _split_by_headers(self, content: str) -> list[tuple[str | None, str]]:
        """
        Split markdown content by H2 (##) and H3 (###) headers.

        Returns:
            List of (header_title, section_content) tuples
        """
        # Pattern to match H2 and H3 headers
        header_pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)

        sections: list[tuple[str | None, str]] = []
        last_end = 0
        last_title: str | None = None

        for match in header_pattern.finditer(content):
            # Save previous section if it exists
            if last_end > 0 or match.start() > 0:
                section_content = content[last_end : match.start()]
                if section_content.strip():
                    sections.append((last_title, section_content))

            last_title = match.group(2).strip()
            last_end = match.end()

        # Don't forget the last section
        if last_end < len(content):
            section_content = content[last_end:]
            if section_content.strip():
                sections.append((last_title, section_content))

        # If no headers found, treat entire content as one section
        if not sections and content.strip():
            sections.append((None, content))

        return sections

    def _extract_keywords(self, title: str | None, content: str) -> list[str]:
        """
        Extract keywords from section title and content.

        Simple approach for P05 MVP:
        - Extract words from title (high weight)
        - Extract code identifiers (functions, classes)
        - Extract frequently occurring words
        """
        keywords: set[str] = set()

        # Add words from title (these are high signal)
        if title:
            title_words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", title.lower())
            keywords.update(w for w in title_words if len(w) > 2)

        # Extract code identifiers (function names, class names)
        # Look for patterns like: def func_name, class ClassName, function funcName
        code_patterns = [
            r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # Python functions
            r"\bclass\s+([A-Z][a-zA-Z0-9_]*)",  # Python/JS classes
            r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # JS functions
            r"\bconst\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # JS const
            r"`([a-zA-Z_][a-zA-Z0-9_]*)`",  # Backtick identifiers
        ]
        for pattern in code_patterns:
            matches = re.findall(pattern, content)
            keywords.update(m.lower() for m in matches if len(m) > 2)

        # Extract capitalized multi-word phrases (likely proper nouns/concepts)
        concept_pattern = r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b"
        concepts = re.findall(concept_pattern, content)
        for concept in concepts[:10]:  # Limit to avoid noise
            keywords.add(concept.lower().replace(" ", "_"))

        # Word frequency analysis (words appearing 3+ times)
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", content.lower())
        word_counts: dict[str, int] = {}
        for word in words:
            if word not in self.STOP_WORDS and len(word) > 3:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Add words that appear frequently
        frequent = [w for w, c in word_counts.items() if c >= 3]
        keywords.update(frequent[:20])  # Limit to top 20

        # Remove stop words and return sorted list
        keywords = {k for k in keywords if k not in self.STOP_WORDS}
        return sorted(keywords)[:30]  # Max 30 keywords per section

    def get_scan_summary(self, discoveries: list[DiscoveredSection]) -> dict:
        """
        Generate a summary of scan results.

        Returns:
            Dictionary with counts by source type
        """
        from typing import Any

        by_source: dict[str, dict[str, Any]] = {}
        files_scanned: set[str] = set()

        for d in discoveries:
            # Count by source type
            if d.source_type not in by_source:
                by_source[d.source_type] = {
                    "files": set(),
                    "sections": 0,
                }
            by_source[d.source_type]["files"].add(d.source_file)
            by_source[d.source_type]["sections"] += 1
            files_scanned.add(d.source_file)

        # Convert sets to counts for JSON serialization
        for source_type in by_source:
            by_source[source_type]["files"] = len(by_source[source_type]["files"])

        summary: dict[str, Any] = {
            "total": len(discoveries),
            "by_source": by_source,
            "files_scanned": len(files_scanned),
        }

        return summary
