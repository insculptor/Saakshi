# PROPOSAL — what replaces the second-printing test · 2026-08-18

> ✅✅✅ **TAKEN, AND ARMED — the owner answered both questions on 2026-08-18.** This file
> is kept as written, as the record of what was proposed and on what evidence. What changed
> when it was taken is recorded at the end, under *What was done when this was taken*.
>
> ⭐ The retired control was **withdrawn as a `correction` row**, carrying the three
> candidates' measurements into it. `MarkerAlphabet` and `AbsenceAcrossReadings` stand
> unmodified, no absence was re-scored, and the twelve spellings were not narrowed.

The second-printing test was retired as written for two independent defects, both published
in `2026-08-18-the-alphabet-that-marked-the-wrong-hand.md`:

| | the defect | what it costs |
|---|---|---|
| **1** | four of the twelve spellings mark the translator, the translated first sutra, and the reader's own damage | carrying none of the twelve is a condition **no copy of this work can satisfy** |
| **2** | the same edition read three times gives three answers — 4 of 12 flip zero / non-zero | a clean pass would have **measured the reader** |

⛔ A replacement answers **both** or it is not a replacement. This file proposes one, shows
it against the copies actually held, and records **two further designs that were measured
and refused** — so that neither has to be re-derived.

---

## 1. ⭐⭐⭐ Both defects are the same defect, and it is the VERDICT SHAPE

The retired test's verdict was **a zero**: *this copy carries none of the twelve spellings.*
Every property that made it unusable follows from that one choice.

**⛔ A zero is the one measurement a broken reader produces for free.** The library scan — a
machine reading of an English printing carrying **no Latin letters at all** — was re-scored
here on the eleven spellings that are words:

```
spellings that are words: 11    with any hit: 0    ⇒ 0 of 11 → PASS
```

⭐ It is not that the noise copy *nearly* passed. Scored on the words it passes **perfectly**,
and it passes because it was never read. The asterisk that denied it — the twelfth spelling,
which is typography and marks nothing — was a defective entry doing accidental work.

**⛔ And the two failure directions are not symmetrical.** Under an absence, a reader that
damages a word turns a hit into a zero, and a zero is a **pass** — the instrument's errors
all point at *success*. Under a presence claim, a reader that damages a word turns a
resolution into a nothing, and nothing is a **refusal** — the instrument's errors all point
at *refusing to answer*.

> ⭐⭐⭐ **A test whose errors are false passes needs a guard against every way a reader can
> fail. A test whose errors are refusals needs none.** Defect 2 is not a flaw to be guarded
> against; it is what an absence-shaped verdict is made of.

⇒ **The replacement must require a PRESENCE.**

---

## 2. ⛔⛔ AND THE GUARD THAT *DID* PROTECT THE REPOSITORY IS SCRIPT-CONTINGENT — measured here

The eleventh session armed a script refusal, and it is what actually rejected the noise copy:
the twelve spellings are Latin, the copy carries no Latin letter, so the row is refused before
a spelling is counted. That is why the repository was never exposed.

⚠ **That protection holds only while the alphabet is Latin.** The library scan's machine
reading is not empty — it carries **34 414 Devanagari letters**, which is the script the
second copy's located rules are written in. Run with a Devanagari alphabet, every armed guard
passes it:

| check, as armed | over the noise copy, alphabet = the five located rules (Devanagari) |
|---|---|
| `carries_searchable_text` | ✅ passes — 246 777 searchable characters |
| `scripts_required_by(alphabet)` | `['devanagari']` |
| `carries_script('devanagari')` | ✅ **True** — 34 414 letters |
| the script refusal fires? | ⛔ **No** |
| a positive control quoted from the copy's own noise, resolving exactly once | ✅ found — nothing in a noise rendering repeats |
| **`AbsenceSearch` constructs?** | ⛔⛔⛔ **YES. The absence is licensed over a rendering of pure noise.** |

⚠ **Latent, not live.** No published row takes a Devanagari absence over that copy, and none
of the twenty-two artifacts is affected. Nothing here falsifies anything published.

