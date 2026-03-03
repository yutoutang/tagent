"""Skill loading and management for pi-coding.

Converted from TypeScript core/skills.ts
Implements the Agent Skills standard: https://agentskills.io/specification
"""
import os
import re
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from .diagnostics import ResourceDiagnostic, ResourceCollision
from ..utils.frontmatter import parse_frontmatter


# Constants per Agent Skills spec
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

# Ignore file names to check
IGNORE_FILE_NAMES = [".gitignore", ".ignore", ".fdignore"]


@dataclass
class SkillFrontmatter:
    """Parsed frontmatter from a skill file."""
    name: Optional[str] = None
    description: Optional[str] = None
    disable_model_invocation: bool = False


@dataclass
class Skill:
    """A loaded skill definition."""
    name: str
    description: str
    file_path: str
    base_dir: str
    source: str  # "user", "project", or "path"
    disable_model_invocation: bool = False


@dataclass
class LoadSkillsResult:
    """Result from loading skills."""
    skills: List[Skill] = field(default_factory=list)
    diagnostics: List[ResourceDiagnostic] = field(default_factory=list)


@dataclass
class LoadSkillsOptions:
    """Options for loading skills."""
    cwd: Optional[Path] = None
    agent_dir: Optional[Path] = None
    skill_paths: Optional[List[str]] = None
    include_defaults: bool = True


# =============================================================================
# Validation Functions
# =============================================================================

def validate_name(name: str, parent_dir_name: str) -> List[str]:
    """
    Validate skill name per Agent Skills spec.

    Args:
        name: The skill name to validate
        parent_dir_name: Expected name (parent directory name)

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []

    if name != parent_dir_name:
        errors.append(f'name "{name}" does not match parent directory "{parent_dir_name}"')

    if len(name) > MAX_NAME_LENGTH:
        errors.append(f'name exceeds {MAX_NAME_LENGTH} characters ({len(name)})')

    if not re.match(r'^[a-z0-9-]+$', name):
        errors.append('name contains invalid characters (must be lowercase a-z, 0-9, hyphens only)')

    if name.startswith('-') or name.endswith('-'):
        errors.append('name must not start or end with a hyphen')

    if '--' in name:
        errors.append('name must not contain consecutive hyphens')

    return errors


def validate_description(description: Optional[str]) -> List[str]:
    """
    Validate description per Agent Skills spec.

    Args:
        description: The description to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []

    if not description or description.strip() == '':
        errors.append('description is required')
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f'description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)})')

    return errors


# =============================================================================
# XML Formatting
# =============================================================================

def _escape_xml(s: str) -> str:
    """Escape special XML characters."""
    return (
        s.replace('&', '&amp;')
         .replace('<', '&lt;')
         .replace('>', '&gt;')
         .replace('"', '&quot;')
         .replace("'", '&apos;')
    )


def format_skills_for_prompt(skills: List[Skill]) -> str:
    """
    Format skills for inclusion in a system prompt.

    Uses XML format per Agent Skills standard.
    See: https://agentskills.io/integrate-skills

    Skills with disable_model_invocation=True are excluded from the prompt
    (they can only be invoked explicitly via /skill:name commands).

    Args:
        skills: List of skills to format

    Returns:
        XML-formatted string for system prompt
    """
    visible_skills = [s for s in skills if not s.disable_model_invocation]

    if not visible_skills:
        return ''

    lines = [
        '',
        '',
        'The following skills provide specialized instructions for specific tasks.',
        'Use the read tool to load a skill\'s file when the task matches its description.',
        'When a skill file references a relative path, resolve it against the skill directory (parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.',
        '',
        '<available_skills>',
    ]

    for skill in visible_skills:
        lines.append('  <skill>')
        lines.append(f'    <name>{_escape_xml(skill.name)}</name>')
        lines.append(f'    <description>{_escape_xml(skill.description)}</description>')
        lines.append(f'    <location>{_escape_xml(skill.file_path)}</location>')
        lines.append('  </skill>')

    lines.append('</available_skills>')

    return '\n'.join(lines)


# =============================================================================
# Ignore File Handling
# =============================================================================

def _to_posix_path(p: str) -> str:
    """Convert path to POSIX format (forward slashes)."""
    return p.replace(os.sep, '/')


