<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:58a6ff,50:a371f7,100:3fb950&height=210&section=header&text=Kevin&fontSize=76&fontColor=ffffff&fontAlignY=32&desc=I%20break%20things%20on%20purpose%2C%20then%20send%20the%20patch&descAlignY=54&descSize=18&animation=fadeIn" width="100%" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=21&duration=3400&pause=900&color=58A6FF&center=true&vCenter=true&width=780&lines=git+commit+-m+%22fix%3A+the+bug+that+only+appears+in+production%22;Cross-replica+state.+Fail-closed+policy.+Loops+that+never+terminate.;A+test+that+FAILS+before+and+PASSES+after+%E2%80%94+every+single+time.;Rust+%C2%B7+TypeScript+%C2%B7+Python" alt="Typing SVG" />

<br/>

![Rust](https://img.shields.io/badge/Rust-000000?style=for-the-badge&logo=rust&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Bun](https://img.shields.io/badge/Bun-000000?style=for-the-badge&logo=bun&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" />

</div>

## <img src="https://raw.githubusercontent.com/MartinHeinz/MartinHeinz/master/wave.gif" width="28"/> What I actually do

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

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" />

## 🎯 Bugs I have shipped fixes for

<table>
<tr><th align="left">Project</th><th align="center">Landed</th><th align="left">The bug</th></tr>

<tr>
<td><a href="https://github.com/CopilotKit/OpenBot"><b>CopilotKit/OpenBot</b></a><br/><sub>AI coworker platform</sub></td>
<td align="center"><img src="https://img.shields.io/badge/12-commits-3fb950?style=flat-square"/></td>
<td>A snapshot cache living in process memory meant element refs <b>silently stopped resolving the moment a second replica existed</b> — moved it into Postgres. A deny rule written for one action surface <b>refused every other surface too</b>. A policy dry-run recorded a <b>refused connector call as a success</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/edwardkim/rhwp"><b>edwardkim/rhwp</b></a><br/><sub>Rust document engine</sub></td>
<td align="center"><img src="https://img.shields.io/badge/600%2B-commits-3fb950?style=flat-square"/></td>
<td>Rendering fidelity against ground-truth documents, the CLI &amp; agent surface, and a long campaign of static-analysis <b>panic &amp; DoS</b> fixes.</td>
</tr>

<tr>
<td><a href="https://github.com/leookun/cursor-byok"><b>leookun/cursor-byok</b></a><br/><sub>Local Cursor backend</sub></td>
<td align="center"><img src="https://img.shields.io/badge/4-merged-3fb950?style=flat-square"/></td>
<td>A tool-call id reused across rounds <b>wedged the run forever, with no timeout on that path</b>. A codec alias gap aborted the turn on every <code>Bash</code> call, mid-stream. Empty tool arguments <b>killed the entire run</b> with <code>EOF while parsing a value</code>.</td>
</tr>

<tr>
<td><a href="https://github.com/shy3130/tick-stock-panel"><b>shy3130/tick-stock-panel</b></a><br/><sub>A-share quant workbench</sub></td>
<td align="center"><img src="https://img.shields.io/badge/4-landed-3fb950?style=flat-square"/></td>
<td>A forced-exit signal <b>evaporated under pandas copy-on-write</b> — chained assignment, dropped without a warning. An upload handler read <b>whole files into memory with no cap at all</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/lightningpixel/modly"><b>lightningpixel/modly</b></a><br/><sub>Image to 3D desktop app</sub></td>
<td align="center"><img src="https://img.shields.io/badge/merged-3fb950?style=flat-square"/></td>
<td>Headless runs wrote their results into an <b>unindexed folder the app could never see</b>.</td>
</tr>

<tr>
<td><a href="https://github.com/akitaonrails/ai-memory"><b>akitaonrails/ai-memory</b></a><br/><sub>Long-term memory for agent CLIs</sub></td>
<td align="center"><img src="https://img.shields.io/badge/landed-3fb950?style=flat-square"/></td>
<td>A packaging test that <b>could never pass on Windows</b> — found by running the suite where CI does not.</td>
</tr>

</table>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" />

## 🛠️ Things I built

<table>
<tr>
<td width="50%" valign="top">

### 🔍 [patent-intel](https://github.com/kevin9327/patent-intel)
`Python`

Ask patent questions in plain language.
Get answers with the **measurement shown**, not asserted.

</td>
<td width="50%" valign="top">

### 💾 [ai-disktracker](https://github.com/kevin9327/ai-disktracker)
`Python`

A live treemap of exactly what your
AI coding agent is **doing to your disk**.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ✅ [workproof](https://github.com/kevin9327/workproof)
`JavaScript`

After the agent says it is done —
**prove the work actually happened.**

</td>
<td width="50%" valign="top">

### 📡 [opportunity-radar](https://github.com/kevin9327/opportunity-radar)
`Python`

Ask out loud which public funding you can
**actually** apply for. Self-hosted, real data.

</td>
</tr>
</table>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" />

<div align="center">

## 📊 By the numbers

<img height="160" src="https://github-readme-stats-sigma-five.vercel.app/api?username=kevin9327&show_icons=true&theme=github_dark&hide_border=true&bg_color=0d1117&title_color=58a6ff&icon_color=a371f7&text_color=c9d1d9&include_all_commits=true" />
<img height="160" src="https://streak-stats.demolab.com?user=kevin9327&theme=github-dark-blue&hide_border=true&background=0d1117&ring=a371f7&fire=3fb950&currStreakLabel=58a6ff" />

<br/><br/>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake.svg" />
  <img alt="contribution snake" src="https://raw.githubusercontent.com/kevin9327/kevin9327/output/github-contribution-grid-snake.svg" width="98%" />
</picture>

</div>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" />

## 💬 How I work with maintainers

> A maintainer closed one of my pull requests with:
> ***"Closing this as already landed, but you found a real bug and got there independently."***
>
> The fix had shipped inside someone else's PR — **after I left a review pointing at the exact failure mode.**

That is the job. Not the badge on the pull request — **the bug being gone.**

<div align="center">

<br/>

**The reviews I leave are the ones I would stake my name on. Silence otherwise.**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3fb950,50:a371f7,100:58a6ff&height=130&section=footer" width="100%" />

</div>
