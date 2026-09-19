import os
import sys
import json
import re
import yaml
import time
import requests
import logging
from dotenv import load_dotenv
from crewai import LLM

# Setup logging
logging.basicConfig(
    filename='execution.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add repo root to path to import src.mcp_loader
# current file is in examples/07_movie_analyst/src/
# repo root is ../../../
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)

# Check if mcp_loader exists
if not os.path.exists(os.path.join(repo_root, "src", "mcp_loader.py")):
    print(f"Error: mcp_loader.py not found at {os.path.join(repo_root, 'src', 'mcp_loader.py')}")
    sys.exit(1)

from src.mcp_loader import MCPLoader


STALE_OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash-lite",
}

def clear_ollama_vram(base_url="http://localhost:11434"):
    """
    Attempts to unload models from Ollama to clear VRAM.
    """
    print("🧹 Attempting to clear Ollama VRAM...")
    try:
        # To unload a model in Ollama, we can generate a request with keep_alive=0
        # We try to unload common models we might have used
        models_to_unload = ["llama3", "llama3.2", "mistral", "gemma"]
        
        for model in models_to_unload:
            try:
                # We don't care about the prompt, just the keep_alive parameter
                payload = {
                    "model": model,
                    "prompt": "",
                    "keep_alive": 0
                }
                response = requests.post(f"{base_url}/api/generate", json=payload, timeout=2)
                if response.status_code == 200:
                    print(f"   Requested unload for {model}")
            except Exception:
                pass # Model might not be loaded or name is wrong, ignore
        
        print("   VRAM cleanup signal sent.")
    except Exception as e:
        print(f"   Warning: Could not contact Ollama to clear VRAM: {e}")