def _prefix_ignore_pattern(line: str, prefix: str) -> Optional[str]:
    """
    Prefix an ignore pattern with a directory prefix.

    Args:
        line: The ignore pattern line
        prefix: The directory prefix to add

    Returns:
        Prefixed pattern or None if line should be skipped
    """
    trimmed = line.strip()
    if not trimmed:
        return None
    if trimmed.startswith('#') and not trimmed.startswith('\\#'):
        return None

    pattern = line
    negated = False

    if pattern.startswith('!'):
        negated = True
        pattern = pattern[1:]
    elif pattern.startswith('\\!'):
        pattern = pattern[1:]

    if pattern.startswith('/'):
        pattern = pattern[1:]

    prefixed = f'{prefix}{pattern}' if prefix else pattern
    return f'!{prefixed}' if negated else prefixed


def _collect_ignore_patterns(dir_path: Path, root_dir: Path) -> List[str]:
    """
    Collect ignore patterns from ignore files in a directory.

    Args:
        dir_path: Directory to check for ignore files
        root_dir: Root directory for relative path calculation

    Returns:
        List of ignore patterns
    """
    patterns: List[str] = []

    try:
        relative_dir = root_dir.relative_to(dir_path)
        prefix = f'{_to_posix_path(str(relative_dir))}/'
    except ValueError:
        # dir_path is not relative to root_dir
        prefix = ''

    for filename in IGNORE_FILE_NAMES:
        ignore_path = dir_path / filename
        if not ignore_path.exists():
            continue

        try:
            content = ignore_path.read_text(encoding='utf-8')
            for line in content.splitlines():
                pattern = _prefix_ignore_pattern(line, prefix)
                if pattern:
                    patterns.append(pattern)
        except Exception:
            continue

    return patterns


def _should_ignore_path(path: Path, relative_path: str, patterns: List[str]) -> bool:
    """
    Check if a path should be ignored based on patterns.

    Simple implementation - does not handle all .gitignore patterns.
    For full support, consider using the pathspec library.

    Args:
        path: The path to check
        relative_path: Relative path from root
        patterns: List of ignore patterns

    Returns:
        True if path should be ignored
    """
    if not patterns:
        return False

    posix_path = _to_posix_path(relative_path)

    for pattern in patterns:
        if pattern.startswith('!'):
            # Negation pattern - not fully implemented
            continue

        # Simple glob matching
        if fnmatch.fnmatch(posix_path, pattern):
            return True
        # Also check with trailing slash for directories
        if fnmatch.fnmatch(f'{posix_path}/', pattern):
            return True

    return False


# =============================================================================
# Skill Loading Functions
# =============================================================================

def _load_skill_from_file(
    file_path: Path,
    source: str
) -> Tuple[Optional[Skill], List[ResourceDiagnostic]]:
    """
    Load a single skill from a markdown file.

    Args:
        file_path: Path to the skill markdown file
        source: Source identifier (user, project, path)

    Returns:
        Tuple of (Skill or None, list of diagnostics)
    """
    diagnostics: List[ResourceDiagnostic] = []

    try:
        raw_content = file_path.read_text(encoding='utf-8')
        parsed = parse_frontmatter(raw_content)
        frontmatter_data = parsed.frontmatter

        # Parse frontmatter into typed object
        frontmatter = SkillFrontmatter(
            name=frontmatter_data.get('name'),
            description=frontmatter_data.get('description'),
            disable_model_invocation=frontmatter_data.get('disable-model-invocation', False),
        )

        skill_dir = file_path.parent
        parent_dir_name = skill_dir.name

        # Validate description
        desc_errors = validate_description(frontmatter.description)
        for error in desc_errors:
            diagnostics.append(ResourceDiagnostic(
                type='warning',
                message=error,
                path=str(file_path),
            ))

        # Use name from frontmatter, or fall back to parent directory name
        name = frontmatter.name or parent_dir_name

        # Validate name
        name_errors = validate_name(name, parent_dir_name)
        for error in name_errors:
            diagnostics.append(ResourceDiagnostic(
                type='warning',
                message=error,
                path=str(file_path),
            ))

        # Still load the skill even with warnings (unless description is completely missing)
        if not frontmatter.description or frontmatter.description.strip() == '':
            return None, diagnostics

        return Skill(
            name=name,
            description=frontmatter.description,
            file_path=str(file_path),
            base_dir=str(skill_dir),
            source=source,
            disable_model_invocation=frontmatter.disable_model_invocation,
        ), diagnostics

    except Exception as e:
        message = str(e) if str(e) else 'failed to parse skill file'
        diagnostics.append(ResourceDiagnostic(
            type='warning',
            message=message,
            path=str(file_path),
        ))
        return None, diagnostics


