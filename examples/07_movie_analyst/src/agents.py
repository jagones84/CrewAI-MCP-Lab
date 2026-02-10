from crewai import Agent

class MovieAnalystAgents:
    def movie_curator(self, tools, llm=None):
        return Agent(
            role='Movie Curator',
            goal='Discover content matching specific mood/criteria and analyze scores deeply',
            backstory='You are a discerning film curator. You don\'t just look for "good" movies; you look for a specific *vibe* (mood) and fit. You pay attention to the difference between Critic Scores (Rotten Tomatoes Tomatometer/Metacritic) and Audience Scores (IMDb/Popcornmeter) to find hidden gems.',
            tools=tools,
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def streaming_specialist(self, tools, llm=None):
        return Agent(
            role='Streaming Specialist',
            goal='Find accurate streaming availability for movies/series in a specific country',
            backstory='You are an expert in global streaming markets (Netflix, Prime, etc.). You know exactly which service holds the rights to a title in a specific region (e.g., Italy vs USA). You prioritize "included" (flatrate) options over rentals.',
            tools=tools,
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def link_verifier(self, tools, llm=None):
        return Agent(
            role='Link Verification Expert',
            goal='Ensure every single link works and is not a 404 or generic homepage',
            backstory='You are a cynical QA specialist. You assume every link provided by others is broken until proven otherwise. You use search tools to find the ACTUAL, working watch page. You know that "hbo.com/originals/show-name" is often a broken guess. You verify specific regional availability (e.g. Italy).',
            tools=tools,
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def reporter(self, llm=None):
        return Agent(
            role='Entertainment Reporter',
            goal='Compile a final, definitive table of recommendations',
            backstory='You are a data-driven entertainment journalist. You hate clutter. You organize complex information into clean, readable Markdown tables. You ensure every row is unique and all viewing options for a title are consolidated into a single cell.',
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
