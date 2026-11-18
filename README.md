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

## Jazyky rozhraní

Přihlášení, centrální panel, pracovní prostor i terminál obsahují přepínač češtiny, angličtiny a němčiny. Volba se uchovává v prohlížeči pod `noira.language` a platí i po opětovném otevření. Změna nepřepisuje rozpracované formuláře, skutečné hodnoty `<option>`, názvy provozů a produktů ani měny uložených výsledků. Texty zadané uživatelem a katalogové podklady zůstávají v původním znění. Slovník ovládání a překladová vrstva jsou v `server/web/i18n.js`.

## Denní uzávěrky — pouze majitel

V existujícím Nastavení majitele je konfigurace původu uzávěrek a import CSV podle vzoru NOIRA. Porovnání provozů obsahuje denní historii, datumové a provozní filtry, samostatné měny, chybějící náklady, graf a export vybraného období. Karta provozu ukazuje poslední importovaný den. Hlavní nabídka a její pořadí zůstávají zachovány. Provozní ani zaměstnanecké rozhraní finanční reporty nenačítá; server odmítá všechny finanční endpointy uvnitř provozu i běžnému účtu s oprávněním správy uživatelů. Každý dotaz také ověřuje vlastníka provozovny.

Aktivní je **ruční CSV import**, nikoli automatická synchronizace s dodavateli. Nabídka Dotykačka / Storyous / Septim pouze označuje zdroj dat. Nezobrazuje falešné připojení a neukládá dodavatelské klíče. Pro skutečný konektor potřebuje NOIRA registraci aplikace, přístupy dodavatele a schválení majitele dat; implementace a integrační ověření následují až s těmito přístupy. Viz oficiální dokumentace [Dotykačky](https://docs.api.dotypos.com/getting-started/), [Storyous](https://docs.api.storyous.com/) a [služby Septim](https://www.septim.cz/sluzby-servis/vyvoj-na-miru).

CSV používá UTF-8, středník, čárku nebo tabulátor. Požadované sloupce: `datum`, `trzby_bez_dph`; volitelné: `kasa`, `mena`, `naklady_zbozi`, `provozni_naklady`, `uzaverka_id`. Jeden řádek musí být souhrn jedné pokladny za jeden provozní den, nikoli jednotlivá účtenka nebo směna. Datum je ISO nebo `DD.MM.RRRR`, nejvýše dnešní provozní datum v Europe/Prague. Částky mají nejvýše dvě desetinná místa; prázdné náklady znamenají neznámé hodnoty. Nula je skutečně nulový náklad. Vzor lze stáhnout přímo v nastavení.

Částky se ukládají jako celé setiny měny. Odhad zisku se počítá pouze při známých nákladech zboží i provozu: tržby bez DPH minus obě nákladové položky. Nejde automaticky o účetní čistý zisk. Různé měny se nesčítají a dny bez záznamu neznamenají nulové tržby. Stejný den a identifikátor pokladny aktualizují existující záznam; opakování stejného souboru nepřidá duplicitní výsledky. Každá oprava má zachovaný předchozí snímek, původ a čas. Celý import probíhá v jedné transakci s omezením na 5 000 souhrnů / 2 MB. Denní finanční historie a revize se neořezávají úklidem běžné 90denní aktivity.

Tabulky `pos_connections`, `pos_days`, `pos_revisions`, `pos_imports` jsou v soukromém centrálním schématu; vznikají idempotentně při spuštění stejně jako zbytek tohoto projektu. RLS je zapnuté, přímá oprávnění `PUBLIC`, `anon`, `authenticated` odebraná. Do Supabase Data API se finanční tabulky nezpřístupňují; přístup vede výhradně přes autorizovaný backend.

Ověření: `python -m pytest -q tests/test_pos.py` a `python tests/noira-languages-pos.py` (druhý pouze lokálně, se stejným účtem a serverem jako ostatní browser testy).

## Zaměstnanecké profily

Tlačítko **Vytvořit zaměstnanecký profil** nahrazuje pozvánky v centrální sekci Uživatelé a přístupy a ve správě uživatelů provozu. Majitel zadává jméno, příjmení, přihlašovací jméno, heslo a čtyřmístný PIN; v centrálním panelu navíc vybere provoz. Po vytvoření je účet ihned použitelný jménem/heslem a na spárovaném terminálu PINem. Pořadí hlavní nabídky se nemění. Formulář a potvrzení jsou také v angličtině a němčině.

Server vytváří běžný zaměstnanecký účet s výchozími oprávněními a přístupem ke skladům majitele daného provozu. Majitel pak může rozsah upravit existujícím nastavením oprávnění a skladů. Vytvářet profily smí pouze majitel; oprávnění `users.manage` samo o sobě nepovoluje zakládání přihlašovacích údajů a PINů. Endpointy: `POST /api/owner/venues/<id>/members` v centrálním panelu a `POST /v/<id>/api/admin/users` uvnitř provozu.

Založení účtu, připojení ke skladům, otisk PINu a audit probíhají atomicky. Přihlašovací jméno je jedinečné bez rozlišení velikosti písmen v rámci provozu. PIN je jedinečný v pracovním prostoru včetně PINu majitele; přidělení používá stejný transakční zámek jako dosavadní změny PINu. Heslo (8–128 znaků) i PIN (přesně čtyři ASCII číslice, včetně úvodní nuly) se ukládají pouze jako otisky scrypt. Ve výstupech, seznamu ani auditu nejsou hesla, PINy a jejich otisky. Založení zaměstnance nemění přihlášení majitele ani nevytváří zaměstnanci centrální účet. Historické API pozvánek zůstává pro kompatibilitu, nové rozhraní je nenabízí.

Ověření: `python -m pytest -q tests/test_employees.py` a lokálně `python tests/noira-employee-browser.py`.

## Pozice, oprávnění a zaměstnanecké přihlášení (1.3)

Ve stejné sekci týmu majitel spravuje pozice pro vybraný provoz. Výchozí názvy jsou Zaměstnanec, Kuchař, Číšník a Manager; jejich oprávnění si nastavuje majitel. Nový profil dostane vybranou pozici a může mít individuální výjimky. Uložení změny pozice aktualizuje přiřazené profily, zachová jejich výjimky a při změně práv ukončí přihlášení. Pozice ani účty se mezi provozy nesdílejí. Seznamy týmů a profil zobrazují název pozice.

Soukromý centrální adresář směruje zaměstnanecké přihlášení z hlavní adresy do správného provozu. Existující účty se při startu zaindexují bez změny hesel a PINů. Pokud stejným údajům odpovídá více provozů, zobrazí se výběr pouze po ověření hesla; zaměstnanec tím nezíská centrální účet ani přístup jinam. Adresář a tabulky pozic mají RLS a odebraná veřejná oprávnění stejně jako ostatní soukromá data.

Oprávnění zvlášť pokrývají barové a skladové inventury, historii, katalog, ověřenou databázi, přehledy, příjmy, výdeje a správu. Zakázané funkce se skryjí a zápisy kontroluje server. Na osobním profilu není u inventur další výzva k PINu. Na sdíleném terminálu zůstává PIN identifikací zaměstnance. Nové inventury a pohyby získávají autora a čas ze serveru; zaměstnanci nesmějí přepisovat ani mazat uzavřené záznamy, ani pokud stará data obsahují `inventory.adjust: true`. Opravy historie jsou vyhrazené majiteli. Souběžný zápis nepřepisuje novější inventuru a audit aktivity se již automaticky nemaže po 90 dnech.

Ověření: `python -m pytest -q`, `python tests/noira-employee-browser.py`, `python tests/noira-staff-browser.py` (poslední dva pouze proti lokální testovací aplikaci).

## Inteligentní inventury a schvalování (1.4)

Analytika je v existujícím Porovnání; schvalování v Inventurách → Kontrola inventur. Zaměstnanecká uzávěrka se uloží jako čekající podklad a do skladových zůstatků se promítne až po schválení jinou oprávněnou osobou. Majitel může inventury uzavírat přímo. Oprávnění inventory.review nastavuje majitel pozici nebo profilu, samo o sobě nedává přístup k financím. Vlastní zaměstnaneckou inventuru nelze schválit sobě. Vrácení a opravy mají povinný důvod; předchozí snímky a rozhodnutí zůstávají v auditu. Schválení používá revize proti dvojímu zápisu a ponechává původní čas měření. Opravy uzavřených schválených inventur zůstávají pouze majiteli a vyžadují důvod.

Manko a přebytky se sčítají zvlášť podle jednotek, období, skladů a produktů. Chybějící výchozí stav není nulové manko. Opakované manko vyžaduje nejméně tři výskyty z posledních pěti srovnatelných inventur. Neobvyklá procentní odchylka vyžaduje nejméně pět předchozích měření; používá medián a robustní rozptyl MAD. Upozornění uvádějí podklady a možné kontroly, nikoli prokázanou příčinu.

Majitel má navíc souhrn tržeb, hrubé marže a odhadu zisku po měnách, se srovnáním předchozího stejně dlouhého období. Chybějící náklady nebo uzávěrky jsou označené. Pro spotřebu proti prodejům slouží úplný položkový CSV export jedné pokladny za deklarované období a verzované receptury s datem platnosti. Import celého období nahrazuje předchozí položkové prodeje a archivuje revizi; nezapočítá je dvakrát. Převody ml/l a g/kg jsou podporované, ostatní jednotky se musí shodovat se skladem. Všechny pokladny z denních uzávěrek musí mít potvrzené úplné položkové pokrytí a všechny prodané kódy platnou recepturu. Při chybějících datech se nesoulad neoznačuje za doložený. Tolerance je 5 %; evidované odpisy a převody jsou zohledněné. Dodavatelská API pokladen stále vyžadují jejich přístupy.

Push oznámení o čekající inventuře dostávají pouze přihlášená zařízení majitele a oprávněných schvalovatelů se správným rozsahem skladů a zapnutými oznámeními. Kontrola inventur funguje i bez push. Nové soukromé tabulky mají RLS a odebraná oprávnění veřejných rolí.

Ověření v GitHub Actions: python -m pytest -q, kompilace Pythonu a kontrola syntaxe JavaScriptu. Vývojová větev se nenasazuje do Renderu před dokončením kontrol.

### Spolumajitelé
V panelu majitele → Uživatelé a přístupy → Přidat spolumajitele lze vytvořit další účet s vlastním heslem a volitelným telefonem/e-mailem. Spolumajitel sdílí všechny stávající i budoucí provozy, sklady, inventury, katalog a kalibrace. Události a skladové změny nadále evidují skutečného autora. Každý majitel si mění vlastní heslo.

V centrální tabulce users označuje stock_owner_id u dalších adminů hlavního majitele; nezávislé účty s NULL zůstávají oddělené. Provozy a skladové dokumenty patří hlavnímu majiteli, lokální kopie účtů mají náhodná hesla a nepřebírají centrální přihlašovací heslo. Hlavní majitel může pozastavit nebo obnovit přístup spolumajitele. Pozastavení ruší jeho centrální i provozní relace a přihlášení do terminálu; členství se navíc kontroluje centrálně při každém požadavku i přihlášení PINem. Každý spolumajitel může přidat dalšího spolumajitele do stejné skupiny, ale nemůže blokovat hlavního majitele.

Ověření: `python -m pytest -q tests/test_coowners.py` a `node tests/coowners-browser.cjs` proti izolovanému lokálnímu serveru.
