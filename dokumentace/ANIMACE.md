# Vybrané animace NOIRA

| Oblast | Varianta | Chování |
| --- | --- | --- |
| Tlačítka | 8 | Indikátor během skutečného zápisu, obnovení popisku po dokončení |
| Přechody | 1 | Prolnutí nového obsahu; stávající přehled zůstává při načítání viditelný |
| Boční menu | 2 | Mobilní panel odsune obsah o 90 px |
| Karty provozů | 5 | Zvýraznění provozu při použití jeho ovládacích prvků |
| Dialogy | 7 | Odhalení ze středu bez posunu obsahu |
| Načítání | Zrušeno | Procentuální indikátor byl na přání majitele odstraněn |
| Potvrzení | 8 | Indikátor se po úspěšném zápisu změní na zatržítko |
| Formuláře | 10 | Telefon a e-mail zaměstnance se přidávají postupně |

Společné soubory `server/web/motion.js` a `motion.css` používá panel majitele, aplikace provozu a pracovní terminál. Nová pole mají dál původní názvy a validaci; uložené hodnoty zůstávají dostupné.

Efekty respektují `prefers-reduced-motion`.

Ověření: `tests/motion-browser.cjs` a `tests/sidebar-profiles-browser.cjs` proti izolovanému testovacímu serveru přes `NOIRA_TEST_URL`.
