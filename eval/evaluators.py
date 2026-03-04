"""Evaluators for scoring agent outputs against expected results.

Each evaluator returns an arize.experiments.EvaluationResult.
"""

import json
import logging
import os
import re
import subprocess

from arize.experiments import EvaluationResult

logger = logging.getLogger(__name__)


def evaluate_task(output: str, task: dict) -> EvaluationResult:
    """Route to the correct evaluator based on task expected_output type."""
    expected = task.get("expected_output", {})
    eval_type = expected.get("type", "")

    if eval_type == "exact":
        return exact_match(output, expected)
    elif eval_type == "structured":
        return structured_match(output, expected)
    elif eval_type == "state_check":
        return state_check(output, expected, task)
    elif eval_type == "llm_judge":
        return llm_judge(output, expected)
    elif eval_type == "approximate":
        return approximate_match(output, expected)
    else:
        return EvaluationResult(
            score=0, label="unknown_type",
            explanation=f"Unknown expected_output type: {eval_type}",
        )


def exact_match(output: str, expected: dict) -> EvaluationResult:
    """Compare agent output to an exact expected value."""
    value = expected["value"]
    output_lower = output.lower().strip()

    if isinstance(value, list):
        # Check all items appear in the output
        found = [str(v).lower() in output_lower for v in value]
        score = sum(found) / len(found) if found else 0
        label = "correct" if all(found) else "partial" if any(found) else "incorrect"
        missing = [str(v) for v, f in zip(value, found) if not f]
        explanation = f"Expected {value}. Missing: {missing}" if missing else "All values found."
    elif isinstance(value, (int, float)):
        # Look for the number in the output
        numbers = re.findall(r'\b' + str(value) + r'\b', output)
        score = 1.0 if numbers else 0.0
        label = "correct" if numbers else "incorrect"
        explanation = f"Expected {value}. {'Found' if numbers else 'Not found'} in output."
    else:
        # String comparison
        str_value = str(value).lower()
        score = 1.0 if str_value in output_lower else 0.0
        label = "correct" if score == 1.0 else "incorrect"
        explanation = f"Expected '{value}'. {'Found' if score else 'Not found'} in output."

    return EvaluationResult(score=score, label=label, explanation=explanation)


def approximate_match(output: str, expected: dict) -> EvaluationResult:
    """For approximate-type tasks, do a best-effort keyword check."""
    value = expected.get("value", "")
    explanation = expected.get("explanation", "")

    # Extract key terms from the expected value/explanation
    if isinstance(value, dict):
        key_terms = list(value.values())
    elif isinstance(value, str):
        key_terms = [value]
    else:
        key_terms = [str(value)]

    output_lower = output.lower()
    found = sum(1 for term in key_terms if str(term).lower() in output_lower)
    total = max(len(key_terms), 1)
    score = found / total

    return EvaluationResult(
        score=score,
        label="approximate" if score > 0.5 else "mismatch",
        explanation=f"Matched {found}/{total} key terms. Expected: {value}",
    )


def structured_match(output: str, expected: dict) -> EvaluationResult:
    """Check that expected structured fields appear in the output."""
    value = expected["value"]
    output_lower = output.lower()
    checks_passed = 0
    checks_total = 0
    details = []

    def check_value(key, val):
        nonlocal checks_passed, checks_total
        checks_total += 1
        str_val = str(val).lower()
        if str_val in output_lower:
            checks_passed += 1
            details.append(f"  [pass] {key}: {val}")
        else:
            details.append(f"  [fail] {key}: {val}")

    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, list):
                for item in v:
                    check_value(k, item)
            else:
                check_value(k, v)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, list):
                        for sub in v:
                            check_value(k, sub)
                    else:
                        check_value(k, v)
            else:
                check_value("item", item)

    score = checks_passed / checks_total if checks_total > 0 else 0
    label = "correct" if score >= 0.8 else "partial" if score > 0.3 else "incorrect"

    return EvaluationResult(
        score=score, label=label,
        explanation=f"Matched {checks_passed}/{checks_total} fields.\n" + "\n".join(details),
    )


