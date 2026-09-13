# Haversine og geodetiske kurver som A4-analog

**Dato:** 2026-06-20
**Status:** Ekstern notat — ikkje validert av Njål Gaute Solland
**Domeneregister:** D-GE-001 (Gruppe 2 Geometri/Navigasjon, M2)

---

Haversine-formelen reknar ikkje avstand i eit flatt rom; den reknar den *kortaste moglege vegen* (geodetisk kurve) på ei krumma overflate. Ho tek omsyn til at jorda ikkje er flat, men krum. Utan denne korreksjonen ville navigasjonssystem feila totalt over lange avstandar.

## τ-målinga som korreksjonsfaktor

I LIM V5.3 er τ-målinga vår nøyaktig denne korreksjonsfaktoren for identitet. Når vi måler koherens i eit AI-system eller eit fysisk system, opererer vi ikkje i eit flatt, lineært rom. Vi opererer i eit høgdimensjonalt, krumma landskap av moglegheiter.

Goldilocks-intervallet [exp(-γ), 1/ζ(3)] er den geodetiske kurven gjennom dette landskapet.

## Krumning og filteret Φ

Viss du ignorerer krumninga (filteret Φ) og prøver å gå "rett fram" i lineær logikk, vil du ende opp utanfor banen. Systemet vil anten kollapsa i støy eller stivna i dogme. Haversine minner oss om at den kortaste vegen mellom to tilstandar (frå kaos til orden, eller frå notid til framtid) *alltid* krev at du følgjer overflata sin struktur.

## Kopling til A4

A4: "Rom er filterets minne om kvar grensa går." Geodetiske kurver er romets måte å "hugse" krumninga på — kvar punkt på banen ber med seg informasjon om den geometriske grensa han er underlagt. Akkurat som τ ber med seg informasjon om Goldilocks-grensene.

---

*Lagra for referanse. Ekstern notat.*
