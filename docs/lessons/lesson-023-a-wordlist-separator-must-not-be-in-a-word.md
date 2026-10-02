---
id: "lesson-a-wordlist-separator-must-not-be-in-a-word"
type: lesson
scope: local
tags: [crypto, passphrase, testing, ux]
created: "2026-10-01"
source: "FEAT-009 PR 2, bundling the EFF large wordlist for the sealed private data"
---

# Lesson: A Wordlist Separator Must Not Appear Inside a Word

## Context

ADR-007 decision 4 takes a five-word passphrase from the EFF large wordlist, typed with spaces
or hyphens between the words, and normalizes it to lowercase words joined by a space on both the
sealing and the opening side.

## Problem

Four entries of the EFF list contain a hyphen: `drop-down`, `felt-tip`, `t-shirt`, `yo-yo`.
Because a hyphen is also a separator, `yo-yo` typed back splits into `yo` and `yo`, which are
not on the list and are a repeated word. A generated passphrase holding one of those words could
be sealed and then never opened. It was found only by checking every word against the
normalizer, not by the round-trip test, which used a fixed phrase.

## Solution

The four words are removed from the bundled list (7,772 words left; five words are still about
64.6 bits) and the header of `data/eff_large_wordlist.txt` says so.
`tests/test_seal_command.py` now asserts that every word of the list survives the
normalization on its own, so a future list update that brings a separator back fails.

## Takeaway

When a format joins tokens with a separator, test that each token survives a split on that
separator. Check a bundled data file against the code that reads it, word by word, rather than
with one hand-picked example.