⭐⭐⭐ But it settles the question the assignment asks — *the score was never the protection,
so what is?* — and the answer is that **the script guard is not it either.** It is one
alphabet's worth of protection on a test that can be re-run in another alphabet tomorrow.

> ⭐⭐⭐ **The only protection that does not have to be maintained is the one the verdict
> shape provides.** A presence claim rejects the noise copy *by measuring it*, not by being
> guarded from it — see *Shown against the copies actually held*, row D.

---

## 3. The proposal — **the independent-hand test**

> **A rule this file publishes as one hand's is safe from a second hand's reach when the rule
> is also stated, at its own located place, in a copy that hand could not have touched.**

### 3.1 What it measures

For every rule filed as `commentary` — the rows attributed to a **hand** rather than to the
text, and therefore the only rows a second commenting hand could have authored — whether the
rule resolves at a locus in a copy **outside that hand's reach**.

⭐ The verdict is a **resolution**, never a zero. The rule must be **found**.

### 3.2 ⭐⭐⭐ Why it discriminates — the reach is structural, not lexical

The retired alphabet tried to discriminate by **vocabulary**: spellings the second hand uses
and the translator supposedly does not. ⛔ That can never work, because the two hands are
printed on the same pages, write the same subject in the same language, and share a
vocabulary — which is exactly how `Prof.`, `Professor`, `my work` and `*` got in.

The reach argument uses no vocabulary at all:

* the second hand is a **reviser of one English translation** — that is what the copy that
  names it says on its own title page;
* a **different translator, working from the original into another language**, is outside
  that reach **by construction**;
* ⇒ a rule stated in both copies was in the work **before** the second hand touched it,
  whoever's English prose states it here.

⛔ **There is no alphabet, so there is nothing to contaminate.** The translator's honorific,
the translated first sutra and the reader's own asterisk damage are all simply irrelevant —
none of them is being scored on. **Defect 1 does not have an analogue in this design.**

### 3.3 ⛔ Its preconditions, each of them measured rather than asserted

| # | precondition | why it is required | how it is measured |
|---|---|---|---|
| P1 | the second copy is a **different translation**, not another printing of the same one | ⛔ this is `revised_printing_cannot_witness_the_unrevised_words` restated as an entry condition: two printings one hand revised agree about the revision | the copy carries the **original's script**; the English printings carry zero of it |
| P2 | the second copy is **not noise** | ⛔ *the guard is script-contingent*, above — a Devanagari noise rendering passes it | ⭐ nothing extra is needed: a noise copy fails P3 |
| P3 | the rule **resolves exactly once** at a located place in it | a presence claim is a location or it is nothing | `resolve()`, as everywhere else in this module |
| P4 | the fragment is **long enough that chance resolution is implausible** | ⛔ this file already measured that in a noise rendering **300 of 300** eight-character fragments resolve exactly once | the located fragments are whole sentences |

⚠ **P1 and P2 are not the same check and neither implies the other.** The noise copy carries
Devanagari and satisfies a naive P1; the fifth edition is clean English and satisfies a naive
P2. ⭐ It takes both, and the pair is what separates the second translation from every other
copy held.

---

## 4. Shown against the copies actually held

The five rules, resolved at their own loci in each candidate for the second copy. ⛔ The
rows that matter are the two filed **`commentary`** — the ones the question is live at.

| rule | filed as | second translation (Hindi) | fifth edition | third ed., reading A | library scan (noise) |
|---|---|---|---|---|---|
| the first significator is the highest in degrees | translation | **1** | 0 | 0 | 0 |
| the second significator is next in degrees | translation | **1** | 0 | 0 | 0 |
| the third significator is next again | translation | **1** | 0 | 0 | 0 |
| **the node is ranked by reversed degrees** | **commentary** | **1 / 1** | 0 / 0 | 0 / 0 | 0 / 0 |
| **a tie merges two places and the node fills the vacancy** | **commentary** | **1 / 1** | 0 / 0 | 0 / 0 | 0 / 0 |
| | | ✅ **5 of 5 → PASS** | ⛔ refused at P1 | ⛔ refused at P1 | ⛔ **0 of 5 → FAIL** |

