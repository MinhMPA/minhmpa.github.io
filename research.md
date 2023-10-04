---
layout: page
title: Research
sitemap:
    priority: 0.7
    lastmod: 2017-11-02
    changefreq: weekly
---
<p align="center">
 <span><img src="{{ "images/ESA_Planck_cosmic_history.jpg" | absolute_url }}" alt="" width="100%" height="100%" /></span></p>
*How exactly did galaxies, galaxy clusters and filaments form and evolve?*  
*How do tiny initial fluctuations that seed the large-scale structure look?*  
*What set those initial conditions of our Universe?*  
I work between the interface of astrophysics and cosmology trying to answer those questions.

For cosmologists, I am a modeler. I model different observables, including galaxy number counts, galaxy intrinsic shapes, cluster Sunyaev-Zeldovich (SZ) effect in the Cosmic Microwave Background (CMB), and growth of LSS, in order to confront theoretical assumptions and predictions with current and future observations. Specifically, most of my works have focused on *forward*-modeling the aforementioned statistics directly at the *field*-level.
In particular, physical processes and systematic effects are explicitly modeled in forward simulations, all starting from initial conditions of the observed volume.

<hr />

To this end, I combine perturbative approaches, e.g. perturbation theory (PT) or effective field theory of large-scale structure (EFTofLSS) and Bayesian statistics to build roburst (forward-)models that yield unbiased inference. To interface Bayesian inference with galaxy and/or CMB survey datasets requires developing sophisticated computer algorithms and scalable implementations, while, sometimes, to reach beyond the regime of PT and EFTofLSS necessitates utilizing N-body simulations and simulation-based inference (SBI) techniques.

The full list of my publications can be found <a href="https://arxiv.org/search/?query=nguyen%2C+nhat-minh&searchtype=author&abstracts=show&order=-announced_date_first&size=50">here</a> on arxiv. Below I highlight some key projects where I have a) led the effort or b) made key contributions and/or am one the co-corresponding authors.

### Latest (interesting!) result

Analyzing current CMB and LSS data, we detect evidence for a suppressed growth rate of large scale structure in the late Universe.

<!--The first plot below illustrate this growth suppression effect. It compares the constraint on growth rate assuming General Relativity (GR) and the concordance cosmological model $\Lambda$CDM (black) and the constraint on growth rate should growth be allowed to deviate from the prediction by GR+$\Lambda$CDM. The second plot elucidates a very interesting feature of the suppressed growth. That is, it offers a new interpretation for the so-called S8 tension: If LSS growth rate was to be suppressed fairly recently, the constraints on matter fluctuation amplitude at redshift $z=0$, S8, from CMB and LSS can be brought into well agreement.-->

<!--<p align="center">-->
<!--<img src="{{ "/images/fsigma8z_constraints_vs_data.png" | absolute_url }}"  width="100%" height="80%" style="float:left; padding-left:-1px;-->
<!--padding-bottom:25px; padding-right:25px ; padding-top:10px" alt="" />-->
<!--</p>-->
<!--<p align="center">-->
<!--<img src="{{ "/images/gamma_S8_omegam_H0_2Dcontours.png" | absolute_url }}"  width="100%" height="80%" style="float:left; padding-left:-1px;-->
<!--padding-bottom:25px; padding-right:25px ; padding-top:10px" alt="" />-->
<!--</p>-->

Here is my interview with <a href="https://twitter.com/just_shaun">Shaun Hotchkiss</a> on Cosmology Talks about this result:
<iframe
    width="640"
    height="480"
    src="https://www.youtube.com/embed/Tov5KahGEVQ"
    frameborder="0"
    allow="encrypted-media"
    allowfullscreen
>
</iframe>

If you are still curious, please see the <a href="https://arxiv.org/abs/2302.01331">arXiv preprint</a> for full details.
<The published version is now <a href="https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.131.111001">online</a> at Physical Review Letters as an <a href="https://drive.google.com/file/d/1IRPuo9XLeOXeCcimqh63ZLEVlmJye4iP/view?usp=sharing">Editor's Suggestion</a>.

New Scientist's coverage of our results can be found <a href="https://drive.google.com/file/d/1n8CXz9rjoiPBGgbkAQXByujPVaYo3saO/view?usp=sharing">here</a>.
You might also want to check out the original press release by University of Michigan News <a href="https://news.umich.edu/the-universe-caught-suppressing-cosmic-structure-growth/">here</a>.
If you prefer to read about it in my own words, <a href="https://phys.org/news/2023-10-molasses-cosmic-large-scale-caught-slower.html">here</a> is my Science x Dialog on Phys.org.

### Field-level, forward-modeling of galaxy clustering

<p align="center">
<img src="{{ "/images/ICBORG_flowchart.png" | absolute_url }}"  width="100%" height="80%" style="float:left; padding-left:-1px;
padding-bottom:25px; padding-right:25px ; padding-top:10px" alt="" />
</p>

The above flowchart depicts the process of how to connect early fluctuations to late-time 3D galaxy field observed by galaxy redshift surveys in the forward-modeling framework. While the whole process involves quite a number of moving parts, using N-body simulations as the reference (hence ``galaxy``->``halo`` in the third blue block), I have systematically investigated how each ingredient, including but not limited to gravity, galaxy bias model and likelihood (red blocks), affects the inferred initial conditions (first blue block). I demonstrate that the (Fourier) phase of initial conditions are robustly recovered well beyond the linear limit in quasi-linear regime. Further, I show that the bias model and likelihood for galaxy can significantly bias the inferred amplitude of initial conditions, which implies the same for inference of cosmological parameters. Alarmingly, none of the models I tested could avoid this bias. My findings underlie the demand for either a more rigorous physical model, e.g. EFTofLSS, or a more flexible data-driven approach, e.g. SBI.