def state_check(output: str, expected: dict, task: dict) -> EvaluationResult:
    """Verify repo state after a write operation using gh CLI."""
    checks = expected.get("checks", [])
    repo = os.environ.get("EVAL_REPO", "")
    passed = 0
    details = []

    for check_desc in checks:
        result = _verify_state_check(check_desc, repo)
        if result:
            passed += 1
            details.append(f"  [pass] {check_desc}")
        else:
            details.append(f"  [fail] {check_desc}")

    total = max(len(checks), 1)
    score = passed / total
    label = "correct" if score == 1.0 else "partial" if score > 0 else "incorrect"

    return EvaluationResult(
        score=score, label=label,
        explanation=f"State checks: {passed}/{total} passed.\n" + "\n".join(details),
    )


def _verify_state_check(check_desc: str, repo: str) -> bool:
    """Run a gh CLI command to verify a single state check.

    Parses the check description to determine what to verify.
    """
    desc_lower = check_desc.lower()

    try:
        # Check if an issue is closed
        if "is closed" in desc_lower:
            num = _extract_issue_number(check_desc)
            if num:
                result = subprocess.run(
                    ["gh", "issue", "view", str(num), "--repo", repo, "--json", "state", "--jq", ".state"],
                    capture_output=True, text=True, timeout=10,
                )
                return result.stdout.strip().upper() == "CLOSED"

        # Check if an issue has a label
        if "has the" in desc_lower and "label" in desc_lower:
            num = _extract_issue_number(check_desc)
            label_match = re.search(r"'([^']+)'\s*label", check_desc)
            if num and label_match:
                label = label_match.group(1)
                result = subprocess.run(
                    ["gh", "issue", "view", str(num), "--repo", repo, "--json", "labels", "--jq", "[.labels[].name] | join(\",\")"],
                    capture_output=True, text=True, timeout=10,
                )
                return label in result.stdout.strip()

        # Check if a label exists
        if "label" in desc_lower and "exists" in desc_lower:
            label_match = re.search(r"'([^']+)'", check_desc)
            if label_match:
                label = label_match.group(1)
                result = subprocess.run(
                    ["gh", "label", "list", "--repo", repo, "--json", "name", "--jq", ".[].name"],
                    capture_output=True, text=True, timeout=10,
                )
                return label in result.stdout.strip().split("\n")

        # Check if a PR exists
        if "pr exists" in desc_lower or "pr" in desc_lower and "has a review" in desc_lower:
            num = _extract_pr_number(check_desc)
            if num:
                result = subprocess.run(
                    ["gh", "pr", "view", str(num), "--repo", repo, "--json", "state", "--jq", ".state"],
                    capture_output=True, text=True, timeout=10,
                )
                return result.stdout.strip().upper() == "OPEN"

        # Check if an issue exists with a title
        if "issue exists" in desc_lower:
            title_match = re.search(r"'([^']+)'", check_desc)
            if title_match:
                title = title_match.group(1)
                result = subprocess.run(
                    ["gh", "issue", "list", "--repo", repo, "--state", "open", "--search", title, "--json", "title", "--jq", ".[].title"],
                    capture_output=True, text=True, timeout=10,
                )
                return title in result.stdout.strip()

        # Check if an issue has a comment
        if "has a comment" in desc_lower:
            num = _extract_issue_number(check_desc)
            if num:
                result = subprocess.run(
                    ["gh", "issue", "view", str(num), "--repo", repo, "--json", "comments", "--jq", ".comments | length"],
                    capture_output=True, text=True, timeout=10,
                )
                count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                return count > 0

        # Check if a branch exists on remote
        if "branch" in desc_lower and "exists" in desc_lower:
            branch_match = re.search(r"(?:branch\s+)?(\S+)\s+exists", check_desc, re.IGNORECASE)
            if branch_match:
                branch = branch_match.group(1)
                result = subprocess.run(
                    ["git", "ls-remote", "--heads", "origin", branch],
                    capture_output=True, text=True, timeout=10,
                )
                return branch in result.stdout

    except (subprocess.TimeoutExpired, ValueError):
        pass

    logger.warning("Could not verify state check: %s", check_desc)
    return False