def load_skills_from_dir(
    dir_path: Path,
    source: str,
    include_root_files: bool = True,
    ignore_patterns: Optional[List[str]] = None,
    root_dir: Optional[Path] = None
) -> LoadSkillsResult:
    """
    Load skills from a directory.

    Discovery rules:
    - Direct .md children in the root (when include_root_files=True)
    - Recursive SKILL.md under subdirectories (when include_root_files=False)

    Args:
        dir_path: Directory to scan for skills
        source: Source identifier (user, project, path)
        include_root_files: Whether to include .md files in root
        ignore_patterns: Existing ignore patterns to extend
        root_dir: Root directory for relative path calculation

    Returns:
        LoadSkillsResult with skills and diagnostics
    """
    skills: List[Skill] = []
    diagnostics: List[ResourceDiagnostic] = []

    if not dir_path.exists():
        return LoadSkillsResult(skills=skills, diagnostics=diagnostics)

    root = root_dir or dir_path

    # Collect ignore patterns from this directory
    patterns = list(ignore_patterns) if ignore_patterns else []
    new_patterns = _collect_ignore_patterns(dir_path, root)
    patterns.extend(new_patterns)

    try:
        entries = list(dir_path.iterdir())
    except Exception:
        return LoadSkillsResult(skills=skills, diagnostics=diagnostics)

    for entry in entries:
        name = entry.name

        # Skip hidden files
        if name.startswith('.'):
            continue

        # Skip node_modules
        if name == 'node_modules':
            continue

        try:
            # Handle symlinks
            if entry.is_symlink():
                try:
                    resolved = entry.resolve()
                    is_dir = resolved.is_dir()
                    is_file = resolved.is_file()
                except Exception:
                    continue
            else:
                is_dir = entry.is_dir()
                is_file = entry.is_file()
        except Exception:
            continue

        # Calculate relative path for ignore checking
        try:
            relative_path = str(entry.relative_to(root))
        except ValueError:
            relative_path = name

        # Check if ignored
        ignore_path = f'{relative_path}/' if is_dir else relative_path
        if _should_ignore_path(entry, ignore_path, patterns):
            continue

        if is_dir:
            # Recursively scan subdirectories (with include_root_files=False)
            sub_result = load_skills_from_dir(
                entry, source, False, patterns, root
            )
            skills.extend(sub_result.skills)
            diagnostics.extend(sub_result.diagnostics)
            continue

        if not is_file:
            continue

        # Check if this is a skill file we should load
        is_root_md = include_root_files and name.endswith('.md')
        is_skill_md = not include_root_files and name == 'SKILL.md'

        if not is_root_md and not is_skill_md:
            continue

        # Load the skill
        skill, skill_diagnostics = _load_skill_from_file(entry, source)
        diagnostics.extend(skill_diagnostics)

        if skill:
            skills.append(skill)

    return LoadSkillsResult(skills=skills, diagnostics=diagnostics)


def _normalize_path(input_path: str, cwd: Path) -> Path:
    """Normalize a path, expanding ~ and resolving relative paths."""
    trimmed = input_path.strip()

    if trimmed == '~':
        return Path.home()
    elif trimmed.startswith('~/'):
        return Path.home() / trimmed[2:]
    elif trimmed.startswith('~'):
        return Path.home() / trimmed[1:]

    normalized = Path(trimmed)
    if normalized.is_absolute():
        return normalized
    return cwd / trimmed


