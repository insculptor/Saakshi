# Two readers, one file — and one that was measuring itself

> Date: **2026-08-04** · Generators: `r2_kernel_states.py`, `publisher_testpo.py`
> Host: one workstation, `x86_64` Windows, CPython 3.12.11
> ⚠ **One host, one platform.** Everything below is a measurement taken here, not a
> claim about every machine.

Four fixture sets were generated: geometric states and the publisher's own test values,
each against both `de440s.bsp` (32.7 MB, 1849–2150) and `de440.bsp` (119.8 MB, 1550–2650).
Both files were identified by SHA-256 before a value was read from either.

---

## 1. ⭐ The recorder was measuring its own arithmetic

**This is the finding worth carrying past this file.**

The first run reported a worst-case disagreement of **2.0 × 10⁻⁵ km** — two centimetres —
between the SPICE Toolkit and `jplephem` reading the identical bytes. The disagreement
appeared on **direct** segments, so it was not a chaining artifact, and it was large
enough that anyone reading it as a precision floor would have set a tolerance band four
orders of magnitude too loose.

It was not a difference between the readers. It was this:

```python
jd = 2451545.0 + et / 86400.0        # ⛔ the division rounds
```

The Toolkit takes the epoch as seconds past J2000 and uses it exactly. `jplephem` takes a
Julian date, so the recorder converted — and three centuries from J2000 the rounding of
that one division is ≈4 × 10⁻¹² days. The fastest body in the file moves ≈2 × 10⁻⁵ km in
that time. The entire signal was the conversion.

Handing the epoch over as an exactly-representable integral day plus a sub-day fraction:

```python
whole_days = math.floor(et / 86400.0)
remainder  = et - whole_days * 86400.0
jd, jd_fraction = 2451545.0 + whole_days, remainder / 86400.0
```

…the two implementations agree **bit for bit** at the epoch that had been worst — every
component, every direct segment, zero difference.

⭐ **The general form: a recorder that converts units before handing a value to the thing
it is measuring ends up measuring its own arithmetic.** The conversion has to happen at
the edge, or not at all. It is the reason `publisher_testpo.py` emits the publisher's
values in the publisher's own units and never rescales them — the AU constant is recorded
*beside* the rows as a stated input instead.

---

## 2. The floor, once the recorder stopped contributing

`de440s.bsp`, 1 323 states over 49 stratified epochs × 27 body pairs:

| Chain shape | Rows | Worst disagreement | Rows differing |
|---|---|---|---|
| `direct_identically_zero` | 196 | **0.0** | 0 |
| `common_ancestor_not_root` | 196 | 5.8 × 10⁻¹¹ km | 54 |
| `direct` | 1 176 | 1.2 × 10⁻⁷ km | 139 |
| `through_root` | 1 078 | 9.5 × 10⁻⁷ km | 436 |

**891 of 1 323 states are bit-identical.** The worst absolute disagreement, 9.5 × 10⁻⁷ km,
is on Pluto's barycentre relative to Earth at a span edge — where the coordinate is
≈4.3 × 10⁹ km, so **relative error 2.22 × 10⁻¹⁶, which is 1.00 × 2⁻⁵²**. The worst
absolute velocity disagreement, 1.42 × 10⁻¹⁴ km s⁻¹, is Mercury relative to Earth at
≈64.7 km s⁻¹ — 0.99 × 2⁻⁵².

Taking the worst **relative** disagreement anywhere in the grid rather than the worst
absolute one, which is the fairer question:

| | Worst relative | ÷ 2⁻⁵² |
|---|---|---|
| Position | 3.4 × 10⁻¹⁶ | **1.5** |
| Velocity | 5.7 × 10⁻¹⁶ | **2.6** |

⭐ So the honest floor is **a small multiple of 2⁻⁵²**, and the absolute figure scales with
the magnitude of the coordinate rather than being a fixed distance. **A band expressed in
kilometres would be the wrong shape for this quantity** — at Pluto's distance it would
have to be a millimetre, and the same band would be absurdly loose for the Moon.