*(the two `commentary` rules carry a second located fragment each; both resolve)*

**Row A — the two at-risk rows pass.** Both rules filed as the translator's notes resolve, on
both of their fragments, in a translation the second hand did not make.

**Row B — the same-translation copies are refused at P1, not scored.** ⭐ Their zeroes are
worth noticing anyway: every fragment resolves **once** in the copy in hand and **zero** times
in three readings of a printing that certainly contains the same rules. ⛔ Exact resolution
across readers is worth nothing, which is the collation design's whole subject, below.

**Row C — the scripts, measured.** P1 is not an opinion about the copies:

| copy | latin | the original's script |
|---|---|---|
| second translation (Hindi) | 8 959 | **196 380** |
| fifth edition | 206 676 | **0** |
| third edition, reading A | 205 055 | **0** |
| library scan | **0** | 34 414 |

**Row D — ⭐⭐⭐ THE SAME COPY, THE OPPOSITE VERDICT.** The library scan under the retired
test scores **0 of 11 → a perfect pass**. Under the replacement it scores **0 of 5 → fail**.

> ⛔ Nothing was added to catch it. It is caught because the test asks the copy to **say
> something**, and a rendering that cannot express the words says nothing. That is the answer
> to *the score was never the protection — what is?*

---

## 5. ⛔ What the replacement does NOT establish

⚠ Stated first and at length, because a proposal that oversells is worse than no proposal.

