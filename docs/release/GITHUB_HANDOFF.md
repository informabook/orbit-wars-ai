# GitHub release handoff

Use the following settings for the initial private repository. Run the commands after reviewing the local release candidate. Commands assume you are in the `orbit-wars-ai` directory with Git, GitHub CLI and Python available.

| Setting | Value |
| --- | --- |
| Repository | `orbit-wars-ai` |
| Description | Reusable research framework for autonomous strategic agents, replay-based learning, automated agent search and multi-stage validation in Kaggle Orbit Wars. |
| Release title | Orbit Wars v0.3.0 — Reusable research framework |
| Initial commit | `Initial release of Orbit Wars research framework (v0.3.0)` |
| Profile pin | After the approved public release, pin `orbit-wars-ai` on the GitHub profile. The public README leads with the documented placement, full V5 report and graphical research workflow. |

Topics: `artificial-intelligence`, `machine-learning`, `multi-agent-systems`, `autonomous-agents`, `kaggle`, `orbit-wars`, `evolutionary-search`, `reproducible-research`, `game-ai`, `experimental-validation`.

## Create and push the private repository

~~~powershell
gh auth status --hostname github.com
if (-not (Test-Path -LiteralPath .git)) { git init -b main }
git status --short --branch
git -c core.autocrlf=false add -A
python -c "import csv, hashlib, subprocess; rows = list(csv.DictReader(open('docs/release/PUBLIC_FILES.csv', encoding='utf-8'))); expected = {r['path'] for r in rows}; actual = {p.decode('utf-8') for p in subprocess.check_output(['git', 'ls-files', '-z']).split(bytes(1)) if p}; assert actual == expected, (actual - expected, expected - actual); mismatched = [r['path'] for r in rows if r['sha256'] and hashlib.sha256(subprocess.check_output(['git','show',':' + r['path']])).hexdigest() != r['sha256']]; assert not mismatched, mismatched"
git -c core.whitespace=cr-at-eol,-blank-at-eof diff --cached --check
git diff --cached --stat
git commit -m "Initial release of Orbit Wars research framework (v0.3.0)"
gh repo create orbit-wars-ai --private --source=. --remote=origin --description "Reusable research framework for autonomous strategic agents, replay-based learning, automated agent search and multi-stage validation in Kaggle Orbit Wars." --push
gh repo edit --add-topic artificial-intelligence,machine-learning,multi-agent-systems,autonomous-agents,kaggle,orbit-wars,evolutionary-search,reproducible-research,game-ai,experimental-validation
gh repo view --json nameWithOwner,visibility,url
~~~

The diff check accepts the line endings and final blank lines present in the reviewed Phase 3 files. Stop if the inventory assertion or staged diff checks fail. If the name already exists on the intended account, inspect that repository before attaching the local tree to it. Confirm `PRIVATE` in the final command. Review the README, PDF, Actions and file list on the private repository, then obtain explicit owner approval for public visibility.

## Prepare the release and publish only after validation

These commands require a confirmed private origin and explicit final owner validation. The draft ships the exact contents in Git at the tag. The audit ZIP can also be attached if desired.

~~~powershell
git tag -a v0.3.0 -m "Orbit Wars v0.3.0"
git push origin v0.3.0
gh release create v0.3.0 --verify-tag --draft --title "Orbit Wars v0.3.0 — Reusable research framework" --notes-file docs/release/RELEASE_NOTES_v0.3.0.md
~~~

After the final approval to publish, switch visibility, publish the release and confirm the URL.

~~~powershell
gh repo edit --visibility public --accept-visibility-change-consequences
gh release edit v0.3.0 --draft=false
gh repo view --json nameWithOwner,visibility,url
~~~

Once the repository is public, add its actual URL to the approved LinkedIn post. The remaining post text stays as approved.
