# Skladové kontroly a nastavení provozu

## Minimální zásoba

Minimum je ve formuláři produktu nepovinné. Prázdné pole upozornění vypne; explicitní nula upozorní při vyčerpání. Dříve nastavené kladné minimum zůstává aktivní. Upozornění platí při `aktuální množství <= minimum`. Chybějící měření ani odstraněný sklad upozornění nevytvářejí.

Widget „Nutné doplnit skladové zásoby!“ je prvním widgetem přehledu majitele a provozu. Majitel vidí provoz i sklad, zaměstnanec pouze sklady ve svém oprávněném rozsahu. Stav v tabulce a detailu produktu je při dosažení minima červeně zvýrazněný.

## Provozní doba a upozornění

Majitel otevře „Otevírací doba a upozornění“ na kartě provozu nebo v nastavení majitele. Každý den může být zavřený nebo mít čas otevření a zavření. Dřívější zavření než otevření znamená směnu přes půlnoc. Stejný čas znamená nepřetržitý provoz daný den. Nastavení má vlastní časové pásmo, výchozí je Praha. Bez nastavených hodin se události mimo provozní dobu neoznačují.

Limity lze nastavit samostatně pro kusy, litry, kilogramy a balení, dále pro procentní rozdíl inventury, opakování a čas zpětného přesunu. Přehled vyhodnocuje posledních 30 dní: velké pohyby a odpisy, opakované odpisy, inventurní rozdíly a opakované manko, pohyby a inventury mimo otevírací dobu, rychlé přesuny tam a zpět a opakované opravy schválených inventur. Opakované odpisy se seskupují v sedmidenním okně. Bez výchozího stavu se nepočítá manko.

Každý případ uvádí důvod označení, autora, čas, podklady a odkaz na záznam. Majitel může zapsat vysvětlení, označit případ za vysvětlený a znovu ho otevřít. Historie těchto rozhodnutí zůstává zachovaná; aktuální přehled zobrazuje případy v třicetidenním okně a podle platných limitů. Upozornění neurčuje viníka ani samo o sobě nedokazuje pochybení.

## Odpisy

Oprávnění `stock.writeoff` je samostatné a pro běžné uživatele ve výchozím stavu vypnuté. Majitel ho přiděluje v oprávněních zaměstnance nebo pozice. `stock.move` dál umožňuje výdej a přesun, nikoli odpis. Kontrola platí v běžné aplikaci i v pracovním terminálu na serveru.

Nový odpis musí obsahovat důvod o délce 5–500 znaků. Snižuje skladový stav a uchovává autora a čas. Pracovní terminál navíc kontroluje dostupné množství a používá ID operace proti dvojímu zápisu.

## Provoz a ověření

Procentuální načítání bylo odstraněno; indikátory skutečného ukládání v tlačítkách zůstávají. Nová metadata provozů a historie vysvětlení se doplní při startu serveru. Původní skladové doklady se nepřepisují. Nové databázové tabulky jsou soukromé, s RLS a bez přístupu veřejných klientských rolí.

Ověření: `tests/test_controls.py`, související testy skladů, oprávnění, oznámení a inventur; `tests/controls-browser.cjs`, `tests/motion-browser.cjs` a `tests/sidebar-profiles-browser.cjs` proti oddělené testovací databázi.
