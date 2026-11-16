# NOIRA · Midnight Club

Centrální aplikace majitele s libovolným počtem samostatných provozů. Vychází z [Barometru](https://github.com/dohnalvojtech8-gif/Barometr); zachovává jeho účtovou aplikaci, obchod s lahvemi a balíčky, sklady, inventury, kalibrace, skenování i pracovní terminál s PINem.

## Menu majitele

1. Souhrnný přehled všech provozů
2. Moje provozy
3. Uživatelé a přístupy k provozům
4. Vytvoření nového provozu
5. Porovnání provozů
6. Aktivita napříč provozy
7. Nastavení majitele a účtu

Menu uvnitř provozu přebírá původní Barometr.

## Render + Supabase

1. Vytvořte samostatný projekt Supabase pro Allin Barometr.
2. V Supabase otevřete **Connect → Session pooler**. Použijte PostgreSQL connection string (port 5432), doplňte databázové heslo a `sslmode=require`. Speciální znaky v hesle musí být URL encoded. Project URL ani API klíč nejsou připojením k databázi.
3. V Renderu vytvořte Blueprint z tohoto repozitáře; načte soubor `render.yaml`. Případně založte Python Web Service se stejnými příkazy.
4. V Render **Environment** vyplňte:

| Proměnná | Hodnota |
|---|---|
| `SUPABASE_DATABASE_URL` | PostgreSQL connection string ze Supabase; pouze na serveru |
| `ADMIN1_USERNAME` | Vaše přihlašovací jméno majitele |
| `ADMIN1_PASSWORD` | Dlouhé vlastní heslo majitele |
| `BAROMETR_DB_SCHEMA` | `allin_barometr` (již v Blueprintu) |

Build: `pip install -r requirements.txt`

Start: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 server.app:app`

Health check: `/healthz`

5. Spusťte deploy a otevřete adresu služby. Přihlaste se údaji z bodu 4 a vytvořte první provoz.

Tabulky a soukromá schémata se vytvářejí automaticky. Připojená databázová role potřebuje oprávnění vytvářet schémata a tabulky (standardní PostgreSQL připojení projektu). Schémata `allin_barometr` a `venue_*` nepřidávejte mezi Exposed schemas v Supabase. Aplikace používá vlastní serverové účty, nikoli Supabase Auth. Není potřeba publishable ani service role API klíč.

V centrálním panelu i v profilu každého provozu je tlačítko Změnit heslo. U majitele mění společné přihlašovací heslo; zaměstnanec mění pouze heslo svého účtu v konkrétním provozu. Zaměstnanecká hesla mají nejméně 8 znaků, majitel může použít vlastní heslo od 4 znaků.

Heslo z prostředí vytvoří účet při prvním startu; pozdější změny hesla se provádějí v aplikaci. Změna původního env hesla nepřepisuje existující účet.

## Oddělení provozů

- `/` je centrální panel, `/v/<id>/` konkrétní Barometr.
- Každý provoz má vlastní PostgreSQL schéma, tabulky, uživatele, relace, sklady, záznamy, pozvánky, kalibrace a snímky. SQLite při testování používá samostatné soubory.
- Identifikátor provozu se ověřuje v centrální evidenci. SQL schéma se odvozuje pouze z ověřeného serverového UUID.
- Majitel vstupuje přes centrální panel. Jeho relace v provozu navíc vyžaduje platné centrální přihlášení; centrální odhlášení proto zneplatní běžný přístup majitele do provozů.
- Zaměstnanec se registruje pozvánkou na adrese konkrétního provozu. Oprávnění i dostupné sklady se kontrolují serverově. Účty zaměstnanců jsou pro každý provoz samostatné.
- Pracovní terminál zůstává svázaný s jedním provozem a má vlastní relace i PINy.
- Tabulky mají RLS a odebraná veřejná oprávnění. Data se čtou přes Flask backend a jeho ověřené relace; frontend nemá databázové přihlašovací údaje.
- Kopíruje se kód a katalog. Existující produkční účty a provozní data původního Barometru se neimportují automaticky.

Přehled i porovnání ukazují skladové množství po jednotlivých jednotkách (ks, l, kg, balení). Jednotky se nesčítají dohromady. Nezměřené položky nejsou považovány za nulový stav. Manko se uvádí v jednotkách poslední inventury, bez cen a finančních ukazatelů. Historická nákladová pole zůstávají v uložených dokumentech kvůli kompatibilitě, rozhraní je nevyužívá.

## Lokální ověření

```sh
python -m pip install -r requirements.txt pytest
python -m pytest -q
node tests/scanner-math.cjs
node tests/reference-weight.cjs
```

Původní testy používají výhradně dočasný SQLite a `ALLIN_LEGACY_TEST_API=1`. Tento režim není v PostgreSQL dostupný. Nové testy `tests/test_allin.py` vypínají legacy režim a ověřují produkční směrování, oddělení dvou provozů, zaměstnanců, pozvánek, odemčení a terminálů i přístup dalšího majitele.

Prohlížečový test: `python tests/allin-browser.py` (vyžaduje Playwright, Chromium a lokálně spuštěný server s testovacím účtem `owner` / `local-browser-test-password`). Používá jen `127.0.0.1:10000` a vytváří testovací provozy. Pro lokální server nastavte `BAROMETR_TEST_DB=/tmp/allin-local.sqlite3`, `BAROMETR_TEST_HTTP=1`, `ADMIN1_USERNAME=owner`, `ADMIN1_PASSWORD=local-browser-test-password` a spusťte výše uvedený start příkaz s portem 10000.

Nasazení na konkrétní Render a Supabase projekt je třeba ověřit po zadání skutečného připojení. Lokální SQLite testy neověřují síťové připojení ani oprávnění produkční databázové role.

Původní dokumentace a známá omezení měření: [README-BAROMETR.md](README-BAROMETR.md), [dokumentace](dokumentace/). Platby zůstávají vypnuté a automatická AI analýza vyžaduje samostatnou konfiguraci stejně jako v původním Barometru.

## PWA a oznámení

Centrální panel i samostatné provozy mají manifest, ikonu a instalaci na plochu. Na iPhonu otevřete adresu v Safari → Sdílet → Přidat na plochu; pro Web Push je potřeba iOS 16.4+ a spuštění z plochy.

V Nastavení → Oznámení si uživatel vybere uložené inventury/měření, zásoby pod minimem a pohyby zboží. Zapnutí a vypnutí platí pro konkrétní zařízení, účet a provoz. Centrální účet majitele může odebírat události ze všech svých provozů. Zkušební oznámení používá skutečné Web Push doručení. Přihlášení k push neprobíhá automaticky; uživatel musí stisknout tlačítko a povolit prohlížeč.

Server uchovává VAPID klíče v soukromé databázi, do prohlížeče vrací jen veřejný klíč. Skladová změna ukládá událost ve stejné transakci do outboxu. Po úspěšném požadavku ji doručí omezený pracovní thread webové služby; přechodné chyby se zkoušejí znovu při dalších požadavcích (maximálně 3 pokusy během 24 hodin). Příjemci se kontrolují podle vlastníka, aktivního účtu, oprávnění a dostupných skladů. Expirovaná push připojení se odstraňují. Odhlášení odpojí push připojení pro aktuální účet/provoz na tomto zařízení.

Ověření push logiky: `python -m pytest -q tests/test_notifications.py`. Doručení v testech je simulované; příjem na skutečném telefonu ověřuje uživatel tlačítkem Zkušební oznámení po udělení oprávnění.

Ověření mobilního kontrastu: `python tests/noira-login-contrast.py` proti lokálnímu serveru.
