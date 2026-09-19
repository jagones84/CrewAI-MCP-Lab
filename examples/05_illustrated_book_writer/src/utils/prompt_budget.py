from __future__ import annotations

from collections import OrderedDict


ELLIPSIS = "\n...[trimmed]...\n"


def trim_text(
    text: str,
    max_chars: int,
    keep_end: bool = False,
    preserve_prefix_chars: int = 0,
) -> str:
    """Trim text to a hard character budget while keeping either the start or end."""
    if not text or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    if max_chars <= len(ELLIPSIS) + 16:
        return text[:max_chars]

    keep = max_chars - len(ELLIPSIS)
    if keep_end:
        prefix = text[: min(preserve_prefix_chars, max_chars // 3, len(text))]
        remaining = keep - len(prefix)
        if remaining <= 0:
            return text[:max_chars]
        return prefix + ELLIPSIS + text[-remaining:]
    return text[:keep] + ELLIPSIS


def trim_character_context(character_context: str, max_chars: int) -> str:
    """Preserve the character sheet structure while trimming each section."""
    if not character_context or max_chars <= 0:
        return ""
    if len(character_context) <= max_chars:
        return character_context

    lines = character_context.splitlines()
    header_lines = []
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_title or current_lines:
                sections.append((current_title, current_lines))
            current_title = line
            current_lines = [line]
        elif current_title:
            current_lines.append(line)
        else:
            header_lines.append(line)

    if current_title or current_lines:
        sections.append((current_title, current_lines))

    assembled: list[str] = []
    if header_lines:
        assembled.append("\n".join(header_lines))

    remaining = max_chars - sum(len(part) for part in assembled) - (2 if assembled and sections else 0)
    if remaining <= 0:
        return trim_text(character_context, max_chars)

    section_count = max(1, len(sections))
    per_section = max(400, remaining // section_count)

    kept_sections = []
    for _, section_lines in sections:
        section_text = "\n".join(section_lines).strip()
        kept_sections.append(trim_text(section_text, per_section))

    result_parts = assembled + kept_sections
    result = "\n\n".join(part for part in result_parts if part)
    return trim_text(result, max_chars)


def fit_story_context(
    *,
    master_plot: str,
    character_context: str,
    rag_context: str,
    recent_summary: str,
    world_bible_context: str,
    total_char_budget: int = 9000,
) -> OrderedDict[str, str]:
    """Trim story-context fields so the combined payload stays under a safe budget."""
    budgets = OrderedDict(
        [
            ("master_plot", int(total_char_budget * 0.30)),
            ("character_context", int(total_char_budget * 0.28)),
            ("rag_context", int(total_char_budget * 0.18)),
            ("recent_summary", int(total_char_budget * 0.12)),
            ("world_bible_context", total_char_budget),
        ]
    )
    budgets["world_bible_context"] -= sum(budgets.values()) - budgets["world_bible_context"]

    fitted = OrderedDict(
        [
            ("master_plot", trim_text(master_plot, budgets["master_plot"])),
            ("character_context", trim_character_context(character_context, budgets["character_context"])),
            ("rag_context", trim_text(rag_context, budgets["rag_context"], keep_end=True, preserve_prefix_chars=32)),
            ("recent_summary", trim_text(recent_summary, budgets["recent_summary"], keep_end=True, preserve_prefix_chars=32)),
            ("world_bible_context", trim_text(world_bible_context, budgets["world_bible_context"])),
        ]
    )

    total = sum(len(value) for value in fitted.values())
    if total <= total_char_budget:
        return fitted

    overflow = total - total_char_budget
    fitted["world_bible_context"] = trim_text(
        fitted["world_bible_context"],
        max(0, len(fitted["world_bible_context"]) - overflow),
    )
    return fitted


def fit_revision_context(
    *,
    draft_text: str,
    critique_feedback: str,
    world_bible_context: str,
    total_char_budget: int = 7000,
) -> OrderedDict[str, str]:
    """Trim critique/revision payloads so editor prompts stay within model limits."""
    effective_budget = min(total_char_budget, 2400)
    budgets = OrderedDict(
        [
            ("draft_text", int(effective_budget * 0.50)),
            ("critique_feedback", int(effective_budget * 0.20)),
            ("world_bible_context", effective_budget),
        ]
    )
    budgets["world_bible_context"] -= sum(budgets.values()) - budgets["world_bible_context"]

    fitted = OrderedDict(
        [
            ("draft_text", trim_text(draft_text, budgets["draft_text"], keep_end=True, preserve_prefix_chars=32)),
            ("critique_feedback", trim_text(critique_feedback, budgets["critique_feedback"], keep_end=True, preserve_prefix_chars=32)),
            ("world_bible_context", trim_text(world_bible_context, budgets["world_bible_context"])),
        ]
    )
    total = sum(len(value) for value in fitted.values())
    if total <= effective_budget:
        return fitted

    overflow = total - effective_budget
    trim_order = (
        ("world_bible_context", False, 0),
        ("critique_feedback", True, 32),
        ("draft_text", True, 32),
    )
    for key, keep_end, preserve_prefix_chars in trim_order:
        if overflow <= 0:
            break
        current = fitted[key]
        if not current:
            continue
        min_len = 0
        if preserve_prefix_chars:
            min_len = min(len(current), preserve_prefix_chars + len(ELLIPSIS) + 16)
        target_len = max(min_len, len(current) - overflow)
        fitted[key] = trim_text(
            current,
            target_len,
            keep_end=keep_end,
            preserve_prefix_chars=preserve_prefix_chars,
        )
        overflow = sum(len(value) for value in fitted.values()) - effective_budget

    return fitted


def fit_briefing_context(
    *,
    chapter_summary: str,
    rag_context: str,
    recent_summary: str,
    arc_summary: str,
    world_bible_context: str,
    total_char_budget: int = 4200,
) -> OrderedDict[str, str]:
    """Trim continuity-briefing inputs so manager prompts stay within a safer size."""
    effective_budget = min(total_char_budget, 4200)
    budgets = OrderedDict(
        [
            ("chapter_summary", int(effective_budget * 0.15)),
            ("rag_context", int(effective_budget * 0.22)),
            ("recent_summary", int(effective_budget * 0.14)),
            ("arc_summary", int(effective_budget * 0.27)),
            ("world_bible_context", effective_budget),
        ]
    )
    budgets["world_bible_context"] -= sum(budgets.values()) - budgets["world_bible_context"]

    fitted = OrderedDict(
        [
            ("chapter_summary", trim_text(chapter_summary, budgets["chapter_summary"], keep_end=True, preserve_prefix_chars=32)),
            ("rag_context", trim_text(rag_context, budgets["rag_context"], keep_end=True, preserve_prefix_chars=48)),
            ("recent_summary", trim_text(recent_summary, budgets["recent_summary"], keep_end=True, preserve_prefix_chars=32)),
            ("arc_summary", trim_text(arc_summary, budgets["arc_summary"], keep_end=True, preserve_prefix_chars=48)),
            ("world_bible_context", trim_text(world_bible_context, budgets["world_bible_context"])),
        ]
    )
    total = sum(len(value) for value in fitted.values())
    if total <= effective_budget:
        return fitted

    overflow = total - effective_budget
    trim_order = (
        ("arc_summary", True, 48),
        ("rag_context", True, 48),
        ("world_bible_context", False, 0),
        ("recent_summary", True, 32),
        ("chapter_summary", True, 32),
    )
    for key, keep_end, preserve_prefix_chars in trim_order:
        if overflow <= 0:
            break
        current = fitted[key]
        if not current:
            continue
        min_len = 0
        if preserve_prefix_chars:
            min_len = min(len(current), preserve_prefix_chars + len(ELLIPSIS) + 16)
        target_len = max(min_len, len(current) - overflow)
        fitted[key] = trim_text(
            current,
            target_len,
            keep_end=keep_end,
            preserve_prefix_chars=preserve_prefix_chars,
        )
        overflow = sum(len(value) for value in fitted.values()) - effective_budget

    return fitted


def fit_outline_context(
    *,
    master_plot: str,
    character_context: str,
    total_char_budget: int = 4200,
) -> OrderedDict[str, str]:
    """Trim outline-generation inputs so chapter-planning prompts stay compact."""
    effective_budget = min(total_char_budget, 3000)
    budgets = OrderedDict(
        [
            ("master_plot", int(effective_budget * 0.6)),
            ("character_context", effective_budget),
        ]
    )
    budgets["character_context"] -= sum(budgets.values()) - budgets["character_context"]

    fitted = OrderedDict(
        [
            ("master_plot", trim_text(master_plot, budgets["master_plot"], keep_end=True, preserve_prefix_chars=64)),
            ("character_context", trim_character_context(character_context, budgets["character_context"])),
        ]
    )
    total = sum(len(value) for value in fitted.values())
    if total <= effective_budget:
        return fitted

    overflow = total - effective_budget
    fitted["master_plot"] = trim_text(
        fitted["master_plot"],
        max(0, len(fitted["master_plot"]) - overflow),
        keep_end=True,
        preserve_prefix_chars=64,
    )
    return fitted


def fit_scene_prompt_inputs(
    *,
    scene_number: int,
    scene_name: str,
    action_text: str,
    setting_text: str,
    emotion_text: str,
    character_context: str,
    briefing_context: str,
    previous_scene_text: str,
    total_char_budget: int = 6500,
) -> OrderedDict[str, str]:
    """Trim scene-writing inputs while preserving the core scene instructions."""
    # CrewAI adds substantial wrapper/system prompt overhead around the task
    # description, so scene-writing prompts need a much tighter payload budget
    # than the raw model context window would suggest.
    effective_budget = min(total_char_budget, 3500)
    budgets = OrderedDict(
        [
            ("action_text", min(700, int(effective_budget * 0.18))),
            ("setting_text", min(500, int(effective_budget * 0.12))),
            ("emotion_text", min(220, int(effective_budget * 0.06))),
            ("character_context", int(effective_budget * 0.25)),
            ("briefing_context", int(effective_budget * 0.22)),
            ("previous_scene_text", effective_budget),
        ]
    )
    budgets["previous_scene_text"] -= sum(budgets.values()) - budgets["previous_scene_text"]

    fitted = OrderedDict(
        [
            ("action_text", trim_text(action_text, budgets["action_text"], preserve_prefix_chars=24)),
            ("setting_text", trim_text(setting_text, budgets["setting_text"], preserve_prefix_chars=24)),
            ("emotion_text", trim_text(emotion_text, budgets["emotion_text"], preserve_prefix_chars=24)),
            ("character_context", trim_character_context(character_context, budgets["character_context"])),
            ("briefing_context", trim_text(briefing_context, budgets["briefing_context"], keep_end=True, preserve_prefix_chars=48)),
            ("previous_scene_text", trim_text(previous_scene_text, budgets["previous_scene_text"], keep_end=True, preserve_prefix_chars=32)),
        ]
    )
    total = sum(len(value) for value in fitted.values())
    if total <= effective_budget:
        return fitted

    overflow = total - effective_budget
    trim_order = (
        ("briefing_context", True, 48),
        ("character_context", False, 0),
        ("action_text", False, 24),
        ("setting_text", False, 24),
        ("emotion_text", False, 24),
        ("previous_scene_text", True, 32),
    )
    for key, keep_end, preserve_prefix_chars in trim_order:
        if overflow <= 0:
            break
        current = fitted[key]
        if not current:
            continue
        min_len = 0
        if preserve_prefix_chars:
            min_len = min(len(current), preserve_prefix_chars + len(ELLIPSIS) + 16)
        target_len = max(min_len, len(current) - overflow)
        fitted[key] = trim_text(
            current,
            target_len,
            keep_end=keep_end,
            preserve_prefix_chars=preserve_prefix_chars,
        )
        overflow = sum(len(value) for value in fitted.values()) - effective_budget

    return fitted
