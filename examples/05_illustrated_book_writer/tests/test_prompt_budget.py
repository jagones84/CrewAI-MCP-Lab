from src.agents.tasks import BookTasks
from src.utils.prompt_budget import (
    fit_briefing_context,
    fit_outline_context,
    fit_revision_context,
    fit_scene_prompt_inputs,
    fit_story_context,
)


def test_fit_story_context_trims_large_inputs_under_budget():
    master_plot = "# MASTER PLOT\n" + ("plot detail " * 2000)
    character_context = "\n".join(
        [
            "=== CHARACTER REFERENCE SHEET ===",
            "## Thorne",
            "Appearance: " + ("gaunt apprentice " * 500),
            "Personality: " + ("silent obsessive " * 500),
            "## Elara",
            "Appearance: " + ("predatory noblewoman " * 500),
            "Personality: " + ("ruthless zealot " * 500),
        ]
    )
    rag_context = "RAG: " + ("memory fragment " * 1200)
    recent_summary = "SUMMARY: " + ("chapter summary " * 600)
    world_bible = "BIBLE: " + ("rule " * 900)

    fitted = fit_story_context(
        master_plot=master_plot,
        character_context=character_context,
        rag_context=rag_context,
        recent_summary=recent_summary,
        world_bible_context=world_bible,
        total_char_budget=9000,
    )

    assert sum(len(value) for value in fitted.values()) <= 9000
    assert "MASTER PLOT" in fitted["master_plot"]
    assert "## Thorne" in fitted["character_context"]
    assert "## Elara" in fitted["character_context"]
    assert "RAG:" in fitted["rag_context"]
    assert "SUMMARY:" in fitted["recent_summary"]
    assert "BIBLE:" in fitted["world_bible_context"]


def test_fit_revision_context_trims_draft_and_feedback_under_budget():
    draft_text = "DRAFT: " + ("dense scene prose " * 1800)
    critique_feedback = "CRITIQUE: " + ("specific rewrite note " * 1500)
    world_bible = "BIBLE: " + ("style rule " * 1200)

    fitted = fit_revision_context(
        draft_text=draft_text,
        critique_feedback=critique_feedback,
        world_bible_context=world_bible,
        total_char_budget=7000,
    )

    assert sum(len(value) for value in fitted.values()) <= 7000
    assert "DRAFT:" in fitted["draft_text"]
    assert "CRITIQUE:" in fitted["critique_feedback"]
    assert "BIBLE:" in fitted["world_bible_context"]


def test_fit_scene_prompt_inputs_trims_scene_payload_under_budget():
    character_context = "\n".join(
        [
            "=== CHARACTER REFERENCE SHEET ===",
            "## Thorne",
            "Appearance: " + ("scarred alchemist " * 500),
            "## Lyra",
            "Appearance: " + ("white-eyed seer " * 500),
            "## Elara",
            "Appearance: " + ("violet-eyed scholar " * 500),
        ]
    )
    briefing = "WRITER'S BRIEFING: " + ("continuity fact " * 1200)
    previous_text = "PREVIOUS TEXT: " + ("prior scene " * 900)

    fitted = fit_scene_prompt_inputs(
        scene_number=1,
        scene_name="The Discovery",
        action_text="Action: " + ("ancient scroll " * 200),
        setting_text="Setting: " + ("dusty study " * 200),
        emotion_text="Emotion: " + ("uneasy curiosity " * 120),
        character_context=character_context,
        briefing_context=briefing,
        previous_scene_text=previous_text,
        total_char_budget=6500,
    )

    assert sum(len(value) for value in fitted.values()) <= 6500
    assert "## Thorne" in fitted["character_context"]
    assert "Action:" in fitted["action_text"]
    assert "WRITER'S BRIEFING:" in fitted["briefing_context"]
    assert "PREVIOUS TEXT:" in fitted["previous_scene_text"]


def test_fit_briefing_context_trims_payload_under_budget():
    fitted = fit_briefing_context(
        chapter_summary="CHAPTER: " + ("chapter beat " * 300),
        rag_context="RAG: " + ("memory fragment " * 1600),
        recent_summary="RECENT: " + ("prior chapter " * 900),
        arc_summary="ARC: " + ("master plot " * 2200),
        world_bible_context="BIBLE: " + ("world law " * 1200),
        total_char_budget=4200,
    )

    assert sum(len(value) for value in fitted.values()) <= 4200
    assert "CHAPTER:" in fitted["chapter_summary"]
    assert "RAG:" in fitted["rag_context"]
    assert "RECENT:" in fitted["recent_summary"]
    assert "ARC:" in fitted["arc_summary"]
    assert "BIBLE:" in fitted["world_bible_context"]


