
from crewai import Task

class BookTasks:
    def master_plot_task(self, agent, title, genre, theme, character_context):
        return Task(
            description=f"""
            Plan the MASTER PLOT for a {genre} book titled '{title}'.
            Theme: {theme}
            
            Characters involved:
            {character_context}
            
            Your job is to design a complex, non-banal narrative structure.
            Your planning must include:
            1. Central Conflict & Stakes: What is the main problem and why does it matter?
            2. Narrative Arc: Outline the Inciting Incident, Plot Point 1, Midpoint, Plot Point 2, and Climax.
            3. Character Arcs: How do the main characters change from beginning to end?
            4. Thematic Motifs: Specific recurring symbols or ideas that reinforce the theme.
            5. Plot Twists & Complexity: Elements that make the story unique and non-linear.
            
            Ensure the story is mature, deep, and cohesive. Avoid cliches.
            """,
            expected_output="A detailed Master Plot document",
            agent=agent
        )

    def character_design_task(self, agent, genre, theme, count=4, mandatory_names=None):
        names_str = f" MANDATORY NAMES: {', '.join(mandatory_names)}" if mandatory_names else ""
        return Task(
            description=f"""
            Create {max(count, len(mandatory_names) if mandatory_names else 0)} detailed, complex characters for a {genre} story.
            Theme: {theme}
            {names_str}
            
            REQUIREMENTS:
            1. Characters should be morally ambiguous, deep, and "Mature" (matching the genre).
            2. Avoid generic tropes. Give them flaws, obsessions, and secrets.
            3. Provide a diversity of roles (Protagonist, Antagonist, Wildcard, etc.).
            4. If MANDATORY NAMES are provided, you MUST use those names for the characters.
            5. For EACH character, provide:
               - Name
               - Role
               - Physical Appearance (Detailed for image generation, as a STRING)
               - Personality/Psychology (As a STRING)
               - Backstory (The "Ghost" or trauma)
            
            Return a JSON object:
            {{
                "characters": [
                    {{
                        "name": "...",
                        "role": "...",
                        "appearance": "...",
                        "personality": "...",
                        "backstory": "..."
                    }},
                    ...
                ]
            }}
            """,
            expected_output="JSON list of detailed characters",
            agent=agent
        )

    def structure_task(self, agent, genre, title, chapter_count=5, master_plot="", character_context=""):
        return Task(
            description=f"""
            Create a detailed outline for a {genre} book titled '{title}' with exactly {chapter_count} CHAPTERS.
            
            MASTER PLOT CONTEXT:
            {master_plot}
            
            CHARACTERS:
            {character_context}
            
            Your job:
            Translate the Master Plot into a chapter-by-chapter structure.
            For each chapter, provide:
            1. Title
            2. Plot Summary (Ensure it advances the central conflict and character arcs)
            3. A "Visual Concept" describing the key scene to be illustrated.
            
            Return the outline as valid JSON:
            {{
                "outline": [
                    {{
                        "chapter": 1,
                        "title": "...",
                        "summary": "...",
                        "visual_concept": "..."
                    }},
                    ...
                ]
            }}
            """,
            expected_output="JSON Outline",
            agent=agent
        )

    def update_outline_task(self, agent, current_outline, modification_prompt):
        return Task(
            description=f"""
            UPDATE the existing book outline based on the User's Request.
            
            Current Outline:
            {current_outline}
            
            User Request:
            "{modification_prompt}"
            
            Your job:
            1. Keep existing chapters if they still fit.
            2. Add new chapters if requested (e.g., "Add a chapter about Mars").
            3. Modify chapter summaries if requested (e.g., "Make chapter 2 darker").
            4. Remove chapters if requested.
            
            CRITICAL: Return the COMPLETE new outline (old + new).
            Mark any chapter that needs (re)generation with "status": "pending".
            Mark unchanged chapters with "status": "done".
            
            Return JSON:
            {{
                "outline": [
                    {{
                        "chapter": 1,
                        "title": "...",
                        "summary": "...",
                        "visual_concept": "...",
                        "status": "done" (or "pending" if it changed)
                    }},
                    ...
                ]
            }}
            """,
            expected_output="JSON Updated Outline",
            agent=agent
        )

    def extend_outline_task(self, agent, current_outline, target_chapters, master_plot):
        return Task(
            description=f"""
            EXTEND the existing book outline to reach a total of {target_chapters} chapters.
            
            Current Outline:
            {current_outline}
            
            Master Plot:
            {master_plot}
            
            Your job:
            1. Keep the existing chapters EXACTLY as they are.
            2. Add new chapters that logically follow the existing ones and align with the Master Plot.
            3. Ensure the narrative flow is consistent.
            
            Return the COMPLETE updated outline (existing + new chapters).
            
            Return JSON:
            {{
                "outline": [
                    {{
                        "chapter": 1,
                        "title": "...",
                        "summary": "...",
                        "visual_concept": "...",
                        "status": "done"
                    }},
                    ...
                ]
            }}
            """,
            expected_output="JSON Extended Outline",
            agent=agent
        )

    def character_portrait_task(self, agent, character_data):
        return Task(
            description=f"""
            Generate a high-fidelity image prompt for the character: {character_data['name']}.
            
            Role: {character_data['role']}
            Appearance: {character_data['appearance']}
            Personality: {character_data['personality']}
            
            CRITICAL REQUIREMENTS:
            1. The prompt must be LITERAL and PHOTOREALISTIC - describe the character as a REAL HUMAN BEING.
            2. Extract and list EXPLICITLY from Appearance:
               - Age and gender
               - Hair: color, length, style
               - Face: eye color, facial hair, scars, distinctive features
               - Build: height, body type
               - Clothing: specific items, colors, condition
            3. Style: Professional portrait photography, cinematic lighting, 8k, highly detailed, realistic
            4. MANDATORY: Include a NEGATIVE PROMPT section to exclude unwanted elements
            
            OUTPUT FORMAT (two sections):
            
            POSITIVE PROMPT:
            [Character name], [age] [gender], [detailed physical description including all traits above], [clothing details], [portrait photography, cinematic lighting, 8k, photorealistic, highly detailed]
            
            NEGATIVE PROMPT:
            zombie, undead, demon, skeleton, horror, supernatural, glowing eyes, fangs, monster, creature, alien, fantasy, cartoon, anime, low quality, blurry, distorted
            
            OUTPUT ONLY THE TWO SECTIONS ABOVE. Nothing else.
            """,
            expected_output="Image Prompt with Positive and Negative sections",
            agent=agent
        )

    def briefing_task(self, agent, chapter_info, context_from_rag, recursive_summaries, world_bible_context):
        recent_summary = recursive_summaries.get(2, "No previous chapter.")
        arc_summary = recursive_summaries.get(1, "Beginning of story.")
        
        return Task(
            description=f"""
            Create a "Writer's Briefing" for Chapter {chapter_info['chapter']}: {chapter_info['title']}.
            
            Description: {chapter_info['summary']}
            
            WORLD RULES (BIBLE):
            {world_bible_context}
            
            KNOWN CONTEXT (Simulated Memory):
            {context_from_rag}
            
            PREVIOUS CHAPTER SUMMARY:
            {recent_summary}
            
            ARC SUMMARY:
            {arc_summary}
            
            Your job is acting as the "Continuity Investigator":
            1. Analyze the Context and Previous Summary for any established facts (locations, character names, states of objects).
            2. Cross-reference with the current Chapter Description.
            3. Detect any potential contradictions or plot holes (e.g., a character dead in prev chapter appearing here).
            4. Provide the Writer with strict continuity guidelines and facts to verify.
            5. Highlight specifically what MUST NOT change from the past history.
            """,
            expected_output="Briefing Paragraph",
            agent=agent
        )

    # --- FRACTAL PLANNING ---
    def breakdown_chapter_task(self, agent, chapter_info, context, scene_count=3):
        return Task(
            description=f"""
            Break down Chapter {chapter_info['chapter']} ("{chapter_info['title']}") into exactly {scene_count} detailed Scenes.
            
            Chapter Summary: {chapter_info['summary']}
            Context: {context}
            
            Return a JSON list of scenes. Each scene must have:
            - "number": integer
            - "name": string
            - "description": specific action/beats (what happens)
            - "setting": location details
            - "emotional_beat": the shift in emotion
            
            Output JSON format:
            {{
                "scenes": [
                    {{ ... }}
                ]
            }}
            """,
            expected_output="JSON list of Scenes",
            agent=agent
        )

    # --- WRITING LOOP ---
    def write_scene_task(self, agent, scene_data, context, previous_scene_text="", character_context="", word_count=500):
        return Task(
            description=f"""
            Write SCENE {scene_data['number']}: {scene_data['name']}.
            
            ACTION: {scene_data['description']}
            SETTING: {scene_data['setting']}
            EMOTION: {scene_data['emotional_beat']}
            
            CHARACTER REFERENCE:
            {character_context}
            
            CONTEXT from RAG: {context}
            PREVIOUS TEXT: {previous_scene_text[-500:]}
            
            Instructions:
            - Write approx {word_count} words.
            - Reference physical traits from CHARACTER REFERENCE (mention ONCE at scene start, not every paragraph).
            - Focus on SELECTIVE sensory details (choose impactful moments - not everything needs metaphor).
            - "Show, Don't Tell".
            - VARY sentence structure: Mix short/long, simple/complex. Avoid 3+ fragments in a row.
            - Balance dense prose with clarity - reader should follow action easily.
            - Dialogue must have subtext and follow character speech patterns.
            - NO filler, no moralizing at the end.
            """,
            expected_output="Draft Scene Text",
            agent=agent
        )

    def critique_scene_task(self, agent, draft_text, world_bible_context):
        return Task(
            description=f"""
            CRITIQUE this draft scene as a Ruthless Editor.
            
            DRAFT:
            {draft_text}
            
            STYLISTIC GLOSSARY (BIBLE):
            {world_bible_context}
            
            Check for:
            
            1. **Overwriting/Purple Prose**:
               - Flag if 4+ metaphors in single paragraph
               - Flag excessive compound adjectives (ice-sweat, fire-hot, tomb-thick, shadow-soaked)
               - Flag pretentious verb choices without clear meaning
            
            2. **Sentence Structure Monotony**:
               - Flag if 3+ sentence fragments in a row
               - Require mix of short/medium/long sentences
            
            3. **Repetitive Descriptions**:
               - Flag if character physical traits mentioned 2+ times in same scene
               - Character should be described ONCE then ref by name/pronoun
            
            4. **AI Cliches** (EXPANDED LIST):
               - Worn verbs: clawed, bled, echoed (for memories), whispered (for non-speech), danced
               - Overwrought compounds: any shadow+verb combo, X-soaked, Y-drenched
               - Generic intensity: testament, tapestry, symphony, kaleidoscope
               - Body-part autonomy: eyes that "rake/claw", hands that "claw" (unless literal)
               - Neon references in cyberpunk (overdone)
            
            5. **Clarity Issues**:
               - Are time transitions clear (flashback vs present)?
               - Can reader follow who/what/when/where without re-reading?
               - Are metaphors grounded in concrete imagery?
            
            6. **Pacing**:
               - Is there variation in intensity or is it 11/10 non-stop?
               - Are there "breathing moments" between intense passages?
            
            Return SPECIFIC, ACTIONABLE feedback. Quote exact phrases to fix.
            
            If you find 5+ major issues, recommend REWRITE not just revision.
            
            If genuinely excellent (rare), say "APPROVED".
            """,
            expected_output="Critique Points",
            agent=agent
        )

    def revise_scene_task(self, agent, draft_text, critique_feedback, word_count=500):
        return Task(
            description=f"""
            REWRITE the scene based on this critique.
            
            CRITIQUE:
            {critique_feedback}
            
            ORIGINAL:
            {draft_text}
            
            REVISION REQUIREMENTS:
            1. Fix ALL issues mentioned in critique
            2. If critique says "overwritten", CUT 20-30% of adjectives/metaphors
            3. If critique flags repetition, REMOVE redundant descriptions
            4. If critique notes structure monotony, VARY sentence types
            5. Maintain word count around {word_count} BUT prioritize clarity over length
            
            Apply the changes. Keep the word count around {word_count}.
            Return ONLY the final polished text.
            DO NOT include "Final Polished Scene Text" or any markdown headers like "## Scene".
            DO NOT include conversational filler like "Here is the revised scene".
            Just the story text.
            """,
            expected_output="Final Polished Scene Text",
            agent=agent
        )

    # --- VISUALS ---
    def illustration_task(self, agent, chapter_info, scene_text, output_path, character_context=""):
        # Agent generates ONLY the image prompt, tool call happens externally
        return Task(
            description=f"""
            You are a Visual Director. Generate a detailed, LITERAL image prompt for this scene.
            
            CHARACTER VISUALS (YOUR PRIMARY REFERENCE):
            {character_context}
            
            SCENE CONTEXT:
            Chapter: {chapter_info['title']}
            Summary: {chapter_info['summary']}
            
            SCENE TEXT:
            {scene_text[:1500]}
            
            TASK:
            Create a SINGLE, detailed image prompt that LITERALLY depicts the scene.
            
            CRITICAL REQUIREMENTS:
            
            1. **Character Identification**:
               - READ the scene text carefully
               - IDENTIFY which characters from CHARACTER VISUALS are present
               - LIST each character BY NAME with their exact appearance from CHARACTER VISUALS
               - If Elias Korran is in the scene, you MUST describe: "Elias Korran, mid-40s gaunt man with salt-and-pepper shoulder-length hair, jagged scar from temple to cheekbone, faded leather jacket"
            
            2. **LITERAL Description** (NOT metaphorical):
               - Describe what is LITERALLY happening, not symbolic/artistic interpretation
               - If text says "hunched over developer tray" → prompt should say "hunched over developer tray"
               - If text says "gaunt frame" → prompt should say "gaunt, thin build"
               - NO artistic liberties with character appearance
            
            3. **Setting & Action**:
               - Describe the physical location from the text
               - Include key objects/props mentioned
               - Specify character positions and actions
            
            4. **Style**:
               - Photorealistic, cinematic lighting, high detail, 8k
               - Noir/dark atmosphere if genre appropriate
            
            5. **MANDATORY Negative Prompt**:
               - You MUST include a negative prompt section
               - Exclude: zombie, undead, demon, skeleton, horror creature, supernatural, glowing red eyes, glowing white eyes, fangs, monster
            
            OUTPUT FORMAT (two sections required):
            
            POSITIVE PROMPT:
            [Character names and literal descriptions], [specific action from text], [literal setting details], [lighting/mood], [style: photorealistic, cinematic, 8k, highly detailed]
            
            NEGATIVE PROMPT:
            zombie, undead, demon, skeleton, horror creature, supernatural, glowing red eyes, glowing white eyes, glowing eyes, fangs, monster, alien, fantasy creature, cartoon, anime, distorted, low quality, blurry
            
            EXAMPLE:
            If scene shows "Elias examining a photo in his darkroom":
            
            POSITIVE PROMPT:
            Elias Korran, mid-40s gaunt man with salt-and-pepper shoulder-length hair tied back, jagged scar from temple to cheekbone, deep-set hazel eyes, faded leather jacket over threadbare shirt, examining a photograph in a dimly lit darkroom, red safelight illuminating shelves of crime scene photos, developer trays on concrete floor, underground bunker atmosphere, cinematic lighting, photorealistic, 8k, highly detailed
            
            NEGATIVE PROMPT:
            zombie, undead, demon, skeleton, horror creature, supernatural, glowing red eyes, glowing white eyes, glowing eyes, fangs, monster, female, woman, alien, fantasy creature, cartoon, anime, distorted, low quality, blurry
            
            OUTPUT ONLY THE TWO SECTIONS. No explanations or commentary.
            """,
            expected_output="A detailed image generation prompt with positive and negative sections (text only)",
            agent=agent
        )

    def formatting_task(self, agent, book_title, html_body):
        return Task(
            description=f"""
            Wrap the following HTML body into a complete, professional HTML document for '{book_title}'.
            
            HTML Body:
            {html_body}
            
            Requirements:
            - Add <head> with CSS for:
              - Font: Times New Roman (body), Helvetica (headers).
              - Margins: 2.5cm.
              - Justified text.
              - Images centered with max-width 100%.
            - Return the FULL <html> string.
            """,
            expected_output="Full HTML String",
            agent=agent
        )