def _is_under_path(target: Path, root: Path) -> bool:
    """Check if target path is under root path."""
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def load_skills(options: Optional[LoadSkillsOptions] = None) -> LoadSkillsResult:
    """
    Load skills from all configured locations.

    Returns skills and any validation diagnostics.

    Discovery order (later overrides earlier):
    1. ~/.pi/agent/skills/ (user skills) - if include_defaults
    2. .pi/skills/ (project skills) - if include_defaults
    3. Explicit skill_paths from options

    Args:
        options: Loading options

    Returns:
        LoadSkillsResult with skills and diagnostics
    """
    if options is None:
        options = LoadSkillsOptions()

    cwd = options.cwd or Path.cwd()
    agent_dir = options.agent_dir or _get_default_agent_dir()
    skill_paths = options.skill_paths or []
    include_defaults = options.include_defaults

    skill_map: Dict[str, Skill] = {}
    real_path_set: set = set()
    all_diagnostics: List[ResourceDiagnostic] = []
    collision_diagnostics: List[ResourceDiagnostic] = []

    def add_skills(result: LoadSkillsResult) -> None:
        """Add skills from a loading result to the map."""
        nonlocal all_diagnostics, collision_diagnostics

        all_diagnostics.extend(result.diagnostics)

        for skill in result.skills:
            # Resolve symlinks to detect duplicate files
            try:
                real_path = str(Path(skill.file_path).resolve())
            except Exception:
                real_path = skill.file_path

            # Skip silently if we've already loaded this exact file (via symlink)
            if real_path in real_path_set:
                continue

            existing = skill_map.get(skill.name)
            if existing:
                collision_diagnostics.append(ResourceDiagnostic(
                    type='collision',
                    message=f'name "{skill.name}" collision',
                    path=skill.file_path,
                    collision=ResourceCollision(
                        resource_type='skill',
                        name=skill.name,
                        winner_path=existing.file_path,
                        loser_path=skill.file_path,
                    ),
                ))
            else:
                skill_map[skill.name] = skill
                real_path_set.add(real_path)

    # Load from default locations
    if include_defaults:
        user_skills_dir = agent_dir / 'skills'
        project_skills_dir = cwd / '.pi' / 'skills'

        add_skills(load_skills_from_dir(user_skills_dir, 'user', True))
        add_skills(load_skills_from_dir(project_skills_dir, 'project', True))

    # Helper to determine source for explicit paths
    user_skills_dir = agent_dir / 'skills'
    project_skills_dir = cwd / '.pi' / 'skills'

    def get_source(resolved_path: Path) -> str:
        if not include_defaults:
            if _is_under_path(resolved_path, user_skills_dir):
                return 'user'
            if _is_under_path(resolved_path, project_skills_dir):
                return 'project'
        return 'path'

    # Load from explicit skill paths
    for raw_path in skill_paths:
        resolved_path = _normalize_path(raw_path, cwd)

        if not resolved_path.exists():
            all_diagnostics.append(ResourceDiagnostic(
                type='warning',
                message='skill path does not exist',
                path=str(resolved_path),
            ))
            continue

        try:
            source = get_source(resolved_path)

            if resolved_path.is_dir():
                add_skills(load_skills_from_dir(resolved_path, source, True))
            elif resolved_path.is_file() and resolved_path.suffix == '.md':
                skill, skill_diagnostics = _load_skill_from_file(resolved_path, source)
                all_diagnostics.extend(skill_diagnostics)
                if skill:
                    add_skills(LoadSkillsResult(skills=[skill]))
            else:
                all_diagnostics.append(ResourceDiagnostic(
                    type='warning',
                    message='skill path is not a markdown file',
                    path=str(resolved_path),
                ))
        except Exception as e:
            message = str(e) if str(e) else 'failed to read skill path'
            all_diagnostics.append(ResourceDiagnostic(
                type='warning',
                message=message,
                path=str(resolved_path),
            ))

    return LoadSkillsResult(
        skills=list(skill_map.values()),
        diagnostics=all_diagnostics + collision_diagnostics,
    )


def _get_default_agent_dir() -> Path:
    """Get the default agent configuration directory."""
    from ..config import get_agent_dir
    return get_agent_dir()


__all__ = [
    "SkillFrontmatter",
    "Skill",
    "LoadSkillsResult",
    "LoadSkillsOptions",
    "validate_name",
    "validate_description",
    "format_skills_for_prompt",
    "load_skills_from_dir",
    "load_skills",
]
