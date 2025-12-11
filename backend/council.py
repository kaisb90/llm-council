"""3-stage LLM Council orchestration with dynamic provider support."""

from typing import List, Dict, Any, Tuple, Optional
import asyncio
from .providers.factory import create_provider
from .providers import ModelConfig
from .config import load_provider_configs, get_enabled_council_models, get_chairman_model

async def query_model_dynamic(
    model_conf: Dict[str, Any],
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model using the dynamic provider system.

    Args:
        model_conf: Model configuration dict with provider, model_id, etc.
        messages: Chat messages to send
        timeout: Request timeout

    Returns:
        Response dict with 'content' and 'reasoning_details', or None if failed
    """
    try:
        # Load provider configuration
        config = load_provider_configs()
        provider_name = model_conf.get("provider")
        provider_config = config["providers"].get(provider_name)

        if not provider_config or not provider_config.get("enabled"):
            print(f"Provider {provider_name} is not enabled")
            return None

        # Create ModelConfig instance
        model_config = ModelConfig(
            provider=provider_name,
            model_id=model_conf.get("model_id"),
            display_name=model_conf.get("display_name", model_conf.get("model_id")),
            enabled=model_conf.get("enabled", True),
            temperature=model_conf.get("temperature", 0.7),
            max_tokens=model_conf.get("max_tokens", 4096)
        )

        # Create provider instance via factory
        provider = create_provider(provider_name, provider_config)

        # Query the model
        response = await provider.query_model(model_config, messages, timeout)

        return response

    except Exception as e:
        print(f"Error in query_model_dynamic for {model_conf.get('display_name')}: {e}")
        return None

async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all enabled council models.
    Uses dynamic provider configuration.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [
        {
            "role": "system",
            "content": "Du bist ein hochintelligenter Assistent und Teil eines Expertenrates. "
                       "Deine Aufgabe ist es, die Fragen des Nutzers so präzise, objektiv und "
                       "umfassend wie möglich zu beantworten. Nutze dein gesamtes Wissen, denke "
                       "Schritt für Schritt und begründe deine Aussagen. Antworte ausschließlich auf Deutsch."
        },
        {"role": "user", "content": user_query}
    ]

    # Load enabled council models dynamically
    council_models = get_enabled_council_models()

    if not council_models:
        print("Warning: No enabled council models found")
        return []

    # Query all models in parallel
    tasks = [query_model_dynamic(model_conf, messages) for model_conf in council_models]
    responses = await asyncio.gather(*tasks)

    # Format results (only include successful responses)
    stage1_results = []
    for model_conf, response in zip(council_models, responses):
        if response is not None:
            stage1_results.append({
                "model": model_conf.get("display_name"),
                "response": response.get('content', '')
            })

    return stage1_results

async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""Du bewertest verschiedene Antworten auf die folgende Frage:
Frage: {user_query}

Hier sind die Antworten verschiedener Modelle (anonymisiert):

{responses_text}

Deine Aufgabe:

Analysiere jede Antwort kritisch. Achte besonders auf:

Korrektheit: Sind die Fakten richtig?

Vollständigkeit: Wurden alle Aspekte der Frage beantwortet?

Objektivität: Ist die Antwort neutral und ausgewogen?

Verständlichkeit: Ist die Antwort klar strukturiert und gut lesbar?

Identifiziere mögliche Fehler, Halluzinationen oder Ungenauigkeiten.

Gib ganz am Ende deiner Antwort eine abschließende Rangliste an.

WICHTIG: Deine abschließende Rangliste MUSS EXAKT wie folgt formatiert sein:

Beginne mit der Zeile "ABSCHLIESSENDES RANKING:" (alles in Großbuchstaben, mit Doppelpunkt)

Liste dann die Antworten von der besten zur schlechtesten als nummerierte Liste auf

Jede Zeile sollte so aussehen: Nummer, Punkt, Leerzeichen, dann NUR das Antwort-Label (z.B. "1. Response A")

Füge keine weiteren Texte oder Erklärungen im Ranking-Abschnitt hinzu

Beispiel für das korrekte Format deiner GESAMTEN Antwort:

Response A ist sehr detailliert, enthält aber einen sachlichen Fehler bei...
Response B ist prägnant und korrekt, lässt aber...
Response C bietet die beste Balance aus Tiefe und...

ABSCHLIESSENDES RANKING:

1. Response C

2. Response B

3. Response A

Bitte gib nun deine detaillierte Analyse und das Ranking ab:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all enabled council models in parallel
    council_models = get_enabled_council_models()
    tasks = [query_model_dynamic(model_conf, messages) for model_conf in council_models]
    responses = await asyncio.gather(*tasks)

    # Format results
    stage2_results = []
    for model_conf, response in zip(council_models, responses):
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model_conf.get("display_name"),
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model

async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response using dynamic configuration.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""Du bist der Vorsitzende eines Rates von KI-Modellen (LLM Council). Mehrere KI-Modelle haben Antworten auf die Frage eines Nutzers geliefert und sich gegenseitig bewertet.
Ursprüngliche Frage: {user_query}

STAGE 1 - Individuelle Antworten:
{stage1_text}

STAGE 2 - Bewertungen der Peers:
{stage2_text}

Deine Aufgabe als Vorsitzender ist es, all diese Informationen zu einer einzigen, bestmöglichen Antwort zu synthetisieren.

Vorgehensweise:

Analysiere die Qualität der Antworten basierend auf den Peer-Reviews (Stage 2). Gewichte höher bewertete Antworten stärker.

Identifiziere Widersprüche zwischen den Modellen. Wenn Modelle sich widersprechen, nutze deine eigene Urteilskraft, um die korrekte Information zu bestimmen, und weise transparent auf die Unsicherheit hin.

Erstelle eine strukturierte, umfassende Antwort.

Struktur der Antwort:

Zusammenfassung: Eine direkte Antwort auf die Frage.

Details: Ausführliche Erklärungen, die die besten Erkenntnisse aller Modelle kombinieren.

Dissent/Nuancen (optional): Falls es interessante Meinungsverschiedenheiten im Rat gab, erwähne diese kurz.

Gib eine klare, professionelle und gut begründete endgültige Antwort auf Deutsch:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Get chairman model configuration
    chairman_conf = get_chairman_model()

    if not chairman_conf:
        return {
            "model": "error",
            "response": "Error: No chairman model configured."
        }

    # Query the chairman model dynamically
    response = await query_model_dynamic(chairman_conf, messages)

    if response is None:
        return {
            "model": chairman_conf.get("display_name", "Chairman"),
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman_conf.get("display_name", "Chairman"),
        "response": response.get('content', '')
    }

def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the ranking section from the model's response.
    Supports "ABSCHLIESSENDES RANKING:" (German) and "FINAL RANKING:" (English/Legacy).

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Define possible delimiters for the ranking section
    delimiters = ["ABSCHLIESSENDES RANKING:", "FINAL RANKING:"]

    ranking_section = None
    for delimiter in delimiters:
        if delimiter in ranking_text:
            parts = ranking_text.split(delimiter)
            if len(parts) >= 2:
                ranking_section = parts[-1]
                break

    if ranking_section:
        # Try to extract numbered list format (e.g., "1. Response A")
        numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
        if numbered_matches:
            return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

        # Fallback: Extract all "Response X" patterns in order
        matches = re.findall(r'Response [A-Z]', ranking_section)
        if matches:
            return matches

    # Final fallback: try to find any "Response X" patterns in the full text
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches

def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get('parsed_ranking', [])

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate

async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generiere einen sehr kurzen Titel (maximal 3-5 Wörter), der die folgende Frage zusammenfasst.
Der Titel sollte prägnant und beschreibend sein. Verwende keine Anführungszeichen oder Satzzeichen im Titel. Antworte auf Deutsch.

Frage: {user_query}

Titel:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Try to use a fast model for title generation
    # We'll use the first available enabled council model or a default config
    council_models = get_enabled_council_models()
    if council_models:
        title_model_conf = council_models[0]
    else:
        # Fallback if no models enabled
        title_model_conf = {
            "provider": "openrouter",
            "model_id": "google/gemini-2.5-flash",
            "display_name": "Title Generator",
            "temperature": 0.5,
            "max_tokens": 50
        }

    response = await query_model_dynamic(title_model_conf, messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title

async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process with dynamic provider support.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please check your provider configurations and try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
