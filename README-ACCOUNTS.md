# BAROMETR — účty a pozvánky

Aktuální server: Flask + PostgreSQL. `server/web/` obsahuje přihlašovací bránu a aplikaci, `aplikace/` sdílený katalog a obrázky. Původní samostatné HTML soubory jsou archivní prototyp, nikoli přihlášená aplikace.

Render Blueprint: `render-auth.yaml`. Bezplatný web a databáze ve Frankfurtu. DATABASE_URL se připojuje soukromě přes fromDatabase. Zadané administrátory založí při prvním startu ADMIN1_USERNAME, ADMIN1_PASSWORD, ADMIN2_USERNAME, ADMIN2_PASSWORD; hodnoty patří pouze do Render Environment. Existující hesla se při restartu nepřepisují.

Administrátoři mohou odemykat katalog zdarma, evidovat inventuru, vytvářet jednorázové nebo omezené pozvánky, sledovat aktivitu a blokovat či odstranit běžné účty. Běžné účty nyní mohou odemykat produkty i balíčky zdarma, otevírat je a vést vlastní inventuru. Ceny jsou pouze informativní. Dočasný režim lze ukončit nastavením BAROMETR_FREE_UNLOCKS=0 a nasazením; výchozí hodnota je 1. Správa uživatelů, pozvánek a AI analýza zůstávají jen administrátorům. Oprávnění kontroluje server. Platby nejsou zapnuté. Automatické měření objemu z fotografie není implementované; inventura pracuje se zadaným množstvím.

Hesla: scrypt. Relace: náhodný token, hash v DB, Secure/HttpOnly/SameSite cookie; CSRF pro změny, omezení pokusů o přihlášení. Aktivita se uchovává 90 dní; mazání účtu odstraní jeho relace, inventuru a historii. Uživatelé jsou o evidenci aktivity informováni při registraci.

Testy: `pip install -r requirements.txt pytest` a `pytest -q tests/test_accounts.py`. Browser test vyžaduje Playwright a Chromium; TEST_URL, TEST_ADMIN1, TEST_PASSWORD1, TEST_ADMIN2, TEST_PASSWORD2 nastavte mimo zdrojový kód. SQLite funguje pouze při explicitním BAROMETR_TEST_DB pro testy; v produkci je povinná DATABASE_URL.

Dočasná bezplatná databáze vytvořená 12. 11. 2026 vyprší 12. 12. 2026. Před expirací je nutná migrace nebo změna plánu; nepředstavuje trvalé úložiště. Bezplatný web může po nečinnosti při prvním otevření chvíli startovat.

## Připravené připojení Supabase

Server podporuje `BAROMETR_DB_SCHEMA=barometr` a `DATABASE_URL` z Connect → Session pooler v Supabase. Přesný pooler host je nutné převzít z dashboardu, neodvozovat z regionu. Připojení musí mít `sslmode=require` nebo přísnější ověřování TLS.

Schéma `barometr` a jeho deset tabulek jsou připravené v projektu Supabase pro Barometr. SQL je v `database/supabase-schema.sql`. Schéma není vystavené veřejnému Data API; role anon/authenticated k němu nemají přístup. Účty aplikace zůstávají spravované Flask backendem.

Před změnou produkčního DATABASE_URL je nutné přenést a ověřit existující účty, inventury, fotografie, pozvánky a další záznamy. Připravené tabulky samy o sobě neznamenají přepnutí běžící aplikace. Původní Render databázi neodstraňovat před dokončením migrace a ověřením dat.

Bez BAROMETR_DB_SCHEMA se chování dosavadní databáze nemění. Pokud konfiguraci spravuje Blueprint, jeho DATABASE_URL nyní stále odkazuje na Render databázi přes fromDatabase; při přechodu je nutné upravit i tento zdroj konfigurace, aby další synchronizace nevrátila staré připojení.

## Produkční převod do Supabase a skladová evidence

`SUPABASE_DATABASE_URL` je oddělené připojení do Supabase (Session pooler, TLS). Původní `DATABASE_URL` zůstává zdrojem a zálohou; Blueprint ho nepřepisuje. Při prvním startu nové verze server zamkne zápisy původních tabulek, zkopíruje všech deset původních tabulek i případná nová skladová data do neveřejného schématu `barometr` a ověří počty i SHA-256 otisky všech řádků. Tím zachová ID, scrypt hesla, jména, role, odemčení, stav inventur, fotografie, relace a pozvánky. Až úspěšná transakce zapíše migrační značku, začne aplikace používat Supabase. Další starty migraci neopakují a nepřepisují novější data starou zálohou. Zdrojový zámek se uvolní po 120 sekundách, aby staré instance nemohly přijmout pozdní zápis během přepnutí provozu.

`/healthz` uvádí verzi a aktivní databázový backend bez přihlašovacích údajů. Chyba připojení nebo rozdíl při kontrole migraci zastaví; databáze se nemažou.

Nová tabulka `stock_documents` uchovává sklady, vlastní produkty, uzavřené a rozpracované inventury, pohyby a měsíční porovnání odděleně pro každý účet. `/api/stock` vyžaduje přihlášení a CSRF. Optimistická revize brání přepsání novějších dat jiným zařízením. Schéma není přístupné rolím anon/authenticated.

## Verze 0.12 — inventury, sklady a kontrola majitele

Mobilní navigace používá vysouvací boční panel. Produkty vznikají v konkrétním skladu; příjem celé dodávky má společné ID a vyžaduje jedno potvrzení. Inventurní rekapitulace rozlišuje účetní/evidovaný stav od zjištěného. Očekávané množství a nákupní cena se do uzavřeného skladového záznamu otisknou na serveru. První inventura bez výchozí evidence není označována jako schodek. Nevyplněná cena se nezaměňuje za nulové manko.

`stock_change_log` zaznamenává úpravy atomicky s jejich uložením, včetně aktéra, skladu a hodnot před/po. Původní změny před zavedením logu nelze zpětně rekonstruovat. Historie není měnitelná klientem a zůstává zachována i po odstranění účtu. Administrátoři ji otevřou v Nastavení; delegovaný čtenář pouze pro svůj přidělený pracovní prostor.

Majitel může jednotlivým uživatelům přidělovat serverem ověřovaná oprávnění a přístup ke svým skladům pomocí `stock_owner_id`. Výchozí vlastní pracovní prostory a osobní profily se nepřepisují. Role majitele se tímto formulářem nemění. Oprávnění jsou čtena z databáze při každém požadavku.

Nastavení inventury uchovává pořadí fyzických lahví a volitelnou nákupní cenu. Po dokončení sekvence se otevře celkový přehled s potvrzením, který může zahrnout také více zvážených sudů stejného produktu. Průběžná jednotlivá měření zůstávají uložená pro obnovu po výpadku; závěrečné potvrzení vytváří uzavřenou inventuru baru.

OCR displeje používá připnuté lokálně hostované Tesseract.js 6.0.1, Core 6.0.0 a tessdata_fast 4.1.0. Fotografie neopouští prohlížeč. Uživatel vybere rozpoznané číslo, zkontroluje jednotku a potvrdí výsledek po odečtení obalu. Čtení není garantované pro každý typ displeje; dostupné je označení výřezu i ruční oprava. Pro litry je potřeba skutečná hustota a hmotnost obalu, pro kusy hmotnost kusu. Tato funkce se neopírá o externí placené API ani neaktivuje nepřipojené AI měření hladiny.
