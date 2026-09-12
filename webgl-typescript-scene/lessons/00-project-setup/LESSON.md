---
id: 00-project-setup
title: A minimal graphics workspace
design_refs: [platform-toolchain]
validators: [has-index, has-entrypoint, typecheck, build, browser-check]
---

## Purpose

Create a repeatable feedback loop before graphics code introduces browser-only failures.

## Prerequisites

TypeScript, npm and browser developer tools. No earlier lesson.

## Learning objectives

- Distinguish type checking, bundling and static serving
- Run a TypeScript entry point in a plain HTML page
- Use the console and page as separate sources of evidence

## Theory

TypeScript does not run in the browser. `tsc --noEmit` checks types, while esbuild resolves
module imports and emits browser JavaScript. A local HTTP origin is used from the beginning
because later asset requests cannot reliably use `file://`.

## Concepts to teach

Entrypoints, ES modules, bundling, source maps, static origins and browser developer tools.

## Constraints

Copy `starter/package.json`, `starter/package-lock.json`, `starter/tsconfig.json`,
`starter/index.html` and `starter/src/main.ts` into their corresponding repository-root paths,
preserving `src/`.
Do not introduce a framework, DOM component library or rendering dependency. Read
`starter/README.md` before giving the first task; it defines the supplied commands and layout.

## Suggested progression

Install dependencies, inspect each supplied file, type-check, build, start the development
server, and verify both page output and the absence of console errors.

## Completion conditions

`npm run typecheck` and `npm run build` succeed. `npm run serve` exposes the page on its
reported local URL, the page shows the starter heading, and the console has no error.

## On completion, persist

Record the verified npm commands and local URL in `STATE.md`. Do not copy starter source into
state or design notes.

## Optional deeper paths

Explain how esbuild differs from `tsc`, but do not teach general bundler configuration.