def extract_json_payload(text):
    decoder = json.JSONDecoder()

    fenced_match = re.search(r"```json\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced_match:
        return json.loads(fenced_match.group(1).strip())

    generic_fence = re.search(r"```\s*([\s\S]*?)```", text)
    if generic_fence:
        candidate = generic_fence.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
            return payload
        except json.JSONDecodeError:
            continue

    raise ValueError("No JSON payload found in model response")


def normalize_provider_name(name):
    simplified = re.sub(r"[^a-z0-9]+", "", name.lower())
    aliases = {
        "primevideo": "amazonprimevideo",
        "amazonprime": "amazonprimevideo",
        "amazonprimevideo": "amazonprimevideo",
        "disneyplus": "disneyplus",
        "nowtv": "nowtv",
        "netflix": "netflix",
    }
    return aliases.get(simplified, simplified)


def normalize_title(name):
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def parse_justwatch_results(search_output, subscribed_providers, only_free_included):
    provider_set = {normalize_provider_name(provider) for provider in subscribed_providers}
    sections = re.split(r"\n\s*\d+\.\s*\n", search_output)
    parsed = []

    for block in sections[1:]:
        title_match = re.search(r"Title:\s*(.+)", block)
        year_match = re.search(r"Release Year:\s*(\d{4})", block)
        type_match = re.search(r"Type:\s*([A-Z]+)", block)
        imdb_match = re.search(r"IMDb Score:\s*([0-9.]+/10)", block)
        tmdb_match = re.search(r"TMDb Score:\s*([0-9.]+/10)", block)

        if not title_match:
            continue

        offers = []
        offer_pattern = re.compile(
            r"-\s*(.+?)\s*\((.+?)\)\s*\n\s*URL:\s*(https?://\S+)",
            re.MULTILINE,
        )
        for offer_match in offer_pattern.finditer(block):
            provider = offer_match.group(1).strip()
            offer_meta = offer_match.group(2).strip()
            url = offer_match.group(3).strip()
            monetization = offer_meta.split(",")[0].strip().upper()

            if only_free_included and monetization != "FLATRATE":
                continue
            if normalize_provider_name(provider) not in provider_set:
                continue

            offers.append({"provider": provider, "url": url})

        if not offers:
            continue

        parsed.append(
            {
                "title": title_match.group(1).strip(),
                "type": (type_match.group(1).strip().title() if type_match else "Movie"),
                "year": int(year_match.group(1)) if year_match else None,
                "imdb_score": imdb_match.group(1) if imdb_match else None,
                "tmdb_score": tmdb_match.group(1) if tmdb_match else None,
                "offers": offers,
            }
        )

    return parsed


def score_to_points(score):
    if not score:
        return 0.0
    percent_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", score)
    if percent_match:
        return float(percent_match.group(1))
    ten_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*/\s*10", score)
    if ten_match:
        return float(ten_match.group(1)) * 10
    number_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", score)
    return float(number_match.group(1)) if number_match else 0.0


def movie_matches_criteria(entry, criteria):
    expected_type = criteria.get("content_type", "movie").lower()
    if entry.get("type", "").lower() != expected_type:
        return False

    year_range = str(criteria.get("year_range", "")).strip()
    if year_range and "-" in year_range:
        start_year, end_year = year_range.split("-", 1)
        year = entry.get("year")
        if year is None or not (int(start_year) <= int(year) <= int(end_year)):
            return False

    minimum_score = float(criteria.get("min_score", 0)) * 10
    strongest_available_score = max(
        score_to_points(entry.get("imdb_score")),
        score_to_points(entry.get("tmdb_score")),
    )
    if strongest_available_score < minimum_score:
        return False

    return True


def render_markdown_report(entries):
    if not entries:
        return "No matching titles were found on the subscribed services for the requested criteria."

    sorted_entries = sorted(
        entries,
        key=lambda item: score_to_points(item.get("critic_score")) + score_to_points(item.get("audience_score")),
        reverse=True,
    )

    lines = [
        "| Title | Type | Year | Critic Score | Audience Score | Vibe Match | Streaming Options |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for entry in sorted_entries:
        options = " <br> ".join(
            f"[{option['provider']}]({option['url']})" for option in entry["streaming_options"]
        )
        lines.append(
            f"| {entry['title']} | {entry['type']} | {entry['year']} | "
            f"{entry.get('critic_score', 'N/A')} | {entry.get('audience_score', 'N/A')} | "
            f"{entry.get('vibe_match', 'N/A')} | {options} |"
        )

    top_pick = sorted_entries[0]
    lines.extend(
        [
            "",
            "## Editor's Choice",
            f"**{top_pick['title']}** stands out as the strongest match for the requested mood and availability.",
        ]
    )
    return "\n".join(lines)


def get_tool_by_name(tools, name):
    for tool in tools:
        if getattr(tool, "name", "") == name:
            return tool
    raise ValueError(f"Required tool '{name}' not found")


def build_candidate_queries(criteria):
    genres = " ".join(criteria.get("genres", []))
    year_range = criteria.get("year_range", "")
    content_type = criteria.get("content_type", "movie")
    mood = criteria.get("mood", "")
    return [
        f"best {year_range} {mood} {genres} {content_type}s",
        f"top {year_range} visually stunning {genres} {content_type}s",
        f"best {year_range} mind-bending sci-fi thriller {content_type}s",
        f"must watch {year_range} {genres} {content_type}s with strong reviews",
    ]


def collect_candidate_movies(criteria, brave_tool, llm):
    target_count = min(max(criteria.get("count", 5) * 2, 10), 20)
    raw_result_chunks = []
    for query in build_candidate_queries(criteria):
        raw_result_chunks.append(brave_tool.run(query=query, count=min(target_count, 8)))
    raw_results = "\n\n".join(raw_result_chunks)
    prompt = f"""
You are extracting real movie candidates from Brave search results.

Return JSON only as an array of objects with keys:
- title
- year
- vibe_match

Rules:
- Keep only real released {criteria.get('content_type', 'movie')}s.
- Keep only years in {criteria.get('year_range', 'any year')}.
- Prefer titles matching genres {criteria.get('genres', [])}.
- Prefer titles that feel "{criteria.get('mood', '')}".
- Return at most {criteria.get('count', 5) * 2} unique titles.

Search results:
{raw_results}
"""
    response = llm.call(prompt)
    payload = extract_json_payload(response)
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list of candidate titles")

    unique = []
    seen = set()
    for item in payload:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        key = normalize_title(title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "title": title,
                "year": item.get("year"),
                "vibe_match": item.get("vibe_match", ""),
            }
        )
    return unique


def generate_llm_candidates(criteria, llm):
    prompt = f"""
Generate a shortlist of real released {criteria.get('content_type', 'movie')} candidates.

Return JSON only as an array of objects with keys:
- title
- year
- vibe_match

Rules:
- Keep only real titles, no invented movies.
- Keep only years in {criteria.get('year_range', 'any year')}.
- Prefer genres {criteria.get('genres', [])}.
- Prefer critically well-received titles that fit "{criteria.get('mood', '')}".
- Return up to {criteria.get('count', 5) * 3} unique entries.
"""
    payload = extract_json_payload(llm.call(prompt))
    if not isinstance(payload, list):
        return []

    unique = []
    seen = set()
    for item in payload:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        key = normalize_title(title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "title": title,
                "year": item.get("year"),
                "vibe_match": item.get("vibe_match", ""),
            }
        )
    return unique


