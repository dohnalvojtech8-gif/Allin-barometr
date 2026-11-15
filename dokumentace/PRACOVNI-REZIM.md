# Pracovní terminál

Pracovní režim je určený pro sdílený tablet nebo počítač. Otevírá se na `/work` a přihlašuje zaměstnance čtyřmístným PINem. PINové přihlášení neposkytuje přístup do běžné správy účtu.

## První zapnutí

1. Majitel se na zařízení přihlásí běžným jménem a heslem.
2. V **Nastavení → Nastavit můj pracovní PIN** si nastaví vlastní PIN.
3. Ve **Správě uživatelů → Detail → Oprávnění** připojí zaměstnance ke svým skladům a povolí jim příjem, výdej nebo historii změn. Inventura terminálu vyžaduje současně oprávnění **Provádět a ukládat inventury** a **Spouštět inventury na pracovním terminálu**.
4. V detailu zaměstnance pod **Nastavit PIN a sklady** nastaví jedinečný PIN a vybere konkrétní sklady, nebo všechny sklady provozu. Omezení skladů platí také v běžné aplikaci. Majitel vždy zachovává přístup ke všem svým skladům.
5. V **Nastavení → Zapnout pracovní režim** potvrdí propojení zařízení. Běžné přihlášení majitele se na tomto zařízení ukončí.

PIN se po uložení nezobrazuje. Majitel jej může nahradit novým nebo zrušit. Změna PINu či výběru skladů zaměstnance odhlásí z terminálů. PIN musí být v provozu jedinečný; nesprávné pokusy jsou omezené.

## Každodenní práce

Po zadání PINu se zobrazí produkty z povolených skladů. Klepnutí na produkt nabídne povolený příjem nebo výdej. Množství a výsledný stav jsou vidět před uložením. Výdej nad dostupné množství nelze uložit.

Menu vpravo nahoře obsahuje rychlý příjem, výdej, kontrolu změn a inventuru podle oprávnění. Inventura vyžaduje skutečné množství každé položky a potvrzení rekapitulace. Po uložení se její stav, historie a datum promítnou do společných skladových dat.

Po pěti minutách nečinnosti se pracovní přihlášení zruší také na serveru. Zamknutí vymaže otevřené formuláře i neuloženou inventuru. Samotné čtení skladů přihlášení neprodlužuje. Při návratu ze spánku nebo jiného okna se přihlášení znovu kontroluje.

**PIN majitele pracovní režim nevypíná.** Majitel s ním běžně přijímá a vydává zboží. Odpojení zařízení vyžaduje samostatnou volbu **Menu → Ukončit pracovní režim** a potvrzení. Další aktivace pak vyžaduje jméno a heslo majitele.

## Obrazovka a připojení

PINová brána má velká pole a číselnou klávesnici; podporuje tablet naležato i na výšku. Tlačítko **Celá obrazovka** odstraní ovládání prohlížeče tam, kde jej přístroj podporuje.

Terminál využívá Screen Wake Lock, pokud jej prohlížeč povolí. Funguje při zobrazení aplikace v popředí a nemůže zabránit manuálnímu zhasnutí přístroje. Pokud prohlížeč tuto funkci nepodporuje, terminál doporučí vypnout automatické uspání v nastavení zařízení. Web nemůže vynutit nastavení operačního systému.

Zápisy vyžadují připojení k serveru. Při souběžné změně skladu se uložením nepřepíší novější data; uživatel musí načíst aktuální stav a zkontrolovat zápis. Opakované odeslání stejného zápisu nevytváří další pohyb ani inventuru.

## Ověření

- `python -m pytest -q` zahrnuje serverové testy PINů, oprávnění, skladů, expirace, opakovaných zápisů a inventur.
- `node tests/work-browser.cjs` ověřuje průchod na lokálním testovacím serveru s účtem `WorkOwner` a heslem `work-owner-test-password`. Spouštějte jen s vlastní testovací databází. Volitelná adresa serveru: `BAROMETR_WORK_TEST_URL`.
