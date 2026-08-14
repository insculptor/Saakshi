# Textual authority: resolving a citation instead of asserting one

**2026-08-14.** Three fixtures, one per textual kind, and the first time any of the three has
been written by a real artifact rather than by its own negative tests.

| Artifact | Kind | What it records |
|---|---|---|
| `out/textual/significator-series-rules.jsonl` | `textual_rule` | five located rules of one translation, and one widely repeated rule it does not contain |
| `out/textual/reduction-rule-fork.jsonl` | `textual_fork` | one chapter, one configuration, three incompatible readings, none adopted |
| `out/textual/reduction-worked-example.jsonl` | `worked_example` | a source's own worked figures, transcribed from two of its own witnesses and reproduced |

---

## 1. The question this reference exists to answer, and it is not "can we cite a book"

⛔ **A citation a reader cannot resolve is not a citation.** Writing down a chapter number
costs nothing and establishes nothing. Two editions of one text differ; a translator's note is
printed on the same page as the translation and carries different authority; and a copy that
reached this machine as a scan was read by a machine before it was read by anyone.

So a locus here is **resolved into a named copy**, and the resolution is on the record:

* the **witness** — the address the copy was asked for, on what date, its status and digest;
* the **rendering** — how those bytes became searchable text, and by what, with its own digest;
* the **extent** — what the copy actually contains, *measured from its own internal boundary
  markers*, never taken from a title;
* the **resolution** — that the words quoted at the locus occur in that rendering **exactly
  once**.

⭐ The generator resolves rather than asserts, and that matters for a reason this repository
learned the hard way in the previous session: **a claim about what an artifact supports is a
claim like any other, and made in prose it is untested.** Prose saying "the citations are
good" is the one form of that claim nobody can check.

### Exactly once, and why two is a refusal rather than a success

A fragment that occurs twice has located nothing, and the failure is the ordinary case rather
than an exotic one: **a table of contents restates the words of the chapter it points at.** A
recorder taking the first hit cites the contents page and calls it the rule. Measured, in the
copies used here: a chapter heading quoted as a locus resolves twice, and a short sentence
inside a worked example resolves twice.

⚠ The same rule governs the landmarks that delimit a table, and there the pair is instructive.
Two landmarks were tried and refused for being ambiguous:

* one opened a region of **548 figures** where twelve were required — a declared cell count
  would have caught it too;
* the other opened **exactly the intended region** — ambiguous and harmless, and no count of
  any kind could have told it apart from a landmark that resolves.

⛔ Judged on either case alone the rule comes out wrong: from the first, that counting is
enough; from the second, that ambiguity does not matter. Nothing in the output says which case
you are in, and on the next copy the two come apart.

---

## 2. What was refused, by name

⚠ **A count with no names is a silent cap on what a reader can check.** Every claim considered
and not written down is a row of its own, carrying its subject, its reason and what would close
it. Eleven refusals across the three files, under six declared reasons.

The two that shape the files most:

**⛔ Neither copy contains the original.** Both are English translations of Sanskrit works, and
both renderings carry **zero code points** of the script the originals are written in —
measured, not assumed. So no locus into an original is resolvable here, and citing a
translation in its place would file a translator's sentence as the text's own. Every locus in
all three files is therefore a `translation`, a `commentary` or a `worked_illustration`, and
none is a `primary_text`.

**⛔ A copy is not the work.** The translation used for the rule fixture is titled a part, and
its own closing markers run out at the fourth pada of the second adhyaya — eight divisions
found, eight looked for. Nothing beyond that was searched, so nothing beyond it is claimed.
⚠ The copy does not establish how many divisions the complete work has either; it establishes
only that it is a part and where its own text stops.

---

## 3. `textual_rule` — five located rules, and one that is absent

⭐ **Two of the five sit in the translator's notes rather than in the sutras**, and every row
says which it is. The rule that the eighth body is ranked by *reversed* degrees is one of
them: the sutra names the body and says nothing about how its degrees are read. A consumer
that took the notes for the text would be implementing a modern commentator under a sutra's
name — and the distinction is invisible on the page, because the two are printed together.

