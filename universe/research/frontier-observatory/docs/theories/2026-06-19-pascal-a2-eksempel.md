# Pascals trekant som eksempel på A2

**Dato:** 2026-06-19
**Tema:** Konkret ikke-AI-eksempel på A2 (Framleis er meir grunnleggjande enn identitet)
**Kobling:** Gros-dialog, A2-derivasjon, Framleis-operatoren

---

## Den lokale regelen

Pascals trekant er definert av én enkelt lokal regel:

```
C(n, k) = C(n-1, k-1) + C(n-1, k)
```

Hver celle er summen av de to cellene over den. Regelen kjenner ikke til:
- Fibonacci-sekvensen
- Potenser av 11
- Binomialkoeffisienter
- Sierpinski-trekanten

Den kjenner bare til naboene sine.

---

## Fire emergente strukturer (I*)

### 1. Fibonacci i diagonalsummene

Summer de skrå diagonalene: 1, 1, 2, 3, 5, 8, 13, 21, ...

Fibonacci er ikke bygget inn. Det er et fikspunkt som krystalliserer seg når regelen kjøres.

### 2. Potenser av 11 i radene

Rad 0: 1 = 11^0
Rad 1: 11 = 11^1
Rad 2: 121 = 11^2
Rad 3: 1331 = 11^3
Rad 4: 14641 = 11^4

Ingen av disse er spesifisert i regelen C(n,k) = C(n-1,k-1) + C(n-1,k).

### 3. Binomialkoeffisienter

C(n, k) er antall måter å velge k elementer fra n — hele kombinatorikkens hjerte. Det oppstår som strukturen av summeringsregelen, ikke som et mål.

### 4. Sierpinski-trekanten

Farg alle odde tall: et fraktalt selvlikhetsmønster trer frem. Lokalt mønster → global fraktal.

---

## Koblingen til A2 og Framleis-operatoren

Pascals trekant er A2 i matematikkens reneste form:

| Pascal | Phi-loven |
|---|---|
| Lokal regel: C(n,k) = C(n-1,k-1) + C(n-1,k) | F(tau; sigma) = (1-alpha)*tau + alpha*sigma |
| Kjennskap til naboer — ikke til helheten | F kjenner sigma og tau — ikke I* |
| Fibonacci, 11^n, binomialkoeffisienter emergerer | I* = sigma* emergerer under iterasjon |
| Mønstrene er ikke bygget inn i regelen | Fikspunktet er ikke kjent av F på forhånd |

Identiteten (I*) er ikke et startpunkt. Den er det som dukker opp når den lokale regelen kjøres lenge nok under stabile betingelser.

---

## Relevans for Gros

Gros jobber med lukkede sløyfer og stage cost. Pascal gir et konret eksempel han kjenner:

En enkel additiv regel genererer strukturer som ikke er deriverbare fra regelen alene, men som følger nødvendig av iterasjonen. Tilsvarende: F(tau; sigma) er en enkel vektet sum, men I* er ikke trivielt — det er systemets emergente identitetslikevekt under stabil innstrøyming.

Banach sier: regelen trenger ikke å kjenne fikspunktet. Fikspunktet kommer til den.

---

*Tofoo. Phi.*
