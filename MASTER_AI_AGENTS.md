# Shared AI agents and resources

This project can discover shared agents through the private
[master registry](https://github.com/manufaujdar/master-github-ai-agents).
Pinned master revision: `3d2668ea268b923a68548ebbb6d7bd2e494fac9f`.

Prefer this project's existing team and installed adaptations. Use the shared
catalog when a task needs another role, skill or resource. Its repository-scoped
definitions apply only to their source project; portable definitions are reusable
task guidance. Archived entries are inactive. Runtime candidates are source
references and require separate implementation and validation.

For example, list review-related portable definitions and this project's sources:

```sh
gh api 'repos/manufaujdar/master-github-ai-agents/contents/catalog.json?ref=3d2668ea268b923a68548ebbb6d7bd2e494fac9f' \
  -H 'Accept: application/vnd.github.raw+json' \
  --jq '.entries[] | select(.archived == false and (.repository == "manufaujdar/Disfigurement-Index" or .scope == "portable")) | select(.id | test("review"; "i")) | {id, kind, scope, revision, blob_sha, url}'
```

Use the installed `$master-github-ai-agents` skill, or the master checkout's
`registry.py list` and `registry.py show ENTRY_ID --output OUTPUT`, to retrieve
one hash-verified definition into an approved local area. Authenticate with `gh`
for private sources. Record the selected source and revision in this project's
existing task record. Read source setup requirements before considering execution.

Availability does not grant provider calls, new runtime tools, parallel work,
publication or release authority. Existing evidence, privacy, safety and review
gates govern the selected task. This integration changes development guidance;
it adds no agent service, package dependency, application behavior or background job.

Rollback: remove this file and the Shared AI-agent resources section in `AGENTS.md`.