### The absence, and the two things that bound it

The most widely repeated rule attributed to this system — that the first place of the
significator series conjoining or aspecting the second is a combination for rulership — is
recorded as **absent** from the extent searched.

⛔ **An absence is only as wide as its alphabet.** Ten spellings were searched and each
carries its own hit count on the row; **133 hits in total**, and every hit of the five
spellings the claim actually rests on is *located* rather than counted, with the text standing
around it. What those hits do say is enumerated: the second place is defined, a sixth counted
from it is used, a further place indicates religious inclination, and a tie sends the first
place elsewhere. ⛔ None of them pairs the first place with the second.

⛔ **And only as wide as the copy.** This is an absence from two divisions of a work whose own
title says it is a part. It is not an absence from the work.

⚠ Two spellings were counted but not enumerated — the general terms, which run to dozens of
hits and which the claim does not rest on. That reduction is stated on the row rather than
left for a reader to infer from a total.

---

## 4. `textual_fork` — a chapter that disagrees with itself

⭐ A fork is usually imagined as two books disagreeing. This one is **one chapter**, which is
the harder kind to notice: a reader who consults the source once comes away certain.

The chapter states a numbered rule for a configuration — two signs of one lord, neither
occupied, holding unequal figures — and then works two illustrations of *that same
configuration*. Nothing the chapter states distinguishes the two illustrated cases: both pairs
are unoccupied and both hold two and one.

Applied to that one configuration:

| Reading | Where it comes from | Gives |
|---|---|---|
| both are given the smaller figure | the chapter's own numbered rule | 1, 1 |
| the smaller goes to zero, the bigger stands | the first illustration | 2, 0 |
| the difference is deducted from both | the second illustration, same paragraph | 1, 0 |

⛔ **Three readings, three answers, one chapter.** ⛔ **None of them is adopted, preferred or
ranked here.** Recording that the source does not settle the question is the whole of the
claim; settling it would be this repository substituting itself for the source.

⭐ **The pair is the finding, not either member.** Read alone, the rule is a rule and each
illustration is an illustration, and all three read as settled. A consumer that consulted this
source once would have come away certain — of whichever of the three it happened to open at.

### The arbiter is measured to be unreadable

The chapter prints a chart carrying the whole illustration, and it is what would decide the
question. In the copy in hand **both of its rows read ten cells where the twelve signs require
twelve**. So it is not read at all here, rather than read in part: the cells that survive are
still digits in a plausible order, and a short row transcribed as an answer is
indistinguishable from a correct one.

⚠ **And legibility is a property of the table, not of the copy.** In the same copy and the
same rendering, the **neighbouring chapter's chart reads twelve of twelve**. Both measurements
are on the file, because either alone licenses a wrong general rule — *"a machine reading of a
scan cannot be trusted with a table"* and *"this one came through fine"* are both wrong.

---

## 5. `worked_example` — reproduction, and nothing more than that

⭐ **A worked example proves reproduction, not accuracy**, which is why the contract forbids
this kind from carrying an astronomical budget row. What is established is that a method read
off the source's own illustration, applied to the figures the source printed, returns the
figures the source printed.

⭐ **The source printed its example twice — as a chart and spelled out in its prose — and so
supplied its own second witness.** Both are transcribed independently and compared cell by
cell before anything is reproduced:

* the figures before the reduction: **12 of 12 cells agree**;
* the figures after: **12 of 12 agree**;
* the method applied to the first, against the second: **12 of 12**.

⚠ One of the two chart rows survived the rendering as a run of digits with its cell boundaries
lost. It is read digit by digit and counted against the twelve the signs require, and it is the
prose that makes that safe. A row read this way with no second witness is a guess with a
plausible shape.

⚠ The two witnesses are two transcriptions of **one printing**, not two sources. A figure
mis-set at the press is mis-set in both, and that is recorded as a refusal.

