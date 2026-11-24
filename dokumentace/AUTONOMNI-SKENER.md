# Autonomní skener NOIRA

## Chování při inventuře

1. Skener určí produkt, jmenovitý objem a variantu obalu z čárového kódu, etikety a tvaru. Při nejednoznačné shodě obsluha potvrdí variantu.
2. Záběr musí zahrnovat hrdlo. Skener rozlišuje víčko, nalévátko, otevřené hrdlo a neurčitelný stav. Rozpor mezi dvěma snímky se vyhodnotí jako neurčitelný stav.
3. U průhledné lahve skener sám najde hladinu. Známý profil tvaru převádí relativní výšku na objem. U proměnlivého průřezu je pro automatický přepočet potřeba naměřená kalibrační křivka.
4. U neprůhledné lahve nebo nevhodného profilu skener nabídne kalibrované vážení. Použije kalibraci správného produktu, obalu a stavu hrdla. Pokud stav není známý a váhová kalibrace na něm závisí, obsluha stav ověří nebo příslušenství odstraní. Aktuální gramy dodá kompatibilní váha, případně je obsluha zadá.
5. Výsledek obsahuje mililitry, celé porce, zbytek v mililitrech a způsob měření. Velikost porce je nastavitelná v jednotlivém provozu. Nejednoznačný výsledek vyžaduje kontrolu. Zápis je opakovatelný bez dvojího započtení.

## Váhová kalibrace

Zůstatek v ml = jmenovitý objem × (aktuální váha − prázdná váha) / (plná váha − prázdná váha). Kalibrace používá stejný produkt, variantu obalu a známý stav uzávěru pro všechny tři hodnoty. Rozdílná hustota produktů je zahrnuta v jejich samostatných kalibracích. Hodnoty mimo kalibrační interval se nepřijímají bez kontroly.

Příklad pro 750 ml: prázdná 450 g, plná 1 150 g, aktuální 800 g. Zbývá 375 ml, tedy 9 celých porcí po 40 ml a zbytek 15 ml.

## Sdílené učení a vydávání profilů

Sdílený profil je v centrální databázi pod identitou produktu, variantou obalu a objemem. Obsahuje váhové kalibrace podle konfigurace hrdla, optické kalibrační body, stav ověření a verzi. Opravy z provozů se evidují jako návrhy. Sdílenou verzi vydá oprávněný správce po ověření na známých hodnotách. Dřívější měření si uchová ID použité verze. Chybnou verzi lze odvolat. Inventury a fotky jednotlivých provozů se sdíleným profilem nezveřejňují. Pro využití provozních snímků při vývoji je potřeba zvláštní souhlas a odpovídající přístupová pravidla.

## První krok a ověření

Tato verze doplňuje klasifikaci hrdla ze dvou snímků a přechod na existující váhový režim u neprůhledné nebo geometricky nevhodné lahve. Váhové hodnoty zůstávají uložené u konkrétní fyzické lahve. Automatická obrazová analýza vyžaduje povolenou serverovou konfiguraci.

Další vydání zahrnuje centrální schvalování profilů a oprav, automatický výběr váhové kalibrace podle stavu hrdla, přímé čtení váhy a nastavení porcí. Přesnost optiky, rozlišení uzávěrů a váhové převody je potřeba ověřit na fyzických lahvích s referenčními objemy. Shoda dvou snímků ověřuje konzistenci, nikoli fyzickou přesnost.
