<div align="center">

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/hero.webp?v=20260903" width="100%" alt="Kevin — rendered in Blender: copper lettering, a spinning crosshair and a skyline of commits" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=19&duration=3400&pause=900&color=F97316&center=true&vCenter=true&width=640&lines=git+commit+-m+%22fix%3A+the+bug+that+only+appears+in+production%22;Cross-replica+state.+Fail-closed+policy.+Loops+that+never+terminate.;A+test+that+FAILS+before+and+PASSES+after+%E2%80%94+every+single+time.;Rust+%C2%B7+TypeScript+%C2%B7+Python" alt="Typing SVG" />

<br/><br/>

<a href="https://github.com/kevin9327"><img src="https://skillicons.dev/icons?i=rust,ts,py,postgres,bun,react,docker,git&theme=dark" alt="stack" /></a>

<br/><br/>

<a href="https://github.com/search?q=is%3Apr+author%3Akevin9327+is%3Amerged+-user%3Akevin9327&type=pullrequests"><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20-user%3Akevin9327&label=pull%20requests%20merged%20upstream&color=3fb950&labelColor=0d1117&style=for-the-badge" alt="pull requests merged upstream" /></a>
&nbsp;
<a href="https://github.com/search?q=is%3Apr+author%3Akevin9327+is%3Aopen+-user%3Akevin9327&type=pullrequests"><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20-user%3Akevin9327&label=in%20review%20right%20now&color=f97316&labelColor=0d1117&style=for-the-badge" alt="pull requests in review" /></a>

<sub>Live counts, straight from GitHub search. Only other people's repositories are counted.</sub>

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/divider.svg" width="100%" />

</div>

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Hand%20gestures/Waving%20Hand.png" width="34" /> What I actually do

I hunt the bugs that **survive code review and only detonate in production** — the ones a
second replica exposes, the ones a policy engine quietly hides, the ones that spin forever
without ever throwing. Then I prove them.

```diff
+ Read the codebase until the failure mode is obvious
+ Write the test that FAILS on main
+ Fix it in the smallest diff the maintainers would have written themselves
+ Watch that same test PASS
- No padding. No drive-by nitpicks. No "looks good to me" reviews.
```

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/hunt.svg" width="100%" alt="bugs go in, fixes come out" />

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/divider.svg" width="100%" />

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Animals/Bug.png" width="34" /> Bugs I have shipped fixes for

<table>
<tr><th align="left">Project</th><th align="center">Landed</th><th align="left">The bug</th></tr>

<tr>
<td><a href="https://github.com/CopilotKit/OpenBot"><b>CopilotKit/OpenBot</b></a><br/><sub>AI coworker platform</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20repo%3ACopilotKit%2FOpenBot&label=merged&color=3fb950&style=flat-square" alt="merged" /><br/><sub>#3 of 24 contributors</sub></td>
<td>A snapshot cache living in process memory meant element refs <b>silently stopped resolving the moment a second replica existed</b> — moved it into Postgres. A deny rule written for one action surface <b>refused every other surface too</b>. An audit page that <b>called a refused call "Allowed"</b>. An empty <code>PORT</code> in the environment that let the server <b>come up on a random port</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/edwardkim/rhwp"><b>edwardkim/rhwp</b></a><br/><sub>Rust document engine</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20repo%3Aedwardkim%2Frhwp&label=merged&color=3fb950&style=flat-square" alt="merged" /><br/><sub>#4 of 58 contributors · 960+ commits</sub></td>
<td>Rendering fidelity against ground-truth documents, the CLI &amp; agent surface, and a long campaign of static-analysis <b>panic &amp; DoS</b> fixes.</td>
</tr>

<tr>
<td><a href="https://github.com/leookun/cursor-byok"><b>leookun/cursor-byok</b></a><br/><sub>Local Cursor backend</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20repo%3Aleookun%2Fcursor-byok&label=merged&color=3fb950&style=flat-square" alt="merged" /><br/><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20repo%3Aleookun%2Fcursor-byok&label=in%20review&color=f97316&style=flat-square" alt="in review" /><br/><sub>#2 of 24 contributors</sub></td>
<td>A tool-call id reused across rounds <b>wedged the run forever, with no timeout on that path</b>. Result truncation that <b>spun at 100% CPU, then underflowed a <code>usize</code></b>. One unreadable proxy row that <b>bricked every request</b>. Empty tool arguments that killed the entire run with <code>EOF while parsing a value</code>. Also landed: the repo's first pull-request CI, so <code>main</code> stops drifting red.</td>
</tr>

<tr>
<td><a href="https://github.com/shy3130/tick-stock-panel"><b>shy3130/tick-stock-panel</b></a><br/><sub>A-share quant workbench</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20repo%3Ashy3130%2Ftick-stock-panel&label=landed&color=3fb950&style=flat-square" alt="landed" /></td>
<td>A forced-exit signal <b>evaporated under pandas copy-on-write</b> — chained assignment, dropped without a warning. An upload handler read <b>whole files into memory with no cap at all</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/lightningpixel/modly"><b>lightningpixel/modly</b></a><br/><sub>Image to 3D desktop app</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20repo%3Alightningpixel%2Fmodly&label=merged&color=3fb950&style=flat-square" alt="merged" /><br/><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20repo%3Alightningpixel%2Fmodly&label=in%20review&color=f97316&style=flat-square" alt="in review" /></td>
<td>Headless runs wrote their results into <b>an unindexed folder the app could never see</b>. The "free the GPU" step ran <b>only on the rare max-iterations exit</b> — dead code on the path that mattered. A tool that reported a <b>failed model unload as success</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/pacifio/atlas"><b>pacifio/atlas</b></a><br/><sub>Source control for agents</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Amerged%20repo%3Apacifio%2Fatlas&label=merged&color=3fb950&style=flat-square" alt="merged" /><br/><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20repo%3Apacifio%2Fatlas&label=in%20review&color=f97316&style=flat-square" alt="in review" /></td>
<td>A CI matrix that had <b>quietly skipped one crate</b> while its clippy denies turned every push red. A midnight-boundary fixture pinned to UTC that <b>failed in every other timezone</b>. In review: a <code>PATH</code> patch that split on <code>:</code>, so <b>every agent server on Windows inherited a corrupted PATH</b>, and a dependency that <b>cannot compile under MSVC</b> at all.</td>
</tr>

