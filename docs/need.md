# The need behind Umbra (owner's words)

Read this before any design or UI work. Every screen is judged against it.

## Who
Rida, an AI consultant (Forward Deployed Engineer path, aiming at Solutions Architect). He does not write or read code line by line: he orchestrates Claude Code agents and focuses on architecture choices.

## The need (translated faithfully from his voice message, 2026-10-27)
"Tomorrow I will work with different clients. They will often put me on projects I do not know. When I arrive in a repo, I cannot open every page, understand every file, every function. I cannot even understand the project at a high level. I am an AI orchestrator: I focus on architecture, for architecture choices, but I will not read thousands of lines of code.
So I must be able to understand a project, know **where it stands**, **what the components are**, etc.
The problem: today my only window of understanding is my Claude Code terminal. I ask it questions and it explains — but not optimally. Visually it is hard to understand: I get no diagram, nothing like that.
I want a tool: I arrive on a project, I launch my tool, **I can navigate the project through this tool**. I see how it is, how it is structured, what the components are, **what the entry is, what the output is**, etc.
The tool you made is not understandable. I have told you this about ten times, and ten times we were not on the same wavelength."

He also said explicitly what it is NOT: "you are making an analysis tool that gives weak points, things to improve. That is not what I am asking."

## The ten misses (what was built, what he said)
1. v0.7 (old): a file watcher where an LLM rewrites a Mermaid diagram + static dashboard.
2. "Factory floor" React UI (engine + React Flow map; components = machines on a factory floor, data = parts on a conveyor, a numbered "line" plays a journey). Mockups: projects/perso/umbra/docs/design/2026-10-25-factory-floor/b-factory-floor.html and a-metro-line.html (+ ref-*.png screenshots of the real UI). Verdict after a cold test on a VM: "pas intuitif du tout" — too much info at once, the same info shown 3 times while following a journey, invented words (metaphor vocabulary), the map does not fit the screen.
3. v2 "guided reading" (text pages): "franchement c pas clair".
4. v3 (simplified guided reading, 3 screens): "tellement pas clair… sur l'interface oui à la limite un peu simplet, mais dans la data y'a rien".
5. v4 (same 3 screens, rich proven content: every fact cites file:lines): "c mieux, mais maintenant c'est au niveau du visuel, comment rendre tout ça digeste".
6. v5 (one step at a time, tabs, folds with counters): asked "with this, do I understand a whole project like a product architect?" — answer was no.
7. v6 (added all 16 journeys, deployment, and an "architect verdict" screen with risks/debt): "that is not what I am asking" + the need above.
Pattern to break: every iteration became a long reading page / report about ONE project, built from a study. He wants a TOOL he can navigate, visual first (diagrams, structure, entry → output), that works on ANY unknown repo, and that fixes the "terminal explains badly, no diagrams" problem.

## Validated direction (2026-10-27)
- Rida on the mock-ups in `docs/design/2026-10-27-project-map/`: "oui c nickel ca". Decision: ADR-0007.
- "Where it stands" means **what is finished and what is not** in the project (his answer "b"), not recent activity.

