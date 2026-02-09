import os
from crewai import Agent, LLM

class YoutubeResearcherAgents:
    def __init__(self):
        # Debug API Key
        key = os.getenv("OPENAI_API_KEY")
        print(f"DEBUG: API Key loaded: {key[:5]}...{key[-5:] if key else 'None'}")
        
        self.llm = LLM(
            model="openai/google/gemini-2.0-flash-001", 
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
        )

    def researcher(self, tools):
        return Agent(
            role='Video Researcher',
            goal='Find 2 recent and relevant videos about cancer cures on YouTube',
            backstory='Expert researcher in medical topics on YouTube.',
            tools=tools,
            llm=self.llm,
            verbose=True
        )

    def transcriber(self, tools):
        return Agent(
            role='Video Transcriber',
            goal='Download and transcribe YouTube videos',
            backstory='Expert in converting video audio to text using advanced AI models.',
            tools=tools,
            llm=self.llm,
            verbose=True
        )

    def summarizer(self):
        return Agent(
            role='Content Summarizer',
            goal='Summarize video transcriptions into concise insights',
            backstory='Expert in synthesizing complex medical information into easy-to-understand summaries.',
            llm=self.llm,
            verbose=True
        )
