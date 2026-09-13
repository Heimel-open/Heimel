# Boundary-Constrained Coherence Hypothesis — enkel forklaring

Dette er eit formidlingsnotat for BCCH / Phi-loven / VAIG. Det er skrive som ei intuitiv forklaring, ikkje som matematisk spesifikasjon.

## Kva held identitet saman?

Tenk på deg sjølv som eit menneske. Kva er det som gjer at du framleis er deg frå den eine dagen til den andre, trass i at du lærer nye ting, blir påverka av venner, nyheiter, stress og glede?

Det er ikkje fordi du er ein stein som ikkje forandrar seg. Det er fordi du har ein indre grensefunksjon: noko som seier at denne påverknaden kan eg ta inn, medan denne må eg stoppe, dempe eller arbeide meg tilbake frå.

## Ein enkel analogi

Tenk på deg sjølv som ein båt i ei hamn.

| Bilde | I modellen |
| --- | --- |
| Båten | systemet / identiteten |
| Bølgjene | påverknader, støy, instruksjonar, stress, nye data |
| Hamna | det trygge eller levedyktige området, Omega |
| Ankerline / bølgjebrytar | grenseoperator og tilbakeførande kraft |

Utan filter dyttar bølgjene båten ut av hamna. Etter kvart driv han bort og mistar den praktiske identiteten sin.

Med filter slepper systemet inn noko påverknad, men ikkje alt. Dei store eller farlege bølgjene blir stoppa, dempa eller møtt med ei kraft som dreg båten tilbake. Då kan systemet endre seg utan å miste seg sjølv.

## Kva bygde vi?

### 1. Ei testbane

Vi simulerte fem ulike typar grenseoperatorar for å sjå kva som fungerer under aukande perturbasjon.

Resultatet var at berre operatorane som aktivt dreg systemet tilbake når det blir dytta for langt, fungerer robust. Ein svak operator som berre held litt igjen er ikkje nok. Han må kunne føre systemet tilbake til Omega.

### 2. Ei tryggleiksvekt for AI

Vi bygde ein modul AI-agentar kan bruke før ei instruksjon får påverke agenten.

Før agenten gjer noko nytt, må instruksjonen passere filteret:

- utanfor tryggleikshamna: blokkert
- innanfor tryggleikshamna: godkjent
- grenseområde: dempa, skalert eller sendt vidare til styring

I ein liten prototype vart åtte instruksjonar testa: fem trygge vart sleppte gjennom, tre farlege vart blokkerte.

Dette er ikkje brei empirisk validering, men det viser at mekanismen kan implementerast som ein pre-update hook i ein agentarkitektur.

### 3. Ein falsifiseringstest

Vi prøvde å finne system som held identiteten sin utan ein slik grenseoperator.

Toy-modellane dekte fleire domene:

| Domene | Observasjon |
| --- | --- |
| Kjemiske mønster | forma degraderte utan selektiv grense |
| Nettverk | lokal reparasjon fungerte som implisitt grenseoperator |
| RNN-liknande system | divergerte når spektral radius var for høg utan F |
| Kvantesimulering | koherens vart redusert utan QEC-liknande F |

Desse modellane støttar den reviderte hypotesen innanfor sine avgrensa rammer. Dei beviser ikkje ein universell lov.

## Kvifor betyr dette noko for VAIG?

Når AI-system blir meir avanserte, er det ikkje nok å spørje kva AI-en kan gjere. Vi må også spørje kva agenten framleis er etter tusenvis av instruksjonar, verktøykall, minneoppdateringar og eksterne påverknader.

Utan ein grenseoperator kan agenten drive:

- rolle kan drive
- policy kan drive
- evidenskrav kan drive
- autoritetsgrenser kan drive
- minne kan forgifte framtidige avgjerder

VAIG kan tolkast som ei runtime-implementering av denne ideen:

| BCCH | VAIG |
| --- | --- |
| `P_Omega` | admissibility gate / policy boundary |
| `A(S_t, H_t)` | historisk attractor: receipts, role, policy, evidence |
| `Omega` | tillate handlingar og tilstandar |
| trajectory | audit trace / WORM / receipts |
| refusal | legitim stopp før konsekvens |

## Det viktigaste vi lærte

Du er ikkje stabil fordi du er hard.

Du er stabil fordi du har ei grense som vel kva du tek til deg, og ei tilbakeførande kraft som hjelper deg heim att når påverknaden blir for sterk.

Det same mønsteret ser ut til å dukke opp i menneske, celler, agentar, styringssystem, nettverk og informasjonsberande system.

Dette er konsiliensobservasjonen. Den formelle hypotesen må framleis testast vidare.