1. ⛔ **It does not identify whose prose the English sentence is.** It establishes that the
   **rule** predates the second hand's reach, not that the **words** are the translator's. A
   row's `the translator's notes` attribution remains unverified.
2. ⛔⛔ **`revised_printing_cannot_witness_the_unrevised_words` STANDS, unchanged and
   unretired.** The replacement does not answer that refusal's question and must not be read
   as discharging it. ⬜ Open question 3 of the hand-off — that no unrevised printing was
   reached — is untouched.
3. ⛔ **The second translator is himself a modern commentator.** Two copies agreeing
   establishes that a rule is **not one hand's invention**; it does not establish that the
   rule is in the sutras. ⚠ The corroboration rows already say this and it does not weaken
   here.
4. ⚠ **One reading of the second copy is held.** ⭐ This matters far less than it would for
   an absence, and the asymmetry is the point of *both defects are the same defect*: a reader can destroy evidence of a
   presence but cannot manufacture it, so a presence found in **one** reading needs no second
   reader, while an absence found in one reading needs every reader there is. ⛔ It is still a
   limit and it is still stated.
5. ⛔ **P1's reach is bounded by what a title page says**, not by proof. That the hand revised
   *this translation* is located on the naming copy's own page. That it never touched any
   other work is **not established either way** — it is not needed, because the rule is
   measured in another language from the original.

⇒ ⭐ The replacement answers **the exposure the retired test was standing in for** — *could a
rule this file publishes be a modern reviser's invention?* — and leaves the **attribution**
question open, refused, and correctly labelled.

---

## 6. ⭐⭐ Why this is worth taking even though it answers a smaller question

The retired test, **had it worked perfectly**, would have found a printing showing the
translator's own words — and the translator is himself a modern commentator whose notes this
file already files as commentary. ⛔ A consumer's exposure would be unchanged.

⇒ The retired test decided an **attribution**; the proposal decides an **exposure**. They are
different questions, and only one of them is answerable from copies held.

| | the retired test | the proposal |
|---|---|---|
| verdict | a zero over a whole copy | a resolution at a locus |
| passable by noise | ⛔ **yes**, 0 of 11 | ✅ no — 0 of 5, fails |
| reachable by any copy of this work | ⛔ **no** | ✅ yes — **taken and passed here** |
| needs an alphabet | ⛔ yes, and it cannot be made to discriminate | ✅ none |
| answers defect 1 | ⛔ no | ✅ no alphabet exists to contaminate |
| answers defect 2 | ⛔ no | ✅ errors are refusals, not passes |
| copies it needs | ⬜ one nobody has found in four askings | ✅ **already held** |

---

## 7. Two further designs, measured and REFUSED

⭐ Recorded so that neither is proposed back. Both are the obvious next idea; both fail on the
copies held, and the measurements are here rather than the arguments.

### 7.1 ⛔ Calibrated cross-printing collation — **the reader noise floor swallows it**

*The design.* Collate each rule passage between printings, and calibrate: three readings of
**one** printing are held, so the disagreement among them is pure reader noise and the true
number of revisions between them is **zero**. Call a cross-printing difference real only where
it exceeds that floor.

*Measured.* Best-matching window per copy, compared copy-to-copy. **Control: the copy the
fragments were read off returns 1.000 on all ten** — the matcher is sound.

| passage | within one printing (A~B, A~C, B~C) | third vs fifth (A, B, C) | floor | verdict |
|---|---|---|---|---|
| rule 1 | .862 .828 .931 | .828 .862 .828 | .828 | within reader noise |
| rule 2 | .857 .786 .857 | .929 .786 **.714** | .786 | *"difference"* — margin **0.072** |
| rule 3 | .895 .789 .842 | .895 .895 .789 | .789 | within reader noise |
| rule 4 | .893 .786 .821 | .929 .964 .857 | .786 | within reader noise |
| rule 5 | .700 .700 .633 | .867 .633 .633 | .633 | within reader noise |
| third-person 1 | **.240 .280 .200** | .880 .280 .280 | **.200** | within reader noise |
| third-person 3 | **.214 .286 .500** | .357 .643 .429 | **.214** | within reader noise |
| second-hand claim 1 | **.333 .267 .200** | .933 .333 .333 | **.200** | within reader noise |
| second-hand claim 2 | **.250 .417 .167** | .833 .333 .500 | **.167** | within reader noise |

⛔⛔⛔ **The floor between two readings of ONE printing runs down to 0.167.** Where the true
difference is *known to be zero*, the instrument reports up to 83% disagreement. The single
verdict that clears the floor does so by **0.072**, inside a floor that itself scatters from
.167 to .828 across passages. ⇒ **That verdict is noise.**

⛔ **And it cannot be repaired by a better statistic.** A noise floor is measurable only where
**two or more readings of one printing** are held. Three readings of the third edition are
held; of the fifth edition and of the copy in hand, **one each**. Every cross-printing
comparison therefore has an **unmeasured reader on one side**, and a difference found there
cannot be assigned to the printing rather than to that reader.

⚠ ⭐ One incidental measurement worth keeping: the **fifth edition** matches the copy in hand
*better* than three readings of the third edition do, at eight of ten passages — including
**1.000** at three of them. ⛔ That is **not** evidence about which printing the copy in hand
is: it conflates *same printing* with *same reading quality*, which is the precise mistake
`place_in_the_work_not_established_across_copies` refuses. It is recorded as a trap, not a
finding.

⬜ What would make this design takeable: **a second machine reading of the fifth edition**, by
its distributor. That is concrete and acquirable — and it is not proposed here.

### 7.2 ⛔ The footnote marker — **6 of 15, and the mark itself is reader-dependent**

*The design.* Drop vocabulary entirely and use **typography**: the second hand's
interpolations in the copy in hand are footnotes, and footnotes carry a printed mark. Delimit
the hand by the mark.

*Measured — and measured by **enumerating every occurrence**, not by sampling.* The copy in
hand carries **15** asterisks in 228 420 characters. Each was read:

| what the mark introduces | count |
|---|---|
| ⭐ the second hand's own material (its two book-claims, its *commentators have not come to our rescue* note, its two third-person interpolations) | **6** |
| sutra headings — the **primary text** | 2 |
| a botanical gloss and the reference to it | 2 |
| a variant-reading note, a note on aspects, a note on ghatis, a marked sutra translation | 4 |
| mid-word, where the reader could not read a letter | 1 |
| | **15** |

⛔⛔ **It is not sound.** Nine of fifteen mark something other than the second hand —
including two that mark the **sutras themselves**, which is defect 1 exactly: a marker firing
on the primary text.

⛔⛔ **And it is not complete.** The established second-hand passage *Though Suryanarain Rao
has elucidated…* carries **no asterisk at all**. Its mark, in this rendering, is `U+00B7`, a
middle dot — one of three in the copy. ⭐ **The footnote mark is itself read differently in
different places by one reader**, so defect 2 reappears in the marker rather than in the
score.

⭐ Worth keeping regardless: **no asterisk lies within 12 881 characters of any of the five
rules.** ⛔ That is *not* a licence. The hand's material is **locatable but not delimitable**:
specific sentences can be proved to be the second hand's; **no sentence can be proved not to
be.** ⇒ No test over the copy in hand alone can settle the attribution — which is *what the replacement does NOT establish*, item 1,
arrived at from the other side.

---

## 8. ⭐⭐⭐ The rule both refused designs leave behind

The twelve spellings were checked for discrimination against **four passages a recorder
thought of**. The asterisk in *the footnote marker* was checked against **all fifteen of its occurrences**. The
difference is not diligence.

> ⭐⭐⭐ **A survey is evidence about the rows it has.** A marker can be *checked* only when its
> occurrences are few enough to **enumerate**; and the eight spellings that survived the
> four-passage survey survived a survey, which is not the same as discriminating. ⛔ This is
> why *drop the four and re-run* is not a repair, and why it is not proposed here.

> ⭐⭐⭐ **The only markers that need no survey are the ones a hand could not have written.**
> *Professor Rao's notes are not clear* cannot be Rao — that is grammar, not statistics. A
> second translation in another language cannot be a reviser of this English one — that is
> construction, not vocabulary. ⇒ **Discrimination is designed in or it is surveyed for, and
> only the first kind holds.**

---

## 9. ⬜⬜⬜ THE OPEN QUESTION — the owner's, and nothing is armed until it is answered

⬜ **Is the independent-hand test taken as the replacement for the second-printing test?**

Taking it would mean, and only means:

1. arming a refusal — a rule filed as a **hand's** commentary must carry an attestation in a
   copy outside that hand's reach, with P1–P4 measured;
2. ⛔ leaving `revised_printing_cannot_witness_the_unrevised_words` **standing**, and leaving
   hand-off open question 3 open;
3. publishing what the attestation does **not** establish (*what it does not establish*) on the row itself, not in prose;
4. ⚠ deciding what happens to the retired control
   `the_second_printing_test_was_run_and_no_candidate_passed_it` — it is currently written to
   fail the day a candidate passes, and no candidate can. ⬜ Whether it is withdrawn as a
   `correction` row or kept as a standing record of an unpassable test **is part of this
   question**, not a detail of it.

⬜ **Two smaller questions ride on the answer and are stated separately:**

* ⬜ Whether the latent guard defect recorded above is repaired now or left recorded. ⚠ It falsifies nothing
  published; it means a Devanagari absence over a noise copy is currently licensed.
* ⬜ Whether a **second machine reading of the fifth edition** is worth acquiring (*the collation design*). It
  is the one acquisition that would make cross-printing collation measurable.

---

## 10. What was deliberately not done

* ⛔ **Nothing was armed.** No class, no refusal, no control, no test was added or changed.
* ⛔ **No absence was re-scored** and **the twelve spellings were not narrowed.**
  `MarkerAlphabet` and `AbsenceAcrossReadings` are **byte-identical** to what was armed last
  session.
* ⛔ **No artifact was re-emitted.** All twenty-two stand as they were.
* ⛔ **No machine reading was produced here.** Every rendering used is its distributor's; the
  windowing in the collation measurement compares distributors' readings and creates none.
* ⛔ **No copy was acquired.** Every measurement above is over copies already in the cache.
* ⛔ **The five rules, the five corroborations and the conventions time-offset artifact were
  not touched.**
* ⛔ **No hand-over into the consuming tree.** Nothing read from or written to it.

---

## ✅ What was done when this was taken

Both open questions were answered by the owner: **take the test**, and **withdraw the retired
control as a `correction` row**.

### Armed

* **`IndependentHandAttestation`** in the textual module, with P1–P4 refusing. ⛔ It refuses a
  row filed as the **text** outright — a sutra is attributed to no hand, so no hand's reach
  bears on it and a passing row there would read as evidence about the primary text.
* **The two rules filed as the translator's notes** — the only two the question is live at —
  now carry an attestation row each, resolving on **both** of their fragments in the second
  translation.
* **A control driven off its own value**: the noise copy, a second printing of the same
  translation, and a rule filed as the text are each **offered** to the instrument and the
  cause of each refusal is recorded on the row. ⛔ Deleting any refusal makes the control fail
  rather than quietly widening what the file may publish.

### Withdrawn

The control `the_second_printing_test_was_run_and_no_candidate_passed_it` is a `correction`
row. Its `held` condition was *no candidate passed*, which every copy of this work satisfies,
so it could not change state and was not a control. ⭐ The three candidates' measurements are
carried **into** the correction row, so nothing measured was lost by withdrawing the verdict
built on top of them.

### ⛔⛔⛔ And one thing in this proposal was WRONG, found by arming it

Precondition **P4** was armed at 24 letters and justified here as *three times the length at
which resolution is free*, citing this repository's measurement that in a rendering of noise
300 of 300 eight-character fragments resolve exactly once. **That reasoning is backwards**, and
the generator refused a real attesting passage before anyone noticed. Measured over the copies
held:

| letters | share resolving exactly once, a real book | … a rendering of noise |
|---|---|---|
| 8 | 0.460 | 0.993 |
| 12 | 0.707 | 1.000 |
| 16 | 0.943 | 0.993 |
| 24 | 0.993 | 1.000 |

⇒ **A longer passage resolves exactly once MORE often, not less.** By 24 letters a real book
and pure noise are indistinguishable. So raising the bound makes an attestation **cheaper** to
obtain, not safer, and **no length bound can defend against chance resolution.**

⭐ The constant now does the one thing it can — refuse a fragment too short to *state a rule* —
and says so. It is set at **12**, below every real attesting passage held (the shortest is 18)
so it is not fitted to the sample. The measured direction is pinned by a test.

> ⭐⭐⭐ *A precondition can be sound in its refusal and wrong in its reason, and the reason is
> what the next reader inherits.* P4 refused the right things for an argument that does not
> hold — and an argument nobody re-derives is the part that survives into the next design.

### The re-emission and its controls

Held file copied aside and digest-verified **first**. Compared **by row identity, never by
position**. **49 byte-identical · 0 changed · 4 added · 1 removed** — every rule, every
corroboration, the earlier corrections, the alignment, the hands row, the naming row, the
foreword row, the absence and all standing refusals untouched. Byte-identical on re-run.

⭐ Comparator driven off its own value, **5/5**: held vs itself 0 changed · new vs itself 0
changed · an untouched **rule** row perturbed → changed 0→**1** · a **carried control** row
perturbed → byte-identical 49→**48** · a row dropped → removed 1→**2**. ⚠ The revert control
was unavailable again because `changed` is 0; the perturbation controls stand in for it.

⚠ **`out/` is git-ignored** — artifacts are local build products stamped with the generator's
commit, and only the generator travels in the repository. Re-measured after the re-emission:
**22/22 resolve**, 7 stamps — `9cdb8e6` ×12, `6fc673e` ×3, `238ddcd` ×2, `3041f4c` ×2,
`eea3150`, `7fc7ba9`, `a1b371b`; the list sums to 22, *checked*. ⛔ Do not carry it — re-measure.

⛔⛔ **21 of those 22 stamps are reachable by a reader; one is not.** The re-emitted artifact
names `a1b371b`, which is local-only and unpushed — *an artifact that names an unpushed commit
is stamped with an address nobody can reach*. It is present, digest-pinned, self-consistent and
unciteable until a push.
