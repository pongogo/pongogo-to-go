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
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class InstructionFile:
    """Represents a single instruction file with metadata and content."""

    def __init__(self, file_path: Path, metadata: Dict, content: str):
        self.file_path = file_path
        self.metadata = metadata
        self.content = content

        # Extract common fields
        self.id = metadata.get('id', file_path.stem)
        self.version = metadata.get('version', '1.0.0')
        self.schema = metadata.get('schema', 'pongogo-instruction-v1')
        self.description = metadata.get('description', '')

        # IMP-004: Support 'domains' as alias for 'categories' (legacy field name)
        # IMP-005: Support 'patterns' as additional tags source
        self.tags = metadata.get('tags', [])
        patterns = metadata.get('patterns', [])
        if patterns and not self.tags:
            self.tags = patterns  # Use patterns as tags if tags empty

        self.categories = metadata.get('categories', [])
        domains = metadata.get('domains', [])
        if domains and not self.categories:
            self.categories = domains  # Use domains as categories if categories empty

        # IMP-006: Support 'applies_to' as top-level glob patterns
        self.routing = metadata.get('routing', {})
        applies_to = metadata.get('applies_to', [])
        if applies_to:
            # Merge applies_to into routing.applyTo.globs
            if 'applyTo' not in self.routing:
                self.routing['applyTo'] = {}
            existing_globs = self.routing['applyTo'].get('globs', [])
            # Combine existing globs with applies_to, avoiding duplicates
            merged_globs = list(set(existing_globs + applies_to))
            self.routing['applyTo']['globs'] = merged_globs

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'file_path': str(self.file_path),
            'id': self.id,
            'version': self.version,
            'schema': self.schema,
            'description': self.description,
            'tags': self.tags,
            'categories': self.categories,
            'routing': self.routing,
            'content': self.content,
            'metadata': self.metadata
        }


class InstructionHandler:
    """Handles loading, parsing, and querying instruction files."""

    def __init__(self, knowledge_base_path: Path):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.instructions: Dict[str, InstructionFile] = {}
        self.by_category: Dict[str, List[str]] = {}

        logger.info(f"InstructionHandler initialized with path: {self.knowledge_base_path}")

    def load_instructions(self) -> int:
        """
        Load all instruction files from knowledge base.

        Returns:
            Number of instruction files loaded
        """
        count = 0

        if not self.knowledge_base_path.exists():
            logger.error(f"Knowledge base path does not exist: {self.knowledge_base_path}")
            return count

        # Find all .instructions.md files recursively
        for file_path in self.knowledge_base_path.rglob("*.instructions.md"):
            try:
                instruction = self._parse_instruction_file(file_path)
                if instruction:
                    self.instructions[instruction.id] = instruction

                    # Index by category
                    for category in instruction.categories:
                        if category not in self.by_category:
                            self.by_category[category] = []
                        self.by_category[category].append(instruction.id)

                    count += 1
                    logger.debug(f"Loaded instruction: {instruction.id} from {file_path}")

            except Exception as e:
                logger.error(f"Error loading instruction file {file_path}: {e}", exc_info=True)

        logger.info(f"Loaded {count} instruction files")
        return count

    def _parse_instruction_file(self, file_path: Path) -> Optional[InstructionFile]:
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
            content = file_path.read_text(encoding='utf-8')

            # Check for YAML frontmatter
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)

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

            # IMP-004: Merge categories from multiple sources
            # IMPORTANT: Directory-based category MUST be first for ground truth matching
            # Ground truth uses format "directory/name" so first category must match directory
            categories = []
            seen = set()

            # 1. Directory-based category FIRST (critical for ground truth matching)
            dir_category = file_path.parent.name
            if dir_category != 'pongogo':
                categories.append(dir_category)
                seen.add(dir_category)

            # 2. Add explicit categories
            for cat in metadata.get('categories', []):
                if cat not in seen:
                    categories.append(cat)
                    seen.add(cat)

            # 3. Add domains as additional categories (legacy field name)
            for cat in metadata.get('domains', []):
                if cat not in seen:
                    categories.append(cat)
                    seen.add(cat)

            # Store merged categories (directory first, then explicit, then domains)
            metadata['categories'] = categories

            # Create InstructionFile
            instruction = InstructionFile(
                file_path=file_path,
                metadata=metadata,
                content=markdown_content.strip()
            )

            return instruction

        except Exception as e:
            logger.error(f"Error parsing instruction file {file_path}: {e}", exc_info=True)
            return None

    def get_instruction(self, category: str, name: str) -> Optional[Dict]:
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
                if category in instruction.categories or category == instruction.file_path.parent.name:
                    return instruction.to_dict()

        logger.warning(f"Instruction not found: {category}/{name}")
        return None

    def get_instructions_by_category(self, category: str) -> List[Dict]:
        """
        Get all instruction files in a category.

        Args:
            category: Category name

        Returns:
            List of instruction dictionaries
        """
        instruction_ids = self.by_category.get(category, [])
        return [self.instructions[id].to_dict() for id in instruction_ids if id in self.instructions]

    def get_all_instructions(self) -> List[Dict]:
        """
        Get all instruction files.

        Returns:
            List of all instruction dictionaries
        """
        return [instruction.to_dict() for instruction in self.instructions.values()]

    def search_instructions(self, query: str, limit: int = 10) -> List[Dict]:
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
                result['search_score'] = score
                result['search_matches'] = matches
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x['search_score'], reverse=True)

        # Return top N results
        return results[:limit]
