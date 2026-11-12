# Rules in force

`active/` holds the rules this repository's demonstration judge applies on top of the
`collections-conduct` pack. Changing them works like changing code:

1. Open a pull request that adds or edits a file in `active/`.
2. [`.github/workflows/rules.yml`](../.github/workflows/rules.yml) runs the
   [Precedent gate](../action.yml) on the changed rules. It uses the corrections in
   `corrections.yaml` and the other active rules.
3. The gate report is posted on the pull request. A BLOCKED rule fails the check.
4. A reviewer other than the author approves, and the merge makes the rule active.
   A revert is a pull request too.

It is the project's own process running on itself.
