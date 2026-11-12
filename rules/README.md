# Rules under review

This directory is gated by [`.github/workflows/rules.yml`](../.github/workflows/rules.yml).
A pull request that adds or changes a file in `proposed/` runs the
[Precedent gate](../action.yml) against the `collections-conduct` pack. The gate
uses the corrections in `corrections.yaml` and the rules already in `active/`.
The result is posted as a comment on the pull request and in the job summary.
A BLOCKED rule fails the check.

It is the project's own process running on itself: a change to how the judge
decides goes through the same review as a change to code.
