---
title: "The Universe Makes Pancakes First"
date: 2026-07-10
summary: The early universe was smooth to one part in a hundred thousand. Gravity turned it into the cosmic web, and the order it works in — sheets, then filaments, then knots — all falls out of one approximation you can drag in your browser.
---

You've seen the cosmic web, that vast lattice of galaxies threaded through every documentary about the cosmos. You've probably pictured it forming wrong. I did, for years.

The early universe was almost perfectly smooth.

We can measure how smooth. The cosmic microwave background says the density of matter, everywhere on the sky, was the same to about one part in a hundred thousand. A featureless soup, barely rippled. And yet look at it now: a web of filaments strung across hundreds of millions of light-years, dense knots where they cross, and between them enormous empty voids. One of the largest, most intricate patterns in nature, grown out of one of the flattest starting conditions in nature.

The thing that did it was gravity, and nothing else. That part isn't surprising. What surprised me, the first time I really sat with it, is the *order* gravity works in. Matter doesn't fall straight to a point. It flattens first — into sheets — then it strings into filaments, and only then does it draw up into knots. Pancakes before noodles before dumplings. The universe makes pancakes first, and the reason it has to is a small, beautiful piece of geometry that you can watch happen in a browser tab.

I built the tab. Everything below is a tour of what it's showing you, and why the physics is simpler than the pictures make it look.

## Gravity is an amplifier

<!-- PULL-QUOTE (screenshot-bait): the two sentences below -->
Structure formation is not creation. It is amplification.

Take that nearly smooth field and find a patch that happens to be a hair denser than average. It pulls a little harder than its surroundings, so it gathers a little more matter, so it gets denser, so it pulls harder still. The rich get richer. Meanwhile the slightly-underdense regions lose the tug of war and drain out, widening into voids. Run that feedback for thirteen billion years and the one-part-in-a-hundred-thousand ripples become order-unity lumps.

Nothing here is invented along the way. The web you end up with was already latent in the initial ripples — gravity just turns up the contrast until the structure separates from the background. It is less like building and more like developing a photograph.

{{< figure src="grow-universe.gif" alt="A near-uniform field sharpening into a cosmic web as cosmic time runs forward." caption="Cosmic time running forward, from a ≈ 0.05 (redshift ~19) to today. The web doesn't appear, it *condenses*. Every filament was already written into the starting field; gravity is developing the negative." >}}

How far the contrast develops depends on how loud the initial ripples were. That amplitude has a name, σ₈, and it's one of the dials on the box. Turn it up and the very same patch of universe collapses further, from a smooth haze into hard knots and empty voids — same arrangement of structure, pushed to a later stage of the same process.

{{< figure src="sigma8-sweep.gif" alt="The same box sharpening from a smooth haze to dense knots as the fluctuation amplitude increases." caption="Raising σ₈, the amplitude of the initial fluctuations, on a fixed patch. The clusters stay where they were — the initial ripples decided that — but the collapse runs harder. Amplitude sets how far, not where." >}}

## Why pancakes come first

Now the surprising part. Why sheets before filaments before knots?

Quick, before you read on: picture a clump of matter collapsing under its own gravity. Did you picture it shrinking to a point, like a deflating balloon? Almost everyone does. That's the wrong picture, and the real one is stranger.

For a blob to collapse straight to a point, it would have to be a perfect sphere shrinking evenly on all sides. But a random patch of a random field is never a sphere. It's a lumpy ellipsoid, longer along some directions than others. And an ellipsoid held together by its own gravity collapses along its *shortest* axis first, because that's where the pull is strongest and the distance to fall is smallest. Squeeze one axis to nothing and you don't get a point. You get a pancake.

That is Zel'dovich's insight, and the approximation named after it turns it into something you can compute. The Zel'dovich approximation says: to find where a bit of matter goes, take its original position on a grid, call it **q**, and slide it by a displacement,

> **x**(t) = **q** + D(t) · **Ψ**(**q**)

where **Ψ** is a fixed pattern of arrows baked into the initial field, and D(t) is a single number — the growth factor — that grows with time and multiplies every arrow at once. That's the whole dynamics. One frozen displacement field, turned up by one dial.

