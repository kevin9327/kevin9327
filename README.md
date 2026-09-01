### Hi, I'm Kevin

I find bugs in other people's code and send the fix.

Mostly the kind that only show up in production: state that breaks the moment you
run a second replica, a policy rule that silently disables the surface it wasn't
written for, a retry loop that never terminates. I read the codebase first, prove
the bug with a test that fails before and passes after, then open the PR.

**Rust · TypeScript · Python**

---

### Recent contributions

| Project | | What landed |
|---|---|---|
| [CopilotKit/OpenBot](https://github.com/CopilotKit/OpenBot) | `12 commits` | Moved the gateway snapshot cache to Postgres so element refs resolve across replicas · stopped a policy rule for one action surface from refusing every other one · fixed dry-run recording a refused connector call as a success |
| [edwardkim/rhwp](https://github.com/edwardkim/rhwp) | `600+ commits` | Document rendering fidelity, CLI/agent surface, static-analysis panic fixes |
| [leookun/cursor-byok](https://github.com/leookun/cursor-byok) | `4 merged` | A reused tool-call id wedged the run forever · `Bash` calls aborted the turn on a codec alias gap · empty tool arguments killed the whole run |
| [shy3130/tick-stock-panel](https://github.com/shy3130/tick-stock-panel) | `4 landed` | A forced-exit signal silently dropped under pandas copy-on-write · an unbounded upload read whole files into memory |
| [lightningpixel/modly](https://github.com/lightningpixel/modly) | `merged` | Headless runs wrote results into an unindexed folder, invisible to the app |
| [akitaonrails/ai-memory](https://github.com/akitaonrails/ai-memory) | `landed` | A packaging test that could never pass on Windows |

---

### Things I built

**[patent-intel](https://github.com/kevin9327/patent-intel)** — Ask patent questions in plain language and get answers with the measurement shown, not asserted.

**[ai-disktracker](https://github.com/kevin9327/ai-disktracker)** — A live treemap of what your AI coding agent is doing to your disk.

**[workproof](https://github.com/kevin9327/workproof)** — After the agent says it's done, prove the work actually happened.

**[opportunity-radar](https://github.com/kevin9327/opportunity-radar)** — Ask out loud which public funding you can actually apply for. Self-hosted, real data.

**[openhwp-studio](https://github.com/kevin9327/openhwp-studio)** — A local-first browser workbench for opening, inspecting and editing HWP documents.

---

<sub>Every fix above ships with a test that fails before it and passes after.</sub>