> ⛔ **Why these read `× 2⁻⁵²` and not "ULP", and why that is not pedantry.**
> An earlier version of this page and of the fixture called this ratio a count of units in
> the last place. It is not one. A double `m × 2ᵉ` with `m ∈ [1, 2)` has one last place at
> `2ᵉ⁻⁵²`, so *relative to the value* one last place is `2⁻⁵²/m` — and the count is this
> figure divided by `m`, somewhere between the figure and half of it, with no way to tell
> which from the figure alone.
>
> ⭐ **Measured, on this repository's own worst rows**, which is what turns the objection
> from a definition into a fact. The publisher-values band is the same number in both
> profiles, **7.105 × 10⁻¹⁵ au** — and it is **one** last place in `de440s` (worst row at
> 37.65 au) and **two** in `de440` (worst row at 29.98 au), because 32 au is a binade
> boundary and the spacing halves below it. The velocity band is **three** last places in
> both, while reading 2.00 × 2⁻⁵². ⛔ So a "1 ULP" label is not even a property of the band:
> it is a property of which row happened to be worst.
>
> ✅ **No number moved.** The band was always declared as the fraction, and the ratio was
> always reporting prose — which is exactly why the label was the whole defect and fixing it
> costs nothing. The fixture now names the division (`band_over_two_to_minus_52`) instead of
> claiming a unit, and a field name that states an arithmetic operation cannot be wrong
> about what it means.
>
> ⚠ **Where "last place" *is* the right word, it is kept.** The grid below steps record
> boundaries with `nextafter`, which really does move one last place; and the service
> sampler reports a disagreement over `math.ulp` of the value itself, an absolute spacing at
> that value's own magnitude. Those are a different quantity that happens to be adjacent,
> and sweeping them into this repair would have replaced one mislabelling with another.

⚠ The two segments the file carries as identically zero — Mercury and Venus relative to
their own system barycentres — agree **exactly**, at every epoch, both readers. They were
put in the grid because a value that is *meant* to be exactly zero is one a reader can get
wrong without a residual showing up anywhere else.

`de440.bsp` gives the same worst case, 9.5 × 10⁻⁷ km, with 871 of 1 323 bit-identical.

### 2a. ⭐ "Relative" is not one question — and the wrong denominator moves the answer

The table above divides each component's disagreement by **that component**. It is the
obvious denominator and it is not the right one: a component passing near zero drives its
own ratio arbitrarily large while nothing whatever has gone wrong. The publisher makes the
same observation from the other direction, arguing in `testeph.f`'s own comment for an
absolute test because *"sometimes the values will be near zero for particular
components"*.

⭐ **The stable denominator is the norm of the section's three components.** It does not
pass through zero except where the whole state is zero, and there it is undefined rather
than misleading. Measured that way on the same grid:

| | Per component (÷ 2⁻⁵²) | Per section norm (÷ 2⁻⁵²) |
|---|---|---|
| Position | 1.5 | **1.36** (3.01 × 10⁻¹⁶) |
| Velocity | 2.6 | **2.36** (5.25 × 10⁻¹⁶) |

The two readings agree on the order of magnitude, which is the point: the finding is robust
and the *shape* still matters, because it is the shape a band has to be written in. So the
R2 fixture declares its band per section, relative to the section norm, at exactly the
worst value observed — **no headroom**, because margin added to an observation is where a
measurement quietly becomes an opinion.

⚠ **98 rows per section have no denominator** — the identically-zero segments. They carry a
null relative disagreement and are excluded from the band entirely. Including them at a
ratio of zero would tighten the reported floor using rows that were never capable of
loosening it, and an exact-zero check is the only check they admit. ⛔ A consumer that
judges those rows by band alone has not judged them.

---

## 3. Where you compose a chain costs more than how you evaluate it

Same reader, same bytes, same state — composed two ways:

* at the **nearest common ancestor** (Moon relative to Earth via the Earth–Moon
  barycentre, both legs small); or
* always **through the root** (two barycentric vectors of ≈1.5 × 10⁸ km, subtracted).

| Kernel | Worst difference between the two strategies | Where |
|---|---|---|
| `de440s.bsp` | **2.9 × 10⁻⁸ km** | Moon relative to Earth |
| `de440.bsp` | **1.5 × 10⁻⁸ km** | Earth relative to Moon |

That is ~30 times the evaluation floor measured above, and it is pure cancellation: the second form
throws away digits before it starts. ⭐ **Anyone implementing chaining faces this choice,
so the cost is recorded rather than left to be rediscovered.** ⛔ It is a property of the
arithmetic, not of either reader, and it is not a tolerance. The emitted fixture values
compose at the nearest common ancestor.

---

## 4. The publisher's own test values reproduce to the last place or two

`testpo.440` — 13 201 values taken from the original integration — checked against each
binary kernel through the SPICE Toolkit.

| | `de440s.bsp` | `de440.bsp` |
|---|---|---|
| Values parsed | 13 201 | 13 201 |
| Rows emitted | **3 099** | **11 354** |
| Excluded: nutations and librations | 1 847 | 1 847 |
| Excluded: epoch outside the kernel's span | 8 255 | 0 |
| **Median absolute difference** | **0.0** | **0.0** |
| Maximum absolute difference | 7.1 × 10⁻¹⁵ au | 7.1 × 10⁻¹⁵ au |
| Rows at or over the publisher's own 1 × 10⁻¹³ | **0** | **0** |

