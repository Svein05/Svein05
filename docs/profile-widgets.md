# Profile widgets

## Stargazers

`update_stars.py` generates `assets/svg/stargazers.svg` from all public repositories
owned by the profile account, including forks. The README displays it below the
contribution snake and above Recent Git Activity. The previous Metrics stargazer
widget and its generation job have been replaced; Steam metrics remain separate.

- English heading: `Stargazers - <current month>`, with the global total at top right.
- `Most starred` and `Latest starred` share one row. Ties for most stars use the
  repository name alphabetically; latest uses the newest surviving star timestamp.
- The horizontal scale reserves one position for each calendar day of the current
  month, including future dates, using `America/Santiago`.
- Only days with changes have a point, a signed delta and a date directly below
  that point. Unchanged days extend the line without adding markers.
- The vertical scale normally starts at the previous month's closing total and
  ends at the current total. Intermediate ticks are distinct integers, with at
  most five ticks including the exact endpoints. A flat month has one tick and
  a horizontal line, without fabricated stars or division by zero.
- If stars are removed, the scale expands to include observed historical values
  and the loss is shown as a negative delta. This avoids hiding a real decrease.

The workflow runs once daily at `02:47 UTC`, which is 22:47 or 23:47 in Santiago,
before the next local date. GitHub's scheduler can delay a run; this schedule is
not a guarantee of execution before midnight. Manual dispatch is also available.
The last daily observation replaces earlier observations on the same local date.

`assets/data/stars-history.json` stores aggregate daily totals and monthly
baselines, without stargazer identities. On the first run, dates are reconstructed
from currently active stars. Previously removed stars cannot be recovered, so
the initial historical baseline is a reconstruction, not a verified historical
snapshot. Later runs preserve daily observations; at rollover, an observed total
on the previous month's final day takes priority. If that day was missed, the
new baseline is reconstructed from current stars and their dates.

The API is fully paginated, uses timeouts, and fails before writing output if any
repository request fails. It uses `METRICS_TOKEN`, falling back to `GITHUB_TOKEN`.
The token must be able to list stargazers for all owned public repositories.
Local runs use environment tokens when provided, or anonymous public API access;
the script never reads credentials from Git Credential Manager.

```sh
python .github/scripts/update_stars.py
python -m unittest discover -s .github/scripts -p 'test_*.py'
```

## Recent Git Activity

Long repository/branch badges are shortened with an ellipsis to leave a fixed
timestamp area and gap in each column. The original label is retained in SVG
`title` metadata. XML escaping is applied after shortening.

The activity, stargazer and Steam workflows share a concurrency group to serialize
writes. The script-based publishers merge remote updates before pushing generated
assets, preserving history without rebasing or force pushes.
