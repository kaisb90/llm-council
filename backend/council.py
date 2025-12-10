"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [
        {"role": "system", "content": "Du bist ein hochintelligenter Assistent und Teil eines Expertenrates. Deine Aufgabe ist es, die Fragen des Nutzers so präzise, objektiv und umfassend wie möglich zu beantworten. Nutze dein gesamtes Wissen, denke Schritt für Schritt und begründe deine Aussagen. Antworte ausschließlich auf Deutsch."},
        {"role": "user", "content": user_query}
    ]

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
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
1. Analysiere jede Antwort kritisch. Achte besonders auf:
   - Korrektheit: Sind die Fakten richtig?
   - Vollständigkeit: Wurden alle Aspekte der Frage beantwortet?
   - Objektivität: Ist die Antwort neutral und ausgewogen?
   - Verständlichkeit: Ist die Antwort klar strukturiert und gut lesbar?
2. Identifiziere mögliche Fehler, Halluzinationen oder Ungenauigkeiten.
3. Gib ganz am Ende deiner Antwort eine abschließende Rangliste an.

WICHTIG: Deine abschließende Rangliste MUSS EXAKT wie folgt formatiert sein:
- Beginne mit der Zeile "ABSCHLIESSENDES RANKING:" (alles in Großbuchstaben, mit Doppelpunkt)
- Liste dann die Antworten von der besten zur schlechtesten als nummerierte Liste auf
- Jede Zeile sollte so aussehen: Nummer, Punkt, Leerzeichen, dann NUR das Antwort-Label (z.B. "1. Response A")
- Füge keine weiteren Texte oder Erklärungen im Ranking-Abschnitt hinzu

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

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
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
    Stage 3: Chairman synthesizes final response.

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
1. Analysiere die Qualität der Antworten basierend auf den Peer-Reviews (Stage 2). Gewichte höher bewertete Antworten stärker.
2. Identifiziere Widersprüche zwischen den Modellen. Wenn Modelle sich widersprechen, nutze deine eigene Urteilskraft, um die korrekte Information zu bestimmen, und weise transparent auf die Unsicherheit hin.
3. Erstelle eine strukturierte, umfassende Antwort.

Struktur der Antwort:
- **Zusammenfassung**: Eine direkte Antwort auf die Frage.
- **Details**: Ausführliche Erklärungen, die die besten Erkenntnisse aller Modelle kombinieren.
- **Dissent/Nuancen** (optional): Falls es interessante Meinungsverschiedenheiten im Rat gab, erwähne diese kurz.

Gib eine klare, professionelle und gut begründete endgültige Antwort auf Deutsch:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
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
                # Take the last part in case the delimiter appears multiple times (unlikely but safer)
                ranking_section = parts[-1]
                break

    if ranking_section:
        # Try to extract numbered list format (e.g., "1. Response A")
        # This pattern looks for: number, period, optional space, "Response X"
        numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
        if numbered_matches:
            # Extract just the "Response X" part
            return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

        # Fallback: Extract all "Response X" patterns in order from the section
        matches = re.findall(r'Response [A-Z]', ranking_section)
        if matches:
            return matches

    # Fallback if no delimiter found or no matches in section:
    # try to find any "Response X" patterns in order from the full text
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
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

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

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

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
            "response": "All models failed to respond. Please try again."
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