<tr>
<td><a href="https://github.com/ZSeven-W/openpencil"><b>ZSeven-W/openpencil</b></a><br/><sub>AI-native vector design tool</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20repo%3AZSeven-W%2Fopenpencil&label=in%20review&color=f97316&style=flat-square" alt="in review" /></td>
<td>Five Windows fixes for the agent layer: executables probed <b>without their <code>.exe</code> / <code>.cmd</code> extensions</b>, an environment allowlist that <b>missed natively-cased Windows variables</b>, restored blobs addressed <b>with the wrong path separator</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/crmne/fastpotify"><b>crmne/fastpotify</b></a><br/><sub>Native Spotify client in Rust</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/github/issues-search?query=is%3Apr%20author%3Akevin9327%20is%3Aopen%20repo%3Acrmne%2Ffastpotify&label=in%20review&color=f97316&style=flat-square" alt="in review" /></td>
<td>A skin colour containing a <b>multi-byte character panicked</b> the parser. The Han fallback font region is now read from the <b>Windows display language</b> instead of assumed.</td>
</tr>

<tr>
<td><a href="https://github.com/akitaonrails/ai-memory"><b>akitaonrails/ai-memory</b></a><br/><sub>Long-term memory for agent CLIs</sub></td>
<td align="center" nowrap><img src="https://img.shields.io/badge/landed-3fb950?style=flat-square" alt="landed" /></td>
<td>A packaging test that <b>could never pass on Windows</b> — found by running the suite where CI does not.</td>
</tr>

</table>

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/divider.svg" width="100%" />

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Hammer%20and%20Wrench.png" width="34" /> Things I built

<table>
<tr>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Magnifying%20Glass%20Tilted%20Left.png" width="24" /> [patent-intel](https://github.com/kevin9327/patent-intel)
`Python`

Ask patent questions in plain language.
Get answers with the **measurement shown**, not asserted.
Its agent sibling: [patent-scout-agent](https://github.com/kevin9327/patent-scout-agent).

</td>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/House.png" width="24" /> [still-here](https://github.com/kevin9327/still-here)
`TypeScript`

A Ring household that checks in on itself.
It **knocks with a chime before it alarms the family**,
and any sign of life counts as an answer.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Animals/Paw%20Prints.png" width="24" /> [pawpaw-arena](https://github.com/kevin9327/pawpaw-arena)
`JavaScript`

Cats, dogs and pigs in a real-time .io arena —
**live on Google Play and in the browser**.
Bots keep every room full, so it is always playable.

</td>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" width="24" /> [opportunity-radar](https://github.com/kevin9327/opportunity-radar)
`Python`

Ask out loud which public funding you can
**actually** apply for. Self-hosted, real data.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Fire.png" width="24" /> [ai-disktracker](https://github.com/kevin9327/ai-disktracker)
`Python`

A live treemap of exactly what your
AI coding agent is **doing to your disk**.

</td>
<td width="50%" valign="top">

### <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Symbols/Check%20Mark%20Button.png" width="24" /> [workproof](https://github.com/kevin9327/workproof)
`JavaScript`

After the agent says it is done —
**prove the work actually happened.**

</td>
</tr>
</table>

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/divider.svg" width="100%" />

<div align="center">

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Bar%20Chart.png" width="34" /> By the numbers

<img height="160" src="https://raw.githubusercontent.com/kevin9327/kevin9327/output/stats.svg" alt="stats" />
<img height="160" src="https://streak-stats.demolab.com?user=kevin9327&theme=github-dark-blue&hide_border=true&background=0d1117&ring=f97316&fire=facc15&currStreakLabel=ec4899" />

<br/><br/>

### A year of commits, in 3D — and it moves

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/main/profile-3d-contrib/profile-night-rainbow-live.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/main/profile-3d-contrib/profile-season-animate-live.svg" />
  <img alt="3D contribution graph, with a wave rolling across the bars" src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/profile-3d-contrib/profile-night-rainbow-live.svg" width="98%" />
</picture>

<br/>

### The snake

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake.svg" />
  <img alt="contribution snake" src="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake.svg" width="98%" />
</picture>

<br/>

### …and Pac-Man

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/pacman-contribution-graph-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/pacman-contribution-graph.svg" />
  <img alt="pac-man contribution graph" src="https://raw.githubusercontent.com/kevin9327/kevin9327/output/pacman-contribution-graph.svg" width="98%" />
</picture>

</div>

<img src="https://raw.githubusercontent.com/kevin9327/kevin9327/main/assets/divider.svg" width="100%" />

## <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Crossed%20Swords.png" width="34" /> How I work with maintainers

> A maintainer closed one of my pull requests with:
> ***"Closing this as already landed, but you found a real bug and got there independently."***
>
> The fix had shipped inside someone else's PR — **after I left a review pointing at the exact failure mode.**

That is the job. Not the badge on the pull request — **the bug being gone.**

<div align="center">

<br/>

**The reviews I leave are the ones I would stake my name on. Silence otherwise.**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:ec4899,50:f97316,100:facc15&height=130&section=footer" width="100%" />

</div>
