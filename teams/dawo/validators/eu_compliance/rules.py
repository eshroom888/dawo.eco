"""Compliance rules management for EU Compliance Checker.

Handles loading and accessing compliance rules configuration.
Rules are loaded via dependency injection - NEVER directly from files.
"""

from typing import Optional


class ComplianceRules:
    """Manages EU compliance rules configuration.

    Provides access to prohibited, borderline, and permitted patterns
    as well as Novel Food classifications.

    CRITICAL: Rules are injected at initialization - NEVER load from files directly.

    Attributes:
        regulation: Regulation identifier (e.g., "EC 1924/2006")
        version: Rules version for tracking updates
        prohibited_patterns: List of prohibited phrase patterns
        borderline_patterns: List of borderline phrase patterns
        permitted_patterns: List of permitted phrase patterns
        novel_food_classifications: Product classification lookup
    """

    def __init__(self, config: dict):
        """Initialize rules from configuration dictionary.

        Args:
            config: Compliance rules configuration dictionary.
                   Injected by Team Builder - NEVER load from file.

        Raises:
            ValueError: If required configuration keys are missing
        """
        self._validate_config(config)

        self.regulation = config.get("regulation", "EC 1924/2006")
        self.version = config.get("version", "unknown")
        self.prohibited_patterns = config.get("prohibited_patterns", [])
        self.borderline_patterns = config.get("borderline_patterns", [])
        self.permitted_patterns = config.get("permitted_patterns", [])
        self.novel_food_classifications = config.get("novel_food_classifications", {})

    def _validate_config(self, config: dict) -> None:
        """Validate configuration has required structure.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If required keys are missing or malformed
        """
        required_keys = [
            "prohibited_patterns",
            "borderline_patterns",
            "permitted_patterns",
        ]

        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required configuration key: {key}")

            if not isinstance(config[key], list):
                raise ValueError(f"Configuration key '{key}' must be a list")

    def get_novel_food_classification(self, product_name: str) -> Optional[dict]:
        """Look up Novel Food classification for a product.

        Args:
            product_name: Normalized product name (lowercase, underscores)

        Returns:
            Classification dict with 'status' and 'use' keys, or None if not found
        """
        # Try exact match first
        if product_name in self.novel_food_classifications:
            return self.novel_food_classifications[product_name]

        # Try common variations
        variations = [
            product_name,
            product_name.replace("_", " "),
            product_name.replace(" ", "_"),
            product_name.replace("'", ""),
            product_name.replace("-", "_"),
        ]

        for variant in variations:
            if variant in self.novel_food_classifications:
                return self.novel_food_classifications[variant]

        return None

    def is_prohibited_pattern(self, text: str) -> bool:
        """Quick check if text contains any prohibited pattern.

        Args:
            text: Text to check

        Returns:
            True if any prohibited pattern is found
        """
        text_lower = text.lower()
        return any(
            pattern["pattern"].lower() in text_lower
            for pattern in self.prohibited_patterns
        )

    def is_borderline_pattern(self, text: str) -> bool:
        """Quick check if text contains any borderline pattern.

        Args:
            text: Text to check

        Returns:
            True if any borderline pattern is found
        """
        text_lower = text.lower()
        return any(
            pattern["pattern"].lower() in text_lower
            for pattern in self.borderline_patterns
        )

    def get_all_prohibited_terms(self) -> list[str]:
        """Get list of all prohibited pattern terms.

        Returns:
            List of prohibited pattern strings
        """
        return [p["pattern"] for p in self.prohibited_patterns]

    def get_all_borderline_terms(self) -> list[str]:
        """Get list of all borderline pattern terms.

        Returns:
            List of borderline pattern strings
        """
        return [p["pattern"] for p in self.borderline_patterns]

    def get_all_permitted_terms(self) -> list[str]:
        """Get list of all permitted pattern terms.

        Returns:
            List of permitted pattern strings
        """
        return [p["pattern"] for p in self.permitted_patterns]
