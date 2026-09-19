from src.agents.tasks import BookTasks
from src.services.characters import CharacterManager


def test_detect_gender_prefers_explicit_gender_field_over_pronouns(tmp_path):
    manager = CharacterManager(str(tmp_path))

    background = (
        "Role: Protagonist\n"
        "Gender: male\n"
        "Appearance: Tall scholar with sharp features.\n"
        "Personality: Quiet and analytical, her restraint is often misunderstood.\n"
    )

    tags = manager._detect_gender(background)

    assert "male" in tags
    assert "female" not in tags


def test_character_portrait_task_includes_explicit_gender_context():
    task = BookTasks().character_portrait_task(
        None,
        {
            "name": "Thorne",
            "role": "Protagonist",
            "gender": "male",
            "appearance": "Tall, pale, black-haired man.",
            "personality": "Reserved and obsessive.",
        },
    )

    assert "Gender: male" in task.description
    assert "authoritative" in task.description.lower()
