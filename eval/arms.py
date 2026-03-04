"""Arm configurations for the 3-arm eval: MCP, Skill-LobeHub, Skill-Vault."""

import os
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

SKILLS_DIR = Path(__file__).parent / "skills"

# Base system prompt appended to all arms
BASE_PROMPT = (
    "You are performing a GitHub operations task. "
    "Answer concisely with the specific information requested. "
    "Do not explain your process unless asked."
)


def _load_skill(filename: str) -> str:
    path = SKILLS_DIR / filename
    return path.read_text()


def get_arm_options(arm: str, repo: str) -> ClaudeAgentOptions:
    """Return ClaudeAgentOptions for the given arm name."""
    repo_prompt = f"\nTarget GitHub repo: {repo}"

    if arm == "mcp":
        return _mcp_options(repo, repo_prompt)
    elif arm == "lobehub":
        return _lobehub_options(repo_prompt)
    elif arm == "vault":
        return _vault_options(repo_prompt)
    else:
        raise ValueError(f"Unknown arm: {arm!r}. Choose from: mcp, lobehub, vault")


def _mcp_options(repo: str, repo_prompt: str) -> ClaudeAgentOptions:
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "GITHUB_PERSONAL_ACCESS_TOKEN must be set in eval/.env for the MCP arm"
        )

    return ClaudeAgentOptions(
        allowed_tools=["mcp__github__*"],
        mcp_servers={
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": token},
            }
        },
        system_prompt=BASE_PROMPT + repo_prompt + "\nUse MCP tools for all GitHub operations.",
        max_turns=25,
    )


def _lobehub_options(repo_prompt: str) -> ClaudeAgentOptions:
    skill_content = _load_skill("gh-cli-lobehub.md")
    return ClaudeAgentOptions(
        allowed_tools=["Bash(gh *)", "Bash(git *)", "Read", "Glob", "Grep"],
        system_prompt=skill_content + "\n\n" + BASE_PROMPT + repo_prompt,
        max_turns=25,
    )


def _vault_options(repo_prompt: str) -> ClaudeAgentOptions:
    skill_content = _load_skill("github-cli-vault.md")
    return ClaudeAgentOptions(
        allowed_tools=["Bash(gh *)", "Bash(git *)", "Read", "Glob", "Grep"],
        system_prompt=skill_content + "\n\n" + BASE_PROMPT + repo_prompt,
        max_turns=25,
    )


ARM_NAMES = ["mcp", "lobehub", "vault"]