If you want the derivations under all of this — the Zel'dovich displacement, its second-order (2LPT) correction, and the Fourier-space machinery in the next section — Donghui Jeong's PhD thesis works through them with unusual care: [*Cosmology with high (z > 1) redshift galaxy surveys*](https://repositories.lib.utexas.edu/items/1c8a7013-91cd-4b13-816a-8db317c366ac) (University of Texas at Austin, 2010).

The direction of collapse lives in how those arrows converge. At each point, the way the displacement stretches and squeezes the local matter is captured by a small 3×3 symmetric matrix (the gradient of **Ψ**), and that matrix has three eigenvalues, λ₁ ≥ λ₂ ≥ λ₃ — one collapse rate for each principal axis. An axis has "turned around" and collapsed when D(t) times its eigenvalue crosses a threshold. So count them:

- **0** axes collapsed → you're in a **void**
- **1** axis → a **sheet** (one-dimensional collapse — the pancake)
- **2** axes → a **filament** (two-dimensional collapse)
- **3** axes → a **node** (three-dimensional collapse — a cluster)

The entire vocabulary of the cosmic web — void, sheet, filament, node — is just the number of collapsing eigenvalues at each point. That's what I find beautiful about it. You don't need four separate theories for four kinds of structure. One linear approximation contains all three dimensionalities of collapse, and they light up in order because the biggest eigenvalue always crosses first.

{{< figure src="web-type.gif" alt="The growing web colored by collapse type: sheets, then filaments, then nodes lighting up in sequence." caption="The same growth, but now each particle is colored by *how many* of its axes are collapsing: dark voids, then green sheets, blue filaments, and the orange nodes where all three have gone. Watch the order — flat regions light up first, knots last." >}}

> **Under the hood — the classifier.** Each particle carries the deformation tensor of the displacement field; the shader solves its cubic characteristic equation in closed form for the three eigenvalues and counts how many exceed a threshold (a T-web classification, after Forero-Romero et al. 2009), and that count picks the color (`index.html:651`). The strict Zel'dovich caustic sits at D·λ = 1, but by today that leaves almost no nodes, so the box uses a gentler threshold — the geometry of the ordering is the same either way.

## The reason it fits in a browser

There is a fair question hiding here: gravity is a long-range force, every lump pulling on every other lump, so how does this run at sixty frames a second on a laptop with no server?

Because the hard step is only hard in the wrong coordinates. The displacement **Ψ** comes from a potential that obeys Poisson's equation, ∇²φ = δ — the density field δ tells the potential how to curve. In real space that's a global problem: the value at every point depends on every other point, which is the O(N²) trap that makes N-body simulations expensive. But go to Fourier space, decompose the field into waves, and Poisson's equation stops being an integral and becomes plain algebra, one wave at a time:

> φ(**k**) = −δ(**k**) / k²,  so  **Ψ**(**k**) = i **k** δ(**k**) / k²

Every wavelength evolves independently of every other. No wave talks to its neighbors. And the Fast Fourier Transform carries the field between real space and Fourier space in O(N log N) time instead of O(N²). So the whole pipeline is short: draw a random density field, multiply each wave by the amplitude the cosmology assigns it, take three inverse FFTs to get the displacement arrows, and slide the particles. That's it. That is why the dials answer the instant you touch them — you are not re-simulating gravity, you are re-scaling a field you already solved.

> **Under the hood — shaping the field.** The amplitude each wave gets is the power spectrum P(k), whose shape comes from the Eisenstein–Hu (1998) transfer function, baryon acoustic wiggles included, evaluated live for the current Ω_m (`index.html:349`). The little P(k) inset in the corner is the exact curve the waves are drawn from; the FFT machinery that turns it into structure is a few dozen lines (`fft3d`, `:336`). Second-order corrections (2LPT) add one more term that sharpens the knots toward a full N-body answer (`:479`). This Fourier/FFT treatment and the 2LPT term are both derived carefully in [Jeong (2010)](https://repositories.lib.utexas.edu/items/1c8a7013-91cd-4b13-816a-8db317c366ac).

## The dots are not the point

One last thing the visualization can quietly mislead you about. The glowing dots are not particles, in the sense of little objects the universe is made of. They are tracers — samples of a continuous mass distribution, each one marking where a parcel of the originally-smooth field has been carried.

That distinction is not pedantic; it changes what you're allowed to draw. Because the dots only sample an underlying continuum, you can render the same physics two completely different ways. You can show the tracers themselves, as points — the splat view, where the cosmic web is a spray of light. Or you can bin the tracers back into the smooth density they were sampling and ray-march that density as a translucent solid — the cloud view, where the web is a volume you could almost cut with a knife. Same field, same physics, two honest pictures of it.

{{< figure src="splats-vs-clouds.jpg" alt="The same cosmic web rendered as sparse glowing points on the left and as a continuous ray-marched volume on the right." caption="The identical box, same seed and same instant. Left: the tracers drawn as points. Right: the continuous density those tracers sample, ray-marched as a volume. Neither is more real than the other — the points sample the cloud, and the cloud is what the points are sampling." >}}

> **Under the hood — where the brightness comes from.** Each particle carries a single-stream density from the Jacobian of the displacement: 1 + δ = 1 / det(**I** + D·**A**), literally one over how much a fluid element has been stretched (`index.html:645`). Where that determinant crosses zero — a caustic, where infinitely many streams pile up — the density formally diverges, which is exactly the bright edge you see lighting up a collapsing pancake.

## What it gets right, and what it doesn't

I would rather you leave with the caveats than without them.

This is the Zel'dovich approximation, plus an optional second-order term. It is not a full gravitational solve. First and second order are honest about the linear and mildly-nonlinear regime, but once streams of matter pass through each other in the dense knots — shell-crossing — the approximation stops being quantitatively right. The pancakes and filaments are real and correctly ordered; the exact densities inside the brightest nodes are not something I'd put on a plot. And the single-stream density politely looks away from precisely the multi-stream regions where the true dynamics get hard.

None of that touches the story, though. Amplification, anisotropic collapse in a fixed order, the whole web taxonomy falling out of three eigenvalues — all of that is exactly right, and cheap enough to hold in your hand and turn over. (One implementation note, since someone always asks: the box runs on a fixed random seed, so it's reproducible. Every reload is the same universe, and every dial you move changes the physics rather than the luck of the draw.)

So here it is. Turn the amplitude up and watch the contrast develop. Color by collapse type and watch the sheets ignite before the knots. Switch it to a cloud. Then, if you want to feel how little of this is really moving, remember that behind all of it there is just one displacement field and one growing number.

<div style="max-width:1100px;margin:2rem auto;">
  <div style="position:relative;aspect-ratio:16/9;border-radius:8px;overflow:hidden;background:#05060a;">
    <button id="cw-launch" aria-label="Launch the interactive Cosmic Web Sandbox"
      style="position:absolute;inset:0;width:100%;height:100%;border:0;cursor:pointer;
             background:url('hero-poster.png') center/cover;color:#fff;font:inherit;
             display:flex;align-items:center;justify-content:center;">
      <span style="background:rgba(0,0,0,.55);padding:.7em 1.2em;border-radius:999px;font-size:1.05rem;">
        ▶&nbsp; Launch the interactive sandbox
      </span>
    </button>
  </div>
  <p style="text-align:center;font-size:.85em;opacity:.7;margin:.5rem 0 0;">
    Runs entirely in your browser, no server ·
    <a href="https://minhmpa.github.io/lss-lab/cosmic-web-sandbox/" target="_blank" rel="noopener">open full screen&nbsp;⤢</a>
  </p>
</div>
<script>
  document.getElementById('cw-launch').addEventListener('click', function () {
    var f = document.createElement('iframe');
    f.src = 'https://minhmpa.github.io/lss-lab/cosmic-web-sandbox/?embed=1';
    f.title = 'Cosmic Web Sandbox';
    f.loading = 'lazy';
    f.allow = 'fullscreen';
    f.allowFullscreen = true;
    f.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:0';
    this.replaceWith(f);
  });
</script>

<!-- PULL-QUOTE (screenshot-bait): the last sentence of this paragraph -->
The cosmic web can look designed, this vast, deliberate-seeming lattice threaded through the dark. It isn't. It's the least imaginative thing gravity could do to a nearly smooth field: pull the dense parts together, in the order the geometry forces. Flat first, then thin, then a point. The universe makes pancakes first, and everything else is patience.

So go make some. [Grow a universe](https://minhmpa.github.io/lss-lab/cosmic-web-sandbox/?embed=1&color=web&a=0.05), color it by collapse type, and watch the sheets ignite before the knots. Then find a setting that comes out looking wrong to you, a tilt or an amplitude or a whole cosmology that breaks your intuition, and come tell me what broke. I read every reply, and I'm honestly curious which one gets you.

<details>
<summary>Code map, for the curious</summary>

All line numbers refer to the single self-contained <code>index.html</code> of the <a href="https://minhmpa.github.io/lss-lab/cosmic-web-sandbox/">Cosmic Web Sandbox</a>.

<table>
<thead><tr><th>Piece</th><th>Where</th></tr></thead>
<tbody>
<tr><td>Seeded Gaussian white-noise field</td><td><code>mulberry32</code> :282, <code>fillGaussian</code> :291, <code>buildGrid</code> :429</td></tr>
<tr><td>In-place 3D FFT (real ↔ Fourier)</td><td><code>fftLine</code> :304, <code>fft3d</code> :336</td></tr>
<tr><td>P(k) shape — Eisenstein–Hu (1998)</td><td><code>makeTransfer</code> :349; <code>makePk</code> :401</td></tr>
<tr><td>Growth factor D(a), Carroll+92</td><td><code>growth</code> :418</td></tr>
<tr><td>Zel'dovich displacement Ψ(k)=i k δ/k²</td><td>:454</td></tr>
<tr><td>Second-order (2LPT) term</td><td>:479</td></tr>
<tr><td>Growth applied as a single GPU uniform</td><td><code>refreshAmp</code> :854</td></tr>
<tr><td>Single-stream Jacobian density</td><td>vertex shader :645</td></tr>
<tr><td>Collapse-type (eigenvalue) classifier</td><td>vertex shader :651</td></tr>
<tr><td>Volumetric (cloud) render</td><td><code>renderPost</code> / volume path</td></tr>
<tr><td>Measured P(k) from the box</td><td><code>measurePk</code> :1324</td></tr>
</tbody>
</table>

</details>
