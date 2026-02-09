from crewai import Task

class YoutubeResearcherTasks:
    def find_videos(self, agent):
        return Task(
            description='Search for "recent cancer cure breakthroughs 2024 2025 documentary English" on YouTube using the web search tool. Find exactly 2 relevant videos that are in English. Return ONLY the 2 YouTube URLs.',
            expected_output='A list of 2 YouTube URLs.',
            agent=agent
        )

    def transcribe_videos(self, agent, context_task):
        # Calculate absolute path to outputs folder
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        output_path = os.path.join(repo_root, "examples", "06_youtube_researcher", "outputs")
        
        return Task(
            description=f'Take the 2 YouTube URLs found. Use the "transcribe_youtube_video" tool to download and transcribe each video. IMPORTANT: You MUST set the `output_path` parameter to exactly "{output_path}" AND set the `language` parameter to "en" to force English transcription. Pass the full transcription text to the next task.',
            expected_output='The full text transcription of the 2 videos.',
            context=[context_task],
            agent=agent
        )

    def summarize_videos(self, agent, context_task):
        return Task(
            description='Analyze the transcriptions provided. Write a comprehensive summary of the cancer cure breakthroughs discussed. Highlight key findings, researchers mentioned, and potential impact.',
            expected_output='A detailed summary report of the videos.',
            context=[context_task],
            agent=agent
        )
