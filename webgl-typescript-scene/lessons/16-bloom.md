---
id: 16-bloom
title: Bloom from bright-pass extraction and blur
design_refs: [post-processing-pipeline, resource-ownership]
validators: [typecheck, build, browser-check]
---

## Purpose

Build a recognisable multi-pass effect while learning that bloom is generated from scene energy,
not a generic blur over the finished picture.

## Prerequisites

Lesson `15-render-to-texture` is complete.

## Learning objectives

- Preserve bright scene values in a floating-point render target
- Extract pixels above a controlled brightness threshold
- Implement separable horizontal and vertical blur with ping-pong targets
- Composite bloom with the original scene without feeding a texture back into itself

## Theory

Bloom approximates light spreading in an imaging system. A bright pass isolates high-intensity
areas; a convolution spreads their energy. A separable kernel reduces a two-dimensional blur to
horizontal and vertical passes. Values above display white require an HDR intermediate target.

## Concepts to teach

HDR render targets, luminance or brightness thresholds, multiple render targets or extraction
passes, convolution kernels, separable Gaussian blur, ping-pong rendering and additive composition.

## Constraints

Use an explicitly supported floating-point colour format and check required capabilities. Keep
blur targets at a documented resolution. Let the learner view the bright pass, each blur direction
and final composition independently. Bloom must be toggleable.

## Suggested progression

Introduce emissive/bright scene values, validate the HDR target, extract bright regions, implement
one blur direction, ping-pong the second direction for a small fixed number of iterations, then
additively compose and tune threshold/intensity.

## Completion conditions

Only intended bright surfaces seed bloom; diagnostic pass views show the expected intermediate
images; toggling bloom preserves the base scene; resize and repeated frames do not leak resources;
and the learner can explain why ordinary clamped colour prevents useful thresholding.

## On completion, persist

Record render-target format, threshold, kernel/iteration policy and bloom target resolution.

## Optional deeper paths

Build a multi-resolution bloom pyramid and compare it with the required single-resolution blur.
