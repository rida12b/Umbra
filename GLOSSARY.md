# Umbra — System Explorer

Umbra lets an engineer understand an unknown software system visually, then follow how it evolves while Claude Code works on it, without reading the code by hand.

## Scope

**Project**:
One software system registered in Umbra, analysed and stored in isolation from every other Project.
_Avoid_: Repo (a Project may span several), workspace, app

## Zoom levels

**Zoom Level**:
One of the five nested views of a system, from the most abstract to the most concrete: Application → Architecture → Component → Module → Function.
_Avoid_: Layer, depth, tier

**Application**:
The system seen as a product: its business purpose, its features and its users.
_Avoid_: Project, product overview

**Architecture**:
The system seen as deployable parts: frontends, backends, services, data stores, infrastructure and the technologies behind them.
_Avoid_: Stack, infra map

**Component**:
A unit of responsibility inside the Architecture, with its own dependencies, inputs and outputs.
_Avoid_: Service (unless it is deployed alone), block, package

**Module**:
One source file or script, with its precise role and its interactions with other Modules.
_Avoid_: File (when talking about the concept), script

**Function**:
One callable unit of code, with its parameters, its result and the other Functions it calls.
_Avoid_: Method (when talking about the concept), routine

## Behaviour

**Journey**:
One operation followed end to end through the system, with its inputs, processing steps, outputs and branches. It starts from an Entry Point of any kind: HTTP request, CLI command, event, pipeline run, deployment. French: *Parcours*.
_Avoid_: Execution path, flow, action, use case

**Entry Point**:
The place where a Journey starts: a route, a command, a screen action, an event handler, an async job, a queue consumer, an AI agent tool, a game loop, a pipeline source or a deployment trigger.
_Avoid_: Trigger, handler, main

## Knowledge status

**Fact**:
A statement derived deterministically from the source code and traceable to an exact location in it.
_Avoid_: Truth, analysis result

**Hypothesis**:
A statement produced by an AI or inferred indirectly; plausible but not proven by the code alone.
_Avoid_: Guess, AI insight

**Observation**:
A statement proven by real execution: a trace, a test run, a log or a metric.
_Avoid_: Verified path, runtime fact

**Human Override**:
A manual correction made by a user (e.g. moving a Module to another Component). It wins for display, is versioned and reversible, and never hides a contradicting Fact. It is not a knowledge status.
_Avoid_: Decision (as a status), manual fact, user claim

**Coverage Gap**:
A part of the system that Umbra does not understand yet, shown explicitly instead of being hidden or guessed.
_Avoid_: Unsupported file, unknown, ignored
