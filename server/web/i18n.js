'use strict';
// UI copy only. Values, API payloads, product/venue names and CSV column keys are never translated.
window.NoiraI18n=(()=>{
 const supported=['cs','en','de'],locales={cs:'cs-CZ',en:'en-GB',de:'de-DE'},key='noira.language';
 let language='cs';try{const saved=localStorage.getItem(key);if(supported.includes(saved))language=saved}catch{}
 const dictionary=new Map(),lowercase=new Map(),textSources=new WeakMap(),attributeSources=new WeakMap();
 function add(source,en,de){dictionary.set(source,[source,en,de]);lowercase.set(source.toLocaleLowerCase('cs'),[source,en,de])}
 const copy=`
Centrální rozhraní majitele|Central owner interface|Zentraler Inhaberbereich
Zatím nemáte uložené sudy.|No saved kegs yet.|Noch keine gespeicherten Fässer.
Kategorie produktů|Product categories|Produktkategorien
Kategorie|Category|Kategorie
Uložené sudy|Saved kegs|Gespeicherte Fässer
Vyberte uložený sud (volitelné)|Choose a saved keg (optional)|Gespeichertes Fass wählen (optional)
Zatím nemáte uložený sud. Vytvořte vlastní; údaje z vážení se uloží pro příště.|No saved kegs yet. Create your own; weighing data will be saved for reuse.|Noch keine gespeicherten Fässer. Erstellen Sie ein eigenes; Wiegedaten werden zur Wiederverwendung gespeichert.
Lihoviny aktivované pro bar|Spirits activated for the bar|Für die Bar aktivierte Spirituosen
Bez propojení s barem|No link to the bar|Keine Verknüpfung mit der Bar
Velikost lahve|Bottle size|Flaschengröße
Propojená lahev se při inventuře baru zobrazí společně se skladovou zásobou.|The linked bottle will appear alongside warehouse stock in the bar inventory.|Die verknüpfte Flasche wird bei der Barinventur zusammen mit dem Lagerbestand angezeigt.
Jednotky produktu|Product units|Produkteinheiten
Ks – kusy|Pcs – pieces|Stk – Stück
L – litr|L – litre|L – Liter
Ml – mililitr|Ml – millilitre|Ml – Milliliter
Kg – kilogramy|Kg – kilograms|Kg – Kilogramm
B – balení|B – packs|B – Packungen
Minimální množství ve skladu (volitelné)|Minimum stock quantity (optional)|Mindestlagerbestand (optional)
Bez upozornění|No alert|Keine Warnung
Prvotní stav při vytvoření a zaskladnění|Opening stock on product creation|Anfangsbestand bei Produkterstellung
Můžete ponechat 0 a zboží přijmout později.|You can leave 0 and receive stock later.|Sie können 0 belassen und die Ware später einlagern.
Parametry pro vážení|Weighing parameters|Wiegeparameter
Celková hmotnost plného obalu (kg)|Total weight of full container (kg)|Gesamtgewicht des vollen Behälters (kg)
Hmotnost jedné jednotky (kg)|Weight per unit (kg)|Gewicht je Einheit (kg)
Další údaje produktu|Additional product details|Weitere Produktangaben
Vyberte hmotnost sudu|Select keg reference weight|Referenzgewicht des Fasses wählen
Plný sud|Full keg|Volles Fass
Prázdný sud|Empty keg|Leeres Fass
Zatím nezváženo|Not weighed yet|Noch nicht gewogen
Výběr hmotnosti nemění prvotní zásobu.|Selecting a weight does not change opening stock.|Die Gewichtsauswahl ändert den Anfangsbestand nicht.
Přidat kategorii|Add category|Kategorie hinzufügen
Název kategorie|Category name|Kategoriename
Odstranit kategorii|Remove category|Kategorie entfernen
Uložit kategorie|Save categories|Kategorien speichern
Obal / jiné kusové zboží|Packaging / other piece goods|Verpackung / sonstige Stückware
Kategorie můžete přejmenovat, přidat nebo odstranit. Existující produkty ani historie se odstraněním kategorie nesmažou.|You can rename, add or remove categories. Removing a category preserves existing products and history.|Sie können Kategorien umbenennen, hinzufügen oder entfernen. Bestehende Produkte und der Verlauf bleiben beim Entfernen einer Kategorie erhalten.
Na baru i ve skladu, rozdělené podle nápoje a velikosti lahve.|Bar and warehouse stock, grouped by drink and bottle size.|Bar- und Lagerbestand, nach Getränk und Flaschengröße gruppiert.
Načítání přehledu…|Loading summary…|Übersicht wird geladen…
Znovu načíst přehled|Reload summary|Übersicht neu laden
Lahve celkem|Total bottles|Flaschen insgesamt
lahví celkem|bottles in total|Flaschen insgesamt
Plných|Full|Voll
Načatých / poloprázdných|Opened / partially full|Angebrochen / teilweise gefüllt
Prázdných k archivaci|Empty for archiving|Leere zur Archivierung
Vypité od minulé inventury|Emptied since last inventory|Seit der letzten Inventur geleert
Vypité lahve se evidují při změně obsahu z kladného množství na 0 ml. Nejde o počet účtenek z pokladny.|Emptied bottles are recorded when their contents change from a positive amount to 0 ml. This is not the number of POS receipts.|Geleerte Flaschen werden erfasst, wenn ihr Inhalt von einer positiven Menge auf 0 ml sinkt. Dies ist nicht die Anzahl der Kassenbelege.
Na baru|At the bar|An der Bar
Ve skladu|In the warehouse|Im Lager
Bez ověřeného stavu|No verified stock level|Kein bestätigter Bestand
Není propojená skladová položka|No linked warehouse item|Kein verknüpfter Lagerartikel
Celkový obsah|Total contents|Gesamtinhalt
Nelze určit úplný obsah|Total contents cannot be determined|Gesamtinhalt nicht bestimmbar
Úplný počet lahví lze určit u skladové zásoby vedené v kusech nebo baleních.|The total bottle count can be determined for warehouse stock tracked in pieces or packs.|Die Gesamtzahl der Flaschen kann für Lagerbestände in Stück oder Packungen ermittelt werden.
Prodané / vypité lahve od minulé inventury|Sold / emptied bottles since last inventory|Seit der letzten Inventur verkaufte / geleerte Flaschen
NÁPOJ|DRINK|GETRÄNK
VELIKOST LAHVE|BOTTLE SIZE|FLASCHENGRÖSSE
POČET VYPITÝCH LAHVÍ|EMPTIED BOTTLES|GELEERTE FLASCHEN
Upravit přehled|Edit summary|Übersicht bearbeiten
Zavřít úpravy|Close editing|Bearbeitung schließen
Upravit před uložením|Edit before saving|Vor dem Speichern bearbeiten
Obsah této lahve v ml|Contents of this bottle in ml|Inhalt dieser Flasche in ml
Důvod úpravy měření|Reason for measurement correction|Grund der Messkorrektur
Přepočítat a zkontrolovat přehled|Recalculate and review summary|Neu berechnen und Übersicht prüfen
Sudy a další naměřené položky|Kegs and other measured items|Fässer und weitere gemessene Artikel
Potvrzením uložíte přehled. Všechny lahve s 0 ml se archivují společně s inventurou a zmizí z aktivního provozu.|Confirm to save the summary. All 0 ml bottles will be archived with the inventory and removed from active use.|Bestätigen Sie zum Speichern der Übersicht. Alle Flaschen mit 0 ml werden mit der Inventur archiviert und aus dem aktiven Betrieb entfernt.
Potvrdit a uložit inventuru|Confirm and save inventory|Inventur bestätigen und speichern
Potvrdit a odeslat ke schválení|Confirm and submit for approval|Bestätigen und zur Freigabe senden
Uložený přehled lahví|Saved bottle summary|Gespeicherte Flaschenübersicht
Archivované prázdné lahve|Archived empty bottles|Archivierte leere Flaschen
NAČATÝCH|OPENED|ANGEBROCHEN
PRÁZDNÝCH|EMPTY|LEER
Zvážený sud|Weighed keg|Gewogenes Fass
Běžné měření obsahu|Regular contents measurement|Normale Inhaltsmessung
Měřím plný sud|Weighing a full keg|Volles Fass wiegen
Měřím prázdný sud|Weighing an empty keg|Leeres Fass wiegen
Provoz je archivovaný|Venue archived|Betrieb archiviert
Přístup je vypnutý. Data a historie zůstávají zachovány. Pro obnovení se obraťte na majitele.|Access is disabled. Data and history are preserved. Contact the owner to restore access.|Der Zugriff ist deaktiviert. Daten und Verlauf bleiben erhalten. Wenden Sie sich zur Wiederherstellung an den Inhaber.
Přejít do panelu majitele|Go to owner panel|Zum Inhaberbereich
Archiv provozů|Venue archive|Betriebsarchiv
Archiv je prázdný.|The archive is empty.|Das Archiv ist leer.
Vypnuté provozy se zachovanými daty a historií.|Disabled venues with their data and history preserved.|Deaktivierte Betriebe mit erhaltenen Daten und Verlauf.
Nabídka provozu|Venue menu|Betriebsmenü
Přidat manažera|Add manager|Manager hinzufügen
Změnit manažera|Change manager|Manager ändern
Spravovat otevírací dobu|Manage opening hours|Öffnungszeiten verwalten
Upravit kartu|Customize card|Karte anpassen
Vypnout a archivovat provoz|Disable and archive venue|Betrieb deaktivieren und archivieren
Vymazat provoz|Delete venue|Betrieb löschen
Obnovit provoz|Restore venue|Betrieb wiederherstellen
Archivovaný provoz · přístup vypnutý|Archived venue · access disabled|Archivierter Betrieb · Zugriff deaktiviert
Data a historie zachovány|Data and history preserved|Daten und Verlauf erhalten
Přístup všech účtů i pracovních terminálů se vypne. Sklady, inventury a historie zůstanou zachovány. Provoz můžete později obnovit.|Access for all accounts and work terminals will be disabled. Stock, inventories and history will be preserved. You can restore the venue later.|Der Zugriff aller Konten und Arbeitsterminals wird deaktiviert. Lager, Inventuren und Verlauf bleiben erhalten. Sie können den Betrieb später wiederherstellen.
Provoz se vrátí mezi aktivní. Uživatelé se budou muset znovu přihlásit a pracovní terminály znovu aktivovat.|The venue will become active again. Users must sign in again and work terminals must be reactivated.|Der Betrieb wird wieder aktiv. Benutzer müssen sich erneut anmelden und Arbeitsterminals müssen erneut aktiviert werden.
Trvale se odstraní provoz, jeho zaměstnanecké profily, sklady, inventury, snímky, prodejní data a historie. Tento krok nelze vrátit. Účty majitelů a ostatní provozy zůstanou zachovány.|The venue, its employee profiles, stock, inventories, photos, sales data and history will be permanently deleted. This cannot be undone. Owner accounts and other venues will be preserved.|Der Betrieb, seine Mitarbeiterprofile, Lager, Inventuren, Fotos, Verkaufsdaten und der Verlauf werden endgültig gelöscht. Dies kann nicht rückgängig gemacht werden. Inhaberkonten und andere Betriebe bleiben erhalten.
Pro potvrzení napište přesný název provozu|Enter the exact venue name to confirm|Geben Sie zur Bestätigung den genauen Betriebsnamen ein
Styl karty|Card style|Kartenstil
Písmo|Font|Schriftart
Velikost názvu|Title size|Titelgröße
Velikost ostatního textu|Body text size|Textgröße
Barva karty|Card color|Kartenfarbe
Barva písma|Text color|Textfarbe
Barva doplňkového textu|Secondary text color|Farbe des Zusatztextes
Barva zvýraznění|Accent color|Akzentfarbe
Zaoblení rohů|Corner radius|Eckenradius
Tučné písmo|Bold text|Fettschrift
Kurzíva|Italic|Kursiv
Stín karty|Card shadow|Kartenschatten
Výchozí vzhled|Default appearance|Standarddarstellung
Uložit vzhled karty|Save card appearance|Kartendarstellung speichern
Vyberte libovolnou barvu z barevného spektra nebo zadejte HEX. Změny ihned uvidíte v náhledu.|Choose any color from the spectrum or enter a HEX code. Changes appear immediately in the preview.|Wählen Sie eine beliebige Farbe aus dem Spektrum oder geben Sie einen HEX-Code ein. Änderungen erscheinen sofort in der Vorschau.
Střídmá elegance|Understated elegance|Schlichte Eleganz
Čistý přehled|Clean overview|Klare Übersicht
Boční linka|Side stripe|Seitenlinie
Barevné záhlaví|Colored header|Farbige Kopfzeile
Redakční styl|Editorial|Redaktioneller Stil
Kompaktní|Compact|Kompakt
Jemný přechod|Subtle gradient|Sanfter Verlauf
Otevřený prostor|Open space|Offener Raum
Provozní přehled|Operations overview|Betriebsübersicht
Tři sloupce|Three columns|Drei Spalten
Obrys|Outline|Kontur
Architektonická|Architectural|Architektonisch
Moderní bezpatkové|Modern sans serif|Moderne serifenlose Schrift
Elegantní patkové|Elegant serif|Elegante Serifenschrift
Klasické bezpatkové|Classic sans serif|Klassische serifenlose Schrift
Výrazně čitelné|Highly readable|Besonders gut lesbar
Kompaktní čitelné|Compact readable|Kompakt und lesbar
Technické|Monospace|Nichtproportional
Zohlednit čas u významných odchylek|Include time context for significant discrepancies|Zeit bei erheblichen Abweichungen berücksichtigen
Počet opakovaných odchylek|Number of repeated discrepancies|Anzahl wiederholter Abweichungen
Majitelé a spolumajitelé|Owners and co-owners|Inhaber und Mitinhaber
Společný přístup ke všem stávajícím i budoucím provozům. Každý má vlastní přihlášení a dohledatelné změny.|Shared access to all current and future venues. Everyone has their own login and attributable changes.|Gemeinsamer Zugriff auf alle bestehenden und künftigen Betriebe. Jeder hat eigene Zugangsdaten und nachvollziehbare Änderungen.
Spolumajitelé spravují společné provozy. Zaměstnancům nastavíte přístup pro konkrétní provoz.|Co-owners manage shared venues. Employees receive access to a specific venue.|Mitinhaber verwalten gemeinsame Betriebe. Mitarbeiter erhalten Zugriff auf einen bestimmten Betrieb.
＋ Přidat spolumajitele|＋ Add co-owner|＋ Mitinhaber hinzufügen
Přidat spolumajitele|Add co-owner|Mitinhaber hinzufügen
Hlavní majitel|Primary owner|Hauptinhaber
Spolumajitel|Co-owner|Mitinhaber
Vy|You|Sie
Všechny společné provozy|All shared venues|Alle gemeinsamen Betriebe
Pozastavit přístup|Suspend access|Zugriff sperren
Obnovit přístup|Restore access|Zugriff wiederherstellen
Pozastavit přístup spolumajitele?|Suspend co-owner access?|Zugriff des Mitinhabers sperren?
Obnovit přístup spolumajitele?|Restore co-owner access?|Zugriff des Mitinhabers wiederherstellen?
Získá plný přístup ke všem vašim provozům, skladům, inventurám i správě zaměstnanců. Může vytvářet další spolumajitele.|They will have full access to all your venues, stock, inventories and employee management. They can create further co-owners.|Die Person erhält vollen Zugriff auf alle Ihre Betriebe, Lager, Inventuren und die Mitarbeiterverwaltung. Sie kann weitere Mitinhaber anlegen.
Počáteční heslo|Initial password|Erstes Passwort
Telefon (volitelné)|Phone (optional)|Telefon (optional)
E-mail (volitelné)|Email (optional)|E-Mail (optional)
Přihlašovací údaje předejte osobně. Spolumajitel si může změnit vlastní heslo v nastavení účtu.|Share the login details in person. The co-owner can change their own password in account settings.|Übergeben Sie die Zugangsdaten persönlich. Der Mitinhaber kann sein Passwort in den Kontoeinstellungen ändern.
Vytvořit účet spolumajitele|Create co-owner account|Mitinhaberkonto erstellen
Ztratí přístup ke všem společným provozům i pracovnímu terminálu. Historie jeho změn zůstane zachována.|They will lose access to all shared venues and the work terminal. Their change history will be preserved.|Die Person verliert den Zugriff auf alle gemeinsamen Betriebe und das Arbeitsterminal. Ihr Änderungsverlauf bleibt erhalten.
Účet se bude moci znovu přihlásit ke společným provozům.|The account will be able to sign in to shared venues again.|Das Konto kann sich wieder bei den gemeinsamen Betrieben anmelden.
← Zpět do panelu majitele|← Back to owner panel|← Zurück zum Inhaberbereich
Zpět do panelu majitele|Back to owner panel|Zurück zum Inhaberbereich
← Majitel|← Owner|← Inhaber
Nutné doplnit skladové zásoby!|Stock replenishment required!|Lagerbestände müssen aufgefüllt werden!
Tyto produkty dosáhly nastaveného minima nebo klesly pod něj.|These products reached or fell below the configured minimum.|Diese Produkte haben den Mindestbestand erreicht oder unterschritten.
Minimální zásoba (volitelné)|Minimum stock (optional)|Mindestbestand (optional)
Bez upozornění|No alert|Keine Warnung
Otevírací doba a upozornění|Opening hours and alerts|Öffnungszeiten und Hinweise
Odepisovat zboží|Write off stock|Waren abschreiben
Vydávat a přesouvat zboží|Issue and transfer stock|Waren ausgeben und umlagern
Odpis zboží|Stock write-off|Warenabschreibung
Zapsat odpis|Save write-off|Abschreibung speichern
Neobvyklé pohyby a inventury|Unusual movements and inventories|Ungewöhnliche Bewegungen und Inventuren
K prověření|Needs review|Zu prüfen
Vysvětlené|Explained|Erklärt
Označit jako vysvětlené|Mark as explained|Als erklärt markieren
Znovu otevřít|Reopen|Erneut öffnen
Používat otevírací dobu|Use opening hours|Öffnungszeiten verwenden
Otevřít produkt|Open product|Produkt öffnen
Uložit nastavení provozu|Save venue settings|Betriebseinstellungen speichern
Limity upozornění|Alert thresholds|Warnschwellen
Pondělí|Monday|Montag
Úterý|Tuesday|Dienstag
Středa|Wednesday|Mittwoch
Čtvrtek|Thursday|Donnerstag
Pátek|Friday|Freitag
Sobota|Saturday|Samstag
Neděle|Sunday|Sonntag
Zavřeno|Closed|Geschlossen
Přidat telefon zaměstnance|Add employee phone|Mitarbeitertelefon hinzufügen
Přidat e-mail zaměstnance|Add employee email|Mitarbeiter-E-Mail hinzufügen
Změny byly uloženy.|Changes saved.|Änderungen gespeichert.
Načítání|Loading|Wird geladen
Ukládám…|Saving…|Wird gespeichert…
Inteligentní provozní analytika|Operational intelligence|Intelligente Betriebsanalyse
Chytřejší vyhodnocení inventur|Smarter inventory analysis|Intelligente Inventurauswertung
Kontrola inventur a schvalování|Inventory review and approval|Inventurprüfung und Freigabe
Kontrola inventur|Inventory review|Inventurprüfung
Čekající inventury, schvalování a opravy s důvodem.|Pending inventories, approval and corrections with reasons.|Ausstehende Inventuren, Freigaben und begründete Korrekturen.
1. Vývoj manka|1. Shortage trends|1. Fehlbestandsentwicklung
2. Neobvyklé a opakované odchylky|2. Unusual and recurring discrepancies|2. Ungewöhnliche und wiederkehrende Abweichungen
3. Spotřeba proti prodejům|3. Consumption versus sales|3. Verbrauch und Verkäufe
4. Tržby a marže provozů|4. Venue revenue and margins|4. Umsätze und Margen der Betriebe
5. Inventury ke kontrole|5. Inventories awaiting review|5. Inventuren zur Prüfung
6. Kontrola a rozhodnutí|6. Review and decision|6. Prüfung und Entscheidung
Čeká na schválení|Awaiting approval|Wartet auf Freigabe
Vrácená k opravě|Returned for correction|Zur Korrektur zurückgegeben
Vrácené k opravě|Returned for correction|Zur Korrektur zurückgegeben
Schválená|Approved|Freigegeben
Schválené|Approved|Freigegeben
Zkontrolovat inventuru|Review inventory|Inventur prüfen
Schválit uzavření|Approve closure|Abschluss freigeben
Vrátit k opravě|Return for correction|Zur Korrektur zurückgeben
Poznámka / důvod vrácení|Note / reason for return|Hinweis / Rückgabegrund
Oprava vrácené inventury|Correct returned inventory|Zurückgegebene Inventur korrigieren
Oprava schválené inventury majitelem|Owner correction of approved inventory|Korrektur einer freigegebenen Inventur durch den Inhaber
Odeslat znovu ke schválení|Resubmit for approval|Erneut zur Freigabe einreichen
Uložit opravu s auditní stopou|Save correction with audit trail|Korrektur mit Prüfprotokoll speichern
Důvod opravy|Reason for correction|Korrekturgrund
Historie rozhodnutí a oprav|Decision and correction history|Entscheidungs- und Korrekturverlauf
Odesláno|Submitted|Eingereicht
Opraveno a znovu odesláno|Corrected and resubmitted|Korrigiert und erneut eingereicht
Schváleno|Approved|Freigegeben
Vráceno|Returned|Zurückgegeben
Oprava schválené inventury|Correction of approved inventory|Korrektur einer freigegebenen Inventur
Odeslat inventuru ke schválení|Submit inventory for approval|Inventur zur Freigabe einreichen
Odeslat ke schválení|Submit for approval|Zur Freigabe einreichen
Inventura byla odeslána ke schválení.|Inventory submitted for approval.|Inventur zur Freigabe eingereicht.
Inventura čeká na schválení manažerem.|Inventory awaits manager approval.|Inventur wartet auf Freigabe durch den Manager.
Kontrolovat a schvalovat inventury ostatních|Review and approve others' inventories|Inventuren anderer prüfen und freigeben
Zobrazit analýzu|Show analysis|Analyse anzeigen
Všechny produkty|All products|Alle Produkte
Období|Period|Zeitraum
Manko|Shortage|Fehlbestand
Přebytek|Surplus|Mehrbestand
Bez výchozího stavu|No baseline|Kein Ausgangsbestand
Provoz / produkt|Venue / product|Betrieb / Produkt
Období měření|Measurement period|Messzeitraum
Skutečná spotřeba|Actual consumption|Tatsächlicher Verbrauch
Podle prodejů|Based on sales|Laut Verkäufen
Úplnost dat|Data coverage|Datenvollständigkeit
Chybí předchozí fyzická inventura|Previous physical inventory missing|Vorherige körperliche Inventur fehlt
Chybí úplné prodeje nebo uzávěrky|Complete sales or closing summaries missing|Vollständige Verkäufe oder Tagesabschlüsse fehlen
Chybí receptura|Recipe missing|Rezeptur fehlt
Změnila se surovina nebo jednotka|Ingredient or unit changed|Zutat oder Einheit wurde geändert
Úplná data|Complete data|Vollständige Daten
Tržby bez DPH|Revenue excluding VAT|Umsatz ohne Mehrwertsteuer
Hrubá marže|Gross margin|Bruttomarge
Změna proti předchozímu období|Change from previous period|Änderung gegenüber dem Vorzeitraum
Odhad zisku|Estimated profit|Geschätzter Gewinn
Dny bez uzávěrky|Days without closing summary|Tage ohne Tagesabschluss
Chybí náklady|Costs missing|Kosten fehlen
Položkové prodeje a receptury|Item sales and recipes|Artikelverkäufe und Rezepturen
Stáhnout vzor CSV|Download CSV template|CSV-Vorlage herunterladen
Připravte úplný export jedné pokladny za vybrané dny. Import nahradí položkové prodeje této pokladny v zadaném období a zachová revizi předchozích dat.|Prepare a complete export for one register and the selected days. Import replaces that register's item sales in the period and preserves a revision of previous data.|Erstellen Sie einen vollständigen Export einer Kasse für die gewählten Tage. Der Import ersetzt die Artikelverkäufe dieser Kasse im Zeitraum und bewahrt eine Version der bisherigen Daten.
Export obsahuje všechny položkové prodeje včetně storen za celou vybranou pokladnu a období.|The export includes all item sales and voids for the entire selected register and period.|Der Export enthält sämtliche Artikelverkäufe und Stornierungen der ausgewählten Kasse im gesamten Zeitraum.
Importovat položkové prodeje|Import item sales|Artikelverkäufe importieren
Import je uložený.|Import saved.|Import gespeichert.
Receptury|Recipes|Rezepturen
Jeden kód produktu pokladny může spotřebovat více skladových surovin. Nová verze má datum platnosti a důvod.|One POS product code can consume several stock ingredients. Each new version has an effective date and reason.|Ein Kassenproduktcode kann mehrere Lagerzutaten verbrauchen. Jede neue Version hat ein Gültigkeitsdatum und eine Begründung.
Kód produktu pokladny|POS product code|Kassenproduktcode
Kód pokladny|POS code|Kassencode
Platí od|Effective from|Gültig ab
Suroviny|Ingredients|Zutaten
Surovina|Ingredient|Zutat
Množství na jeden prodej|Quantity per sale|Menge pro Verkauf
Přidat surovinu|Add ingredient|Zutat hinzufügen
＋ Přidat surovinu|＋ Add ingredient|＋ Zutat hinzufügen
Odebrat surovinu|Remove ingredient|Zutat entfernen
Důvod|Reason|Begründung
Uložit verzi receptury|Save recipe version|Rezepturversion speichern
Receptura je uložená.|Recipe saved.|Rezeptur gespeichert.
Žádné inventury v tomto stavu.|No inventories with this status.|Keine Inventuren mit diesem Status.
Pro vybrané období nejsou data.|No data for the selected period.|Keine Daten für den gewählten Zeitraum.
Tento provoz|This venue|Dieser Betrieb
Spotřeba = počáteční fyzický stav + příjmy a převody − konečný stav − evidované odpisy. S prodeji ji srovnáváme podle receptur platných v okamžiku prodeje. Upozornění používá toleranci 5 %.|Consumption = opening physical stock + receipts and transfers − closing stock − recorded waste. Sales are compared using recipes effective at the time of sale. Alerts use a 5% tolerance.|Verbrauch = körperlicher Anfangsbestand + Zugänge und Umlagerungen − Endbestand − erfasster Schwund. Der Verkaufsabgleich nutzt zum Verkaufszeitpunkt gültige Rezepturen. Hinweise verwenden eine Toleranz von 5 %.
Pouze pro majitele. Částky pocházejí z importovaných uzávěrek; různé měny se nesčítají. Marže vyžaduje náklady zboží, odhad zisku také provozní náklady.|Owner only. Amounts come from imported closing summaries; different currencies are not added together. Margin requires cost of goods; estimated profit also requires operating costs.|Nur für Inhaber. Beträge stammen aus importierten Tagesabschlüssen; verschiedene Währungen werden nicht addiert. Die Marge erfordert Wareneinsatz, der geschätzte Gewinn zusätzlich Betriebskosten.
Ve vybraných datech nebyla nalezena odchylka splňující pravidla. Pro statistické vyhodnocení je potřeba alespoň pět předchozích srovnatelných inventur.|No discrepancy meeting the rules was found. Statistical analysis requires at least five previous comparable inventories.|Es wurde keine Abweichung gefunden, die den Regeln entspricht. Für die statistische Auswertung sind mindestens fünf vorherige vergleichbare Inventuren erforderlich.
Odpovědný manažer (volitelné)|Responsible manager (optional)|Verantwortlicher Manager (optional)
Odpovědný manažer|Responsible manager|Verantwortlicher Manager
Jméno manažera|Manager first name|Vorname des Managers
Příjmení manažera|Manager last name|Nachname des Managers
Přiřadit manažera|Assign manager|Manager zuweisen
Upravit manažera|Edit manager|Manager bearbeiten
Uložit manažera|Save manager|Manager speichern
Nepřiřazen|Unassigned|Nicht zugewiesen
Pro odebrání manažera ponechte obě pole prázdná.|Leave both fields empty to remove the manager.|Lassen Sie beide Felder leer, um den Manager zu entfernen.
Vyplňte jméno i příjmení manažera, nebo ponechte obě pole prázdná.|Enter both manager names or leave both fields empty.|Geben Sie Vor- und Nachnamen des Managers ein oder lassen Sie beide Felder leer.
Kontakt zaměstnance|Employee contact|Mitarbeiterkontakt
Telefon zaměstnance (volitelné)|Employee phone (optional)|Telefon des Mitarbeiters (optional)
E-mail zaměstnance (volitelné)|Employee email (optional)|E-Mail des Mitarbeiters (optional)
Telefon zaměstnance|Employee phone|Telefon des Mitarbeiters
E-mail zaměstnance|Employee email|E-Mail des Mitarbeiters
Vytvoření profilu|Profile created|Profil erstellt
Kontakt|Contact|Kontakt
Zadejte platné telefonní číslo.|Enter a valid phone number.|Geben Sie eine gültige Telefonnummer ein.
Zadejte platný e-mail zaměstnance.|Enter a valid employee email.|Geben Sie eine gültige E-Mail-Adresse des Mitarbeiters ein.
Pozice|Position|Position
Oprávnění zaměstnance|Employee permissions|Mitarbeiterberechtigungen
Pozice a přednastavená oprávnění|Positions and permission presets|Positionen und Berechtigungsvorlagen
Připravte pozice pro zaměstnance jednotlivých provozů.|Set up employee positions for each venue.|Richten Sie Mitarbeiterpositionen für jeden Betrieb ein.
Pozice přednastaví oprávnění. Jednotlivé výjimky můžete upravit pro tohoto zaměstnance.|The position sets default permissions. You can change individual exceptions for this employee.|Die Position legt Standardberechtigungen fest. Individuelle Ausnahmen können Sie für diesen Mitarbeiter ändern.
Historii může upravovat nebo mazat pouze majitel.|Only the owner can edit or delete history.|Nur der Inhaber kann den Verlauf bearbeiten oder löschen.
Upravit pozici|Edit position|Position bearbeiten
Nová pozice|New position|Neue Position
＋ Nová pozice|＋ New position|＋ Neue Position
Název pozice|Position name|Positionsname
Uložit pozici|Save position|Position speichern
Změny oprávnění pozice se promítnou zaměstnancům. Jejich individuální výjimky zůstávají zachované.|Position permission changes apply to assigned employees. Their individual exceptions are preserved.|Änderungen der Positionsberechtigungen gelten für zugewiesene Mitarbeiter. Ihre individuellen Ausnahmen bleiben erhalten.
Inventury baru a měření lahví|Bar inventories and bottle measurements|Barinventuren und Flaschenmessungen
Inventury skladů a vážení zboží|Warehouse inventories and weighing goods|Lagerinventuren und Warenwiegen
Prohlížet historii inventur|View inventory history|Inventurverlauf anzeigen
Prohlížet katalog a knihovnu lahví|View bottle catalog and library|Flaschenkatalog und Bibliothek anzeigen
Prohlížet ověřenou databázi produktů|View verified product database|Geprüfte Produktdatenbank anzeigen
Prohlížet porovnání a přehledy|View comparisons and reports|Vergleiche und Berichte anzeigen
Vyberte svůj provoz.|Select your venue.|Wählen Sie Ihren Betrieb.
Jazyk|Language|Sprache
Přihlášení|Sign in|Anmeldung
Registrace|Register|Registrierung
Váš bar. Váš přehled.|Your bar. Your overview.|Ihre Bar. Ihr Überblick.
Vítejte u nás.|Welcome.|Willkommen.
Přihlaste se do svého účtu a pokračujte v práci.|Sign in to your account and continue working.|Melden Sie sich an, um weiterzuarbeiten.
Vytvořte si účet pomocí pozvánky od administrátora.|Create an account using an invitation from your administrator.|Erstellen Sie ein Konto mit einer Einladung Ihres Administrators.
Uživatelské jméno|Username|Benutzername
Heslo|Password|Passwort
Přihlásit se|Sign in|Anmelden
Zaregistrovat se|Create account|Registrieren
Nemáte účet? Požádejte administrátora o registrační kód.|Need an account? Ask your administrator for an invitation code.|Noch kein Konto? Fragen Sie Ihren Administrator nach einem Einladungscode.
Křestní jméno|First name|Vorname
Příjmení|Last name|Nachname
Invite kód|Invitation code|Einladungscode
Přístup k funkcím určuje správce provozu.|Your venue administrator manages access to features.|Der Betriebsadministrator verwaltet den Zugriff auf Funktionen.
Heslo nejméně 8 znaků. Správci vidí přihlášení, poslední aktivitu a akce provedené v aplikaci. Historie aktivit se uchovává nejvýše 90 dní.|Password: at least 8 characters. Administrators can see sign-ins, last activity and actions in the app. Activity records are kept for up to 90 days.|Passwort: mindestens 8 Zeichen. Administratoren sehen Anmeldungen, letzte Aktivitäten und Aktionen in der App. Das Aktivitätsprotokoll wird höchstens 90 Tage gespeichert.
Připojujeme se…|Connecting…|Verbindung wird hergestellt…
Server zatím není dostupný. Zkuste obnovit stránku za chvíli.|The server is unavailable. Try refreshing shortly.|Der Server ist derzeit nicht erreichbar. Laden Sie die Seite in Kürze neu.
Obnovit|Refresh|Aktualisieren
Požadavek se nepodařil.|The request failed.|Die Anfrage ist fehlgeschlagen.
Nesprávné uživatelské jméno nebo heslo.|Incorrect username or password.|Benutzername oder Passwort ist falsch.
Odhlásit|Sign out|Abmelden
Změnit heslo|Change password|Passwort ändern
Změnit heslo majitele|Change owner password|Inhaberpasswort ändern
Současné heslo|Current password|Aktuelles Passwort
Nové heslo|New password|Neues Passwort
Uložit nové heslo|Save new password|Neues Passwort speichern
Heslo bylo změněno|Password changed|Passwort geändert
Ostatní přihlášení byla ukončena.|Other sessions have been signed out.|Andere Sitzungen wurden abgemeldet.
Zavřít|Close|Schließen
Uložit|Save|Speichern
Zrušit|Cancel|Abbrechen
Zpět|Back|Zurück
Detail|Details|Details
Upravit|Edit|Bearbeiten
Odstranit|Delete|Löschen
Potvrdit|Confirm|Bestätigen
Vyhledat|Search|Suchen
Hledat|Search|Suchen
Vše|All|Alle
Všechny|All|Alle
Všichni|Everyone|Alle
Aktivní|Active|Aktiv
Pozastavený|Suspended|Gesperrt
Zablokovaný|Blocked|Gesperrt
Zablokovaní|Blocked|Gesperrt
Zatím nikdy|Never|Bisher nie
Zatím bez aktivity|No activity yet|Noch keine Aktivität
Novější|Newer|Neuere
Starší|Older|Ältere
Načítání…|Loading…|Wird geladen…
PANEL MAJITELE|OWNER DASHBOARD|INHABERÜBERSICHT
NOIRA / PANEL MAJITELE|NOIRA / OWNER DASHBOARD|NOIRA / INHABERÜBERSICHT
CENTRÁLNÍ APLIKACE|CENTRAL APP|ZENTRALE APP
Centrální panel majitele|Owner dashboard|Inhaberübersicht
Souhrnný přehled|Overview|Gesamtübersicht
Moje provozy|My venues|Meine Betriebe
Uživatelé a přístupy|Users and access|Benutzer und Zugriffsrechte
Vytvoření nového provozu|Create a venue|Betrieb erstellen
Porovnání provozů|Venue comparison|Betriebsvergleich
Aktivita napříč provozy|Activity across venues|Aktivitäten aller Betriebe
Nastavení majitele a účtu|Owner and account settings|Inhaber- und Kontoeinstellungen
Vaše podniky pod kontrolou|Your venues under control|Ihre Betriebe im Blick
Každý provoz. Vlastní prostor.|Each venue. Its own space.|Jeder Betrieb. Ein eigener Bereich.
Jeden přehled pro všechny vaše podniky.|One overview for all your venues.|Ein Überblick für alle Ihre Betriebe.
Vaše provozy.|Your venues.|Ihre Betriebe.
Váš klid.|Your peace of mind.|Alles im Griff.
Vaše provozy|Your venues|Ihre Betriebe
Nový provoz|New venue|Neuer Betrieb
Vytvořit provoz|Create venue|Betrieb erstellen
Vytvořit první provoz|Create your first venue|Ersten Betrieb erstellen
Váš první provoz začíná tady.|Your first venue starts here.|Hier beginnt Ihr erster Betrieb.
Vytvořte samostatný NOIRA pro svůj podnik. Jeho sklady, inventury, lahve i zaměstnanci budou mít vlastní prostor.|Create a separate NOIRA for your venue, with its own warehouses, inventories, bottles and team.|Erstellen Sie eine eigene NOIRA für Ihren Betrieb mit separaten Lagern, Inventuren, Flaschen und Mitarbeitern.
Zásoby|Stock|Bestände
Sklady|Warehouses|Lager
Inventury|Inventories|Inventuren
Zaměstnanci|Employees|Mitarbeiter
Pod minimem|Below minimum|Unter Mindestbestand
Změřené skladové množství|Measured stock quantity|Erfasste Bestandsmenge
Vlastní zásoby a týmy|Separate stock and teams|Eigene Bestände und Teams
Skladových položek k doplnění|Stock items to replenish|Aufzufüllende Lagerpositionen
Porovnat zásoby|Compare stock|Bestände vergleichen
Zatím nezměřeno|Not measured yet|Noch nicht erfasst
Nezměřeno|Not measured|Nicht erfasst
Zatím nezměřené zásoby|Stock not measured yet|Bestände noch nicht erfasst
Samostatný provoz|Independent venue|Eigenständiger Betrieb
Vlastní skladový prostor|Separate stock area|Eigener Lagerbereich
Otevřít provoz|Open venue|Betrieb öffnen
Každý podnik má vlastní NOIRA. Vy máte přístup ke všem.|Each venue has its own NOIRA. You can access them all.|Jeder Betrieb hat seine eigene NOIRA. Sie haben Zugriff auf alle.
Nový provoz. Vlastní NOIRA.|New venue. Its own NOIRA.|Neuer Betrieb. Eigene NOIRA.
Pojmenujte podnik a připravíme pro něj samostatný prostor.|Name your venue and we will create its own space.|Benennen Sie den Betrieb. Wir erstellen einen eigenen Bereich dafür.
Název provozu|Venue name|Betriebsname
Adresa nebo označení pobočky|Address or branch label|Adresse oder Filialbezeichnung
Například Bar na náměstí|For example: Central Bar|Zum Beispiel: Bar am Markt
Město, ulice nebo vaše interní označení|City, street or your internal label|Stadt, Straße oder interne Bezeichnung
Provoz začne s prázdnými sklady a vlastním týmem. K dispozici bude celý katalog a obchod NOIRY, inventury, vážení i pracovní terminál.|The venue starts with empty warehouses and its own team. The full NOIRA catalogue and shop, inventories, weighing and work terminal are included.|Der Betrieb startet mit leeren Lagern und eigenem Team. Der gesamte NOIRA-Katalog und Shop, Inventuren, Wiegen und das Arbeitsterminal sind verfügbar.
Skladová množství po jednotlivých jednotkách.|Stock quantities by individual unit.|Bestandsmengen nach einzelnen Einheiten.
Zásoby pod kontrolou.|Stock under control.|Bestände im Griff.
Každá jednotka zvlášť. Množství, inventury a položky k doplnění.|Each unit separately. Quantities, inventories and items to replenish.|Jede Einheit separat. Mengen, Inventuren und aufzufüllende Artikel.
Skladové množství|Stock quantity|Bestandsmenge
Nejdříve změřte zásoby ve svých provozech.|Measure the stock in your venues first.|Erfassen Sie zuerst die Bestände Ihrer Betriebe.
PROVOZ|VENUE|BETRIEB
STAV ZÁSOB|STOCK LEVEL|BESTAND
SKLADY|WAREHOUSES|LAGER
INVENTURY|INVENTORIES|INVENTUREN
POD MINIMEM|BELOW MINIMUM|UNTER MINDESTBESTAND
MANKO POSLEDNÍ INVENTURY|LAST INVENTORY SHORTAGE|FEHLMENGE DER LETZTEN INVENTUR
Bez výchozího stavu|No baseline|Kein Ausgangsbestand
Bez manka|No shortage|Keine Fehlmenge
Správní lidé. Správný přístup.|The right people. The right access.|Die richtigen Leute. Die richtigen Rechte.
Spravujte zaměstnance a jejich oprávnění samostatně v každém provozu.|Manage employees and their permissions separately for each venue.|Verwalten Sie Mitarbeiter und ihre Rechte für jeden Betrieb separat.
Pozvat zaměstnance|Invite employee|Mitarbeiter einladen
ZAMĚSTNANEC|EMPLOYEE|MITARBEITER
STAV|STATUS|STATUS
POSLEDNÍ AKTIVITA|LAST ACTIVITY|LETZTE AKTIVITÄT
PŘÍSTUP|ACCESS|ZUGRIFF
Upravit přístup|Edit access|Zugriff bearbeiten
Zatím nemáte zaměstnance. Vytvořte pro ně pozvánku do vybraného provozu.|No employees yet. Create an invitation to the selected venue.|Noch keine Mitarbeiter. Erstellen Sie eine Einladung für den gewählten Betrieb.
PIN a přístup ke konkrétním skladům nastavíte ve správě uživatelů uvnitř provozu.|Set PINs and warehouse access in user management inside the venue.|PIN und Lagerzugriff richten Sie in der Benutzerverwaltung des Betriebs ein.
Všechno podle vás.|Everything your way.|Alles nach Ihren Wünschen.
Účet majitele a přístup k vašim podnikům.|Owner account and access to your venues.|Inhaberkonto und Zugriff auf Ihre Betriebe.
Provozů můžete vytvořit více. Data zaměstnanců, inventur, kalibrací a skladů zůstávají oddělená.|You can create multiple venues. Employee, inventory, calibration and warehouse data stay separate.|Sie können mehrere Betriebe erstellen. Mitarbeiter-, Inventur-, Kalibrierungs- und Lagerdaten bleiben getrennt.
Víte, co se právě děje.|Know what is happening.|Wissen, was gerade passiert.
Přihlášení, změny skladů, inventury a správa zaměstnanců napříč podniky.|Sign-ins, stock changes, inventories and employee management across venues.|Anmeldungen, Bestandsänderungen, Inventuren und Mitarbeiterverwaltung aller Betriebe.
Všechny provozy|All venues|Alle Betriebe
Filtrovat provoz|Filter venue|Betrieb filtern
Zatím tu nejsou žádné události.|No events yet.|Noch keine Ereignisse.
Nejnovějších 200 událostí, nejvýše 100 z každého provozu. Historie se uchovává 90 dní.|Latest 200 events, up to 100 per venue. History is kept for 90 days.|Die neuesten 200 Ereignisse, höchstens 100 je Betrieb. Die Historie wird 90 Tage gespeichert.
Načítáme vaše provozy…|Loading your venues…|Ihre Betriebe werden geladen…
Připravujeme váš provoz…|Preparing your venue…|Ihr Betrieb wird vorbereitet…
Zkusit znovu|Try again|Erneut versuchen
Provoz|Venue|Betrieb
Označení pozvánky|Invitation label|Einladungsbezeichnung
Jméno zaměstnance|Employee name|Mitarbeitername
Platnost ve dnech|Validity in days|Gültigkeit in Tagen
Vytvořit pozvánku|Create invitation|Einladung erstellen
Pozvánka je připravená|Invitation ready|Einladung erstellt
Zaměstnanci předejte adresu provozu a registrační kód.|Give the employee the venue URL and registration code.|Geben Sie dem Mitarbeiter die Betriebsadresse und den Registrierungscode.
Adresa provozu|Venue URL|Betriebsadresse
Registrační kód|Registration code|Registrierungscode
Stav|Status|Status
Uložit přístup|Save access|Zugriff speichern
Provoz se nepodařilo otevřít|Could not open venue|Betrieb konnte nicht geöffnet werden
Oznámení|Notifications|Benachrichtigungen
Vyberte si, co chcete vědět o svých zásobách.|Choose what you want to know about your stock.|Wählen Sie, worüber Sie bei Ihren Beständen informiert werden möchten.
Načítání nastavení…|Loading settings…|Einstellungen werden geladen…
Upozornění pro tento provoz.|Alerts for this venue.|Meldungen für diesen Betrieb.
Upozornění napříč vašimi provozy.|Alerts across your venues.|Meldungen aus allen Ihren Betrieben.
Na jiném telefonu si oznámení zapněte zvlášť.|Enable notifications separately on each phone.|Aktivieren Sie Benachrichtigungen auf jedem Telefon separat.
Uložené inventury a měření|Saved inventories and measurements|Gespeicherte Inventuren und Messungen
Zásoby pod nastaveným minimem|Stock below the set minimum|Bestände unter dem festgelegten Minimum
Příjmy, výdeje a přesuny|Receipts, issues and transfers|Zugänge, Abgänge und Umlagerungen
Uložit výběr oznámení|Save notification preferences|Benachrichtigungen speichern
Obnovit připojení tohoto zařízení|Reconnect this device|Dieses Gerät erneut verbinden
Zapnout na tomto zařízení|Enable on this device|Auf diesem Gerät aktivieren
Zkušební oznámení|Test notification|Testbenachrichtigung
Vypnout na tomto zařízení|Disable on this device|Auf diesem Gerät deaktivieren
Oznámení jsou zablokovaná v nastavení telefonu nebo prohlížeče. Povolte je tam a pak se vraťte do NOIRY.|Notifications are blocked in your phone or browser settings. Allow them there, then return to NOIRA.|Benachrichtigungen sind in den Telefon- oder Browsereinstellungen blockiert. Erlauben Sie sie dort und kehren Sie zu NOIRA zurück.
Toto zařízení je připojené.|This device is connected.|Dieses Gerät ist verbunden.
Na tomto zařízení jsou oznámení vypnutá.|Notifications are off on this device.|Benachrichtigungen sind auf diesem Gerät deaktiviert.
Výběr oznámení je uložený.|Notification preferences saved.|Benachrichtigungseinstellungen gespeichert.
Oznámení nebyla povolena.|Notifications were not allowed.|Benachrichtigungen wurden nicht erlaubt.
Oznámení jsou na tomto zařízení zapnutá.|Notifications enabled on this device.|Benachrichtigungen auf diesem Gerät aktiviert.
Oznámení pro tento účet a provoz jsou na tomto zařízení vypnutá.|Notifications for this account and venue are off on this device.|Benachrichtigungen für dieses Konto und diesen Betrieb sind auf diesem Gerät deaktiviert.
Zkušební oznámení bylo odesláno.|Test notification sent.|Testbenachrichtigung gesendet.
Oznámení se nepodařilo nastavit.|Could not set up notifications.|Benachrichtigungen konnten nicht eingerichtet werden.
Na iPhonu otevřete NOIRU v Safari, zvolte Sdílet → Přidat na plochu a potom ji spusťte z plochy. Oznámení vyžadují podporovaný prohlížeč a iOS 16.4 nebo novější.|On iPhone, open NOIRA in Safari, choose Share → Add to Home Screen, then open it from your home screen. Notifications need a supported browser and iOS 16.4 or later.|Öffnen Sie NOIRA auf dem iPhone in Safari, wählen Sie Teilen → Zum Home-Bildschirm und starten Sie die App dort. Benachrichtigungen erfordern einen unterstützten Browser und iOS 16.4 oder neuer.
Přidat NOIRU na plochu|Add NOIRA to home screen|NOIRA zum Home-Bildschirm hinzufügen
NOIRA na ploše telefonu|NOIRA on your home screen|NOIRA auf Ihrem Home-Bildschirm
Otevírejte aplikaci přímo z plochy s vlastní ikonou. Pro přihlášení a práci s daty potřebujete internet.|Open the app from your home screen with its own icon. Signing in and working with data requires internet.|Öffnen Sie die App über ihr eigenes Symbol auf dem Home-Bildschirm. Anmeldung und Datenzugriff benötigen Internet.
Instalovat|Install|Installieren
Otevřete tuto stránku v prohlížeči Chrome.|Open this page in Chrome.|Öffnen Sie diese Seite in Chrome.
Klepněte na nabídku ⋮ vpravo nahoře.|Tap the ⋮ menu at the top right.|Tippen Sie oben rechts auf das Menü ⋮.
Vyberte „Přidat na plochu“ nebo „Instalovat aplikaci“ a potvrďte instalaci.|Choose “Add to Home Screen” or “Install app” and confirm.|Wählen Sie „Zum Startbildschirm hinzufügen“ oder „App installieren“ und bestätigen Sie.
Otevřete tuto stránku v Safari.|Open this page in Safari.|Öffnen Sie diese Seite in Safari.
Klepněte na Sdílet (čtvereček se šipkou nahoru).|Tap Share (the square with an upward arrow).|Tippen Sie auf Teilen (Quadrat mit Pfeil nach oben).
Zvolte „Přidat na plochu“, případně zapněte „Otevřít jako webovou aplikaci“ a klepněte na „Přidat“.|Choose “Add to Home Screen”, enable “Open as Web App” if shown, and tap “Add”.|Wählen Sie „Zum Home-Bildschirm“, aktivieren Sie gegebenenfalls „Als Web-App öffnen“ und tippen Sie auf „Hinzufügen“.
Počítač · Chrome nebo Edge|Desktop · Chrome or Edge|Computer · Chrome oder Edge
Klikněte na ikonu instalace v adresním řádku nebo vyberte instalaci aplikace v nabídce prohlížeče.|Click the install icon in the address bar or choose app installation from the browser menu.|Klicken Sie auf das Installationssymbol in der Adressleiste oder wählen Sie die App-Installation im Browsermenü.
Pokud stránku prohlížíte uvnitř jiné aplikace, otevřete ji nejprve v Chrome nebo Safari. Názvy voleb se mohou podle verze prohlížeče lišit.|If viewing this page inside another app, open it in Chrome or Safari first. Option names may vary by browser version.|Wenn Sie die Seite in einer anderen App ansehen, öffnen Sie sie zuerst in Chrome oder Safari. Die Bezeichnungen können je nach Browserversion abweichen.
Pokladny a denní uzávěrky|POS systems and daily closings|Kassensysteme und Tagesabschlüsse
Import denních souhrnů pro jednotlivé pobočky.|Import daily summaries for each branch.|Tagessummen für einzelne Filialen importieren.
Nyní funguje import CSV ve vzoru NOIRA. Automatické napojení Dotykačky a Storyous vyžaduje partnerské přístupy a dokončení konektoru; Septim dohodu s dodavatelem. Výběr značky zatím automatické spojení nezapíná.|CSV import using the NOIRA template is available. Automatic Dotykačka and Storyous connections require partner access and completion of the connector; Septim requires a vendor agreement. Choosing a brand does not enable automatic syncing yet.|Der CSV-Import mit der NOIRA-Vorlage ist verfügbar. Automatische Verbindungen zu Dotykačka und Storyous erfordern Partnerzugang und einen fertiggestellten Konnektor; Septim erfordert eine Vereinbarung mit dem Anbieter. Die Markenauswahl aktiviert noch keine automatische Synchronisierung.
Pokladní systém|POS system|Kassensystem
Označení pokladny|Register label|Kassenbezeichnung
Uložit nastavení pokladny|Save POS settings|Kasseneinstellungen speichern
Režim: ruční import CSV|Mode: manual CSV import|Modus: manueller CSV-Import
Nejdříve vytvořte provoz.|Create a venue first.|Erstellen Sie zuerst einen Betrieb.
Jiná pokladna / CSV|Other POS / CSV|Andere Kasse / CSV
Jak připravit CSV|How to prepare your CSV|CSV vorbereiten
Jeden řádek je celkový výsledek jedné pokladny za provozní den. Více směn nejdříve sečtěte. Zahrňte opravy a vratky v částce tržeb bez DPH.|Each row is one register’s total for one business day. Combine multiple shifts first. Include corrections and refunds in revenue excluding VAT.|Jede Zeile enthält die Tagessumme einer Kasse für einen Geschäftstag. Fassen Sie mehrere Schichten zuvor zusammen. Berücksichtigen Sie Korrekturen und Retouren im Umsatz ohne MwSt.
Požadované sloupce: datum, trzby_bez_dph. Volitelné: kasa, mena, naklady_zbozi, provozni_naklady, uzaverka_id. Chybějící náklady ponechte prázdné; nula znamená skutečně nulové náklady.|Required columns: datum, trzby_bez_dph. Optional: kasa, mena, naklady_zbozi, provozni_naklady, uzaverka_id. Leave unknown costs blank; zero means actual zero costs.|Pflichtspalten: datum, trzby_bez_dph. Optional: kasa, mena, naklady_zbozi, provozni_naklady, uzaverka_id. Unbekannte Kosten leer lassen; Null bedeutet tatsächlich keine Kosten.
Datum vychází z provozního dne pokladny, nikoli z času nahrání souboru. Opakovaný import stejného dne a pokladny opraví existující záznam a uchová jeho předchozí verzi.|The date is the register’s business day, not the upload time. Reimporting the same day and register updates the existing record and preserves its previous version.|Das Datum entspricht dem Geschäftstag der Kasse, nicht dem Upload-Zeitpunkt. Ein erneuter Import desselben Tages und derselben Kasse aktualisiert den Eintrag und bewahrt die vorherige Version.
Stáhnout vzor CSV|Download CSV template|CSV-Vorlage herunterladen
Nahrát denní uzávěrky|Upload daily closings|Tagesabschlüsse hochladen
Pobočka|Branch|Filiale
Soubor CSV|CSV file|CSV-Datei
Importovat uzávěrky|Import closings|Abschlüsse importieren
Odhad zisku = tržby bez DPH − náklady prodaného zboží − zadané provozní náklady. Nejde automaticky o účetní čistý zisk. Částky se nepřepočítávají mezi měnami.|Estimated profit = revenue excluding VAT − cost of goods sold − entered operating costs. This is not necessarily accounting net profit. Amounts are not converted between currencies.|Geschätzter Gewinn = Umsatz ohne MwSt. − Wareneinsatz − erfasste Betriebskosten. Dies entspricht nicht automatisch dem buchhalterischen Nettogewinn. Beträge werden nicht zwischen Währungen umgerechnet.
Nastavení pokladny je uložené.|POS settings saved.|Kasseneinstellungen gespeichert.
Vyberte CSV nejvýše 2 MB.|Choose a CSV file up to 2 MB.|Wählen Sie eine CSV-Datei bis 2 MB.
Denní výsledky poboček|Daily branch results|Tagesergebnisse der Filialen
Uzavřené dny, tržby a odhad zisku. Historie zůstává dohledatelná od prvního importu.|Closed days, revenue and estimated profit. History remains searchable from the first import.|Abgeschlossene Tage, Umsatz und geschätzter Gewinn. Die Historie ist ab dem ersten Import durchsuchbar.
Od|From|Von
Do|To|Bis
Měna|Currency|Währung
Stav výsledku|Result status|Ergebnisstatus
Chybí náklady|Costs missing|Kosten fehlen
Odhad zisku dostupný|Estimated profit available|Gewinnschätzung verfügbar
Použít filtry|Apply filters|Filter anwenden
Načítání denních výsledků…|Loading daily results…|Tagesergebnisse werden geladen…
Tržby bez DPH|Revenue excluding VAT|Umsatz ohne MwSt.
Odhad zisku|Estimated profit|Geschätzter Gewinn
Exportovat vybrané období|Export selected period|Gewählten Zeitraum exportieren
DEN|DAY|TAG
POBOČKA / KASA|BRANCH / REGISTER|FILIALE / KASSE
TRŽBY BEZ DPH|REVENUE EXCL. VAT|UMSATZ OHNE MWST.
ODHAD ZISKU|ESTIMATED PROFIT|GESCHÄTZTER GEWINN
Detail dne|Day details|Tagesdetails
Pro vybrané období nejsou uzávěrky.|No closings for the selected period.|Keine Abschlüsse im gewählten Zeitraum.
Vývoj po dnech|Daily trend|Tagesentwicklung
Nejvýše posledních 30 dnů vybraného období. Přesné hodnoty zůstávají v historii.|Up to the last 30 days of the selected period. Exact values remain in the history.|Bis zu den letzten 30 Tagen des gewählten Zeitraums. Genaue Werte bleiben in der Historie erhalten.
Náklady zboží|Cost of goods|Warenkosten
Provozní náklady|Operating costs|Betriebskosten
Zdrojová uzávěrka|Source closing|Quellabschluss
Neuvedeno|Not specified|Nicht angegeben
Historie oprav|Revision history|Korrekturhistorie
Poslední uzavřený den|Latest closed day|Letzter abgeschlossener Tag
Denní historie|Daily history|Tageshistorie
PRACOVNÍ PROSTOR|WORKSPACE|ARBEITSBEREICH
Váš pracovní prostor|Your workspace|Ihr Arbeitsbereich
Hlavní strana|Home|Startseite
Hlavní|Home|Start
Alkoholické nápoje|Alcoholic drinks|Alkoholische Getränke
Nastavení|Settings|Einstellungen
Všechny funkce|All features|Alle Funktionen
Nová inventura baru|New bar inventory|Neue Barinventur
Nová inventura skladu|New warehouse inventory|Neue Lagerinventur
Přehled inventur|Inventory history|Inventurübersicht
Porovnání inventur|Compare inventories|Inventuren vergleichen
Přehled skladů|Warehouse overview|Lagerübersicht
Přijmout dodávku|Receive delivery|Lieferung annehmen
Příjmy a výdeje|Receipts and issues|Zugänge und Abgänge
Skenování váhy|Scale scanner|Waagenscanner
Sudy a rozlévané nápoje|Kegs and drinks by the glass|Fässer und offene Getränke
Moje lahve|My bottles|Meine Flaschen
Databáze ověřených dat|Verified reference data|Geprüfte Referenzdaten
Nastavení inventury|Inventory settings|Inventureinstellungen
Historie skladových změn|Stock change history|Historie der Bestandsänderungen
Správa uživatelů|User management|Benutzerverwaltung
Můj profil|My profile|Mein Profil
Lahve a sudy, měření po pořadí a celkový přehled.|Bottles and kegs, sequential measurements and an overview.|Flaschen und Fässer, Messung der Reihe nach und Gesamtübersicht.
Vyberte sklad a spočítejte jeho zboží.|Choose a warehouse and count its stock.|Wählen Sie ein Lager und zählen Sie den Bestand.
Nejnovější inventury nahoře, detail a manko.|Latest inventories first, details and shortages.|Neueste Inventuren zuerst, Details und Fehlmengen.
Filtry typů inventur a porovnání s předchozími měsíci.|Filter inventory types and compare previous months.|Inventurtypen filtern und mit früheren Monaten vergleichen.
Stav zásob, minulý měsíc a poslední inventura.|Stock levels, last month and latest inventory.|Bestand, letzter Monat und letzte Inventur.
Více produktů a balení jedním potvrzením.|Multiple products and packs in one confirmation.|Mehrere Produkte und Packungen mit einer Bestätigung.
Pohyby, odpisy a přesuny mezi sklady.|Movements, write-offs and warehouse transfers.|Bewegungen, Abschreibungen und Umlagerungen.
Sudy, víno, lahve i vážené zboží.|Kegs, wine, bottles and weighed goods.|Fässer, Wein, Flaschen und Wiegewaren.
Katalog lahvových nápojů a balíčky.|Bottled drinks catalogue and bundles.|Katalog für Flaschengetränke und Pakete.
Pivo v sudech, víno a ostatní nápoje ve skladech.|Draught beer, wine and other drinks in stock.|Fassbier, Wein und andere Getränke im Lager.
Odemčené produkty připravené ke skenování.|Unlocked products ready to scan.|Freigeschaltete Produkte zum Scannen.
Přehled nastavení aplikace a kontrola provozu.|App settings and venue controls.|App-Einstellungen und Betriebskontrolle.
Zdroje, objemy a hmotnosti obalů.|Sources, volumes and container weights.|Quellen, Volumen und Behältergewichte.
Přesné pořadí lahví pro skenování po jedné.|Set the exact order for scanning bottles one by one.|Genaue Reihenfolge zum einzelnen Scannen der Flaschen.
Kdo změnil jakou položku, z jaké hodnoty na jakou.|Who changed each item, with previous and new values.|Wer welchen Artikel von welchem Wert auf welchen geändert hat.
Účty, oprávnění k akcím a pracovní prostory.|Accounts, permissions and workspaces.|Konten, Berechtigungen und Arbeitsbereiche.
Účet, heslo a přihlášení.|Account, password and sign-in.|Konto, Passwort und Anmeldung.
ADMINISTRÁTOR|ADMINISTRATOR|ADMINISTRATOR
ZAMĚSTNANEC|EMPLOYEE|MITARBEITER
Účet připojený k serveru|Account connected to server|Konto mit Server verbunden
Každá kapka má své místo.|Every drop in its place.|Jeder Tropfen an seinem Platz.
BAROMETR / PŘEHLED PROVOZU|NOIRA / VENUE OVERVIEW|NOIRA / BETRIEBSÜBERSICHT
Každý sklad.|Every warehouse.|Jedes Lager.
Na první pohled.|At a glance.|Auf einen Blick.
Zásoby, dodávky a inventury na jednom místě.|Stock, deliveries and inventories in one place.|Bestände, Lieferungen und Inventuren an einem Ort.
Otevřít sklady|Open warehouses|Lager öffnen
Zahájit inventuru|Start inventory|Inventur starten
aktivních skladů|active warehouses|aktive Lager
skladových položek|stock items|Lagerpositionen
pod minimem · doplnit|below minimum · replenish|unter Minimum · auffüllen
SROVNÁNÍ SKLADŮ|WAREHOUSE COMPARISON|LAGERVERGLEICH
Kde máte nejvíc položek|Where most items are stored|Wo die meisten Artikel lagern
Počet produktů|Number of products|Produktanzahl
Založte první sklad a porovnání se doplní z vašich dat.|Create your first warehouse to see a comparison of your data.|Erstellen Sie Ihr erstes Lager, um Ihre Daten zu vergleichen.
Počet evidovaných produktů v každém skladu. Různé měrné jednotky nesčítáme.|Number of registered products per warehouse. Different units are not added together.|Anzahl erfasster Produkte pro Lager. Unterschiedliche Einheiten werden nicht addiert.
Sklad|Warehouse|Lager
Produkt|Product|Produkt
Produkty|Products|Produkte
Název|Name|Name
Množství|Quantity|Menge
Jednotka|Unit|Einheit
Minimum|Minimum|Minimum
Příjem|Receipt|Zugang
Výdej|Issue|Abgang
Přesun|Transfer|Umlagerung
Odpis|Write-off|Abschreibung
Inventura|Inventory|Inventur
Nový sklad|New warehouse|Neues Lager
Vytvořit sklad|Create warehouse|Lager erstellen
Přidat sklad|Add warehouse|Lager hinzufügen
Nový produkt|New product|Neues Produkt
Přidat produkt|Add product|Produkt hinzufügen
Upravit produkt|Edit product|Produkt bearbeiten
Uložit produkt|Save product|Produkt speichern
Název skladu|Warehouse name|Lagername
Název produktu|Product name|Produktname
Typ produktu|Product type|Produkttyp
Poznámka|Note|Notiz
Čárový kód|Barcode|Barcode
Objem|Volume|Volumen
Hmotnost|Weight|Gewicht
Počet|Count|Anzahl
Datum|Date|Datum
Akce|Actions|Aktionen
Historie|History|Historie
Přehled|Overview|Übersicht
Přehled zásob|Stock overview|Bestandsübersicht
Celkem|Total|Gesamt
Změna|Change|Änderung
Manko|Shortage|Fehlmenge
Přebytek|Surplus|Überschuss
Nezměřené|Unmeasured|Nicht erfasst
Bez evidence|No records|Keine Erfassung
Hledat produkt|Search products|Produkt suchen
Hledat produkty…|Search products…|Produkte suchen…
Název produktu…|Product name…|Produktname…
Všechny sklady|All warehouses|Alle Lager
Žádné položky.|No items.|Keine Artikel.
Žádné produkty.|No products.|Keine Produkte.
Zatím žádné inventury.|No inventories yet.|Noch keine Inventuren.
Nastavení účtu|Account settings|Kontoeinstellungen
Uživatelé|Users|Benutzer
Oprávnění|Permissions|Berechtigungen
Uložit oprávnění|Save permissions|Berechtigungen speichern
Prohlížet sklady|View warehouses|Lager ansehen
Vytvářet a upravovat sklady a produkty|Create and edit warehouses and products|Lager und Produkte erstellen und bearbeiten
Přijímat dodávky|Receive deliveries|Lieferungen annehmen
Výdeje, odpisy a přesuny|Issues, write-offs and transfers|Abgänge, Abschreibungen und Umlagerungen
Provádět a ukládat inventury|Run and save inventories|Inventuren durchführen und speichern
Opravovat uzavřené inventury|Correct closed inventories|Abgeschlossene Inventuren korrigieren
Odemykat alkoholické nápoje|Unlock alcoholic drinks|Alkoholische Getränke freischalten
Spravovat běžné uživatele a pozvánky|Manage users and invitations|Benutzer und Einladungen verwalten
Číst historii skladových změn|View stock change history|Bestandsänderungen ansehen
Spouštět inventury na pracovním terminálu|Run inventories on the work terminal|Inventuren am Arbeitsterminal starten
Pracovní PIN a sklady|Work PIN and warehouses|Arbeits-PIN und Lager
Pracovní terminál|Work terminal|Arbeitsterminal
PRACOVNÍ TERMINÁL|WORK TERMINAL|ARBEITSTERMINAL
Zadejte svůj PIN|Enter your PIN|PIN eingeben
Čtyři číslice a můžete začít.|Four digits and you are ready.|Vier Ziffern und los geht’s.
Příjem, výdej a inventury vašeho provozu.|Receipts, issues and inventories for your venue.|Zugänge, Abgänge und Inventuren Ihres Betriebs.
Celá obrazovka|Full screen|Vollbild
Udržet obrazovku zapnutou|Keep screen awake|Bildschirm eingeschaltet lassen
Obrazovka zapnutá|Screen awake|Bildschirm aktiv
Váš čtyřmístný PIN|Your four-digit PIN|Ihre vierstellige PIN
Čtyřmístný zaměstnanecký PIN|Four-digit employee PIN|Vierstellige Mitarbeiter-PIN
Smazat poslední číslici|Delete last digit|Letzte Ziffer löschen
Vstoupit|Enter|Öffnen
Pracovní režim|Work mode|Arbeitsmodus
Zamknout|Lock|Sperren
Otevřít pracovní menu|Open work menu|Arbeitsmenü öffnen
RYCHLÝ ZÁPIS|QUICK ENTRY|SCHNELLERFASSUNG
Příjem zboží|Receive goods|Wareneingang
Výdej zboží|Issue goods|Warenausgang
Zboží ve skladech|Goods in warehouses|Waren im Lager
Vyberte položku a zadejte množství.|Select an item and enter the quantity.|Artikel wählen und Menge eingeben.
Klepněte na položku pro příjem nebo výdej.|Tap an item to receive or issue stock.|Tippen Sie auf einen Artikel für Zugang oder Abgang.
Obnovit zásoby|Refresh stock|Bestände aktualisieren
Najít produkt|Find product|Produkt finden
Všechny dostupné sklady|All available warehouses|Alle verfügbaren Lager
Po pěti minutách nečinnosti se terminál automaticky zamkne. Zápisy se ukládají pod vaším jménem.|The terminal locks after five minutes of inactivity. Entries are saved under your name.|Das Terminal wird nach fünf Minuten Inaktivität gesperrt. Einträge werden unter Ihrem Namen gespeichert.
Žádné odpovídající produkty v dostupných skladech.|No matching products in available warehouses.|Keine passenden Produkte in den verfügbaren Lagern.
Obrazovka zůstává rozsvícená, dokud je terminál v popředí.|The screen stays awake while the terminal is in the foreground.|Der Bildschirm bleibt aktiv, solange das Terminal im Vordergrund ist.
Pro stálé rozsvícení povolte v zařízení vypnutí automatického uspání.|Disable automatic sleep in your device settings to keep the screen on.|Deaktivieren Sie den automatischen Ruhezustand in den Geräteeinstellungen, um den Bildschirm eingeschaltet zu lassen.
Nemáte oprávnění|Access denied|Zugriff verweigert
PŘÍSTUP K FUNKCI|FEATURE ACCESS|FUNKTIONSZUGRIFF
O zpřístupnění této akce požádejte majitele.|Ask the owner for access to this action.|Bitten Sie den Inhaber um Zugriff auf diese Aktion.
`;
 for(const row of copy.trim().split('\n')){const [cs,en,de]=row.split('|');if(!cs||!en||!de)throw Error('Invalid translation: '+cs);add(cs,en,de)}
 for(const row of `
Denní|Daily|Täglich
Týdenní|Weekly|Wöchentlich
Měsíční|Monthly|Monatlich
Odhlásit se|Sign out|Abmelden
Administrátor|Administrator|Administrator
Testovací uživatel|Employee|Mitarbeiter
Katalog|Catalogue|Katalog
ZDARMA|FREE|KOSTENLOS
OMEZENO|RESTRICTED|EINGESCHRÄNKT
Menu|Menu|Menü
NOIRA — panel majitele|NOIRA — owner dashboard|NOIRA — Inhaberübersicht
NOIRA — přihlášení a inventura|NOIRA — sign-in and inventory|NOIRA — Anmeldung und Inventur
`.trim().split('\n'))add(...row.split('|'));
 for(const row of `
AI odhad zatím nemá ověřenou přesnost na reálných lahvích.|The AI estimate has not yet been validated on real bottles.|Die Genauigkeit der KI-Schätzung wurde noch nicht an echten Flaschen geprüft.
AKCE / 7 DNÍ|ACTIONS / 7 DAYS|AKTIONEN / 7 TAGE
ALKOHOLICKÉ NÁPOJE|ALCOHOLIC DRINKS|ALKOHOLISCHE GETRÄNKE
Administrátoři|Administrators|Administratoren
Akci se nepodařilo dokončit|Could not complete action|Aktion konnte nicht abgeschlossen werden
Aktivita v posledních 2 minutách|Active in the last 2 minutes|Aktiv in den letzten 2 Minuten
Aktivní za 7 dní|Active in the last 7 days|Aktiv in den letzten 7 Tagen
Aktuální množství|Current quantity|Aktuelle Menge
Aktuální počet|Current count|Aktuelle Anzahl
Aktuální stav skladů|Current warehouse stock|Aktuelle Lagerbestände
Analýza obrazu zatím není připojená nebo povolená na serveru.|Image analysis is not connected or enabled on the server yet.|Bildanalyse ist auf dem Server noch nicht verbunden oder aktiviert.
Automatické rozpoznávání hladiny|Automatic liquid level detection|Automatische Füllstanderkennung
Balíčky týdne|Bundles of the week|Pakete der Woche
Barevné ověření jednotlivých údajů, zdroje a přehled hmotností sudů.|Colour-coded verification, sources and keg weight references.|Farbliche Datenprüfung, Quellen und Fassgewichte im Überblick.
Bez aktivity 7+ dní|Inactive for 7+ days|Seit 7+ Tagen inaktiv
Bez porovnání|No comparison|Kein Vergleich
Brandy a koňak|Brandy and cognac|Brandy und Cognac
Celkem plný|Full container total|Gesamtgewicht voll
Celkem účtů|Total accounts|Konten insgesamt
Celkový přehled a uložení|Review and save|Gesamtübersicht und Speichern
Chybí údaj|Data missing|Angabe fehlt
Co balíček obsahuje|What is in the bundle|Inhalt des Pakets
Cyklus inventur a konec provozního dne.|Inventory cycle and end of business day.|Inventurzyklus und Ende des Geschäftstags.
DATABÁZE PRODUKTŮ|PRODUCT DATABASE|PRODUKTDATENBANK
DOČASNĚ ZDARMA PRO VŠECHNY|TEMPORARILY FREE FOR EVERYONE|VORÜBERGEHEND FÜR ALLE KOSTENLOS
Další|Next|Weiter
Databáze vah a ověřených údajů|Weight and verified reference database|Datenbank für Gewichte und geprüfte Angaben
Detail účtu, přihlášení a pohyby v aplikaci.|Account details, sign-ins and actions in the app.|Kontodetails, Anmeldungen und Aktionen in der App.
Dnešní balíčky pro váš bar|Today’s bundles for your bar|Heutige Pakete für Ihre Bar
Dodávky pod kontrolou|Deliveries under control|Lieferungen im Griff
FOTOGRAFIE VÁHY → ZŮSTATEK|SCALE PHOTO → REMAINING QUANTITY|WAAGENFOTO → RESTMENGE
Historie změn ve skladech|Warehouse change history|Historie der Lageränderungen
Hledat nápoj nebo model sudu|Search drink or keg model|Getränk oder Fassmodell suchen
Hmotnost 1 kusu / balení (kg)|Weight per item / pack (kg)|Gewicht pro Stück / Packung (kg)
Hmotnost prázdného obalu|Empty container weight|Leergewicht des Behälters
Hmotnost závisí na konkrétním obalu. Značka piva sama neurčuje váhu prázdného sudu. Hmotnosti od výrobce označené „cca“ jsou orientační.|Weight depends on the specific container. A beer brand does not determine empty keg weight. Manufacturer weights marked as approximate are estimates.|Das Gewicht hängt vom konkreten Behälter ab. Die Biermarke bestimmt nicht das Leergewicht des Fasses. Herstellerangaben mit „ca.“ sind Näherungswerte.
Hmotnosti plného i prázdného obalu musejí patřit ke stejnému typu obalu.|Full and empty weights must refer to the same container type.|Voll- und Leergewichte müssen zum selben Behältertyp gehören.
Hustota nápoje (kg/l)|Drink density (kg/l)|Getränkedichte (kg/l)
INVENTURY V ČASE|INVENTORIES OVER TIME|INVENTUREN IM ZEITVERLAUF
Inventury, sklady a přehledy na jednom místě.|Inventories, warehouses and reports in one place.|Inventuren, Lager und Auswertungen an einem Ort.
JMÉNO A PŘÍJMENÍ|FULL NAME|VOR- UND NACHNAME
Jak se změnily zásoby baru|How bar stock has changed|Veränderung der Barbestände
Jednotlivé lahve|Individual bottles|Einzelne Flaschen
KATALOG PRO ČESKÉ BARY|CATALOGUE FOR CZECH BARS|KATALOG FÜR TSCHECHISCHE BARS
Kalibrace: litry = (aktuální váha − prázdný obal) / (plný obal − prázdný obal) × objem.|Calibration: litres = (current weight − empty weight) / (full weight − empty weight) × volume.|Kalibrierung: Liter = (aktuelles Gewicht − Leergewicht) / (Vollgewicht − Leergewicht) × Volumen.
Katalog lahví a objemů|Bottle and volume catalogue|Flaschen- und Volumenkatalog
Každá úprava: kdo, kdy, původní hodnota a nová hodnota.|Every edit: who, when, previous value and new value.|Jede Änderung: wer, wann, alter und neuer Wert.
Každý obal má svoji hmotnost|Every container has its own weight|Jeder Behälter hat sein eigenes Gewicht
Kdo, kdy a co změnil. Původní i nová hodnota pocházejí z uložené změny na serveru.|Who changed what and when. Previous and new values come from the change saved on the server.|Wer was wann geändert hat. Alte und neue Werte stammen aus der auf dem Server gespeicherten Änderung.
Kolekce lahví se střídají podle českého času.|Bottle collections rotate according to Czech local time.|Flaschenkollektionen wechseln nach tschechischer Ortszeit.
Kolekce pro vaši knihovnu|Collections for your library|Kollektionen für Ihre Bibliothek
Konec provozního dne|End of business day|Ende des Geschäftstags
Kusy, litry, kilogramy a balení zobrazujeme odděleně. Porovnání zahrnuje jen produkty s evidencí k poslednímu dni minulého měsíce.|Items, litres, kilograms and packs are shown separately. Comparisons only include products with records at the end of last month.|Stück, Liter, Kilogramm und Packungen werden separat angezeigt. Vergleiche enthalten nur Produkte mit erfassten Beständen zum letzten Tag des Vormonats.
Kód se zobrazí pouze při vytvoření.|The code is shown only when created.|Der Code wird nur beim Erstellen angezeigt.
Lahve i balíčky můžete přidávat do vlastní knihovny. Odemčení se ukládají k vašemu účtu.|Add bottles and bundles to your library. Unlocks are saved to your account.|Fügen Sie Flaschen und Pakete Ihrer Bibliothek hinzu. Freischaltungen werden in Ihrem Konto gespeichert.
Lahve projdete ve svém pořadí. Sudy a rozlévané víno přidáte vážením.|Go through bottles in your chosen order. Add kegs and wine by weight.|Gehen Sie Flaschen in Ihrer Reihenfolge durch. Fässer und offenen Wein erfassen Sie durch Wiegen.
Lahve v nastaveném pořadí|Bottles in your set order|Flaschen in festgelegter Reihenfolge
Lahve v pořadí|Ordered bottles|Flaschen in Reihenfolge
Lahve v přesném pořadí|Bottles in the exact order|Flaschen in genauer Reihenfolge
Lahve, doložené objemy a kolekce pro vaše inventury.|Bottles, documented volumes and collections for your inventories.|Flaschen, belegte Volumen und Kollektionen für Ihre Inventuren.
Lahvové nápoje|Bottled drinks|Flaschengetränke
Likéry|Liqueurs|Liköre
Manko za posledních 13 měsíců|Shortages over the last 13 months|Fehlmengen der letzten 13 Monate
Model obalu neznamená přiřazení ke konkrétnímu pivovaru. Pro inventuru zvažte vlastní prázdný a plný obal.|A container model is not a brewery assignment. Weigh your own empty and full container for inventories.|Ein Behältermodell ist keinem bestimmten Brauhaus zugeordnet. Wiegen Sie für die Inventur Ihren eigenen leeren und vollen Behälter.
Moje nápoje|My drinks|Meine Getränke
Měsíc|Month|Monat
NASTAVENÍ INVENTURY|INVENTORY SETTINGS|INVENTUREINSTELLUNGEN
NASTAVENÍ · KONTROLA MAJITELE|SETTINGS · OWNER CONTROLS|EINSTELLUNGEN · INHABERKONTROLLE
NOVÁ INVENTURA BARU|NEW BAR INVENTORY|NEUE BARINVENTUR
NOVÝ VÝBĚR KAŽDÝ DEN|NEW SELECTION EVERY DAY|JEDEN TAG EINE NEUE AUSWAHL
Nabídne se při uložení měření.|Suggested when saving a measurement.|Wird beim Speichern einer Messung vorgeschlagen.
Najít funkci|Find a feature|Funktion finden
Nastavit můj pracovní PIN|Set my work PIN|Meine Arbeits-PIN festlegen
Nastavit pořadí lahví|Set bottle order|Flaschenreihenfolge festlegen
Neaktivní 7+ dní|Inactive for 7+ days|Seit 7+ Tagen inaktiv
Nejdříve si nastavte vlastní pracovní PIN v profilu nebo nastavení.|First set your own work PIN in your profile or settings.|Legen Sie zuerst Ihre Arbeits-PIN im Profil oder in den Einstellungen fest.
Nejnovější nahoře. Každou inventuru otevřete včetně položek a manka.|Latest first. Open any inventory with its items and shortages.|Neueste zuerst. Öffnen Sie jede Inventur einschließlich Artikeln und Fehlmengen.
Neověřeno / chybí údaj|Unverified / data missing|Ungeprüft / Angabe fehlt
Nové kolo|New round|Neue Runde
Nápoj|Drink|Getränk
Nápoje · ověřené objemy sudů|Drinks · verified keg volumes|Getränke · geprüfte Fassvolumen
OZNAČENÍ|LABEL|BEZEICHNUNG
Objem plného obalu (l)|Full container volume (l)|Volumen des vollen Behälters (l)
Odemknout pro mě zdarma|Unlock for free|Kostenlos freischalten
Odemykání pro vás zdarma|Free unlocking for you|Kostenlose Freischaltung für Sie
Odemčené produkty jsou připravené ke skenování.|Unlocked products are ready to scan.|Freigeschaltete Produkte sind zum Scannen bereit.
Odemčený produkt|Unlocked product|Freigeschaltetes Produkt
Otevření katalogu|Opened catalogue|Katalog geöffnet
Otevřete sklad. Produkty, příjmy a správu skladu najdete přímo v jeho detailu.|Open a warehouse to find its products, receipts and management tools.|Öffnen Sie ein Lager. Produkte, Zugänge und Verwaltung finden Sie in den Lagerdetails.
Otevřít databázi|Open database|Datenbank öffnen
Otevřít historii měření lahví|Open bottle measurement history|Flaschenmesshistorie öffnen
Otevřít historii změn|Open change history|Änderungshistorie öffnen
Otevřít katalog|Open catalogue|Katalog öffnen
Otevřít nastavení|Open settings|Einstellungen öffnen
Otevřít přehled|Open overview|Übersicht öffnen
Otevřít sklad a přidat nápoj|Open warehouse and add drink|Lager öffnen und Getränk hinzufügen
Otevřít sklad|Open warehouse|Lager öffnen
Otevřít|Open|Öffnen
Ověřená data k produktům|Verified product data|Geprüfte Produktdaten
Ověřené objemy a váhy sudů|Verified keg volumes and weights|Geprüfte Fassvolumen und -gewichte
Označení fyzické lahve / místo|Physical bottle label / location|Flaschenbezeichnung / Standort
POSLEDNÍ PŘIHLÁŠENÍ|LAST SIGN-IN|LETZTE ANMELDUNG
POUŽITÍ|USES|VERWENDUNGEN
Pivo v sudech, víno a další nápoje z vašich skladů.|Draught beer, wine and other drinks from your warehouses.|Fassbier, Wein und andere Getränke aus Ihren Lagern.
Plný obal včetně nápoje (kg; 0 = neznámá)|Full container including drink (kg; 0 = unknown)|Voller Behälter mit Getränk (kg; 0 = unbekannt)
Po práci na sdíleném zařízení se odhlaste.|Sign out after using a shared device.|Melden Sie sich nach der Arbeit an einem gemeinsam genutzten Gerät ab.
Po uložení dvou inventur baru se zde zobrazí jejich porovnání.|Save two bar inventories to see their comparison here.|Nach zwei gespeicherten Barinventuren erscheint hier der Vergleich.
Položka|Item|Artikel
Porovnání posledních dvou inventur|Compare the last two inventories|Vergleich der letzten beiden Inventuren
Poslední datum inventury|Last inventory date|Datum der letzten Inventur
Poslední inventura|Last inventory|Letzte Inventur
Poslední změna stavu|Last stock change|Letzte Bestandsänderung
Povolte jednotlivé akce a přístup ke skladům majitele.|Allow individual actions and access to the owner’s warehouses.|Erlauben Sie einzelne Aktionen und den Zugriff auf die Lager des Inhabers.
Pozvánky, přístup a aktivita zákazníků na jednom místě.|Invitations, access and user activity in one place.|Einladungen, Zugriff und Benutzeraktivitäten an einem Ort.
Pracovní PIN|Work PIN|Arbeits-PIN
Pracovní režim s PINem|Work mode with PIN|Arbeitsmodus mit PIN
Preference pro budoucí uzávěrky.|Preference for future closings.|Einstellung für künftige Abschlüsse.
Produkt nebo uživatel|Product or user|Produkt oder Benutzer
Produkty a balíčky odemykáte zdarma v katalogu.|Unlock products and bundles for free in the catalogue.|Schalten Sie Produkte und Pakete im Katalog kostenlos frei.
Prohlédnout balíček|View bundle|Paket ansehen
Proti minulému měsíci|Compared with last month|Vergleich zum Vormonat
Prázdné sudy · modely obalů|Empty kegs · container models|Leere Fässer · Behältermodelle
Prázdný obal|Empty container|Leerer Behälter
Prázdný obal (kg)|Empty container (kg)|Leerer Behälter (kg)
Pálenky a lihoviny|Spirits and fruit brandies|Spirituosen und Obstbrände
PŘEDCHOZÍ MĚSÍCE|PREVIOUS MONTHS|VORHERIGE MONATE
PŘEHLEDNĚ PODLE ČINNOSTI|ORGANISED BY ACTIVITY|NACH TÄTIGKEIT GEORDNET
Přehled inventury|Inventory review|Inventurübersicht
Při práci na sdíleném zařízení se odhlaste.|Sign out when using a shared device.|Melden Sie sich an einem gemeinsam genutzten Gerät ab.
Přidat existující lahve z inventury|Add existing inventory bottles|Vorhandene Inventurflaschen hinzufügen
Přidat lahev do pořadí|Add bottle to order|Flasche zur Reihenfolge hinzufügen
Přidejte první lahev. Stejný produkt můžete přidat vícekrát.|Add your first bottle. You can add the same product multiple times.|Fügen Sie die erste Flasche hinzu. Dasselbe Produkt kann mehrfach hinzugefügt werden.
Příjem dodávky a další akce najdete přímo v otevřeném skladu.|Find delivery receipts and other actions inside the warehouse.|Lieferungsannahme und weitere Aktionen finden Sie im geöffneten Lager.
Přístup a preference inventur.|Inventory access and preferences.|Zugriff und Einstellungen für Inventuren.
Přístup k lahvím|Bottle access|Flaschenzugriff
Původní záznamy i fotografie zůstávají zachované.|Original records and photos are preserved.|Ursprüngliche Einträge und Fotos bleiben erhalten.
Registrační pozvánky|Registration invitations|Registrierungseinladungen
Rozpoznané číslo i jednotku před uložením potvrďte. Při vyplnění prázdné a plné hmotnosti použijeme jejich poměr k objemu. Jinak jde o přepočet podle zadané hustoty.|Confirm the recognised number and unit before saving. With empty and full weights, we calculate by their ratio to volume. Otherwise we use the entered density.|Bestätigen Sie vor dem Speichern Zahl und Einheit. Bei erfasstem Leer- und Vollgewicht verwenden wir deren Verhältnis zum Volumen, sonst die eingegebene Dichte.
Rychlý příjem, výdej a inventury. Po pěti minutách nečinnosti se vrátí PINová brána.|Quick receipts, issues and inventories. The PIN screen returns after five minutes of inactivity.|Schnelle Zugänge, Abgänge und Inventuren. Nach fünf Minuten Inaktivität erscheint die PIN-Abfrage.
SDÍLENÝ TABLET|SHARED TABLET|GEMEINSAMES TABLET
SKLADOVÉ POHYBY|STOCK MOVEMENTS|LAGERBEWEGUNGEN
SPRÁVA TESTOVACÍHO PROVOZU|VENUE MANAGEMENT|BETRIEBSVERWALTUNG
Seřaďte lahve podle skutečného umístění. Po posledním skenu otevřeme celkový přehled k uložení.|Arrange bottles by their actual location. After the last scan, review and save the full inventory.|Ordnen Sie Flaschen nach ihrem Standort. Nach dem letzten Scan erscheint die Gesamtübersicht zum Speichern.
Spravovat uživatele|Manage users|Benutzer verwalten
Správa uživatelů a oprávnění|User and permission management|Benutzer- und Rechteverwaltung
Správci evidují přihlášení, poslední aktivitu a akce v této aplikaci pro účely testování. Historie aktivity se uchovává nejvýše 90 dní.|Administrators record sign-ins, last activity and actions in this app for testing. Activity history is kept for up to 90 days.|Administratoren erfassen Anmeldungen, letzte Aktivitäten und Aktionen in dieser App zu Testzwecken. Das Aktivitätsprotokoll wird höchstens 90 Tage gespeichert.
Starší jednotlivá měření lahví|Earlier individual bottle measurements|Frühere einzelne Flaschenmessungen
Střídání po 15 sekundách · český čas|Rotates every 15 seconds · Czech local time|Wechsel alle 15 Sekunden · tschechische Ortszeit
Sud, vak na víno, lahev i přepravka se odečtou podle uložené nebo právě zadané hmotnosti.|Kegs, wine bags, bottles and crates are deducted using their saved or entered weight.|Fässer, Weinbeutel, Flaschen und Kisten werden mit gespeichertem oder eingegebenem Gewicht abgezogen.
Sudy a víno přidáte jako produkt přímo v některém skladu.|Add kegs and wine as products inside a warehouse.|Fügen Sie Fässer und Wein direkt als Produkt in einem Lager hinzu.
Sudy, víno a další vážené položky|Kegs, wine and other weighed items|Fässer, Wein und andere Wiegewaren
Upravit pořadí lahví|Edit bottle order|Flaschenreihenfolge bearbeiten
Určete, která lahev bude první, druhá a další. Po posledním skenu následuje celkový přehled k uložení.|Choose the order of bottles. After the last scan, review and save the full inventory.|Legen Sie die Reihenfolge der Flaschen fest. Nach dem letzten Scan erscheint die Gesamtübersicht zum Speichern.
Uživatelé a jejich aktivita|Users and their activity|Benutzer und ihre Aktivitäten
VAŠE ODEMČENÉ PRODUKTY|YOUR UNLOCKED PRODUCTS|IHRE FREIGESCHALTETEN PRODUKTE
VYBRANÝ MĚSÍC|SELECTED MONTH|GEWÄHLTER MONAT
VYTVOŘIL|CREATED BY|ERSTELLT VON
Ve vybraném měsíci nejsou odpovídající inventury.|No matching inventories in the selected month.|Keine passenden Inventuren im gewählten Monat.
Vizuální režim: v živém náhledu označte hladinu a potvrďte stálý průřez. Pak jedním tlačítkem pořídíte snímek, vypočítáte odhad, uložíte a přejdete na další lahev. Pro neprůhledné nebo tvarované lahve použijte váhu.|Visual mode: mark the level in the live preview and confirm a constant cross-section. One button takes a photo, estimates the quantity, saves it and moves to the next bottle. Use scales for opaque or shaped bottles.|Visueller Modus: Füllstand im Livebild markieren und konstanten Querschnitt bestätigen. Eine Taste erstellt das Foto, schätzt die Menge, speichert und öffnet die nächste Flasche. Verwenden Sie für undurchsichtige oder geformte Flaschen eine Waage.
Vlastní údaj|Custom value|Eigene Angabe
Vyberte produkt; jeho sklad se doplní automaticky.|Choose a product; its warehouse is filled in automatically.|Wählen Sie ein Produkt; das Lager wird automatisch ergänzt.
Vyberte si první produkty v katalogu.|Choose your first products in the catalogue.|Wählen Sie Ihre ersten Produkte im Katalog.
Vyberte sklad, ve kterém chcete pracovat.|Choose the warehouse you want to work in.|Wählen Sie das Lager, in dem Sie arbeiten möchten.
Vyberte typ inventur a měsíc. Porovnání používá poslední dostupnou inventuru před vybraným měsícem.|Choose inventory type and month. The comparison uses the last available inventory before that month.|Wählen Sie Inventurtyp und Monat. Der Vergleich verwendet die letzte verfügbare Inventur vor diesem Monat.
Vyfoťte displej váhy. Odečteme obal a přepočítáme obsah.|Photograph the scale display. We deduct the container and calculate the contents.|Fotografieren Sie das Waagendisplay. Wir ziehen den Behälter ab und berechnen den Inhalt.
Vygenerování registrační pozvánky|Created registration invitation|Registrierungseinladung erstellt
Vypočítat a zkontrolovat zůstatek|Calculate and check remaining quantity|Restmenge berechnen und prüfen
VÁŠ OSOBNÍ ÚČET|YOUR PERSONAL ACCOUNT|IHR PERSÖNLICHES KONTO
VÁŠ ÚČET|YOUR ACCOUNT|IHR KONTO
VÝBĚR SKLADU|CHOOSE WAREHOUSE|LAGER AUSWÄHLEN
Váš vlastní čtyřmístný PIN pro příjem, výdej a správu terminálu.|Your own four-digit PIN for receipts, issues and terminal management.|Ihre eigene vierstellige PIN für Zugänge, Abgänge und Terminalverwaltung.
Vážení sudů, vína a zboží|Weighing kegs, wine and goods|Fässer, Wein und Waren wiegen
Výchozí cyklus|Default cycle|Standardzyklus
VŠECHNY INVENTURY|ALL INVENTORIES|ALLE INVENTUREN
Všechny doložené objemy lahví|All documented bottle volumes|Alle belegten Flaschenvolumen
ZMĚNA|CHANGE|ÄNDERUNG
Zabezpečení účtu|Account security|Kontosicherheit
Zaměstnanec|Employee|Mitarbeiter
Zapnout pracovní režim|Enable work mode|Arbeitsmodus aktivieren
Zatím bez evidence|No records yet|Noch keine Erfassung
Zatím nemáte odemčenou žádnou lahev|No bottles unlocked yet|Noch keine Flasche freigeschaltet
Zatím neproběhla|Not yet completed|Noch nicht durchgeführt
Zatím žádné pohyby.|No movements yet.|Noch keine Bewegungen.
Zatím žádné produkty. Přidejte zboží přímo do tohoto skladu.|No products yet. Add goods directly to this warehouse.|Noch keine Produkte. Fügen Sie Waren direkt in diesem Lager hinzu.
Zatím žádné přijaté dodávky. Po příjmu zde najdete poslední položky.|No deliveries received yet. Recent items will appear here after receipt.|Noch keine Lieferungen angenommen. Nach dem Eingang erscheinen hier die letzten Artikel.
Zkontrolujte lahve i zvážené sudy, rozdíly a manko.|Check bottles, weighed kegs, differences and shortages.|Prüfen Sie Flaschen, gewogene Fässer, Differenzen und Fehlmengen.
Změňte své přihlašovací heslo.|Change your sign-in password.|Ändern Sie Ihr Anmeldepasswort.
Značkové kolekce i tematické výběry. Všechny uvedené objemy produktů jsou součástí balíčku.|Brand collections and themed selections. All listed product volumes are included in the bundle.|Markenkollektionen und thematische Auswahlen. Alle aufgeführten Produktvolumen sind im Paket enthalten.
Zobrazit přehled k uložení|Review before saving|Übersicht zum Speichern anzeigen
Údaje ve vašich skladech|Data in your warehouses|Angaben in Ihren Lagern
Úspěšné přihlášení|Successful sign-in|Erfolgreiche Anmeldung
ÚČET|ACCOUNT|KONTO
Účet připojený ke stejnému pracovnímu prostoru na telefonu i počítači.|Your account connects to the same workspace on phone and desktop.|Ihr Konto nutzt denselben Arbeitsbereich auf Telefon und Computer.
Účty|Accounts|Konten
Čistá hmotnost = celková hmotnost − obal.|Net weight = total weight − container.|Nettogewicht = Gesamtgewicht − Behälter.
Číslo na displeji|Number on display|Zahl auf dem Display
Číslo z fotografie přečteme přímo v tomto zařízení.|The number in the photo is read on this device.|Die Zahl auf dem Foto wird direkt auf diesem Gerät gelesen.
Šipkami změníte pořadí kdykoliv. Stav měření zůstane zachovaný.|Use the arrows to reorder at any time. Measurements are preserved.|Ändern Sie die Reihenfolge jederzeit mit den Pfeilen. Messwerte bleiben erhalten.
Žádné inventury neodpovídají filtrům.|No inventories match the filters.|Keine Inventuren entsprechen den Filtern.
Žádné odpovídající změny. Historie se zaznamenává od zapnutí této funkce.|No matching changes. History starts when this feature is enabled.|Keine passenden Änderungen. Die Historie beginnt mit der Aktivierung dieser Funktion.
Předchozí|Previous|Zurück
≈ Orientační údaj|≈ Approximate value|≈ Näherungswert
≈ Orientační údaj výrobce|≈ Approximate manufacturer value|≈ Ungefähre Herstellerangabe
Sudy, rozlévané víno a další nápoje|Kegs, wine by the glass and other drinks|Fässer, offener Wein und weitere Getränke
Spustit / pokračovat ve skenování|Start / resume scanning|Scannen starten / fortsetzen
Zvážit sud nebo víno|Weigh keg or wine|Fass oder Wein wiegen
✓ Ověřeno|✓ Verified|✓ Geprüft
✓ Ověřeno ze zdroje|✓ Source verified|✓ Anhand der Quelle geprüft
Inventura skladů|Warehouse inventory|Lagerinventur
Odemknout další|Unlock more|Weitere freischalten
Přidat lahev|Add bottle|Flasche hinzufügen
Přidat nápoj přímo ve skladu|Add drink inside warehouse|Getränk direkt im Lager hinzufügen
Vygenerovat pozvánku|Create invitation|Einladung erstellen
Vyfotit displej váhy|Photograph scale display|Waagendisplay fotografieren
`.trim().split('\n'))add(...row.split('|'));

 for(const row of `
Aktuálně|Currently|Aktuell
Aktuální stav|Current stock|Aktueller Bestand
Aktivita účtu|Account activity|Kontoaktivität
Aplikaci se nepodařilo načíst. Obnovte stránku.|Could not load the app. Refresh the page.|Die App konnte nicht geladen werden. Laden Sie die Seite neu.
Balíček|Bundle|Paket
Balení|Packs|Packungen
Barva skladu|Warehouse colour|Lagerfarbe
Celková hmotnost plného obalu (kg)|Full container total weight (kg)|Gesamtgewicht des vollen Behälters (kg)
Celkový přehled|Full overview|Gesamtübersicht
Celou obrazovku můžete zapnout také v nabídce prohlížeče.|You can also enable full screen from the browser menu.|Sie können den Vollbildmodus auch im Browsermenü aktivieren.
Chybí od plné lahve|Missing from full bottle|Fehlmenge zur vollen Flasche
Cyklus uložen.|Cycle saved.|Zyklus gespeichert.
Cílový sklad (jen při přesunu)|Destination warehouse (transfers only)|Ziellager (nur bei Umlagerung)
Detail účtu|Account details|Kontodetails
Další možnosti|More options|Weitere Optionen
Evidované lahve|Registered bottles|Erfasste Flaschen
Evidováno|Recorded|Erfasst
Fotoaparát nebyl povolen nebo není dostupný. Množství můžete zadat ručně.|Camera access was denied or is unavailable. Enter the quantity manually.|Der Kamerazugriff wurde verweigert oder ist nicht verfügbar. Geben Sie die Menge manuell ein.
Fotografie není dostupná|Photo unavailable|Foto nicht verfügbar
Fotografii doplníme|Photo to be added|Foto wird ergänzt
Hladina nebo kalibrované vážení|Liquid level or calibrated weighing|Füllstand oder kalibriertes Wiegen
Hmotnost jedné jednotky (kg)|Weight per unit (kg)|Gewicht pro Einheit (kg)
Hmotnost prázdného obalu (kg)|Empty container weight (kg)|Leergewicht des Behälters (kg)
Inventura byla uložena a promítnuta do zásob.|Inventory saved and stock updated.|Inventur gespeichert und Bestände aktualisiert.
Inventury neobsahují položky v litrech pro porovnání.|The inventories contain no items in litres to compare.|Die Inventuren enthalten keine Artikel in Litern zum Vergleichen.
Jednotek v balení|Units per pack|Einheiten pro Packung
Je všechno správně?|Is everything correct?|Ist alles richtig?
Jemná výplň + barevný pruh|Soft fill and colour stripe|Dezente Füllung und Farbstreifen
K odemčení|Available to unlock|Zum Freischalten
Kalibrované vážení|Calibrated weighing|Kalibriertes Wiegen
Každá lahev. Krok za krokem.|Every bottle. Step by step.|Jede Flasche. Schritt für Schritt.
Kontrola a uložení do inventury|Review and save to inventory|Prüfen und in der Inventur speichern
Kontrola příjmu dodávky|Review delivery receipt|Wareneingang prüfen
Kontrola světla a stabilní náhled|Light check and steady preview|Lichtprüfung und stabiles Livebild
Kontrola změn skladu|Review stock changes|Bestandsänderungen prüfen
Kopírovat kód|Copy code|Code kopieren
Kód zkopírujte a pošlete uživateli. Později jej již nezobrazíme.|Copy the code and send it to the user. It will not be shown again.|Kopieren Sie den Code und senden Sie ihn dem Benutzer. Er wird später nicht mehr angezeigt.
Kusů / jednotek v balení|Items / units per pack|Stück / Einheiten pro Packung
Lahev ke skenování|Bottle to scan|Flasche zum Scannen
Minimální zásoba|Minimum stock|Mindestbestand
Minulé měření|Previous measurement|Vorherige Messung
Mám váhu — přeskočit kameru|I have scales — skip camera|Ich habe eine Waage — Kamera überspringen
Máte přístup pouze k prohlížení zásob.|You can only view stock.|Sie können Bestände nur ansehen.
Měření uloženo do inventury.|Measurement saved to inventory.|Messung in der Inventur gespeichert.
Nová registrační pozvánka|New registration invitation|Neue Registrierungseinladung
Nový stav|New stock level|Neuer Bestand
Nabízené sudy|Available kegs|Verfügbare Fässer
Najít položku dodávky|Find delivery item|Lieferartikel finden
Naměřený obsah ml|Measured contents in ml|Gemessener Inhalt in ml
Načíst aktuální stav a znovu zkontrolovat|Reload stock and check again|Bestand neu laden und erneut prüfen
Načítám kalibraci…|Loading calibration…|Kalibrierung wird geladen…
Načítám týdenní balíčky…|Loading weekly bundles…|Wochenpakete werden geladen…
Načítání dnešní nabídky…|Loading today’s selection…|Heutige Auswahl wird geladen…
Načítání historie…|Loading history…|Historie wird geladen…
Načítání uživatelů…|Loading users…|Benutzer werden geladen…
Nejdřív odemkněte lahev v katalogu.|Unlock the bottle in the catalogue first.|Schalten Sie zuerst die Flasche im Katalog frei.
Nejdřív si odemkněte produkty v katalogu.|Unlock products in the catalogue first.|Schalten Sie zuerst Produkte im Katalog frei.
Nejdříve propojte zařízení s provozem|Connect this device to a venue first|Verbinden Sie zuerst das Gerät mit einem Betrieb
Nejdříve přidejte do skladu produkty.|Add products to the warehouse first.|Fügen Sie zuerst Produkte im Lager hinzu.
Nejdříve vyberte produkt|Select a product first|Wählen Sie zuerst ein Produkt
Nejdříve vytvořte sklad.|Create a warehouse first.|Erstellen Sie zuerst ein Lager.
Nejdříve změřte lahve nebo zvažte sudy.|Measure bottles or weigh kegs first.|Erfassen Sie zuerst Flaschen oder wiegen Sie Fässer.
Nejprve dokončete nebo zrušte rozpracovanou inventuru tohoto skladu.|Finish or cancel the current warehouse inventory first.|Schließen Sie zuerst die laufende Lagerinventur ab oder brechen Sie sie ab.
Nemáte dostupný sklad.|No warehouse available.|Kein Lager verfügbar.
Nemáte oprávnění odemykat nápoje.|You do not have permission to unlock drinks.|Sie dürfen Getränke nicht freischalten.
Nemáte oprávnění odstranit sklad.|You do not have permission to delete a warehouse.|Sie dürfen kein Lager löschen.
Nemáte oprávnění provádět inventury.|You do not have permission to run inventories.|Sie dürfen keine Inventuren durchführen.
Nemáte oprávnění upravovat sklady.|You do not have permission to edit warehouses.|Sie dürfen Lager nicht bearbeiten.
Nemáte oprávnění upravovat zboží.|You do not have permission to edit goods.|Sie dürfen Waren nicht bearbeiten.
Neplatný kalibrační profil.|Invalid calibration profile.|Ungültiges Kalibrierungsprofil.
Nesouhlasí objem kalibrace.|Calibration volume does not match.|Das Kalibrierungsvolumen stimmt nicht überein.
Odemčení zdarma|Free unlock|Kostenlose Freischaltung
Orientační vizuální odečet|Approximate visual reading|Ungefähre visuelle Ablesung
Ostatní výdej|Other issues|Sonstige Abgänge
Objem ověřen ze zdroje. Hmotnost zadejte podle vlastního obalu.|Source-verified volume. Enter the weight of your own container.|Volumen anhand der Quelle geprüft. Geben Sie das Gewicht Ihres eigenen Behälters ein.
Obnovit zásoby a zadat zápis znovu|Refresh stock and enter again|Bestände aktualisieren und erneut eingeben
Obraz se mezi snímky pohnul. Zkuste znovu.|The image moved between shots. Try again.|Das Bild hat sich zwischen den Aufnahmen bewegt. Versuchen Sie es erneut.
Obraz se pohnul. Zopakujte automatický sken.|The image moved. Repeat the automatic scan.|Das Bild hat sich bewegt. Wiederholen Sie den automatischen Scan.
Odemkněte produkt a přidejte první lahev.|Unlock a product and add your first bottle.|Schalten Sie ein Produkt frei und fügen Sie die erste Flasche hinzu.
Odemykání je nyní vypnuté.|Unlocking is currently disabled.|Freischalten ist derzeit deaktiviert.
Odemykání pro běžné účty je nyní vypnuté.|Unlocking is currently disabled for regular accounts.|Freischalten ist für reguläre Konten derzeit deaktiviert.
Odemčené|Unlocked|Freigeschaltet
Odemčené produkty|Unlocked products|Freigeschaltete Produkte
Odemčení přidá produkt do „Moje lahve“. Fyzickou lahev a měření přidáte až potom.|Unlocking adds a product to “My bottles”. Add the physical bottle and measurements afterwards.|Die Freischaltung fügt das Produkt zu „Meine Flaschen“ hinzu. Die tatsächliche Flasche und Messungen erfassen Sie anschließend.
Odstranit účet|Delete account|Konto löschen
Odstranit účet?|Delete account?|Konto löschen?
Oprávnění uživatele|User permissions|Benutzerrechte
Opustit neuloženou inventuru?|Leave unsaved inventory?|Ungespeicherte Inventur verlassen?
Otevřít celoobrazovkový skener|Open full-screen scanner|Vollbildscanner öffnen
Ověření produktu a čárového kódu|Product and barcode verification|Produkt und Barcode prüfen
Ověřit produkt a objem u zdroje|Check product and volume at source|Produkt und Volumen bei der Quelle prüfen
Ověřit variantu u dodavatele|Check variant with supplier|Variante beim Lieferanten prüfen
Ověřit čárový kód online|Check barcode online|Barcode online prüfen
Ověřuji připojení analýzy obrazu…|Checking image analysis connection…|Verbindung zur Bildanalyse wird geprüft…
Označení|Label|Bezeichnung
Označte skutečnou hladinu.|Mark the actual liquid level.|Markieren Sie den tatsächlichen Füllstand.
Panáky 20 a 40 ml|20 and 40 ml shots|Shots mit 20 und 40 ml
Parametry pro vážení|Weighing parameters|Wiegeparameter
Platná přihlášení|Active sessions|Gültige Sitzungen
Plná lahev · 20 ml|Full bottle · 20 ml|Volle Flasche · 20 ml
Plná lahev · 40 ml|Full bottle · 40 ml|Volle Flasche · 40 ml
Plán se nepodařilo uložit. Zkuste znovu.|Could not save the plan. Try again.|Der Plan konnte nicht gespeichert werden. Versuchen Sie es erneut.
Položka plánu se změnila. Otevřete pořadí inventury.|The planned item changed. Open the inventory order.|Der geplante Artikel wurde geändert. Öffnen Sie die Inventurreihenfolge.
Poslední aktivita|Last activity|Letzte Aktivität
Poslední přihlášení|Last sign-in|Letzte Anmeldung
Posledních 100 změn v dostupných skladech.|Latest 100 changes in available warehouses.|Die letzten 100 Änderungen in verfügbaren Lagern.
Potvrdit a přejít k uložení|Confirm and continue to save|Bestätigen und zum Speichern fortfahren
Potvrdit lahev a pokračovat|Confirm bottle and continue|Flasche bestätigen und fortfahren
Potvrdit odemčení zdarma|Confirm free unlock|Kostenlose Freischaltung bestätigen
Pouze barevné ohraničení|Colour border only|Nur farbiger Rahmen
Použít ruční odečet|Use manual reading|Manuell ablesen
Použít váhu|Use scales|Waage verwenden
Povolte zadní fotoaparát…|Allow the rear camera…|Zugriff auf die Rückkamera erlauben…
Pozvěte testovacího uživatele|Invite a user|Benutzer einladen
Počet dosud nevypršelých relací|Number of unexpired sessions|Anzahl noch gültiger Sitzungen
Počet přihlášení|Sign-in count|Anzahl der Anmeldungen
Počet registrací|Number of registrations|Anzahl der Registrierungen
Počkejte na dokončení ukládání.|Wait for saving to finish.|Warten Sie, bis das Speichern abgeschlossen ist.
Počkejte na načtení profilu této varianty.|Wait for this variant’s profile to load.|Warten Sie, bis das Profil dieser Variante geladen ist.
Pracovní PIN a dostupné sklady|Work PIN and available warehouses|Arbeits-PIN und verfügbare Lager
Pracovní menu|Work menu|Arbeitsmenü
Pracovní přístup uložen|Work access saved|Arbeitszugriff gespeichert
Preference uložena.|Preference saved.|Einstellung gespeichert.
Prodeje uloženy.|Sales saved.|Verkäufe gespeichert.
Produkt / označení|Product / label|Produkt / Bezeichnung
Produkt přidáte do vlastní knihovny lahví.|Add the product to your bottle library.|Fügen Sie das Produkt Ihrer Flaschenbibliothek hinzu.
Produkt už není dostupný. Upravte plán.|The product is no longer available. Edit the plan.|Das Produkt ist nicht mehr verfügbar. Bearbeiten Sie den Plan.
Produkty, inventury i historie zůstanou při přejmenování zachované.|Renaming preserves products, inventories and history.|Beim Umbenennen bleiben Produkte, Inventuren und Historie erhalten.
Profil kalibrace se nepodařilo ověřit. Zkuste znovu otevřít skener.|Could not verify the calibration profile. Reopen the scanner.|Das Kalibrierungsprofil konnte nicht geprüft werden. Öffnen Sie den Scanner erneut.
Prohlédnout katalog|Browse catalogue|Katalog ansehen
Prohlížeč nedokázal zablokovat uspání. Vypněte automatické uspání v nastavení přístroje.|The browser could not prevent sleep. Disable automatic sleep in your device settings.|Der Browser konnte den Ruhezustand nicht verhindern. Deaktivieren Sie ihn in den Geräteeinstellungen.
První měření založí počáteční stav této fyzické lahve.|The first measurement sets this bottle’s starting quantity.|Die erste Messung legt den Anfangsbestand dieser Flasche fest.
Před dalším uložením načtěte aktuální stav skladu.|Reload current stock before saving again.|Laden Sie vor dem erneuten Speichern den aktuellen Bestand.
Přejít do katalogu|Go to catalogue|Zum Katalog
Přeskočit|Skip|Überspringen
Přesnost pro tuto konkrétní lahev.|Accuracy for this specific bottle.|Genauigkeit für diese konkrete Flasche.
Přesné hodnoty a názvy položek|Exact values and item names|Genaue Werte und Artikelbezeichnungen
Přečíst označenou váhu|Read selected scale display|Markierte Waagenanzeige ablesen
Přidat do období inventury|Add to inventory period|Zum Inventurzeitraum hinzufügen
Přihlásit majitele|Sign in as owner|Inhaber anmelden
Přisvítit|Turn on light|Licht einschalten
Přístup byl mezitím uzamčen.|Access has been locked.|Der Zugriff wurde inzwischen gesperrt.
Přístup ke skladům|Warehouse access|Lagerzugriff
Původně|Previously|Vorher
Registrován|Registered|Registriert
Rozdíl|Difference|Differenz
Rozpracovaná|In progress|In Bearbeitung
Rozpracovaná inventura se průběžně ukládá.|The inventory draft is saved continuously.|Der Inventurentwurf wird laufend gespeichert.
Ruční odečet hladiny|Manual liquid level reading|Manuelles Ablesen des Füllstands
Samostatné fyzické lahve|Individual physical bottles|Einzelne tatsächliche Flaschen
Sklad zatím nemá produkty.|This warehouse has no products yet.|Dieses Lager enthält noch keine Produkte.
Sklad zmizí z aktivního seznamu. Produkty a historie zůstanou zachované a sklad půjde obnovit.|The warehouse leaves the active list. Products and history remain and the warehouse can be restored.|Das Lager verschwindet aus der aktiven Liste. Produkte und Historie bleiben erhalten; das Lager kann wiederhergestellt werden.
Snímek je příliš velký. Změňte záběr.|The image is too large. Adjust the shot.|Das Bild ist zu groß. Ändern Sie den Ausschnitt.
Součet evidovaných lahví|Total registered bottles|Summe erfasster Flaschen
Spočítáno|Counted|Gezählt
Správa skladu|Warehouse management|Lagerverwaltung
Stavy byly obnoveny. Znovu ověřte spočítaná množství.|Stock reloaded. Check counted quantities again.|Bestände neu geladen. Prüfen Sie die gezählten Mengen erneut.
Stejná barva označí sklad i jeho zásoby. Název zůstává vždy viditelný.|The same colour identifies the warehouse and its stock. The name stays visible.|Dieselbe Farbe kennzeichnet das Lager und seine Bestände. Der Name bleibt sichtbar.
Tato inventura je již uložená.|This inventory is already saved.|Diese Inventur wurde bereits gespeichert.
Terminál se nemohl připojit|Terminal could not connect|Terminal konnte keine Verbindung herstellen
Trvale odstranit účet|Permanently delete account|Konto dauerhaft löschen
Ukončit pracovní režim|Exit work mode|Arbeitsmodus beenden
Ukončit pracovní režim?|Exit work mode?|Arbeitsmodus beenden?
Uloženo|Saved|Gespeichert
Uložení do inventury potvrdíte v následujícím kroku.|Confirm saving to inventory in the next step.|Bestätigen Sie im nächsten Schritt das Speichern in der Inventur.
Uložit do tohoto skladu|Save to this warehouse|In diesem Lager speichern
Uložit inventuru?|Save inventory?|Inventur speichern?
Uložit pracovní přístup|Save work access|Arbeitszugriff speichern
Uložit profil této varianty|Save this variant’s profile|Profil dieser Variante speichern
Uložit změny|Save changes|Änderungen speichern
Upravit oprávnění|Edit permissions|Berechtigungen bearbeiten
Určete akce a sklady, ke kterým má uživatel přístup.|Choose the actions and warehouses this user can access.|Legen Sie zugängliche Aktionen und Lager für diesen Benutzer fest.
V pracovním prostoru zatím nejsou sklady.|No warehouses in this workspace yet.|In diesem Arbeitsbereich gibt es noch keine Lager.
Vlastní referenční měření|Custom reference measurements|Eigene Referenzmessungen
Volné jednotky|Loose units|Lose Einheiten
Vaše inventura začíná první lahví|Your inventory starts with the first bottle|Ihre Inventur beginnt mit der ersten Flasche
Ve vaší knihovně|In your library|In Ihrer Bibliothek
Vlastní produkt / jiný pivovar|Custom product / other brewery|Eigenes Produkt / andere Brauerei
Vlastní sklady uživatele|User’s own warehouses|Eigene Lager des Benutzers
Volba sládků – název aktuálního piva (volitelné)|Brewer’s choice – current beer name (optional)|Brauerwahl – aktueller Biername (optional)
Volba sládků – vlastní název|Brewer’s choice – custom name|Brauerwahl – eigener Name
Vrátit|Return|Zurückgeben
Vybrat jiný sklad|Choose another warehouse|Anderes Lager wählen
Vyplněné hodnoty se neuloží.|Entered values will not be saved.|Eingegebene Werte werden nicht gespeichert.
Vyplňte pouze produkty z právě přijaté dodávky.|Only fill in products from this delivery.|Erfassen Sie nur Produkte dieser Lieferung.
Vypočítat a zkontrolovat|Calculate and review|Berechnen und prüfen
Výdej / přesun|Issue / transfer|Abgang / Umlagerung
Výdej, odpis nebo přesun|Issue, write-off or transfer|Abgang, Abschreibung oder Umlagerung
Výška %|Height %|Höhe %
Všechny cykly|All cycles|Alle Zyklen
Všechny inventury|All inventories|Alle Inventuren
Všechny lahve jsou změřené. Zkontrolujte celkový přehled.|All bottles measured. Review the full overview.|Alle Flaschen sind erfasst. Prüfen Sie die Gesamtübersicht.
Všechny produkty|All products|Alle Produkte
Zbývá|Remaining|Verbleibend
Zjištěno|Measured|Festgestellt
Zkontrolujte před uložením|Check before saving|Vor dem Speichern prüfen
Zadat vlastní měření ručně|Enter custom measurement manually|Eigene Messung manuell eingeben
Zadejte kladné množství.|Enter a positive quantity.|Geben Sie eine positive Menge ein.
Zadejte všechny čtyři číslice PINu.|Enter all four PIN digits.|Geben Sie alle vier PIN-Ziffern ein.
Zahájit počítání|Start counting|Zählung starten
Zamknout terminál|Lock terminal|Terminal sperren
Zapnout pracovní režim na tomto zařízení?|Enable work mode on this device?|Arbeitsmodus auf diesem Gerät aktivieren?
Zapnout pracovní terminál|Enable work terminal|Arbeitsterminal aktivieren
Zapnout vedení náklonu|Enable tilt guidance|Neigungshilfe aktivieren
Zapnout vedení náklonu telefonu|Enable phone tilt guidance|Neigungshilfe für das Telefon aktivieren
Zapsané prodeje|Recorded sales|Erfasste Verkäufe
Zatím nejsou zaznamenané změny.|No changes recorded yet.|Noch keine Änderungen erfasst.
Zatím nemáte žádné pozvánky.|No invitations yet.|Noch keine Einladungen.
Zatím nemáte žádný aktivní sklad.|No active warehouses yet.|Noch keine aktiven Lager.
Zatím žádná inventura.|No inventory yet.|Noch keine Inventur.
Zatím žádné měření|No measurements yet|Noch keine Messungen
Zatím žádné události.|No events yet.|Noch keine Ereignisse.
Začněte etiketou.|Start with the label.|Beginnen Sie mit dem Etikett.
Začít inventuru|Start inventory|Inventur starten
Zboží ve skladu|Goods in warehouse|Waren im Lager
Zbývající množství|Remaining quantity|Restmenge
Zbývající obsah v ml|Remaining contents in ml|Restinhalt in ml
Zbývající zásoba|Remaining stock|Restbestand
Zjištěné manko|Detected shortage|Festgestellte Fehlmenge
Zkontrolovat a uložit pohyb|Review and save movement|Bewegung prüfen und speichern
Zkontrolovat dodávku|Review delivery|Lieferung prüfen
Zkontrolovat orientační výsledek|Review estimated result|Geschätztes Ergebnis prüfen
Zkontrolovat ruční údaj|Review manual reading|Manuelle Angabe prüfen
Zkontrolujte připojení. Před dalším zápisem obnovte stránku.|Check your connection. Refresh the page before entering more data.|Prüfen Sie die Verbindung. Laden Sie die Seite vor weiteren Eingaben neu.
Změnit pořadí|Change order|Reihenfolge ändern
Změnit přístup tohoto účtu? Aktuální přihlášení se ukončí.|Change this account’s access? Current sessions will end.|Zugriff dieses Kontos ändern? Aktuelle Sitzungen werden beendet.
Změřit znovu|Measure again|Erneut messen
Zobrazení barvy|Colour display|Farbdarstellung
Zobrazit uložený snímek|View saved photo|Gespeichertes Foto anzeigen
Zpět do katalogu|Back to catalogue|Zurück zum Katalog
Zpět na automatické rozpoznání|Back to automatic recognition|Zurück zur automatischen Erkennung
Zpřesnit kalibraci této varianty|Refine this variant’s calibration|Kalibrierung dieser Variante verbessern
Zpřesnit kalibrovaným vážením|Refine with calibrated weighing|Mit kalibriertem Wiegen verbessern
Zrušit rozpracovanou|Cancel draft|Entwurf verwerfen
Zrušit rozpracovanou inventuru?|Cancel inventory draft?|Inventurentwurf verwerfen?
Zásoby jsou aktuální.|Stock is up to date.|Bestände sind aktuell.
Zásoby na baru|Bar stock|Barbestand
Zásoby se změnily. Nejdříve obnovte jejich stav.|Stock has changed. Refresh it first.|Die Bestände haben sich geändert. Aktualisieren Sie sie zuerst.
Účty, přihlášení a pohyby v aplikaci.|Accounts, sign-ins and actions in the app.|Konten, Anmeldungen und Aktionen in der App.
Čtyřmístný PIN pro terminál a omezení přístupu ke konkrétním skladům.|Four-digit terminal PIN and access restrictions for specific warehouses.|Vierstellige Terminal-PIN und Zugriffsbeschränkungen für bestimmte Lager.
Část položek bez výchozího stavu|Some items have no baseline|Einige Artikel ohne Ausgangsbestand
Číslo dodacího listu / faktury|Delivery note / invoice number|Lieferschein- / Rechnungsnummer
Žádná funkce neodpovídá hledání.|No features match your search.|Keine Funktionen entsprechen Ihrer Suche.
Žádná položka není pod minimální zásobou.|No items are below minimum stock.|Kein Artikel liegt unter dem Mindestbestand.
Žádné odpovídající účty.|No matching accounts.|Keine passenden Konten.
Ověření lahve|Bottle verification|Flasche prüfen
Příprava skenu|Scan preparation|Scan vorbereiten
Upravit měření|Edit measurement|Messung bearbeiten
Všichni uživatelé|All users|Alle Benutzer
Zpět na produkty|Back to products|Zurück zu Produkten
Spustit skenování|Start scanning|Scannen starten
Potvrdit a uložit inventuru|Confirm and save inventory|Inventur bestätigen und speichern
Přijmout celou dodávku|Receive entire delivery|Gesamte Lieferung annehmen
Uložit celou inventuru|Save entire inventory|Gesamte Inventur speichern
Uložit do inventury|Save to inventory|In Inventur speichern
Chybějící produkt|Missing product|Fehlendes Produkt
Přidat lahev do inventury|Add bottle to inventory|Flasche zur Inventur hinzufügen
Přidat měření|Add measurement|Messung hinzufügen
Přidat měřený bod|Add measurement point|Messpunkt hinzufügen
Přičíst další zvážený obal|Add another weighed container|Weiteren gewogenen Behälter addieren
Přístup do všech skladů tohoto provozu|Access all warehouses in this venue|Zugriff auf alle Lager dieses Betriebs
Zrušit přihlašování PINem|Disable PIN sign-in|PIN-Anmeldung deaktivieren
Zapsat příjem|Record receipt|Zugang erfassen
Zapsat výdej|Record issue|Abgang erfassen
Ano, odpojit tento terminál|Yes, disconnect this terminal|Ja, dieses Terminal trennen
Nesprávné přihlašovací údaje.|Incorrect sign-in details.|Falsche Anmeldedaten.
Přihlaste se prosím.|Please sign in.|Bitte melden Sie sich an.
K této akci nemáte oprávnění.|You do not have permission for this action.|Sie haben keine Berechtigung für diese Aktion.
Tato akce je dostupná pouze administrátorům.|This action is available to administrators only.|Diese Aktion ist nur für Administratoren verfügbar.
Obnovte stránku a zkuste to znovu.|Refresh the page and try again.|Laden Sie die Seite neu und versuchen Sie es erneut.
Příliš mnoho pokusů. Zkuste to za 15 minut.|Too many attempts. Try again in 15 minutes.|Zu viele Versuche. Versuchen Sie es in 15 Minuten erneut.
Současné heslo není správné.|The current password is incorrect.|Das aktuelle Passwort ist falsch.
Heslo musí mít 8–128 znaků.|The password must contain 8–128 characters.|Das Passwort muss 8–128 Zeichen enthalten.
Vyplňte všechna povinná pole.|Fill in all required fields.|Füllen Sie alle Pflichtfelder aus.
Pozvánka je neplatná, použitá nebo vypršela.|The invitation is invalid, used or expired.|Die Einladung ist ungültig, verwendet oder abgelaufen.
Toto uživatelské jméno je již obsazené.|This username is already taken.|Dieser Benutzername ist bereits vergeben.
CSV musí mít unikátní sloupce datum a trzby_bez_dph. Použijte vzor NOIRA.|CSV must have unique datum and trzby_bez_dph columns. Use the NOIRA template.|Die CSV-Datei benötigt eindeutige Spalten datum und trzby_bez_dph. Verwenden Sie die NOIRA-Vorlage.
Částka musí být číslo s nejvýše dvěma desetinnými místy.|Amounts must be numbers with no more than two decimal places.|Beträge müssen Zahlen mit höchstens zwei Nachkommastellen sein.
Neplatná částka.|Invalid amount.|Ungültiger Betrag.
Částka je příliš vysoká.|The amount is too high.|Der Betrag ist zu hoch.
Náklady nemohou být záporné.|Costs cannot be negative.|Kosten dürfen nicht negativ sein.
Datum nesmí být v budoucnosti.|The date cannot be in the future.|Das Datum darf nicht in der Zukunft liegen.
Každá pokladna smí mít pro jeden den pouze jeden denní souhrn.|Each register can have only one summary per day.|Jede Kasse darf nur eine Summe pro Tag haben.
CSV neobsahuje žádné denní souhrny.|The CSV contains no daily summaries.|Die CSV-Datei enthält keine Tagessummen.
Vyberte neprázdné CSV nejvýše 2 MB.|Choose a non-empty CSV file up to 2 MB.|Wählen Sie eine nicht leere CSV-Datei bis 2 MB.
Neplatné datum filtru.|Invalid filter date.|Ungültiges Filterdatum.
Začátek období musí předcházet konci.|The start date must precede the end date.|Das Anfangsdatum muss vor dem Enddatum liegen.
Měnu existujícího denního souhrnu nelze přepsat. Zkontrolujte soubor.|An existing daily summary’s currency cannot be changed. Check the file.|Die Währung einer vorhandenen Tagessumme kann nicht geändert werden. Prüfen Sie die Datei.
Uzávěrka se mezitím změnila. Zopakujte import.|The closing changed in the meantime. Repeat the import.|Der Abschluss wurde inzwischen geändert. Wiederholen Sie den Import.
Neplatná pokladna.|Invalid POS configuration.|Ungültige Kassenkonfiguration.
Denní souhrn neexistuje.|Daily summary not found.|Tagessumme nicht gefunden.
Provoz neexistuje nebo k němu nemáte přístup.|Venue not found or access denied.|Betrieb nicht gefunden oder kein Zugriff.
01 / PŘÍJEM ZÁSOB|01 / STOCK RECEIPTS|01 / WARENEINGANG
03 / SKLADY|03 / WAREHOUSES|03 / LAGER
PRODUKT / NYNÍ|PRODUCT / CURRENT STOCK|PRODUKT / AKTUELL
PŘÍJEM → NOVÝ STAV|RECEIPT → NEW STOCK|ZUGANG → NEUER BESTAND
`.trim().split('\n'))add(...row.split('|'));
 for(const row of `
Aktivita zachycuje akce v aplikaci, ne činnost mimo ni. „Poslední aktivita“ neznamená nepřetržité sledování uživatele.|Activity records actions inside the app only. “Last activity” does not mean continuous employee monitoring.|Aktivitäten erfassen nur Aktionen in der App. „Letzte Aktivität“ bedeutet keine durchgehende Überwachung des Benutzers.
AI vrátila neplatný objem. Nic nebylo uloženo.|AI returned an invalid volume. Nothing was saved.|Die KI hat ein ungültiges Volumen geliefert. Es wurde nichts gespeichert.
Body jsem skutečně změřil/a a ověřil/a referenci dna a plné hladiny.|I measured the points and checked the bottom and full-level references.|Ich habe die Punkte gemessen und Boden- sowie Vollstandreferenz geprüft.
Etiketa i objem odpovídají této lahvi|The label and volume match this bottle|Etikett und Volumen stimmen mit dieser Flasche überein
Kalibrace odpovídá této lahvi, obsahu i víčku.|The calibration matches this bottle, contents and cap.|Die Kalibrierung stimmt mit dieser Flasche, dem Inhalt und dem Verschluss überein.
Lahev má v celém měřeném rozsahu rovný stálý průřez, hladina je viditelná a čáry jsem zkontroloval/a.|The bottle has a constant cross-section throughout the measured range, the level is visible, and I checked the lines.|Die Flasche hat im gesamten Messbereich einen konstanten Querschnitt, der Füllstand ist sichtbar und ich habe die Linien geprüft.
Dejte za ni světlé, jednolité pozadí. Vyhněte se odleskům.|Use a light, plain background behind the bottle. Avoid glare.|Verwenden Sie einen hellen, einfarbigen Hintergrund. Vermeiden Sie Reflexionen.
Dobré podmínky. Lepší odečet.|Better conditions. Better reading.|Gute Bedingungen. Bessere Ablesung.
Doložené velikosti tohoto produktu.|Documented sizes of this product.|Belegte Größen dieses Produkts.
Držte telefon rovně ve výšce hladiny; zahrňte celé tělo lahve.|Hold the phone level at liquid height and include the whole bottle body.|Halten Sie das Telefon gerade auf Füllstandhöhe und erfassen Sie den gesamten Flaschenkörper.
Jedna lahev · svisle · bez odlesků|One bottle · upright · no glare|Eine Flasche · senkrecht · ohne Reflexionen
Kamera se používá jen v tomto zařízení. Žádné snímky se neodesílají.|The camera is used on this device only. No images are sent.|Die Kamera wird nur auf diesem Gerät verwendet. Es werden keine Bilder gesendet.
Majitel se přihlásí do NOIRY, nastaví svůj PIN a v Nastavení zapne pracovní režim. Na tomto zařízení se tím ukončí běžné přihlášení majitele.|The owner signs in, sets a PIN and enables work mode in Settings. This signs the owner out of the regular app on this device.|Der Inhaber meldet sich an, legt eine PIN fest und aktiviert den Arbeitsmodus in den Einstellungen. Die reguläre Inhabersitzung auf diesem Gerät wird dadurch beendet.
Měření přidáte pomocí průvodce skenováním. Nejvyšší přesnost vyžaduje vlastní kalibraci vážením; vizuální odečet je orientační.|Add measurements with the scan guide. Best accuracy requires your own weight calibration; visual readings are approximate.|Erfassen Sie Messungen mit dem Scanassistenten. Die höchste Genauigkeit erfordert eine eigene Gewichtskalibrierung; visuelle Ablesungen sind Näherungswerte.
Namiřte na EAN; případně opište číslice.|Point at the EAN barcode or type the digits.|Richten Sie die Kamera auf den EAN-Code oder geben Sie die Ziffern ein.
Nejdříve si nastavte vlastní pracovní PIN. Po zapnutí se zde ukončí vaše běžné přihlášení. Zaměstnanci budou používat jen své PINy.|Set your work PIN first. Enabling work mode ends your regular session here. Employees will use their own PINs.|Legen Sie zuerst Ihre Arbeits-PIN fest. Beim Aktivieren endet hier Ihre reguläre Sitzung. Mitarbeiter verwenden ihre eigenen PINs.
Nejvýše 30 bodů.|Up to 30 points.|Höchstens 30 Punkte.
Ověřte etiketu a objem, připravte lahev a otevřete skener přes celou obrazovku.|Check the label and volume, prepare the bottle and open the full-screen scanner.|Prüfen Sie Etikett und Volumen, bereiten Sie die Flasche vor und öffnen Sie den Vollbildscanner.
Ověřte značku, příchuť i objem. Podobné lahve mohou mít jiný tvar nebo obsah.|Check brand, flavour and volume. Similar bottles may have different shapes or contents.|Prüfen Sie Marke, Geschmacksrichtung und Volumen. Ähnliche Flaschen können eine andere Form oder einen anderen Inhalt haben.
PIN ani jeho ověřovací otisk se nevracejí do prohlížeče. Nová oprávnění platí při dalším přihlášení.|Neither the PIN nor its hash is returned to the browser. New permissions apply at the next sign-in.|Weder PIN noch Prüfhash werden an den Browser zurückgegeben. Neue Rechte gelten bei der nächsten Anmeldung.
PIN je jedinečný v rámci provozu. Aktuální PIN se nikdy nezobrazuje.|PINs are unique within the venue. The current PIN is never shown.|PINs sind innerhalb des Betriebs eindeutig. Die aktuelle PIN wird nie angezeigt.
Plná hladina musí být nad dnem a aktuální hladina mezi nimi.|The full level must be above the bottom, with the current level in between.|Der Vollstand muss über dem Boden liegen, der aktuelle Stand dazwischen.
Po odemčení spustíte průvodce skenováním. Ověřte objem z etikety; pro přesnější obsah použijte vlastní kalibraci vážením.|Start the scan guide after unlocking. Check the volume on the label; use your own weight calibration for better accuracy.|Starten Sie nach der Freischaltung den Scanassistenten. Prüfen Sie das Volumen auf dem Etikett; für höhere Genauigkeit verwenden Sie eine eigene Gewichtskalibrierung.
Posuvníky zarovnejte se snímkem. Horní čára patří hladině plné lahve, spodní vnitřnímu dnu. Prostřední patří aktuální hladině.|Align the sliders with the photo. The top line is the full level, the bottom line the inside base, and the middle line the current level.|Richten Sie die Regler am Foto aus. Die obere Linie markiert den Vollstand, die untere den inneren Boden und die mittlere den aktuellen Füllstand.
Posuňte čáry na obraz lahve. Pro tvarované a neprůhledné lahve použijte váhu.|Move the lines onto the bottle image. Use scales for shaped or opaque bottles.|Verschieben Sie die Linien auf das Flaschenbild. Verwenden Sie für geformte oder undurchsichtige Flaschen eine Waage.
Potom přidejte první fyzickou lahev a její obsah.|Then add your first physical bottle and its contents.|Fügen Sie danach die erste tatsächliche Flasche und ihren Inhalt hinzu.
Potvrďte správnou lahev, stálý průřez a viditelnost hladiny; jinak použijte váhu.|Confirm the correct bottle, a constant cross-section and a visible level; otherwise use scales.|Bestätigen Sie die richtige Flasche, einen konstanten Querschnitt und sichtbaren Füllstand; verwenden Sie sonst eine Waage.
Počáteční stav je objem při založení lahve. Rozdíl = zjištěný stav − stav po odečtení zapsaných prodejů a ostatního výdeje.|Starting quantity is the volume when the bottle was added. Difference = measured quantity − quantity after recorded sales and other issues.|Der Anfangsbestand ist das Volumen beim Anlegen der Flasche. Differenz = festgestellter Bestand − Bestand nach erfassten Verkäufen und sonstigen Abgängen.
Pro kusové zboží vážením vyplňte hmotnost jednoho kusu. Hmotnost obalu změřte pro konkrétní obal.|To weigh individual items, enter the weight per item. Measure the actual container’s weight.|Geben Sie zum Wiegen von Stückware das Gewicht eines Stücks ein. Messen Sie das Gewicht des konkreten Behälters.
Pro nejpřesnější výsledek použijte váhu a vlastní kalibraci prázdné a plné lahve. Vizuální odečet je orientační.|For best accuracy, use scales and your own empty/full bottle calibration. Visual readings are approximate.|Verwenden Sie für höchste Genauigkeit eine Waage und eine eigene Leer-/Vollflaschenkalibrierung. Visuelle Ablesungen sind Näherungswerte.
Pro přesnější čtení tažením označte jen displej váhy.|For better reading, drag to select only the scale display.|Markieren Sie für eine genauere Ablesung durch Ziehen nur das Waagendisplay.
Při výběru majitele pracuje uživatel ve stejných skladech. Jeho dosavadní vlastní data se nemažou.|Selecting an owner gives the user access to that owner’s warehouses. Existing personal data is not deleted.|Bei Auswahl eines Inhabers arbeitet der Benutzer in dessen Lagern. Seine bisherigen eigenen Daten werden nicht gelöscht.
Připojení se přerušilo. Před zápisem ověříme platnost přihlášení.|The connection was interrupted. We will verify the session before saving.|Die Verbindung wurde unterbrochen. Vor dem Speichern prüfen wir die Sitzung.
U tmavého skla či zakryté hladiny použijte kalibrovanou váhu.|Use calibrated scales for dark glass or an obscured level.|Verwenden Sie bei dunklem Glas oder verdecktem Füllstand eine kalibrierte Waage.
V pořadí zůstávají nezměřené lahve. Při uložení bude inventura označená jako částečná.|Unmeasured bottles remain in the list. The saved inventory will be marked as partial.|In der Reihenfolge verbleiben nicht erfasste Flaschen. Die Inventur wird beim Speichern als teilweise markiert.
Vlastní profil není potvrzením přesnosti AI ani laboratorní kalibrací.|A custom profile does not validate AI accuracy or constitute laboratory calibration.|Ein eigenes Profil bestätigt weder die KI-Genauigkeit noch eine Laborkalibrierung.
Vyberte sklad. Po uložení se stav i datum inventury propíšou do celé aplikace.|Choose a warehouse. Saving updates stock and the inventory date throughout the app.|Wählen Sie ein Lager. Nach dem Speichern werden Bestand und Inventurdatum in der gesamten App aktualisiert.
Váš PIN vás přihlásí k práci. Samotné přihlášení režim nikdy nevypne; odpojení je samostatná potvrzovaná akce v menu.|Your PIN signs you into work mode. Signing in never disables it; disconnecting requires a separate confirmation in the menu.|Ihre PIN meldet Sie zum Arbeiten an. Die Anmeldung beendet den Modus nicht; das Trennen ist eine gesondert zu bestätigende Menüaktion.
Výška hladiny není u tvarovaných lahví úměrná objemu. U ramen, tmavého skla, likérů nebo zakryté hladiny použijte váhu. Vizuální odhad nemá ověřenou přesnost.|Liquid height is not proportional to volume in shaped bottles. Use scales for shoulders, dark glass, liqueurs or obscured levels. Visual estimates have no validated accuracy.|Bei geformten Flaschen ist die Füllhöhe nicht proportional zum Volumen. Verwenden Sie bei Schultern, dunklem Glas, Likören oder verdecktem Füllstand eine Waage. Die Genauigkeit visueller Schätzungen ist nicht geprüft.
Zadejte skutečné množství každé položky, včetně nulových stavů. Před uložením zobrazíme rekapitulaci.|Enter the actual quantity of every item, including zero stock. Review the summary before saving.|Geben Sie die tatsächliche Menge jedes Artikels ein, auch Nullbestände. Vor dem Speichern erscheint eine Zusammenfassung.
Začít nové kolo inventury? Dosavadní měření a snímky zůstanou v historii.|Start a new inventory round? Existing measurements and photos remain in history.|Neue Inventurrunde starten? Bisherige Messungen und Fotos bleiben in der Historie.
Zařízení odpojíte od provozu. Pro další zapnutí bude potřeba přihlášení majitele jménem a heslem.|This disconnects the terminal from the venue. Enabling it again requires the owner’s username and password.|Das Gerät wird vom Betrieb getrennt. Erneutes Aktivieren erfordert Benutzername und Passwort des Inhabers.
Zbývající obsah v litrech podle položek. Chybějící měření nejsou považována za nulu.|Remaining contents in litres by item. Missing measurements are not treated as zero.|Restinhalt in Litern nach Artikel. Fehlende Messungen gelten nicht als Null.
Úpravy i změny oprávnění se zaznamenávají. Zákaz se kontroluje na serveru při každé akci.|Edits and permission changes are recorded. The server checks access on every action.|Bearbeitungen und Rechteänderungen werden protokolliert. Der Server prüft den Zugriff bei jeder Aktion.
Žádné ruční čáry. Dva snímky se odešlou do AI služby. Výsledek je orientační a nemá ověřenou přesnost.|No manual lines. Two images are sent to the AI service. The result is approximate and its accuracy has not been validated.|Keine manuellen Linien. Zwei Bilder werden an den KI-Dienst gesendet. Das Ergebnis ist ungefähr und seine Genauigkeit nicht geprüft.
01 / OVĚŘENÍ LAHVE|01 / VERIFY BOTTLE|01 / FLASCHE PRÜFEN
02 / PŘÍPRAVA|02 / PREPARATION|02 / VORBEREITUNG
Průvodce od A do Z|Step-by-step guide|Schritt-für-Schritt-Anleitung
Založte svůj první sklad.|Create your first warehouse.|Erstellen Sie Ihr erstes Lager.
Hledat produkt nebo kód…|Search product or code…|Produkt oder Code suchen…
Hledat produkt ve skladu|Search products in warehouse|Produkte im Lager suchen
Název nebo čárový kód…|Name or barcode…|Name oder Barcode…
Kategorie|Category|Kategorie
Dodavatel|Supplier|Lieferant
Kusové zboží / obaly|Individual items / containers|Stückware / Behälter
Pivo v sudu|Draught beer|Fassbier
Rozlévané víno|Wine by the glass|Offener Wein
Ostatní nápoj / lahev|Other drink / bottle|Anderes Getränk / Flasche
Vážené zboží|Weighed goods|Wiegewaren
Zboží|Goods|Waren
Poslední|Latest|Letzte
Položky|Items|Artikel
Nový sklad|New warehouse|Neues Lager
Upravit sklad|Edit warehouse|Lager bearbeiten
Odstranit sklad|Delete warehouse|Lager löschen
Obnovit sklad|Restore warehouse|Lager wiederherstellen
Zatím žádná|None yet|Noch keine
Všechny akce se vztahují k tomuto skladu.|All actions apply to this warehouse.|Alle Aktionen beziehen sich auf dieses Lager.
V inventuře budou jen produkty tohoto skladu.|Only products from this warehouse will be counted.|Die Inventur enthält nur Produkte aus diesem Lager.
Spočítejte položky. Před uložením zobrazíme rekapitulaci a manko.|Count the items. Review the summary and shortages before saving.|Zählen Sie die Artikel. Vor dem Speichern erscheinen Zusammenfassung und Fehlmengen.
`.trim().split('\n'))add(...row.split('|'));
 for(const row of `
Vytvořit zaměstnanecký profil|Create employee profile|Mitarbeiterprofil erstellen
Zadejte přihlašovací údaje zaměstnance.|Enter the employee’s sign-in details.|Geben Sie die Anmeldedaten des Mitarbeiters ein.
Jméno|First name|Vorname
Přihlašovací jméno|Username|Benutzername
Vytvořit profil|Create profile|Profil erstellen
Heslo musí mít alespoň 8 znaků. PIN tvoří přesně čtyři číslice a v tomto provozu musí být jedinečný.|The password needs at least 8 characters. The PIN must have exactly four digits and be unique within this venue.|Das Passwort benötigt mindestens 8 Zeichen. Die PIN muss genau vier Ziffern enthalten und in diesem Betrieb eindeutig sein.
Po vytvoření můžete upravit oprávnění a přístup ke skladům.|After creation you can edit permissions and warehouse access.|Nach dem Erstellen können Sie Berechtigungen und Lagerzugriff bearbeiten.
Zaměstnanecký profil je vytvořený|Employee profile created|Mitarbeiterprofil erstellt
Zaměstnanec se může přihlásit zadaným heslem a na pracovním terminálu svým PINem.|The employee can sign in with the chosen password and use their PIN on the work terminal.|Der Mitarbeiter kann sich mit dem vergebenen Passwort anmelden und seine PIN am Arbeitsterminal verwenden.
Heslo ani PIN se v přehledech nezobrazují.|Passwords and PINs are not displayed in lists.|Passwörter und PINs werden nicht in Übersichten angezeigt.
Hotovo|Done|Fertig
Nemáte účet? Požádejte majitele o vytvoření zaměstnaneckého profilu.|Need an account? Ask the owner to create an employee profile.|Noch kein Konto? Bitten Sie den Inhaber, ein Mitarbeiterprofil zu erstellen.
SPRÁVA ZAMĚSTNANCŮ|EMPLOYEE MANAGEMENT|MITARBEITERVERWALTUNG
Zaměstnanecké profily, oprávnění a aktivita na jednom místě.|Employee profiles, permissions and activity in one place.|Mitarbeiterprofile, Berechtigungen und Aktivitäten an einem Ort.
Zatím nemáte zaměstnance. Vytvořte zaměstnanecký profil pro vybraný provoz.|No employees yet. Create an employee profile for the selected venue.|Noch keine Mitarbeiter. Erstellen Sie ein Mitarbeiterprofil für den gewählten Betrieb.
PIN je připravený při vytvoření profilu. Oprávnění a přístup ke skladům můžete následně upravit.|The PIN is set when the profile is created. You can edit permissions and warehouse access afterwards.|Die PIN wird beim Erstellen des Profils festgelegt. Berechtigungen und Lagerzugriff können Sie danach bearbeiten.
Spravovat běžné zaměstnanecké účty|Manage regular employee accounts|Reguläre Mitarbeiterkonten verwalten
Zaměstnanecké profily, oprávnění k akcím a pracovní prostory.|Employee profiles, action permissions and workspaces.|Mitarbeiterprofile, Aktionsberechtigungen und Arbeitsbereiche.
PIN musí obsahovat přesně čtyři číslice.|The PIN must contain exactly four digits.|Die PIN muss genau vier Ziffern enthalten.
Tento PIN už v pracovním prostoru používá jiný zaměstnanec.|Another employee in this workspace already uses this PIN.|Ein anderer Mitarbeiter in diesem Arbeitsbereich verwendet diese PIN bereits.
`.trim().split('\n'))add(...row.split('|'));
 function t(source){
  if(language==='cs')return source;
  const index=supported.indexOf(language),exact=dictionary.get(source);if(exact)return exact[index];
  if(source===source.toLocaleUpperCase('cs')){const upper=lowercase.get(source.toLocaleLowerCase('cs'));if(upper)return upper[index].toLocaleUpperCase(locales[language])}
  // Dynamic copy has stable Czech fragments separated from user data by punctuation or digits.
  const replacements=[
   [/^([\d., \u00a0]+) lahví celkem$/,'$1 bottles in total','$1 Flaschen insgesamt'],
   [/^([\d., \u00a0]+) plných$/,'$1 full','$1 voll'],
   [/^([\d., \u00a0]+) načatých$/,'$1 opened','$1 angebrochen'],
   [/^([\d., \u00a0]+) prázdných$/,'$1 empty','$1 leer'],
   [/^([\d., \u00a0]+) lahví$/,'$1 bottles','$1 Flaschen'],
   [/^Nové heslo musí mít (\d+)–128 znaků\.$/,'The new password must contain $1–128 characters.','Das neue Passwort muss $1–128 Zeichen enthalten.'],
   [/^Množství v (.+)$/,'Quantity in $1','Menge in $1'],
   [/^Po zápisu: (.+)$/,'After entry: $1','Nach Erfassung: $1'],
   [/^(\d+) položek k přijetí$/,'$1 items to receive','$1 Artikel anzunehmen'],
   [/^(\d+) provozů · (\d+) skladů · (\d+) dokončených inventur$/,('$1 venues · $2 warehouses · $3 completed inventories'),('$1 Betriebe · $2 Lager · $3 abgeschlossene Inventuren')],
   [/^(\d+) položek pod minimem$/,'$1 items below minimum','$1 Artikel unter Mindestbestand'],
   [/^(\d+) (?:nezměřených položek|položek zatím nebylo změřeno\.)$/,'$1 unmeasured items','$1 nicht erfasste Artikel'],
   [/^(\d+) souhrnů bez úplných nákladů$/,'$1 summaries with incomplete costs','$1 Summen mit unvollständigen Kosten'],
   [/^(\d+) denních souhrnů · dny bez importu se nepovažují za nulovou tržbu\.$/,'$1 daily summaries · days without an import are not treated as zero revenue.','$1 Tagessummen · Tage ohne Import gelten nicht als Tage ohne Umsatz.'],
   [/^Import hotový: (\d+) nových, (\d+) oprav, (\d+) beze změny\.$/,'Import complete: $1 new, $2 updated, $3 unchanged.','Import abgeschlossen: $1 neu, $2 korrigiert, $3 unverändert.'],
   [/^(\d+) (produktů|PRODUKTŮ)$/,'$1 products','$1 Produkte'],
   [/^(\d+) změn$/,'$1 changes','$1 Änderungen'],
   [/^(\d+) odemčeno$/,'$1 unlocked','$1 freigeschaltet'],
   [/^(\d+) \/ (\d+) uloženo$/,'$1 / $2 saved','$1 / $2 gespeichert'],
   [/^(\d+) čeká · (\d+) přeskočeno$/,'$1 pending · $2 skipped','$1 ausstehend · $2 übersprungen'],
   [/^(\d+) položek · Poslední inventura: zatím neproběhla$/,'$1 items · Last inventory: not yet completed','$1 Artikel · Letzte Inventur: noch nicht durchgeführt'],
   [/^(\d+) lahví v pořadí · po každém skenu následuje další lahev\.$/,'$1 ordered bottles · each scan is followed by the next bottle.','$1 Flaschen in Reihenfolge · nach jedem Scan folgt die nächste Flasche.'],
   [/^(\d+) produktů · všechny dostupné objemy$/,'$1 products · all available volumes','$1 Produkte · alle verfügbaren Volumen'],
   [/^(\d+) \/ (\d+) · Nový výběr každý den$/,'$1 / $2 · New selection every day','$1 / $2 · Jeden Tag eine neue Auswahl'],
   [/^Ověření platí vždy jen pro konkrétní údaj\. Kontrola zdrojů: (.+)$/,'Verification applies to each individual value. Sources checked: $1','Die Prüfung gilt jeweils für die einzelne Angabe. Quellenprüfung: $1'],
   [/^Vytvoření provozu (.+)$/,'Venue created: $1','Betrieb erstellt: $1'],
   [/^Revize (\d+)/,'Revision $1','Revision $1'],
  ];
  for(const [pattern,en,de] of replacements)if(pattern.test(source))return source.replace(pattern,language==='en'?en:de);
  // Preserve decoration and translate UI segments such as “Tržby bez DPH · CZK”.
  const decorated=source.match(/^([＋+←↻↓☀⛶📷◎⚖▤♧⚙◫▥▦◷−✓✎\s]*)(.*?)([\s→↗]+)$/u);
  if(decorated&&dictionary.has(decorated[2]))return decorated[1]+dictionary.get(decorated[2])[index]+decorated[3];
  const leading=source.match(/^([＋+←↻↓☀⛶📷◎⚖▤▦−✓✎\s]+)(.+)$/u);
  if(leading&&dictionary.has(leading[2]))return leading[1]+dictionary.get(leading[2])[index];
  if(source.endsWith(' ·')&&dictionary.has(source.slice(0,-2)))return dictionary.get(source.slice(0,-2))[index]+' ·';
  const line=source.match(/^Řádek (\d+): (.+)$/);if(line)return (language==='en'?'Row ':'Zeile ')+line[1]+': '+t(line[2]);
  const parts=source.split(/( · |: )/);if(parts.length>1)return parts.map(part=>dictionary.get(part)?.[index]||part).join('');
  return source;
 }
 const excluded='script,style,noscript,textarea,code,pre,[translate="no"],[data-i18n-skip],.account-name,#owner-name,.profile-avatar,.venue-monogram,.header-monogram';
 function translateText(node){if(!node.parentElement||node.parentElement.closest(excluded))return;const current=node.nodeValue;if(!current.trim())return;const prev=textSources.get(node);const source=prev&&current===prev.output?prev.source:current;const trimmed=source.trim(),output=source.replace(trimmed,t(trimmed));textSources.set(node,{source,output});if(current!==output)node.nodeValue=output}
 function translateElement(el){if(el.closest(excluded))return;
  let formatted;
  if(el.hasAttribute('data-noira-money'))formatted=new Intl.NumberFormat(locales[language],{style:'currency',currency:el.dataset.noiraCurrency}).format(Number(el.dataset.noiraMoney)/100);
  if(el.hasAttribute('data-noira-date'))formatted=new Date(el.dataset.noiraDate+'T12:00:00').toLocaleDateString(locales[language]);
  if(el.hasAttribute('data-noira-time'))formatted=new Date(Number(el.dataset.noiraTime)*1000).toLocaleString(locales[language]);
  if(formatted!==undefined&&el.textContent!==formatted)el.textContent=formatted;
 if(el.tagName==='OPTION'&&!el.hasAttribute('value'))el.value=el.textContent;let saved=attributeSources.get(el);if(!saved){saved={};attributeSources.set(el,saved)}for(const attr of ['placeholder','aria-label','title']){if(!el.hasAttribute(attr))continue;const current=el.getAttribute(attr),prev=saved[attr],source=prev&&current===prev.output?prev.source:current,output=t(source);saved[attr]={source,output};if(current!==output)el.setAttribute(attr,output)}}
 function apply(root=document.body){if(!root)return;if(root.nodeType===3)return translateText(root);if(root.nodeType!==1)return;translateElement(root);const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode())){if(node.nodeType===3)translateText(node);else translateElement(node)}}
 let control;
 function placeControl(){const parent=document.body.classList.contains('auth-screen')?document.querySelector('.auth-card'):document.querySelector('[data-sidebar-language],.work-header .header-actions,.pin-intro');if(parent&&control.parentNode!==parent)parent.prepend(control)}
 function set(next){if(!supported.includes(next))return;language=next;try{localStorage.setItem(key,next)}catch{}document.documentElement.lang=next;if(control)control.querySelector('select').value=next;apply();apply(document.querySelector('title'));window.dispatchEvent(new CustomEvent('noira:language',{detail:{language:next,locale:locales[next]}}))}
 function start(){document.documentElement.lang=language;control=document.createElement('label');control.className='noira-language';control.setAttribute('translate','no');control.innerHTML='<span>Jazyk / Language / Sprache</span><select aria-label="Jazyk / Language / Sprache"><option value="cs">Čeština</option><option value="en">English</option><option value="de">Deutsch</option></select>';control.querySelector('select').value=language;control.querySelector('select').onchange=e=>set(e.target.value);placeControl();apply();apply(document.querySelector('title'));new MutationObserver(()=>apply(document.querySelector('title'))).observe(document.head,{subtree:true,childList:true,characterData:true});
  new MutationObserver(records=>{for(const record of records){if(record.type==='characterData')translateText(record.target);else if(record.type==='attributes')translateElement(record.target);else for(const node of record.addedNodes)apply(node)}placeControl()}).observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','aria-label','title','class']});
  window.addEventListener('storage',event=>{if(event.key===key&&supported.includes(event.newValue))set(event.newValue)});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
 for(const method of ['confirm','alert']){const original=window[method].bind(window);window[method]=message=>original(t(String(message)))}
 return {t,apply,set,add,get language(){return language},get locale(){return locales[language]}};
})();