<a href="https://iopscience.iop.org/article/10.1088/1475-7516/2021/03/058"><b>Open-access article</b></a> published on <i>Journal of Cosmology and Astroparticle Physics</i>, March 2021. See also this <a href="https://www.mpa-garching.mpg.de/926077/hl202103?c=1056316">press release</a> featured on MPA research highlights, March 2021. Our follow-up work has been published on <a href="https://iopscience.iop.org/article/10.1088/1475-7516/2023/07/063">JCAP</a>. A dedicated description of that paper will soon appear here!

<hr />

### Measuring the kinematic Sunyaev-Zel'dovich while optimally account for cluster velocity uncertainty

As CMB photons traverse the Universe towards us and our telescopes, they encounter and scatter off free electrons inside cluster of galaxies along the line-of-sight (LOS). These scatterings leave tiny secondary anisotropiess on the CMB map.
The cartoon below illustrates such imprints, specifically the *kinematic Sunyaev-Zel'dovich effect* (kSZ): the CMB photons appear to be Doppler-shifted towards either blue or red -- that is, hot or cold relatively to the primary CMB blackbody temperature -- depending on whether the cluster is moving away or towards the observer. At first order, for each individual galaxy cluster, the shift is linearly proportional to the product of cluster's LOS velocity and free electron abundance.
<p align="center">
 <span class=""><img src="{{ "images/kSZmap_WebSkylite.png" | absolute_url }}" alt="" width="100%" height="100%" /></span></p> 

<p> I have developed a Bayesian framework to optimally extract the kSZ signal from cross-correlation between CMB and cluster velocity datasets. The framework, for the first time, consistenly accounts for uncertainty in large-scale velocity reconstruction. On two modest samples of maxBCG galaxy clusters with spectrocospic or photometric reshifts, I find evidence of the kSZ signal at more than 2-sigma level. The amount of free electrons hosted by these clusters is in agreement with the cosmic abundance. My findings are summarized in the figure on the right which shows the kSZ signal amplitude -- or, equivalently, the fraction of (free-)electrons-to-dark-matter -- as a function of cluster relative apparent size.</p>
<p>I further demonstrate that, without accounting for velocity uncertainty, one can bias their kSZ measurement by up to a factor of 2 (see e.g. figure 4 in the paper below).
 <span class="image right"><img src="{{ "images/kSZ_amplitude.png" | absolute_url }}" alt="" width="120%" height="120%" /></span></p>

<a href="https://iopscience.iop.org/article/10.1088/1475-7516/2020/12/011"><b>Open-access article</b></a> published on <i>Journal of Cosmology and Astroparticle Physics</i>, December 2020. See also the same MPA <a href="https://www.mpa-garching.mpg.de/926077/hl202103?c=1056316">research highlight article</a> highlighted above.

I continue to develop forward-model pipeline to infer cluster gas properties from CMB measurements, which is publicly available on <a href="https://github.com/MinhMPA/VelmaSZ">here</a> on GitHub.
The goal is to turn the kSZ effect into not only a measurement of cluster gas properties but also a cosmological probe for primordial non-Gaussianity or growth of structure.

<hr />

### Measuring and modeling galaxy shapes at the field level

The tidal field of large-scale structure tends to align with large-scale filaments. This has indeed been observed in both gravity-only and hydrodynamics cosmological simulations, e.g. the HORIZON-AGN shown in the figure below, taken from Codis et al. 2015.
<p align="center">
<span><img src="{{ "/images/IA_tidal_filament.png" | absolute_url }}" alt="Tidal_field_filament_alignment" width="100%" height="100%"/></span></p>  

As galaxies form along these filaments, they are streched or squeezed by the tidal force, hence the *intrinsic alignment* between galaxy ellipticity (shape) with the tidal field (host filament).
We are the first to measure the amplitude of this intrinsic alignment at the field level, i.e. galaxy by galaxy, in observational data.
Specifically, using an inferred tidal field of Cold Dark Matter (which cannot be observed directly), and the measured shapes of luminous red galaxies within the same volume, we detect an alignment signal at more than 4-sigma level. Our findings align with the galaxy intrinsic alignment picture described above: at linear order, there exists a clear correlation between the LSS tidal field and the galaxy shape, whose amplitude is constant on very large scales, up to 80-100 Mpc/h.
<p align="center">
<span><img src="{{ "/images/IA_amplitude.png" | absolute_url }}" alt="IA_amplitude" width="100%" height="100%" /></span>
</p>

<p>This work was done in collaboration with <a href="https://www.su.se/english/profiles/elts6570-1.450440">Eleni Tsaprazi</a> and the Aquila consortium.<br/>
<a href="https://iopscience.iop.org/article/10.1088/1475-7516/2022/08/003"><b>Open-access article</b></a>, published on <i>Journal of Cosmology and Astroparticle Physics</i>, August 2022. See also this <a href="https://www.mpa-garching.mpg.de/1052846/hl202204?c=27981">press release</a> featured on MPA research highlights, April 2022.</p>

<p>My follow-up project involves developing field-level model of galaxy intrinsic shapes as biased tracers of the LSS tidal field and initial conditions. This will unlock the potential of (intrinsic) shapes as a novel probe of cosmological parameters. I choose the EFTofLSS approach for data modeling and the <a href="https://gitlab.mpcdf.mpg.de/leftfield">LEFTfield framework</a> for code implementation. The latter is going to be publicly released <a href="https://gitlab.mpcdf.mpg.de/leftfield/release">here</a> on GitLab once ready.
