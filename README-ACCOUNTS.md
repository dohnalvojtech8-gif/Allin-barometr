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

`SUPABASE_DATABASE_URL` je oddělené připojení do Supabase (Session pooler, TLS). Původní `DATABASE_URL` zůstává zdrojem a zálohou; Blueprint ho nepřepisuje. Při prvním startu nové verze server zamkne zápisy původních tabulek, zkopíruje všech deset tabulek do neveřejného schématu `barometr` a ověří počty i SHA-256 otisky všech řádků. Tím zachová ID, scrypt hesla, jména, role, odemčení, stav inventur, fotografie, relace a pozvánky. Až úspěšná transakce zapíše migrační značku, začne aplikace používat Supabase. Další starty migraci neopakují a nepřepisují novější data starou zálohou. Zdrojový zámek se uvolní po 120 sekundách, aby staré instance nemohly přijmout pozdní zápis během přepnutí provozu.

`/healthz` uvádí verzi a aktivní databázový backend bez přihlašovacích údajů. Chyba připojení nebo rozdíl při kontrole migraci zastaví; databáze se nemažou.

Nová tabulka `stock_documents` uchovává sklady, vlastní produkty, uzavřené a rozpracované inventury, pohyby a měsíční porovnání odděleně pro každý účet. `/api/stock` vyžaduje přihlášení a CSRF. Optimistická revize brání přepsání novějších dat jiným zařízením. Schéma není přístupné rolím anon/authenticated.
