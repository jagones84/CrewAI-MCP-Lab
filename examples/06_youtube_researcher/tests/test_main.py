import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("example06_main", MODULE_PATH)
main_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main_module)


def test_extract_youtube_urls_returns_two_unique_links():
    text = """
    Here are two strong candidates:
    https://www.youtube.com/watch?v=aaa111
    https://www.youtube.com/watch?v=bbb222
    https://www.youtube.com/watch?v=aaa111
    """

    urls = main_module.extract_youtube_urls(text, expected_count=2)

    assert urls == [
        "https://www.youtube.com/watch?v=aaa111",
        "https://www.youtube.com/watch?v=bbb222",
    ]


def test_transcribe_video_urls_calls_tool_directly(tmp_path):
    calls = []

    class DummyTool:
        def run(self, **kwargs):
            calls.append(kwargs)
            return f"Transcript for {kwargs['youtube_url']}"

    urls = [
        "https://www.youtube.com/watch?v=aaa111",
        "https://www.youtube.com/watch?v=bbb222",
    ]

    combined = main_module.transcribe_video_urls(
        urls=urls,
        transcription_tool=DummyTool(),
        output_path=str(tmp_path),
    )

    assert len(calls) == 2
    assert calls[0]["youtube_url"] == urls[0]
    assert calls[0]["language"] == "en"
    assert calls[1]["youtube_url"] == urls[1]
    assert "Transcript for https://www.youtube.com/watch?v=aaa111" in combined
    assert "Transcript for https://www.youtube.com/watch?v=bbb222" in combined


def test_transcribe_video_urls_reads_saved_transcription_files(tmp_path):
    class DummyTool:
        def run(self, **kwargs):
            output_file = tmp_path / f"{kwargs['output_name']}.txt"
            output_file.write_text(f"FULL TEXT FOR {kwargs['youtube_url']}", encoding="utf-8")
            return "Success! Transcription saved."

    urls = ["https://www.youtube.com/watch?v=aaa111"]

    combined = main_module.transcribe_video_urls(
        urls=urls,
        transcription_tool=DummyTool(),
        output_path=str(tmp_path),
    )

    assert "FULL TEXT FOR https://www.youtube.com/watch?v=aaa111" in combined