def choose_best_match(matches, candidate):
    candidate_title = normalize_title(candidate["title"])
    candidate_year = candidate.get("year")

    def match_rank(entry):
        exact_title = normalize_title(entry["title"]) == candidate_title
        exact_year = candidate_year is not None and entry.get("year") == candidate_year
        return (exact_title, exact_year, len(entry["offers"]))

    ranked = sorted(matches, key=match_rank, reverse=True)
    return ranked[0] if ranked else None


def shortlist_streaming_movies(candidates, user_context, justwatch_tool, criteria, limit):
    selected = []
    seen = set()
    for candidate in candidates:
        if len(selected) >= limit:
            break

        raw_result = justwatch_tool.run(
            query=candidate["title"],
            country=user_context["country"],
            language="en",
            count=5,
            best_only=True,
        )
        matches = parse_justwatch_results(
            raw_result,
            subscribed_providers=user_context["subscribed_providers"],
            only_free_included=user_context.get("only_free_included", False),
        )
        matches = [entry for entry in matches if movie_matches_criteria(entry, criteria)]
        best_match = choose_best_match(matches, candidate)
        if not best_match:
            continue

        key = normalize_title(best_match["title"])
        if key in seen:
            continue
        seen.add(key)

        selected.append(
            {
                "title": best_match["title"],
                "type": best_match["type"],
                "year": best_match["year"],
                "audience_score": best_match.get("imdb_score") or "N/A",
                "critic_score": best_match.get("tmdb_score") or "N/A",
                "vibe_match": candidate.get("vibe_match") or "",
                "streaming_options": best_match["offers"],
            }
        )
    return selected


def enrich_movie(movie, brave_tool, llm):
    raw_results = brave_tool.run(
        query=f"{movie['title']} {movie['year']} Rotten Tomatoes Metacritic IMDb reviews",
        count=5,
    )
    prompt = f"""
Extract review metadata for this movie from the Brave search results.

Return JSON only with keys:
- critic_score
- audience_score
- vibe_match

Rules:
- critic_score should prefer Rotten Tomatoes or Metacritic if visible.
- audience_score should prefer IMDb if visible.
- vibe_match should be one short sentence.
- If a score is not visible, return "N/A".

Movie:
{json.dumps(movie, ensure_ascii=True)}

Search results:
{raw_results}
"""

    try:
        payload = extract_json_payload(llm.call(prompt))
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    enriched = dict(movie)
    enriched["critic_score"] = payload.get("critic_score") or movie.get("critic_score") or "N/A"
    enriched["audience_score"] = payload.get("audience_score") or movie.get("audience_score") or "N/A"
    enriched["vibe_match"] = payload.get("vibe_match") or movie.get("vibe_match") or "Strong thematic fit."
    return enriched

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "preferences.yaml")
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        return None
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_llm_instance(config):
    """
    Creates and returns the LLM instance based on configuration.
    """
    llm_config = config.get("llm_config", {})
    selected_profile_name = llm_config.get("selected", "openai")
    
    print(f"🧠 Selected LLM Profile: {selected_profile_name}")
    
    profiles = llm_config.get("profiles", {})
    profile = profiles.get(selected_profile_name)
    
    if not profile:
        print(f"Warning: Profile '{selected_profile_name}' not found in profiles. Falling back to default OpenAI.")
        return None # CrewAI defaults to OpenAI gpt-4 if None

    provider = profile.get("provider", "").lower()
    model = profile.get("model")
    base_url = profile.get("base_url")

    is_openrouter = (
        provider == "openrouter"
        or selected_profile_name.lower() == "openrouter"
        or "openrouter.ai" in (base_url or "").lower()
    )
    
    if provider == "ollama":
        # For Ollama, we use the standard OpenAI-compatible endpoint usually, 
        # but CrewAI has a specific way or we can use the generic LLM class.
        # CrewAI's LLM class supports 'ollama/model_name' format or custom base_url.
        print(f"   Using Ollama: {model} at {base_url}")
        return LLM(
            model=f"ollama/{model}",
            base_url=base_url
        )
        
    elif is_openrouter:
        # Normalize OpenRouter settings even if the config profile was mislabeled as openai.
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENROUTER_MODEL") or model
        model = STALE_OPENROUTER_MODELS.get(model, model)
        if model and not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
        if api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ.pop("OPENAI_API_BASE", None)

        print(f"   Using OpenRouter: {model}")
        return LLM(
            model=model,
            api_key=api_key,
        )

    elif provider == "openai":
        # Standard OpenAI
        print(f"   Using OpenAI: {model}")
        return LLM(model=model)
    
    return None