### ⛔ Two things this example does not establish, both measured

1. **It does not exercise the exception its own chapter states.** The chapter says no
   reduction is needed where a member of a group holds nothing. **No group in this example
   contains such a member** — measured on the printed figures, not assumed. An implementation
   with that exception inverted reproduces every figure in the file. ⭐ A worked example
   resolves a method only over the inputs it happens to contain, and a consumer pinning
   against it has tested the inputs rather than the rule.
2. **The method reproduced is not the rule the chapter states.** Read literally, the rule
   sentence deducts a member's figure from the *sum* of its group's three. On this example's
   own first group that gives **8**, larger than any figure in the group; the example resolves
   to deducting the group's smallest, which gives **2**. The two are recorded as separate
   claims because they are separate claims.

---

## 6. What this session changed in the contract

⛔ **The locus law checked presence and never value.** `source_kind` and
`interpretation_status` had no declared value set, so a typo passed the writer and reached a
reader as a group of one. R6 was the first artifact to stand on those fields, so it closed
the hole: both now have registries, and `language` is held to a shape.

⭐ **The proof that the hole was real was in this repository's own tests.** Their shared locus
carried `interpretation_status: "settled"` — a value no registry has ever declared — and every
test using it passed. ⚠ **A field whose value set is "any string" reports a pass on anything.**

`tests/test_textual.py` adds 63 tests, including a negative case for every field the locus law
requires, in both of the shapes an incomplete locus actually arrives in: absent, and present
but empty.

### And one thing it changed in the leak check

The textual reference acquires other people's published texts, and the words in them were
chosen by their authors. ⛔ Measured on the first two acquired: one contains a reserved name
twice, as the name of a sage, in a work of the tradition a consumer of this repository was
itself named after. **It is there by construction, not by accident**, and the next classical
text will carry it too.

⚠ A check that always fires is a check nobody reads. So the acquisition cache is exempt from
the **content** pass — and from that pass only:

* nothing there is authored here and nothing there is ever committed;
* what this repository *writes* from those texts is scanned exactly as before, and a quotation
  carrying a reserved name is refused like any other content;
* ⛔ **every path under the cache is still listed and still matched.** The failure the
  working-tree scan exists for was a consumer-named *directory* planted by a parallel session,
  and the cache is the directory such a session is most likely to write into. Exempting it
  wholesale would have reopened that hole in exactly the worst place. Two tests pin it.

---

## 7. Reproducing these files

All three regenerate byte for byte from the same copies at the same commit. They read from an
acquired copy on disk and **do not go to the network**; acquisition is a separate step.

```bash
python generators/r6_karaka_rules.py --acquire --out out/
python generators/r6_reduction_fork.py --acquire --out out/
python generators/r6_reduction_example.py --out out/
```

⛔ **Emission never acquires.** A generator that fetched at emit time would stamp today's date
on a copy obtained months ago — false in the one field the witness exists to establish — and
would need a network to reproduce its own output. The retrieval is written beside the copy
once, and read unchanged afterwards.

⛔ **The address that answered is deliberately not recorded.** Asked twice, one of these
resources was served by two different hosts of a distribution network. That is a property of
the transaction and not of the copy, and writing it down would make the record fail to
reproduce for the next reader.

---

## 8. What R6 still owes

* ⚠ **Every rule in the first file rests on one witness** — one copy, one translation, one
  translator. That is recorded as a refusal rather than left as an impression: a rule resolved
  against a single edition is *resolved*, not *corroborated*.
* ⬜ **A second translation of the disputed chapter** would show whether the disagreement is in
  the work or in this translation of it. It is the first question a reader of the fork will
  ask and it is not answered.
* ⬜ **A copy carrying the originals.** Every claim here is about a translation.
* ⬜ **A text that resolves a worked example in a subject other than this one**, so the
  `worked_example` kind is exercised somewhere its figures reach the exceptions its own rules
  state.
