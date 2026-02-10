from crewai import Task

class MovieAnalystTasks:
    def recommend_movies(self, agent, criteria):
        content_type = criteria.get('content_type', 'movie')
        mood = criteria.get('mood', 'General')
        runtime = criteria.get('max_runtime_minutes', 999)
        language = criteria.get('language', 'English')
        
        return Task(
            description=f'Find a list of at least {criteria["count"]} top-rated {content_type}s matching these criteria:\n'
                        f'- Genres: {", ".join(criteria["genres"])}\n'
                        f'- Year Range: {criteria["year_range"]}\n'
                        f'- Mood/Vibe: "{mood}" (Prioritize content that fits this specific atmosphere)\n'
                        f'- Max Runtime: {runtime} minutes\n'
                        f'- Primary Language: {language}\n\n'
                        f'For each item, find TWO scores if possible:\n'
                        f'1. Critic Score (e.g., Rotten Tomatoes %, Metacritic)\n'
                        f'2. Audience Score (e.g., IMDb rating, Rotten Tomatoes Audience Score)\n\n'
                        f'FILTERING RULES:\n'
                        f'- Minimum Score: {criteria["min_score"]}/10 (or equivalent percentage)\n'
                        f'- NO DUPLICATE TITLES.\n\n'
                        f'Output a structured list with: Title, Year, Critic Score (Numeric), Audience Score (Numeric), and a brief "Vibe Check" explanation of why it fits the "{mood}" mood.',
            expected_output=f'A list of {criteria["count"]} unique {content_type}s with numeric scores and vibe explanations.',
            agent=agent
        )

    def check_availability(self, agent, movies_task, user_context):
        cost_instruction = ""
        if user_context.get('only_free_included', False):
            cost_instruction = "IMPORTANT: The user wants ONLY content included in their subscription ('flatrate'). " \
                               "IF A TITLE IS NOT AVAILABLE ON THE SUBSCRIBED SERVICES FOR FREE, REMOVE IT FROM THE LIST. " \
                               "Do not show rental/buy options."

        return Task(
            description=f'Take the list of provided titles. Check their streaming availability in {user_context["country"]}. '
                        f'For each title, find DIRECT streaming links valid for {user_context["country"]}. '
                        f'The user subscribes to: {", ".join(user_context["subscribed_providers"])}. '
                        f'{cost_instruction} '
                        f'Be very specific about the region. Netflix US catalog is different from Netflix IT. '
                        f'If a title is available on multiple services, FIND LINKS FOR ALL OF THEM.\n'
                        f'Output Format for each title:\n'
                        f'Title: [Name]\n'
                        f'Services: [Service 1]: https://... , [Service 2]: https://...',
            expected_output='A filtered list of titles available on the user\'s specific services with direct URLs.',
            agent=agent,
            context=[movies_task]
        )

    def verify_links(self, agent, availability_task, user_context):
        return Task(
            description=f'Review the streaming links provided. '
                        f'AGGRESSIVELY verify validity for {user_context["country"]}. '
                        f'Suspect any clean "pretty" URL (like hbo.com/originals/name) of being a 404 guess. '
                        f'Use the "fetch_html" (or "fetch") tool to access the URL and check if it exists. '
                        f'IMPORTANT: If using "fetch_html", you MUST provide {{"startCursor": 0}} as an argument along with the url. '
                        f'Check the fetched content for "404", "Not Found", "Sorry", "Could not find". '
                        f'If a link is broken, use the Search Tool to find the ACTUAL watch URL. '
                        f'Ensure the Type (Movie or TV Series) is correctly identified for each title. '
                        f'Output must contain FULL, DIRECT URLs (starting with http/https) and the Type.',
            expected_output='A validated list of titles with verified, direct URL links and content type (Movie/Series).',
            agent=agent,
            context=[availability_task]
        )

    def compile_guide(self, agent, verification_task, report_preferences):
        format_type = report_preferences.get('format', 'table')
        
        return Task(
            description=f'Compile the final "What to Watch" guide. \n'
                        f'STRICT FORMATTING RULES:\n'
                        f'1. Use a Markdown Table.\n'
                        f'2. Columns: Title | Type | Year | Critic Score | Audience Score | Vibe Match | Streaming Options\n'
                        f'3. DEDUPLICATION: Each Title must appear in ONLY ONE ROW.\n'
                        f'4. STREAMING LINKS (CRITICAL): \n'
                        f'   - You MUST use standard Markdown link syntax: [Service Name](URL).\n'
                        f'   - Example: [Netflix](https://www.netflix.com/title/12345)\n'
                        f'   - DO NOT write "Netflix (Link)". The "Link" text is useless. The URL must be embedded.\n'
                        f'   - If multiple services, separate with <br>. Example: [Netflix](https://...) <br> [Prime](https://...)\n'
                        f'5. SCORES: Must be numeric (e.g. "8.5/10" or "92%"). Do NOT use stars (*****).\n'
                        f'6. Vibe Match: A short sentence explaining why it fits the requested mood.\n\n'
                        f'Add a concluding "Editor\'s Choice" section recommending the #1 pick.',
            expected_output='A clean, deduplicated Markdown table with INTERACTIVE links, Type column, and numeric scores.',
            agent=agent,
            context=[verification_task]
        )
