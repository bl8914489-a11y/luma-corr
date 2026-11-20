from pathlib import Path

p = Path(r"F:\周四焜哥论文\paper\manuscript_v2.md")
s = p.read_text(encoding="utf-8")
anchor = "It is not given the clean reference $I$."
block = r"""It is not given the clean reference $I$.

The quantities used below are defined as:

1. Offset injection: $\hat I = \mathrm{clip}(I - 20, 0, 255)$.
2. Gamma injection: $\hat I = 255\,(I/255)^{\gamma}$, with $\gamma=2$ or $1.3$.
3. Local target: for each frame $t$, fit $y_t = a + b t$ on the clean context frames and use $\hat y_t$ as the target luma.
4. Outside change: $\mathrm{OutFrac} = \frac{1}{|\Omega|}\sum_{x\in\Omega} [O(x)\neq I(x)]$, where $\Omega$ is the outside region.
5. Interval error: $\mathrm{Y\text{-}MAE} = \frac{1}{|\mathcal{I}|}\sum_{t\in\mathcal{I}} |Y(O_t)-Y(I_t)|$, with $Y$ the luma channel.
"""
assert anchor in s
s = s.replace(anchor, block, 1)
p.write_text(s, encoding="utf-8")
print("ok")
