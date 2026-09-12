# tutorail-bundles

Tutorial bundles for [tutorAIl](https://github.com/skomp/tutorAIl).

Each subfolder is one self-contained bundle.

```
tutorail-bundles/
├── rust-automaton-db/        # one bundle
└── webgl-typescript-scene/   # another
    ├── tutorial.yaml
    ├── COURSE.md
    ├── DESIGN.md
    ├── STATE.template.md
    └── lessons/
```

## What a bundle is

A bundle is a **course**: written once, used by many learners. It carries no
learner progress.

A learner's progress lives in an **instance** — a `tutorial/` directory inside
that learner's own workspace, created by the runner when they start the course.
The instance is the only place a `STATE.md` ever exists.

The mechanical rule:

> A bundle contains `STATE.template.md` and never `STATE.md`.
> An instance contains `STATE.md` and never `STATE.template.md`.

## Adding a bundle

1. Create a subfolder named after the bundle `id`.
2. Follow the authoring contract: `skills/tutorail/references/bundle-format.md`
   in the tutorAIl repository.
3. Validate it before committing.
4. Register it in a catalogue so a runner can find it.

## Bundles

| id | Title | Subjects | Level |
|---|---|---|---|
| `rust-automaton-db` | Learn Rust by Building AutomatonDB | rust, databases, distributed-systems | intermediate-to-advanced |
| `webgl-typescript-scene` | Learn WebGL 2 by Building a 3D Scene | webgl2, computer-graphics, typescript | intermediate |