def run():
    print("Starting Example 07: Movie Analyst (Advanced)")
    
    # Load env
    load_dotenv(os.path.join(repo_root, ".env"), override=True)
    
    # Load Config
    config = load_config()
    if not config:
        print("Failed to load configuration.")
        return

    print(f"Target Criteria: {config['movie_criteria']}")
    print(f"User Context: {config['user_context']}")
    print(f"Report Preferences: {config.get('report_preferences', {})}")

    # Setup LLM
    llm = get_llm_instance(config)

    # Load MCP Tools
    config_path = os.path.join(repo_root, "crewai_mcp.json")
    loader = MCPLoader(config_path)
    
    # Get tools from MCP servers
    print("Loading MCP Tools...")
    
    jw_tools = []
    bs_tools = []
    fetch_tools = []
    
    try:
        # Load JustWatch
        jw_adapter = loader.load_server("justwatch")
        jw_tools = jw_adapter.tools if hasattr(jw_adapter, 'tools') else []
        print(f"Loaded {len(jw_tools)} JustWatch tools.")

        # Load Brave Search
        bs_adapter = loader.load_server("brave-search")
        bs_tools = bs_adapter.tools if hasattr(bs_adapter, 'tools') else []
        print(f"Loaded {len(bs_tools)} Brave Search tools.")

        # Load Multi-Fetch (or fetch)
        try:
            # Try Multi-Fetch as requested by user
            mf_adapter = loader.load_server("Multi-Fetch")
            fetch_tools = mf_adapter.tools if hasattr(mf_adapter, 'tools') else []
            print(f"Loaded {len(fetch_tools)} Multi-Fetch tools.")
        except Exception as e_mf:
            print(f"Multi-Fetch not found or failed, trying standard fetch: {e_mf}")
            try:
                f_adapter = loader.load_server("fetch")
                fetch_tools = f_adapter.tools if hasattr(f_adapter, 'tools') else []
                print(f"Loaded {len(fetch_tools)} Fetch tools.")
            except Exception as e_f:
                print(f"Fetch tools also failed: {e_f}")
        
    except Exception as e:
        print(f"Error loading MCP servers: {e}")

    if not jw_tools and not bs_tools and not fetch_tools:
        print("Warning: No tools loaded. The agents might fail.")

    brave_tool = get_tool_by_name(bs_tools, "brave_web_search")
    justwatch_tool = get_tool_by_name(jw_tools, "search_content")

    print("Collecting candidate movies...")
    candidates = collect_candidate_movies(config["movie_criteria"], brave_tool, llm)

    print("Checking streaming availability...")
    shortlisted = shortlist_streaming_movies(
        candidates,
        config["user_context"],
        justwatch_tool,
        config["movie_criteria"],
        limit=config["movie_criteria"]["count"],
    )
    if not shortlisted:
        print("No matches from Brave-derived candidates, trying LLM-derived candidates...")
        fallback_candidates = generate_llm_candidates(config["movie_criteria"], llm)
        shortlisted = shortlist_streaming_movies(
            fallback_candidates,
            config["user_context"],
            justwatch_tool,
            config["movie_criteria"],
            limit=config["movie_criteria"]["count"],
        )

    print("Enriching review data...")
    enriched = [enrich_movie(movie, brave_tool, llm) for movie in shortlisted]

    result = render_markdown_report(enriched)
    print("######################")
    print(result)

    # Save result to file
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "Movie_Guide_Report.md")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(result))
    
    print(f"Report saved to {output_file}")

if __name__ == "__main__":
    run()
