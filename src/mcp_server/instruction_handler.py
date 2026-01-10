"""Instruction File Handler

Handles reading, parsing, and querying instruction files in Enhanced MDC format
(Markdown + YAML frontmatter).

Enhanced MDC Format:
---
id: unique-id
version: 1.0.0
schema: pongogo-instruction-v1
description: Brief description
tags: [tag1, tag2]
categories: [category1, category2]
routing:
  applyTo:
    globs: ['**/*.py']
  triggers:
    keywords: [keyword1, keyword2]
---

# Markdown Content
"""

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class InstructionFile:
    """Represents a single instruction file with metadata and content."""

    def __init__(self, file_path: Path, metadata: dict, content: str):
        self.file_path = file_path
        self.metadata = metadata
        self.content = content

        # Extract common fields
        self.id = metadata.get("id", file_path.stem)
        self.version = metadata.get("version", "1.0.0")
        self.schema = metadata.get("schema", "pongogo-instruction-v1")
        self.description = metadata.get("description", "")

        # Support 'domains' as alias for 'categories' (legacy field name)
        # Support 'patterns' as additional tags source
        self.tags = metadata.get("tags", [])
        patterns = metadata.get("patterns", [])
        if patterns and not self.tags:
            self.tags = patterns  # Use patterns as tags if tags empty

        self.categories = metadata.get("categories", [])
        domains = metadata.get("domains", [])
        if domains and not self.categories:
            self.categories = domains  # Use domains as categories if categories empty

        # Support 'applies_to' as top-level glob patterns
        self.routing = metadata.get("routing", {})
        applies_to = metadata.get("applies_to", [])
        if applies_to:
            # Merge applies_to into routing.applyTo.globs
            if "applyTo" not in self.routing:
                self.routing["applyTo"] = {}
            existing_globs = self.routing["applyTo"].get("globs", [])
            # Combine existing globs with applies_to, avoiding duplicates
            merged_globs = list(set(existing_globs + applies_to))
            self.routing["applyTo"]["globs"] = merged_globs

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": str(self.file_path),
            "id": self.id,
            "version": self.version,
            "schema": self.schema,
            "description": self.description,
            "tags": self.tags,
            "categories": self.categories,
            "routing": self.routing,
            "content": self.content,
            "metadata": self.metadata,
        }


