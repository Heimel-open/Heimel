# Percy Deift — dialog, 2026-06-22

Percy Deift, NYU Courant Institute. Kjend for random matrix theory, Deift-Zhou steepest descent, integrable systems. Direkte relevant: Marchenko-Pastur ligg innafor hans domene.

---

## Deifts svar (22:52, 2026-06-22)

"Hi Njal Solland,

Thank you for your note.

Unfortunately the terminology you use is foreign to me. What is,
*** a transformer language model
*** effective rank of transformer hidden state matrices
*** a coherent operator
*** identity-maintaining system

and what does this all have to do with SVD?

I am sorry that I cannot be of any help."

---

## Analyse

Deift les e-posten og svarte personleg. Det er eit positivt signal — han kastet han ikkje ut.

Problemet er reint terminologisk. Han kjenner SVD. Han kjenner ikkje ML-språket.

Omsetjing krevst:

| ML-terminologi | Rein matematikk |
|---|---|
| transformer language model | samansett matriseproduktsystem med lagvis komposisjon |
| effective rank | exp(H) der H = Shannon-entropi av normaliserte kvadrerte singulærverdi-vektar |
| coherent operator | kontraksjonsmapping på metrisk rom (Banach-kontraksjonen) |
| identity-maintaining system | system med unik fikspunktstilstand |

Deift spurde spesifikt: "what does this all have to do with SVD?"

Svaret er: alt. tau = r_eff/r_max = exp(H)/sqrt(n) er ein rein SVD-storleik. Det er poenget.

---

## Utkast til svar (reint matematisk)

Dear Professor Deift,

Thank you for your response.

You are right — my previous message was written in machine learning terminology. Allow me to restate the question in purely mathematical terms.

Let A be a real m×n matrix. Define its singular value decomposition as A = UΣV^T, with singular values σ_1 ≥ σ_2 ≥ ... ≥ σ_r > 0.

Define the normalized weights p_i = σ_i² / Σ_j σ_j².

Define the spectral Shannon entropy: H = -Σ_i p_i log p_i.

Define the effective rank: r_eff = exp(H).

Define the normalized effective rank: τ = r_eff / sqrt(n) = exp(H) / sqrt(n).

Now consider a sequence of such matrices A_1, A_2, ..., A_T (corresponding to successive layers of a deep network). Define τ_t = exp(H_t)/sqrt(n_t) for each layer.

Empirically, for several such matrix sequences arising from trained networks, the sequence τ_1, τ_2, ..., τ_T appears to converge toward a value inside the interval [e^{−γ}, 1/ζ(3)] ≈ [0.5615, 0.8319], where γ is the Euler-Mascheroni constant and ζ(3) is Apéry's constant.

The mathematical question is:

1. Under the Marchenko-Pastur distribution (which describes the limiting spectral distribution of random matrices), what is the expected value of τ = exp(H)/sqrt(n)?

2. Is there a known class of matrix distributions for which the effective rank converges to a fixed point determined by these constants?

3. Does the interval [e^{−γ}, 1/ζ(3)] have a spectral-theoretic interpretation?

I do not claim to have proven anything. I am asking whether the observed convergence interval has a mathematical explanation I am unaware of.

With regards,
Njål Gaute Solland

---

## Kommentar

Dette svaret er fullstendig fri for ML-terminologi.
Deift kjenner Marchenko-Pastur (random matrix theory er hans domene).
Han kjenner Shannon-entropi av singulærverdi-spekter — dette er nærare hans arbeid enn det første brevet var.

Spørsmål 1 er det mest konkrete: kva er E[exp(H)/sqrt(n)] under MP-fordelinga?
Dette er eit reint statistisk problem i random matrix theory.