def _extract_issue_number(text: str) -> int | None:
    match = re.search(r'#(\d+)', text)
    return int(match.group(1)) if match else None


def _extract_pr_number(text: str) -> int | None:
    match = re.search(r'PR\s*#(\d+)', text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def judge_output_quality(output: str, task: dict) -> EvaluationResult:
    """LLM-as-judge scoring completeness, accuracy, and organization for tier 4 tasks.

    Returns a normalized 0-1 score based on three dimensions:
    - Completeness: Did it include all expected items?
    - Accuracy: Are the facts correct, no hallucinations?
    - Organization: Is the output well-structured and usable?
    """
    from anthropic import Anthropic

    description = task.get("description", "")
    criteria = task.get("expected_output", {}).get("criteria", [])
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""You are evaluating the quality of an AI agent's analysis output.

## Task
{description}

## Agent Output
{output}

## Reference Criteria
{criteria_text}

## Instructions
Score the output on three dimensions (each 1-5):

1. **Completeness**: Does the output cover all the items and aspects mentioned in the criteria? Are there gaps?
2. **Accuracy**: Are the stated facts correct? Is there any hallucinated or fabricated content?
3. **Organization**: Is the output well-structured, clear, and directly usable? Or is it rambling/disorganized?

Respond in JSON:
{{"completeness": <1-5>, "accuracy": <1-5>, "organization": <1-5>, "explanation": "<brief summary>"}}"""
        }],
    )

    try:
        response_text = response.content[0].text
        json_match = re.search(r'\{[^{}]*"completeness"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            comp = result.get("completeness", 0)
            acc = result.get("accuracy", 0)
            org = result.get("organization", 0)
            avg = (comp + acc + org) / 3.0
            normalized = avg / 5.0
            label = "good" if avg >= 4 else "fair" if avg >= 2.5 else "poor"
            return EvaluationResult(
                score=normalized, label=label,
                explanation=f"completeness={comp}/5, accuracy={acc}/5, organization={org}/5. {result.get('explanation', '')}",
            )
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    return EvaluationResult(
        score=0, label="judge_error",
        explanation=f"Failed to parse quality judge response: {response.content[0].text[:200]}",
    )


def llm_judge(output: str, expected: dict) -> EvaluationResult:
    """Use Claude Opus as LLM-as-judge to score output against criteria."""
    from anthropic import Anthropic

    criteria = expected.get("criteria", [])
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    client = Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""You are an evaluation judge. Score the following agent output against the criteria below.

## Agent Output
{output}

## Criteria
{criteria_text}

## Instructions
For each criterion, determine if the output meets it (yes/no).
Then provide an overall score from 0 to 5:
- 5: All criteria fully met
- 4: Most criteria met, minor gaps
- 3: About half the criteria met
- 2: Some criteria met but significant gaps
- 1: Very few criteria met
- 0: No criteria met or output is irrelevant

Respond in JSON format:
{{"score": <0-5>, "met": [<criteria that were met>], "missed": [<criteria that were missed>], "explanation": "<brief explanation>"}}"""
        }],
    )

    try:
        response_text = response.content[0].text
        # Extract JSON from response (may be wrapped in markdown code blocks)
        json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            raw_score = result.get("score", 0)
            normalized = raw_score / 5.0  # Normalize to 0-1
            label = "good" if raw_score >= 4 else "fair" if raw_score >= 2 else "poor"
            return EvaluationResult(
                score=normalized, label=label,
                explanation=result.get("explanation", response_text),
            )
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    return EvaluationResult(
        score=0, label="judge_error",
        explanation=f"Failed to parse LLM judge response: {response_text[:200]}",
    )
