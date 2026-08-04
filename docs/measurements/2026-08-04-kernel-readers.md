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
≈4.3 × 10⁹ km, so **relative error 2.22 × 10⁻¹⁶: one unit in the last place.** The worst
absolute velocity disagreement, 1.42 × 10⁻¹⁴ km s⁻¹, is Mercury relative to Earth at
≈64.7 km s⁻¹ — 0.99 ULP.

Taking the worst **relative** disagreement anywhere in the grid rather than the worst
absolute one, which is the fairer question:

| | Worst relative | In ULP |
|---|---|---|
| Position | 3.4 × 10⁻¹⁶ | **1.5** |
| Velocity | 5.7 × 10⁻¹⁶ | **2.6** |

⭐ So the honest floor is **a small number of ULP**, and the absolute figure scales with
the magnitude of the coordinate rather than being a fixed distance. **A band expressed in
kilometres would be the wrong shape for this quantity** — at Pluto's distance it would
have to be a millimetre, and the same band would be absurdly loose for the Moon.

⚠ The two segments the file carries as identically zero — Mercury and Venus relative to
their own system barycentres — agree **exactly**, at every epoch, both readers. They were
put in the grid because a value that is *meant* to be exactly zero is one a reader can get
wrong without a residual showing up anywhere else.

`de440.bsp` gives the same worst case, 9.5 × 10⁻⁷ km, with 871 of 1 323 bit-identical.

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

That is ~30 times the 1-ULP evaluation floor, and it is pure cancellation: the second form
throws away digits before it starts. ⭐ **Anyone implementing chaining faces this choice,
so the cost is recorded rather than left to be rediscovered.** ⛔ It is a property of the
arithmetic, not of either reader, and it is not a tolerance. The emitted fixture values
compose at the nearest common ancestor.

---

## 4. The publisher's own test values reproduce to 1 ULP

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

The maximum, 7.1 × 10⁻¹⁵ au against coordinates of order 30 au, is again **one ULP**. More
than half the rows reproduce exactly. The publisher's distributed test program warns at
1 × 10⁻¹³; nothing here comes within a factor of fourteen of it.

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
  correctly, and that is all it is — which is why the fixture carries an explicit
  `contract_deviation` rather than being filed under a reference that judges accuracy.

⚠ Nutation and libration values are excluded because a planetary-position kernel does not
carry them. That is a property of the kernel, not a gap in the evidence.

---

## 5. What was not measured

* ⛔ **Only one platform.** Both readers, the same CPU, the same libm. Whether the ULP-level
  agreement survives a different target is untested.
* ⛔ **Only two readers, and they are not fully independent of each other** in the sense
  that matters most: both were written against the same published format specification.
  Agreement between them is evidence about implementation, not about the specification.
* ⛔ **No timing.** Nothing here is a performance number.
* ⚠ The grid is 49 epochs, not a survey. It is stratified — span edges, record boundaries
  and one ULP either side of them, record midpoints, and a deterministic spread — because
  a boundary is where a reader is wrong, and a uniform random sample lands on one almost
  never.
