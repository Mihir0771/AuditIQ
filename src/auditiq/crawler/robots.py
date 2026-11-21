"""RFC 9309 compliant robots.txt parser and AI bot rule evaluator."""

import contextlib
import fnmatch
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class Rule(BaseModel):
    allow: bool
    pattern: str


class UserAgentBlock(BaseModel):
    user_agents: list[str] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)
    crawl_delay: float | None = None


class RobotsTxtInfo(BaseModel):
    sitemaps: list[str] = Field(default_factory=list)
    blocks: list[UserAgentBlock] = Field(default_factory=list)
    raw_content: str = ""


class RobotsTxtParser:
    """Parses and evaluates robots.txt files following RFC 9309 specifications."""

    def __init__(self, content: str = "") -> None:
        self.info = RobotsTxtInfo(raw_content=content)
        if content:
            self.parse(content)

    def parse(self, content: str) -> None:
        """Parses the text of a robots.txt file into structured user-agent blocks."""
        self.info = RobotsTxtInfo(raw_content=content)
        current_block: UserAgentBlock | None = None
        has_rules_in_current_block = False

        for raw_line in content.splitlines():
            line = raw_line.strip()
            # Remove comments
            if "#" in line:
                line = line[: line.find("#")].strip()
            if not line:
                continue

            if ":" not in line:
                continue

            field, _, value = line.partition(":")
            field = field.strip().lower()
            value = value.strip()

            if field == "user-agent":
                ua = value.lower()
                # If the previous block already had rules, start a fresh block
                if current_block is None or has_rules_in_current_block:
                    current_block = UserAgentBlock(user_agents=[ua])
                    self.info.blocks.append(current_block)
                    has_rules_in_current_block = False
                else:
                    current_block.user_agents.append(ua)

            elif field == "disallow":
                if current_block is not None:
                    # Empty disallow means allow everything
                    if not value:
                        current_block.rules.append(Rule(allow=True, pattern="/"))
                    else:
                        current_block.rules.append(Rule(allow=False, pattern=value))
                    has_rules_in_current_block = True

            elif field == "allow":
                if current_block is not None and value:
                    current_block.rules.append(Rule(allow=True, pattern=value))
                    has_rules_in_current_block = True

            elif field == "crawl-delay":
                if current_block is not None:
                    with contextlib.suppress(ValueError):
                        current_block.crawl_delay = float(value)

            elif field == "sitemap" and value and value not in self.info.sitemaps:
                self.info.sitemaps.append(value)

    def is_allowed(self, user_agent: str, url_or_path: str) -> bool:
        """Determines if a specific user-agent is permitted to crawl the given path."""
        parsed = urlparse(url_or_path)
        path = parsed.path or "/"

        ua_lower = user_agent.lower()

        # 1. Look for an exact user-agent block match
        matching_block: UserAgentBlock | None = None
        for block in self.info.blocks:
            for agent in block.user_agents:
                if agent == ua_lower:
                    matching_block = block
                    break
            if matching_block:
                break

        # 2. Fall back to wildcard '*' block
        if not matching_block:
            for block in self.info.blocks:
                if "*" in block.user_agents:
                    matching_block = block
                    break

        if not matching_block or not matching_block.rules:
            return True  # If no rule matches, default is allowed

        # 3. RFC 9309 rule matching: longest pattern wins; on tie, Allow wins
        best_match_rule: Rule | None = None
        best_match_length = -1

        for rule in matching_block.rules:
            if self._path_matches(rule.pattern, path):
                pattern_len = len(rule.pattern)
                if pattern_len > best_match_length:
                    best_match_rule = rule
                    best_match_length = pattern_len
                elif (
                    pattern_len == best_match_length
                    and rule.allow
                    and best_match_rule is not None
                    and not best_match_rule.allow
                ):
                    # Allow takes precedence over Disallow on equal length
                    best_match_rule = rule

        if best_match_rule is not None:
            return best_match_rule.allow

        return True

    def get_crawl_delay(self, user_agent: str) -> float | None:
        """Retrieves configured crawl-delay for the given user-agent, if any."""
        ua_lower = user_agent.lower()
        for block in self.info.blocks:
            if ua_lower in block.user_agents and block.crawl_delay is not None:
                return block.crawl_delay
        for block in self.info.blocks:
            if "*" in block.user_agents and block.crawl_delay is not None:
                return block.crawl_delay
        return None

    def evaluate_ai_bot_matrix(
        self, known_bots: list[dict[str, str]], test_paths: list[str]
    ) -> dict[str, dict[str, bool]]:
        """Evaluates permission matrix for a list of known AI bot user-agents across key paths.

        Returns:
            { "GPTBot": { "/": True, "/blog": True, "/api": False }, ... }
        """
        matrix: dict[str, dict[str, bool]] = {}
        for bot in known_bots:
            ua = bot.get("user_agent", bot.get("name", ""))
            matrix[ua] = {}
            for path in test_paths:
                matrix[ua][path] = self.is_allowed(ua, path)
        return matrix

    @staticmethod
    def _path_matches(pattern: str, path: str) -> bool:
        """Tests whether a URL path matches a robots.txt pattern (handling * and $)."""
        if not pattern:
            return True

        # End of path marker $
        ends_with_dollar = pattern.endswith("$")
        if ends_with_dollar:
            pattern = pattern[:-1]

        # Escape special regex/glob characters except *
        # RFC 9309 specifies standard prefix matching with '*' wildcard
        if "*" not in pattern:
            if ends_with_dollar:
                return path == pattern
            return path.startswith(pattern)

        # Handle wildcard pattern using fnmatch
        glob_pattern = pattern if pattern.endswith("*") else f"{pattern}*"
        return fnmatch.fnmatchcase(path, glob_pattern)