The maximum, 7.1 × 10⁻¹⁵ au, is **one last place** where it occurs in `de440s` (at 37.65 au)
and **two** where it occurs in `de440` (at 29.98 au) — the same absolute number, a different
count, because the two worst rows sit either side of a binade boundary. ⭐ That pair is the
demonstration in the box above, and it is why this page states the coordinate a count was
taken at. More than half the rows reproduce exactly. The publisher's distributed test program
warns at 1 × 10⁻¹³; nothing here comes within a factor of fourteen of it.

### 4a. ⭐ The band, and what a single number across both sections was hiding

The fixture declares that floor as its band — **per section, at exactly the worst value
observed, no headroom.** Both kernels give the same two numbers:

| Section | Band | Rows measured | The publisher's 1 × 10⁻¹³ is |
|---|---|---|---|
| `position_au` | **7.1054 × 10⁻¹⁵ au** | 1 507 / 5 608 | **14.1 ×** it |
| `velocity_au_per_day` | **2.0817 × 10⁻¹⁷ au/day** | 1 592 / 5 746 | **4 804 ×** it |

⚠ **Per section is forced here, not chosen.** Position is printed in au and velocity in
au/day, so the larger of the two is not a wider band — it is a number with no unit. That is
the same objection that makes a single kilometre band wrong for the state fixtures
above, arriving through
*dimensions* rather than through magnitude, and the second row is what it was concealing:
one band of 7.1 × 10⁻¹⁵ would have declared the velocity section **341 times looser than it
was ever measured to be**, and every velocity row would have passed it without being
checked at all.

⭐ **The two tolerances are a floor and a margin, not rivals.** 1 × 10⁻¹³ ÷ 7.1 × 10⁻¹⁵ is
about fourteen, so the publisher's stated number is a floor of this order plus roughly one
decade of headroom over it. Both are recorded, the publisher's verbatim with its source, and
the ratio is stated on the row rather than left to a reader to divide out.

⚠ **The band is ABSOLUTE here and RELATIVE for the state fixtures above, and that is not
an inconsistency.** A
relative band needs a denominator that exists in the row: the R2 rows each carry the norm of
their own three components, and these rows carry a single printed component and no scale to
divide by. The publisher argues the absolute form from the other side in the same comment
quoted above — a fractional test is unsuitable *"since sometimes the values will be near
zero for particular components"*.

⛔ **The limit, which matters more than the number.** This floor was measured between **one**
toolkit and the publisher's printed values. The reader that will be judged against these rows
is a **third implementation**, which this run did not observe at all — so the band is a proxy
for that reader's floor, not a measurement of it. ⭐ Zero headroom is the right choice for a
band that *reports* a floor and the wrong choice for one that *gates*: a third reader
differing by two ULP where this one differs by one has not malfunctioned, and a band with no
headroom cannot tell that from a defect.

Three things this establishes, and one it does not:

* ✅ These repackaged binary files carry the same ephemeris as the published test set. No
  systematic repackaging difference is visible at this precision.
* ✅ The body-numbering table is correct. The publisher's test-file numbering and its
  binary kernels' numbering are **different schemes and neither is derivable from the
  other**; a single wrong row would have produced a residual of millions of kilometres
  rather than 10⁻¹⁵.
* ✅ Every excluded row is counted by reason. 3 099 + 1 847 + 8 255 = 13 201.
* ⛔ **It says nothing about how accurately the ephemeris models the solar system.** The
  publisher is on both sides of this comparison. It is evidence that a reader reads
  correctly, and that is all it is — which is why the fixture is filed under a reference
  that names *both* of the publisher's artifacts and the relationship between them, rather
  than under one that judges accuracy.

⚠ Nutation and libration values are excluded because a planetary-position kernel does not
carry them. That is a property of the kernel, not a gap in the evidence.

---

## 5. What was not measured

* ⛔ **Only one platform.** Both readers, the same CPU, the same libm. Whether agreement at
  the last place or two survives a different target is untested.
* ⛔ **Only two readers, and they are not fully independent of each other** in the sense
  that matters most: both were written against the same published format specification.
  Agreement between them is evidence about implementation, not about the specification.
* ⛔ **No timing.** Nothing here is a performance number.
* ⚠ The grid is 49 epochs, not a survey. It is stratified — span edges, record boundaries
  and one ULP either side of them, record midpoints, and a deterministic spread — because
  a boundary is where a reader is wrong, and a uniform random sample lands on one almost
  never.
