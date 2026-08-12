"""Offline diligence harness for Catalyst/HALO public-sandbox evaluation."""

__version__ = "0.1.0"

BASELINE_COMMIT = "d674a065819a0bd45357f8530b4f15775bfdaac9"
EXPECTED_REPO_SUFFIXES = ("bitcoin-sat-tracker",)
ALLOWED_ARMS = (
    "codex-native-otel",
    "codex-openinference",
    "codex-baseline",
    "codex-halo",
    "gateway-base",
    "small-base",
    "small-tuned",
    "gpt56-reference",
    "offline-fixture",
)
ALLOWED_SPLITS = ("dev", "holdout")
PHASE2_ARMS = tuple(a for a in ALLOWED_ARMS if a != "offline-fixture")
