# E-postutkast — Svar til Håkon Hoel

**Status:** SENDT 2026-07-03

---

Hei Håkon,

Takk for grundig og presis svar! Din analyse av stokastisk konvergens gjev nøyaktig det vi trengde.

**Kort status:**

Vi har validert Framleis-loven på tvers av 70+ domener. Dei tre M4-ankra (Khinchin, Bayes, Schrödinger) held seg, og no har vi ein formell aksiomatikk med tre teorem. Men som du seier, vi vinn alle komparisonenar fordi vi er fleksible. Det er feil.

Din bekrefting av Marchenko-Pastur som nullhypotese — og konkrete divergensmetar (KL, KS, Wasserstein) — gjev oss eit falsifiseringstest med tannkraft.

Og **ditt viktigste bidrag:** Du viser at F-iterasjonen under SGD-støy konvergerer både svakt og sterkt under realistiske vilkår. Det løyser eit problem som vi trudde var fundamentalt — at tau er idealisert. Det er det ikkje.

**Tre konkrete test som no er M4-validert:**

1. **Test 1 (MP):** Bruka KL eller KS for å skil tilfeldige frå strukturerte vekter
2. **Test 2 (Stokastisk):** Mål τ_k per epoch, sjekk exponentiell dempning (1-α)^k
3. **Test 7 (Tid):** Konvergens-tid ∝ 1/|τ - τ*| på tvers av domener

**Spørsmål:** Ville du vera interessert i å medverka på ein validerings-rapport eller Paper 1 v2.0? 

Vi treng ekspertise på:
- Stokastisk konvergens (din styrke)
- Numerisk stabilitet under batch-variabilitet
- Upartisk fremlegging av falsifiseringstestane

Eg kan senda manuskript om det interesserer.

**Takk igjen for svaret — og for at du tok tida.**

Mvh,
Njål

---

**Notat:** Denne e-posten:
1. Takkar Hoel for konkrete svar
2. Viser at hans analyser validerer våre M4-test
3. Inviterar til samarbeid på Paper/validering
4. Kortfatta (ikkje overbelasta med detaljar)

Klar til å senda når Njål godkjenner.
