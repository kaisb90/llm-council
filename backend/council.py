"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
import json
import re
import asyncio
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
    messages = [{"role": "user", "content": user_query}]

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


def parse_json_review(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly parse JSON review from text.

    Args:
        text: The raw text response from the model

    Returns:
        Parsed JSON dict or None if parsing failed
    """
    # 1. Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try to find the first outer-most JSON object
    try:
        # Match starting from first { to last }
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


async def stage2_collect_reviews(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model provides detailed reviews and rankings in JSON format.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (results list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the review prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    review_prompt = f"""You are a strict code reviewer and expert evaluator.

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. Analyze each response for correctness, completeness, and safety.
2. Identify specific bugs or issues.
3. Provide a final ranking.

CRITICAL: You MUST Output ONLY valid JSON using this EXACT schema:

{{
  "schema_version": 1,
  "reviews": {{
    "Response A": {{
      "bugs": [
        {{
          "title": "Short title of the issue",
          "evidence": {{
            "substring": "Exact substring from response text (must match exactly!)",
            "start": 0,
            "end": 0
          }},
          "fix": {{
            "summary": "How to fix it",
            "patch_unified_diff": "Optional unified diff string"
          }},
          "severity": 1,
          "confidence": 0.0
        }}
      ],
      "tests": ["Suggested test case description"],
      "notes": "General evaluation notes (in German)"
    }}
  }},
  "final_ranking": ["Response A", "Response C", "Response B"]
}}

Rules:
- severity: 1 (minor) to 5 (critical)
- confidence: 0.0 to 1.0
- If no bugs are found, "bugs" should be an empty list.
- Do NOT include any text outside the JSON block.
- Ensure the JSON is valid.
"""

    messages = [{"role": "user", "content": review_prompt}]

    # Get reviews from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            review_json = parse_json_review(full_text)

            # Create result entry
            result = {
                "model": model,
                "ranking": full_text, # Keep raw text for debugging/fallback
                "review_json": review_json,
                "parsed_ranking": []
            }

            # Extract ranking if JSON parsing succeeded
            if review_json and "final_ranking" in review_json:
                result["parsed_ranking"] = review_json["final_ranking"]

            stage2_results.append(result)

    return stage2_results, label_to_model


async def stage25_repair(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Stage 2.5: Models repair their own responses based on aggregated findings.

    Args:
        user_query: Original user query
        stage1_results: Stage 1 responses
        stage2_results: Stage 2 reviews (containing bugs/findings)
        label_to_model: Mapping from Response Label to Model Name

    Returns:
        List of repair results (revised answers)
    """
    # 1. Aggregate findings per model (Response Label)
    # Map: Label -> List of Bugs (across all reviewers)
    findings_per_label = {label: [] for label in label_to_model.keys()}

    for reviewer_result in stage2_results:
        review_json = reviewer_result.get("review_json")
        if not review_json or "reviews" not in review_json:
            continue

        reviews = review_json["reviews"]
        for target_label, review_data in reviews.items():
            if target_label in findings_per_label and "bugs" in review_data:
                # Add bugs to the list
                findings_per_label[target_label].extend(review_data["bugs"])

    # 2. Prepare tasks for each model
    repair_tasks = {} # model_name -> messages
    original_responses = {
        result['model']: result['response']
        for result in stage1_results
    }

    results = [] # To store final results

    for label, model_name in label_to_model.items():
        if model_name not in original_responses:
            continue

        original_response = original_responses[model_name]
        bugs = findings_per_label[label]

        # Filter significant bugs (Severity >= 3)
        significant_bugs = [b for b in bugs if b.get('severity', 0) >= 3]

        # 3. No-Op Check
        if not significant_bugs:
            # Pass-through
            results.append({
                "model": model_name,
                "revised_answer": original_response,
                "fix_log": [],
                "remaining_risks": [],
                "passthrough": True
            })
            continue

        # 4. Construct Repair Prompt
        bugs_text = json.dumps(significant_bugs, indent=2)

        repair_prompt = f"""You previously provided a response to: "{user_query}"

Peer reviewers identified the following significant issues (bugs) in your response:
{bugs_text}

Your task:
1. Review these findings.
2. Fix the issues in your response.
3. Provide a revised, corrected response.

CRITICAL: Output ONLY valid JSON using this schema:
{{
  "revised_answer": "The full corrected response text (Markdown allowed)",
  "fix_log": [
    {{"issue": "Brief description of issue fixed", "change": "What you changed"}}
  ],
  "remaining_risks": ["Any known limitations remaining"],
  "passthrough": false
}}
"""
        repair_tasks[model_name] = [{"role": "user", "content": repair_prompt}]

    # 5. Execute repairs in parallel
    if repair_tasks:
        # We need to query specific models. query_models_parallel queries ALL council models with the SAME message.
        # Here we have different messages for different models.
        # We can use query_model for each task and gather them.

        # Create coroutines for each repair task
        tasks = []
        model_names = []
        for model_name, messages in repair_tasks.items():
            tasks.append(query_model(model_name, messages))
            model_names.append(model_name)

        # Run all repair tasks concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for model_name, response in zip(model_names, responses):
            if isinstance(response, Exception) or response is None:
                # Fallback to original if repair fails
                results.append({
                    "model": model_name,
                    "revised_answer": original_responses[model_name],
                    "fix_log": [{"issue": "Repair failed", "change": "Reverted to original"}],
                    "remaining_risks": ["Repair process failed"],
                    "passthrough": True # Technically failed repair implies passthrough of original
                })
            else:
                # Parse JSON response
                content = response.get('content', '')
                parsed = parse_json_review(content) # Reuse robust parser

                if parsed and "revised_answer" in parsed:
                    results.append({
                        "model": model_name,
                        "revised_answer": parsed.get("revised_answer", ""),
                        "fix_log": parsed.get("fix_log", []),
                        "remaining_risks": parsed.get("remaining_risks", []),
                        "passthrough": False
                    })
                else:
                    # Parsing failed
                    results.append({
                        "model": model_name,
                        "revised_answer": original_responses[model_name],
                        "fix_log": [{"issue": "Repair JSON parse failed", "change": "Reverted to original"}],
                        "remaining_risks": ["Repair parsing failed"],
                        "passthrough": True
                    })

    return results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Legacy Stage 2: Text-based ranking (kept for reference, usually bypassed by stage2_collect_reviews).
    """
    return await stage2_collect_reviews(user_query, stage1_results)


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage25_results: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        stage25_results: Revised responses from Stage 2.5 (optional)

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman

    # Check if we have revised answers
    if stage25_results:
        stage1_context_header = "STAGE 2.5 - Revised Responses (after Peer Review):"
        responses_text = ""
        for result in stage25_results:
            model = result['model']
            revised = result['revised_answer']
            fix_log = result.get('fix_log', [])
            passthrough = result.get('passthrough', False)

            changes_text = "No changes (passed validation)." if passthrough else "Changes made:\n" + "\n".join([f"- {entry.get('issue')}: {entry.get('change')}" for entry in fix_log])

            responses_text += f"\n\nModel: {model}\nStatus: {changes_text}\nResponse:\n{revised}"
    else:
        stage1_context_header = "STAGE 1 - Individual Responses:"
        responses_text = "\n\n".join([
            f"Model: {result['model']}\nResponse: {result['response']}"
            for result in stage1_results
        ])

    stage2_text = ""
    for result in stage2_results:
        model_name = result['model']
        if result.get('review_json'):
            # Use structured JSON content
            json_content = json.dumps(result['review_json'], indent=2, ensure_ascii=False)
            stage2_text += f"\n\nModel: {model_name}\nReview (JSON): {json_content}"
        else:
            # Fallback to raw text
            stage2_text += f"\n\nModel: {model_name}\nReview: {result['ranking']}"

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, peer-reviewed each other, and then refined their answers.

Original Question: {user_query}

{stage1_context_header}
{responses_text}

STAGE 2 - Peer Findings (Reference):
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question.

Important:
- Use the REVISED responses from Stage 2.5 as your primary source material, as they have been improved based on peer review.
- Check the 'fix_log' to see what was corrected.
- Verify if the revised answers actually address the findings in Stage 2.
- If a model failed to fix a critical issue, correct it in your final synthesis.

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

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
    Parse the FINAL RANKING section from the model's response.

    Note: This is now mostly used as a fallback or by legacy functions.
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
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
        # Prioritize parsed ranking from JSON
        parsed_ranking = ranking.get('parsed_ranking', [])

        # Fallback to text parsing if empty
        if not parsed_ranking and ranking.get('ranking'):
             parsed_ranking = parse_ranking_from_text(ranking['ranking'])

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
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

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


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict, List]:
    """
    Run the complete 3-stage council process (plus stage 2.5).

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata, stage25_results)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}, []

    # Stage 2: Collect reviews (JSON)
    stage2_results, label_to_model = await stage2_collect_reviews(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 2.5: Self-repair
    stage25_results = await stage25_repair(user_query, stage1_results, stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        stage25_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata, stage25_results
