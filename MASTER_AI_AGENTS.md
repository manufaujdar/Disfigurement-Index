# Shared AI agents and resources

[Master registry](https://github.com/manufaujdar/master-github-ai-agents) · pinned revision `f8042c51d3fdd10c8be4bdefc0ee0536f621809f`.
This repository has seven original shared role prompts, an automatically discoverable `$master-repo-team` skill, and its own
[project context](.ai/master-agents/PROFILE.md).

Use planning → building → review → QA → documentation as applicable. Select
security or synchronization for tasks that need them. Prefer the existing
specialist team; only load the selected role. The full source catalog remains
available, including licensed Agency roles and GitBot presets. Availability
and role registration do not establish runtime behavior or grant tool access.

```sh
gh api 'repos/manufaujdar/master-github-ai-agents/contents/catalog.json?ref=f8042c51d3fdd10c8be4bdefc0ee0536f621809f' \
  -H 'Accept: application/vnd.github.raw+json' \
  --jq '.entries[] | select(.archived == false and (.repository == "manufaujdar/Disfigurement-Index" or .scope == "portable")) | {id, kind, scope, revision, blob_sha, url}'
```

For other sources use the installed `$master-github-ai-agents` skill or the
master checkout's `registry.py list` and `registry.py show ID --output NEW_FILE`.
Authenticate for private sources and keep repository-scoped content local.
Review source setup, license and requirements before adopting a runtime.

The [managed manifest](.ai/master-agents/manifest.json) records content hashes.
Change personalization in the master `profiles.json`; `prepare_rollout.py`
checks remote managed files for manual drift before preparing an update.
Review the patch, run project checks, then commit/push its existing draft branch.
No merge, dependency, provider call, server or background schedule is added.

Rollback: remove this guide, `.ai/master-agents/`, the `master-repo-team` skill,
and the Shared AI-agent resources section in root `AGENTS.md`. Existing team
instructions and safety, evidence, privacy and release gates retain authority.