def test_briefing_task_prompt_stays_under_safe_size_budget():
    fitted = fit_briefing_context(
        chapter_summary="CHAPTER: " + ("chapter beat " * 300),
        rag_context="RAG: " + ("memory fragment " * 1600),
        recent_summary="RECENT: " + ("prior chapter " * 900),
        arc_summary="ARC: " + ("master plot " * 2200),
        world_bible_context="BIBLE: " + ("world law " * 1200),
        total_char_budget=4200,
    )

    task = BookTasks().briefing_task(
        None,
        {
            "chapter": 2,
            "title": "The Hungering Formula",
            "summary": fitted["chapter_summary"],
        },
        fitted["rag_context"],
        {2: fitted["recent_summary"], 1: fitted["arc_summary"]},
        fitted["world_bible_context"],
    )

    assert len(task.description) <= 5200


def test_fit_outline_context_trims_payload_under_budget():
    fitted = fit_outline_context(
        master_plot="# MASTER PLOT\n" + ("plot detail " * 2600),
        character_context="\n".join(
            [
                "=== CHARACTER REFERENCE SHEET ===",
                "## Thorne",
                "Appearance: " + ("scarred alchemist " * 700),
                "Personality: " + ("grim and obsessive " * 500),
                "## Aurelius",
                "Appearance: " + ("vault keeper " * 700),
                "Personality: " + ("measured and secretive " * 500),
            ]
        ),
        total_char_budget=4200,
    )

    assert sum(len(value) for value in fitted.values()) <= 4200
    assert "MASTER PLOT" in fitted["master_plot"]
    assert "## Thorne" in fitted["character_context"]


def test_structure_task_prompt_stays_under_safe_size_budget():
    fitted = fit_outline_context(
        master_plot="# MASTER PLOT\n" + ("plot detail " * 2600),
        character_context="\n".join(
            [
                "=== CHARACTER REFERENCE SHEET ===",
                "## Thorne",
                "Appearance: " + ("scarred alchemist " * 700),
                "Personality: " + ("grim and obsessive " * 500),
                "## Aurelius",
                "Appearance: " + ("vault keeper " * 700),
                "Personality: " + ("measured and secretive " * 500),
            ]
        ),
        total_char_budget=4200,
    )

    task = BookTasks().structure_task(
        None,
        genre="Dark Fantasy - Theme: Legacy",
        title="The Alchemist's Shadow",
        chapter_count=2,
        master_plot=fitted["master_plot"],
        character_context=fitted["character_context"],
    )

    assert len(task.description) <= 4200


def test_write_scene_prompt_stays_under_safe_size_budget():
    character_context = "\n".join(
        [
            "=== CHARACTER REFERENCE SHEET ===",
            "## Thorne",
            "Appearance: " + ("scarred alchemist " * 500),
            "Personality: " + ("grim and obsessive " * 300),
            "## Eldrin",
            "Appearance: " + ("crimson scholar " * 500),
            "Personality: " + ("guarded and manipulative " * 300),
        ]
    )
    briefing = "Writer's Briefing for Chapter 2: " + ("continuity fact " * 1200)

    fitted = fit_scene_prompt_inputs(
        scene_number=1,
        scene_name="The Hungering Shadow",
        action_text="Action: " + ("ancient scroll " * 200),
        setting_text="Setting: " + ("dusty library " * 200),
        emotion_text="Emotion: " + ("horrified realization " * 120),
        character_context=character_context,
        briefing_context=briefing,
        previous_scene_text="",
        total_char_budget=6500,
    )

    task = BookTasks().write_scene_task(
        None,
        {
            "number": 1,
            "name": "The Hungering Shadow",
            "description": fitted["action_text"],
            "setting": fitted["setting_text"],
            "emotional_beat": fitted["emotion_text"],
        },
        fitted["briefing_context"],
        fitted["previous_scene_text"],
        character_context=fitted["character_context"],
        word_count=700,
    )

    assert len(task.description) <= 5000


def test_critique_scene_prompt_stays_under_safe_size_budget():
    fitted = fit_revision_context(
        draft_text="DRAFT: " + ("dense scene prose " * 2200),
        critique_feedback="",
        world_bible_context="BIBLE: " + ("style rule " * 1800),
        total_char_budget=7000,
    )

    task = BookTasks().critique_scene_task(
        None,
        fitted["draft_text"],
        fitted["world_bible_context"],
    )

    assert len(task.description) <= 4200