class InstructionHandler:
    """Handles loading, parsing, and querying instruction files."""

    def __init__(self, knowledge_base_path: Path, core_path: Path | None = None):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.core_path = Path(core_path) if core_path else None
        self.instructions: dict[str, InstructionFile] = {}
        self.by_category: dict[str, list[str]] = {}
        self._protected_ids: set = set()  # Track protected instruction IDs

        logger.info(
            f"InstructionHandler initialized with path: {self.knowledge_base_path}"
        )
        if self.core_path:
            logger.info(f"Core instructions path: {self.core_path}")

    def load_instructions(self) -> int:
        """
        Load all instruction files from knowledge base.

        Loads in two phases:
        1. Core instructions (protected, bundled in package) - loaded first
        2. User instructions (from .pongogo/instructions/) - skip if shadows protected ID

        Returns:
            Number of instruction files loaded
        """
        count = 0

        # Phase 1: Load CORE instructions first (protected, bundled in package)
        if self.core_path and self.core_path.exists():
            for file_path in self.core_path.rglob("*.instructions.md"):
                try:
                    instruction = self._parse_instruction_file(file_path)
                    if instruction:
                        # Mark as protected
                        instruction.metadata["protected"] = True
                        self.instructions[instruction.id] = instruction

                        # Track protected IDs (both with and without core: prefix)
                        self._protected_ids.add(instruction.id)
                        base_id = instruction.id.replace("core:", "")
                        self._protected_ids.add(base_id)

                        # Index by category
                        for category in instruction.categories:
                            if category not in self.by_category:
                                self.by_category[category] = []
                            self.by_category[category].append(instruction.id)

                        count += 1
                        logger.debug(
                            f"Loaded CORE instruction: {instruction.id} from {file_path}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error loading core instruction file {file_path}: {e}",
                        exc_info=True,
                    )

            logger.info(
                f"Loaded {len(self._protected_ids) // 2} core instruction files"
            )

        # Phase 2: Load USER instructions (skip if shadows protected ID)
        if not self.knowledge_base_path.exists():
            # Not an error - core instructions are still available
            # User instructions are optional (projects may only use core)
            logger.debug(
                f"No user instructions at {self.knowledge_base_path} (using core only)"
            )
            return count

        for file_path in self.knowledge_base_path.rglob("*.instructions.md"):
            try:
                instruction = self._parse_instruction_file(file_path)
                if instruction:
                    # Check if this shadows a protected ID
                    if instruction.id in self._protected_ids:
                        logger.warning(
                            f"Skipping '{instruction.id}' from {file_path} - "
                            f"shadows protected core instruction"
                        )
                        continue

                    self.instructions[instruction.id] = instruction

                    # Index by category
                    for category in instruction.categories:
                        if category not in self.by_category:
                            self.by_category[category] = []
                        self.by_category[category].append(instruction.id)

                    count += 1
                    logger.debug(
                        f"Loaded instruction: {instruction.id} from {file_path}"
                    )

            except Exception as e:
                logger.error(
                    f"Error loading instruction file {file_path}: {e}", exc_info=True
                )

        logger.info(f"Loaded {count} instruction files total")
        return count

    def _parse_instruction_file(self, file_path: Path) -> InstructionFile | None:
        """
        Parse instruction file in Enhanced MDC format.

        Expected format:
        ---
        id: unique-id
        ...metadata...
        ---
        # Markdown content

        Returns:
            InstructionFile instance or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Check for YAML frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
            )

            if frontmatter_match:
                # Enhanced MDC format with YAML frontmatter
                yaml_content = frontmatter_match.group(1)
                markdown_content = frontmatter_match.group(2)

                try:
                    metadata = yaml.safe_load(yaml_content) or {}
                except yaml.YAMLError as e:
                    logger.error(f"YAML parsing error in {file_path}: {e}")
                    return None

            else:
                # Plain markdown (no frontmatter)
                metadata = {}
                markdown_content = content

            # Merge categories from multiple sources
            # IMPORTANT: Directory-based category MUST be first for ground truth matching
            # Ground truth uses format "directory/name" so first category must match directory
            categories = []
            seen = set()

            # 1. Directory-based category FIRST (critical for ground truth matching)
            dir_category = file_path.parent.name
            if dir_category != "pongogo":
                categories.append(dir_category)
                seen.add(dir_category)

            # 2. Add explicit categories
            for cat in metadata.get("categories", []):
                if cat not in seen:
                    categories.append(cat)
                    seen.add(cat)

            # 3. Add domains as additional categories (legacy field name)
            for cat in metadata.get("domains", []):
                if cat not in seen:
                    categories.append(cat)
                    seen.add(cat)

            # Store merged categories (directory first, then explicit, then domains)
            metadata["categories"] = categories

            # Create InstructionFile
            instruction = InstructionFile(
                file_path=file_path, metadata=metadata, content=markdown_content.strip()
            )

            return instruction

        except Exception as e:
            logger.error(
                f"Error parsing instruction file {file_path}: {e}", exc_info=True
            )
            return None

    def get_instruction(self, category: str, name: str) -> dict | None:
        """
        Get specific instruction file by category and name.

        Args:
            category: Category directory name
            name: Instruction file name (without .instructions.md)

        Returns:
            Instruction dictionary or None if not found
        """
        # Try direct lookup by id
        instruction_id = f"{category}/{name}"
        if instruction_id in self.instructions:
            return self.instructions[instruction_id].to_dict()

        # Try lookup by name only
        if name in self.instructions:
            return self.instructions[name].to_dict()

        # Try finding by file name
        for instruction in self.instructions.values():
            if instruction.file_path.stem == name:
                # Check if category matches
                if (
                    category in instruction.categories
                    or category == instruction.file_path.parent.name
                ):
                    return instruction.to_dict()

        logger.warning(f"Instruction not found: {category}/{name}")
        return None

    def get_instructions_by_category(self, category: str) -> list[dict]:
        """
        Get all instruction files in a category.

        Args:
            category: Category name

        Returns:
            List of instruction dictionaries
        """
        instruction_ids = self.by_category.get(category, [])
        return [
            self.instructions[id].to_dict()
            for id in instruction_ids
            if id in self.instructions
        ]

    def get_all_instructions(self) -> list[dict]:
        """
        Get all instruction files.

        Returns:
            List of all instruction dictionaries
        """
        return [instruction.to_dict() for instruction in self.instructions.values()]

    def search_instructions(self, query: str, limit: int = 10) -> list[dict]:
        """
        Full-text search across instruction files.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching instruction dictionaries with snippets
        """
        results = []
        query_lower = query.lower()

        for instruction in self.instructions.values():
            # Search in id, description, tags, categories, content
            score = 0
            matches = []

            # Check id
            if query_lower in instruction.id.lower():
                score += 10
                matches.append(f"ID: {instruction.id}")

            # Check description
            if query_lower in instruction.description.lower():
                score += 8
                matches.append(f"Description: {instruction.description}")

            # Check tags
            for tag in instruction.tags:
                if query_lower in tag.lower():
                    score += 5
                    matches.append(f"Tag: {tag}")

            # Check categories
            for category in instruction.categories:
                if query_lower in category.lower():
                    score += 7
                    matches.append(f"Category: {category}")

            # Check content
            if query_lower in instruction.content.lower():
                score += 3
                # Find snippet around first match
                idx = instruction.content.lower().index(query_lower)
                start = max(0, idx - 100)
                end = min(len(instruction.content), idx + 100)
                snippet = instruction.content[start:end]
                matches.append(f"Content: ...{snippet}...")

            if score > 0:
                result = instruction.to_dict()
                result["search_score"] = score
                result["search_matches"] = matches
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x["search_score"], reverse=True)

        # Return top N results
        return results[:limit]
