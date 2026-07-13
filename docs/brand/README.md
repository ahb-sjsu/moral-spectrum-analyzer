# Brand assets — Moral Spectrum Analyzer

Source of truth is the **SVG** (hand-editable, `viewBox` fixed). Rasterize from these; don't
hand-edit exported PNGs. All marks are flat — **no shadows, no 3-D, no gradients**.

| File | What it is | Use on |
|---|---|---|
| `erisml_apple.svg` | The ErisML golden apple (from the Atlas brand kit) | dark backgrounds |
| `erisml_apple_light.svg` | Light-background apple variant | light backgrounds |
| `analyzer_mark.svg` | **Product sub-mark** — apple refracting into the 9-axis moral spectrum | dark backgrounds |
| `analyzer_mark_light.svg` | Light-background analyzer mark | light backgrounds |

## The analyzer mark

The `analyzer_mark` builds *on top of* the golden apple — it embeds the canonical
`erisml_apple` geometry **unchanged** and adds the product's thesis as one image: the apple
(the judgment) **refracts, prism-like, into nine coloured bars** (the moral spectrum). Per-bar
rays fan from the apple's edge to each bar top — the dispersion. The spectrum's **warm end
(gold) sits nearest the apple**, so the apple and the instrument read as one system; it cools
to blue across the nine axes.

Symbolism carried over from the apple: the **sphere** is the logic and machinery of the
judgment; the **stem + leaf** root it in earth and life — the *Grounded* trust beat (every
number traces to a validated encoder, anchored in real data).

## Rules (inherited from the Atlas brand kit)

- **Never recolour the apple.** The gold (`#f5c147` dark / `#c38a00` light) is the Eris
  reference — *"to the fairest"* — and is load-bearing. Same for the green leaf and brown stem.
- The nine spectrum colours are a warm→cool ramp; keep gold as bar 0 so it meets the apple.
- No shadows / 3-D / gradients. Flat fills only.

| Token | Dark | Light |
|---|---|---|
| Apple gold | `#f5c147` | `#c38a00` |
| Leaf green | `#4ade80` | `#15803d` |
| Stem brown | `#6b3a00` | `#6b3a00` |
| Spectrum (warm→cool) | `#F5C147 … #4C8BF5` | `#C38A00 … #2B5CE6` |
