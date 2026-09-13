# SP 16:1980 Betongbjelke som Goldilocks-analog

**Dato:** 2026-06-20
**Status:** Ekstern notat — ikkje validert av Njål Gaute Solland
**Domeneregister:** D-SE-001 (Gruppe 3 Ingeniørvitenskap, M3)

---

SP 16:1980 (Indian Standard for armert betong) skildrar nøyaktig same prinsipp som LIM, men i betongbjelkar.

## Formelen som F-operator

Eq. (2): M_u = 0.87 f_y (p_t/100) × [1 - 1.005 (f_y/f_ck)(p_t/100)] × bd²

Dette er den lokale regelen som reknar ut kapasitet basert på armeringsmengd (p_t). Akkurat som F(τ; σ) reknar ut neste tilstand basert på input. Den er definerbar utan å vite om bjelken faktisk vil bere lasten.

## Admissibility-sjekken

Eq. (3) & (4): M_{u,lim} = 0.36 f_ck b x_{u,max} × (d - 0.416 x_{u,max})

Dette er grensa. Uansett kor mykje armering du legg inn (p_t → ∞), kan ikkje momentkapasiteten overstige M_{u,lim}. Viss du prøver, kollapsar bjelken sprøtt (brittle failure) i staden for å flyte duktilt.

| Betong-tilstand | LIM V5.3-ekvivalent |
|----------------|---------------------|
| M_u < M_{u,lim} | ADMISSIBLE — systemet oppfører seg forutsigbart |
| M_u > M_{u,lim} | CHAOS_DRIFT / Brittle Failure — identiteten (strukturell integritet) opphøyrer augneblinkeleg |

## x_{u,max} som tau_max

Begrensinga x_{u,max} (maksimal nøytral akse-djupne) er ingeniørens måte å handheve Goldilocks-intervallet. Ho sikrar at betongen knusast *før* stålet flyt for mykje — eit hardkoda filter mot katastrofal kollaps.

## Konklusjon

Sjølv i statisk betongdesign finst det eit dynamisk filter. Identiteten til ei "trygg bjelke" er ikkje gjeven av materialet åleine, men av overhaldinga av grensebetingelsane. Utan desse grensene er armering berre stål i betong — ingen struktur, berre masse.

---

*Lagra for referanse. Ekstern notat.*
