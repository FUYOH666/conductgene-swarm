"""Precedent: pull requests for AI judgment.

A human correction of an AI judge becomes a scoped, versioned rule. The rule
has to pass a blocking gate before it can change a single verdict, needs a
second person to approve it, and can be reverted. Every step is written to a
hash-chained event log.
"""

__version__ = "2.0.0.dev0"
