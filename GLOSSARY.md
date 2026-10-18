# Umbra — System Explorer

Umbra lets an engineer understand an unknown software system visually, then follow how it evolves while Claude Code works on it, without reading the code by hand.

## Scope

**Project**:
One software system registered in Umbra from one folder, analysed and stored in isolation from every other Project.
_Avoid_: Repo, workspace, app

**Validation Corpus**:
The fixed set of repositories of different project types (public ones, plus one of the author's own followed live) on which every V1 acceptance criterion is measured.
_Avoid_: Test repos, benchmark, samples

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
One source file, with its precise role and its interactions with other Modules.
_Avoid_: File (when talking about the concept), script

**Function**:
One callable unit of code, with its parameters, its result and the other Functions it calls.
_Avoid_: Method (when talking about the concept), routine

## Behaviour

**Journey**:
One operation followed end to end through the system, from an Entry Point to its final outputs, with its inputs, processing steps and branches. French: *Parcours*.
_Avoid_: Execution path, flow, action, use case

**Essential Transition**:
A step of a Journey without which it cannot go from its Entry Point to a final output (a call on the main path, a write to a data store, a call to another service).
_Avoid_: Key step, main hop

**Complete Journey**:
A Journey whose Entry Point, final outputs and every Essential Transition are backed by Facts or Observations. One Hypothesis or Coverage Gap on an Essential Transition makes it incomplete, and that uncertainty is shown.
_Avoid_: Full path, finished flow

**Entry Point**:
The place where a Journey starts: an HTTP route, a CLI command, a screen action, a pipeline run, a deployment, an event, an async job, a message queue, an AI agent tool or a game loop.
_Avoid_: Trigger, handler, main

## Knowledge

**Claim**:
One assertion Umbra holds about the system (for example "this route calls this Function"), with exactly one knowledge status, its Evidence and the Analyzer or model that produced it.
_Avoid_: Statement, edge, finding

**Evidence**:
What a Claim rests on: a source location for a Fact, the producer and its inputs for a Hypothesis, an execution artifact for an Observation.
_Avoid_: Proof (unless it is an Observation), source

**Fact**:
A Claim derived deterministically from the code or the configuration files and traceable to an exact location in them.
_Avoid_: Truth, analysis result

**Hypothesis**:
A Claim produced by an AI or inferred indirectly; plausible but not proven by the code alone.
_Avoid_: Guess, AI insight

**Observation**:
A Claim proven by real execution: a trace, a test run, a log or a metric.
_Avoid_: Verified path, runtime fact

**Declaration**:
A Fact about what configuration says should exist (a service in a compose file, a Terraform resource); never proof that it runs or is deployed.
_Avoid_: Deployed resource, running service

**Human Override**:
A manual correction made by a user (e.g. moving a Module to another Component). It wins for display, is versioned and reversible, and never hides a contradicting Fact. It is not a knowledge status.
_Avoid_: Decision (as a status), manual fact, user claim

**Coverage Gap**:
A part of the system that Umbra does not understand yet, shown explicitly instead of being hidden or guessed.
_Avoid_: Unsupported file, unknown, ignored

## Engine

**Analyzer**:
A pluggable unit that recognises one kind of content (a language, a framework, a configuration format, a runtime trace) and produces Claims from files the Secret Guard has released.
_Avoid_: Parser, plugin, scanner

**Secret Guard**:
The single gate through which Umbra reads Project files: it excludes sensitive files and redacts secrets before any content is used.
_Avoid_: Filter, sanitizer

**Event Journal**:
The persistent, append-only local record of what happened in a Project's development sessions (edits, prompts, Claude's final messages), replayed in order to rebuild state.
_Avoid_: Log, spool, history
