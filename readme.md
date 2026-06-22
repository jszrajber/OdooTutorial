# Odoo — notatki z setupu lokalnego

## 1. Struktura projektu

```
.
├── docker-compose.yml
├── config/
│   └── odoo.conf
└── addons/
    └── hello/                  ← moduł
        ├── __init__.py
        ├── __manifest__.py
        └── models/
            ├── __init__.py
            └── product.py
```

---

## 2. docker-compose.yml

```yaml
services:
  web:
    image: odoo:17.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - ./addons:/mnt/extra-addons
      - ./config:/etc/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_USER=odoo
```

**Co tu się dzieje:**
- `volumes` mapuje folder z twojego komputera na folder wewnątrz kontenera:
  `./addons` (host) → `/mnt/extra-addons` (kontener)
  `./config` (host) → `/etc/odoo` (kontener)
- Każda ścieżka w plikach konfiguracyjnych Odoo (np. `addons_path`) odnosi się do **wnętrza kontenera**, nie do twojego dysku.
- `db` w `environment: HOST=db` to nazwa serwisu z tego samego pliku — kontenery widzą się po nazwie serwisu, nie po `localhost`.

---

## 3. config/odoo.conf

```ini
[options]
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
addons_path = /mnt/extra-addons
```

- `[options]` to nazwa sekcji wymagana przez Odoo (format `.ini`) — bez niej dostajesz błąd `NoSectionError`.
- `addons_path` musi wskazywać na ścieżkę **w kontenerze** (`/mnt/extra-addons`), nie na `./addons`.

---

## 4. Podstawowe komendy

**Start / restart środowiska:**
```bash
docker compose up        # start (z logami w terminalu)
docker compose up -d     # start w tle
docker compose down      # stop i usunięcie kontenerów (dane w bazie zostają, jeśli używasz named volumes)
docker compose restart   # restart — potrzebne po zmianie kodu Pythona
```

**Podgląd logów (debugowanie błędów):**
```bash
docker compose logs web --tail 50
```

**Wejście do kontenera Odoo (np. do bash):**
```bash
docker exec -it odootutorial-web-1 bash
```
(nazwę kontenera sprawdzasz przez `docker ps`)

**Shell Odoo — interaktywny Python z gotowym `env`:**
```bash
docker exec -it odootutorial-web-1 odoo shell -d mydb
```
- `-d mydb` — nazwa bazy danych do której się podłączasz (ta sama, którą stworzyłeś przy pierwszym wejściu na `localhost:8069`)
- W tym shellu `env` jest już dostępne, nie trzeba go importować

---

## 5. Tworzenie modułu od zera

### a) Manifest — `addons/hello/__manifest__.py`

```python
{
    "name": "Hello",
    "version": "1.0",
    "depends": ["base"],
    "data": [],
    "installable": True,
}
```

- Bez tego pliku Odoo **nie rozpozna folderu jako modułu** — nie pojawi się w Apps.
- `depends` — lista modułów które muszą być zainstalowane przed twoim (ich modele/dane są wtedy dostępne). `base` to fundament Odoo (zawiera `res.partner`, `res.users` itd.) — praktycznie zawsze jest w `depends`.
- Wartości takie jak `"version"` muszą być stringami, nie liczbami (`"1.0"`, nie `1.0`).

### b) `addons/hello/__init__.py`

```python
from . import models
```

### c) `addons/hello/models/__init__.py`

```python
from . import product
```

⚠️ **Częsty błąd:** zostawienie tego pliku pustym. Bez importu, Python nigdy nie wczyta `product.py`, więc model nie istnieje — nawet jeśli moduł jest "installed".

### d) `addons/hello/models/product.py`

```python
from odoo import models, fields

class Product(models.Model):
    _name = "hello.product"
    _description = "My First Product"

    name = fields.Char(required=True)
    price = fields.Float()
    active = fields.Boolean(default=True)
```

**Wyjaśnienie pól:**

| Element | Co robi |
|---|---|
| `_name` | Metadane, nie kolumna. Nazwa modelu → nazwa tabeli SQL (`hello.product` → `hello_product`). |
| `_description` | Metadane, czytelna nazwa w UI. Czysto kosmetyczne. |
| `name = fields.Char(required=True)` | Prawdziwa kolumna VARCHAR. `required=True` = constraint NOT NULL. |
| `price = fields.Float()` | Kolumna liczbowa zmiennoprzecinkowa. |
| `active = fields.Boolean(default=True)` | Kolumna boolean. Specjalne znaczenie w Odoo: rekordy z `active=False` są automatycznie filtrowane z `search()` (mechanizm "soft delete"). |

**Konwencja nazewnictwa:** `_name = "hello.product"` to dowolna nazwa którą wybiera deweloper — prefiks (`hello`) zwyczajowo odpowiada nazwie modułu, żeby uniknąć konfliktów z innymi modułami, ale to konwencja, nie wymóg techniczny. Nazwa pliku (`product.py`) nie musi pokrywać się z `_name`.

---

## 6. Instalacja / aktualizacja modułu

### Przez UI:
1. Włącz developer mode: `http://localhost:8069/web?debug=1`
2. Apps → **Update Apps List**
3. Wyszukaj nazwę z manifestu (`Hello`) → **Install**
4. Po zmianie kodu Pythona: `docker compose restart`, potem w Apps → **Upgrade**

### Przez shell (szybsze, bez klikania):

```python
# sprawdzić status modułu
env['ir.module.module'].search([('name', '=', 'hello')]).state

# instalacja
env['ir.module.module'].search([('name', '=', 'hello')]).button_immediate_install()

# upgrade (po zmianie kodu / dodaniu pól)
env['ir.module.module'].search([('name', '=', 'hello')]).button_immediate_upgrade()
```

---

## 7. Praca z ORM w shellu

```python
# Wszystkie rekordy
env['hello.product'].search([])

# Tworzenie rekordu
env['hello.product'].create({'name': 'Laptop', 'price': 2999.99})

# Wyciąganie konkretnego pola z setu rekordów
records = env['hello.product'].search([])
records.mapped('name')          # -> ['Laptop']

# Filtrowanie (domena = lista trójek: pole, operator, wartość)
env['hello.product'].search([('price', '>', 1000)])

# Update
records.write({'price': 1999.99})

# Usuwanie
records.unlink()
```

**`env` vs `self.env`:**
- W shellu `env` jest gotowe od razu.
- W kodzie modułu (klasa modelu) piszesz `self.env`, bo `self` to instancja klasy dziedziczącej po `models.Model`, a Odoo wstrzykuje `env` jako atrybut tej instancji.

---

## 7a. Pełny ściągawka ORM — operacje na bazie

### CRUD

```python
# CREATE — pojedynczy rekord
record = env['hello.product'].create({'name': 'Laptop', 'price': 2999.99})

# CREATE — wiele rekordów na raz (szybsze niż create() w pętli)
records = env['hello.product'].create([
    {'name': 'Laptop', 'price': 2999.99},
    {'name': 'Mysz', 'price': 49.99},
])

# READ — wszystkie rekordy
env['hello.product'].search([])

# READ — z limitem, offsetem, sortowaniem
env['hello.product'].search([], limit=10, offset=20, order='price desc')

# READ — pobranie konkretnego rekordu po ID
env['hello.product'].browse(1)          # nie odpytuje bazy, tylko tworzy "wskaźnik"
env['hello.product'].browse([1, 2, 3])  # kilka ID na raz

# READ — szybkie wyciąganie danych jako dict (bez ładowania pełnych obiektów ORM)
env['hello.product'].search_read(
    domain=[('price', '>', 0)],
    fields=['name', 'price'],
)

# UPDATE — na zbiorze rekordów (wszystkie dostają tę samą wartość)
records.write({'price': 1999.99})

# DELETE
records.unlink()
```

### Domeny (filtrowanie) — najczęstsze operatory

```python
[('price', '>', 100)]
[('price', '>=', 100)]
[('price', '<', 100)]
[('price', '<=', 100)]
[('name', '=', 'Laptop')]
[('name', '!=', 'Laptop')]
[('name', 'like', 'Lap')]        # SQL LIKE, case-sensitive
[('name', 'ilike', 'lap')]       # LIKE, case-insensitive (najczęściej używany)
[('name', 'in', ['Laptop', 'Mysz'])]
[('name', 'not in', ['Laptop'])]
[('active', '=', False)]         # bez tego search() pomija nieaktywne rekordy

# Łączenie warunków — domyślnie AND
[('price', '>', 100), ('active', '=', True)]

# OR / AND / NOT trzeba pisać prefiksowo (notacja polska)
['|', ('price', '<', 10), ('price', '>', 1000)]          # price < 10 OR price > 1000
['&', ('active', '=', True), ('price', '>', 0)]          # explicit AND (rzadko potrzebne)
['!', ('name', '=', 'Laptop')]                            # NOT
```

### Operacje na recordsetach (zbiorach rekordów)

Recordset w Odoo zachowuje się jak lista, ale ma własne metody:

```python
records = env['hello.product'].search([])

records.mapped('name')              # lista wartości pola -> ['Laptop', 'Mysz']
records.mapped(lambda r: r.price * 2)  # mapped przyjmuje też funkcję

records.filtered(lambda r: r.price > 100)   # filtrowanie w Pythonie (po załadowaniu)
records.filtered('active')                  # skrót dla lambda r: r.active

records.sorted('price')                     # sortowanie rosnąco
records.sorted('price', reverse=True)       # sortowanie malejąco
records.sorted(key=lambda r: r.price)

len(records)                        # liczba rekordów w zbiorze
records.ids                         # lista ID -> [1, 2, 3]
record in records                   # sprawdzenie przynależności

records[0]                          # pierwszy rekord (wciąż jako recordset, nie dict)
records[0].name                     # dostęp do pola pierwszego rekordu

# Iterowanie
for r in records:
    print(r.name, r.price)
```

### Liczenie i sprawdzanie istnienia

```python
env['hello.product'].search_count([('price', '>', 100)])   # liczba rekordów, bez ładowania ich
records.exists()                     # odfiltrowuje rekordy które już nie istnieją w bazie (np. usunięte przez kogoś innego)
bool(records)                        # recordset jest "falsy" gdy pusty — można pisać if records:
```

### Pola obliczane i kontekst

```python
# Wymuszenie przeliczenia pól compute (rzadko potrzebne ręcznie)
records._compute_field_value('price_with_tax')

# Wywołanie z innym kontekstem (np. innym językiem albo bez wyzwalania automatyzacji)
env['hello.product'].with_context(lang='en_US').search([])
records.with_context(active_test=False).search([])  # pokaż też nieaktywne rekordy

# Wywołanie jako inny użytkownik (np. z uprawnieniami superuser)
env['hello.product'].with_user(env.ref('base.user_admin')).search([])
records.sudo()    # ignoruje reguły dostępu (uprawnienia) — używaj ostrożnie
```

### Transakcje w shellu

Shell **nie zapisuje automatycznie** zmian do bazy między komendami — działa w ramach jednej transakcji którą musisz sam zatwierdzić:

```python
env.cr.commit()      # zatwierdź zmiany na trwałe
env.cr.rollback()     # wycofaj niezatwierdzone zmiany
```

W normalnym działaniu Odoo (przez UI / kontroler) commit dzieje się automatycznie po zakończeniu requestu — to dotyczy tylko pracy w shellu.

---

## 8. Najczęstsze błędy i ich przyczyny

| Błąd | Przyczyna |
|---|---|
| `NoSectionError: No section: 'options'` | Plik `odoo.conf` jest pusty lub nie ma `[options]` na początku. |
| `KeyError: 'hello.product'` w shellu | Model nie został zaimportowany — sprawdź `models/__init__.py` (musi mieć `from . import product`). |
| Moduł nie pojawia się w Apps | Brak `__manifest__.py` albo błąd w jego składni (np. `version` jako liczba zamiast stringa). |
| `bind source path does not exist` | `docker-compose.yml` wskazuje na plik/folder którego nie ma na dysku (np. `odoo_pg_pass`, `config/`) — trzeba je stworzyć. |
| Zmiana w kodzie Pythona nie widoczna | Brak `docker compose restart` po edycji plików `.py`. |

---

## 9. Logika biznesowa — computed fields, metody, override create()

### a) Computed field — pole wyliczane automatycznie

```python
from odoo import models, fields, api

class Product(models.Model):
    _name = "hello.product"
    _description = 'My First Product'

    name = fields.Char(required=True)
    price = fields.Float()
    active = fields.Boolean(default=True)

    price_with_tax = fields.Float(compute='_compute_price_with_tax', store=True)

    @api.depends("price")
    def _compute_price_with_tax(self):
        for record in self:
            record.price_with_tax = record.price * 1.23
```

| Element | Co robi |
|---|---|
| `compute='_compute_price_with_tax'` | Wskazuje nazwę metody liczącej wartość pola — wartość nie przychodzi z `create()`, Odoo ją wylicza. |
| `store=True` | Zapisuje wyliczoną wartość jako prawdziwą kolumnę w bazie (umożliwia filtrowanie/sortowanie po niej w `search()`). Bez tego pole liczy się "w locie" i nie jest dostępne w domenach. |
| `@api.depends("price")` | Mówi Odoo "przelicz to pole na nowo, gdy zmieni się `price`". Mechanizm reaktywności — działa jak `useEffect` w React, tylko dla pól bazy danych. |
| `for record in self:` | **Kluczowy wzorzec w Odoo.** `self` w metodzie modelu to nie jeden obiekt, a recordset (zbiór rekordów) — nawet jeśli ma jeden element. Metoda musi działać dla wielu rekordów naraz, stąd zawsze pętla, nawet gdy w praktyce operujesz na jednym. |

Test w shellu:
```python
record.price              # sprawdź obecną wartość
record.price_with_tax       # price * 1.23

record.price = 1000
record.price_with_tax        # przeliczone automatycznie, bez ręcznego wywołania
```

### b) Własna metoda biznesowa (wywoływana ręcznie)

```python
def apply_discount(self, percent):
    for record in self:
        record.price = record.price * (1 - percent / 100)
```

Brak dekoratora — to zwykła metoda Pythona, nie jest powiązana z żadnym wyzwalaczem frameworku. Wywołujesz ją explicite, kiedy chcesz:
```python
record.apply_discount(10)   # obniża cenę o 10%
```

### c) Nadpisanie (override) `create()`

```python
@api.model_create_multi
def create(self, vals_list):
    records = super().create(vals_list)
    for record in records:
        print(f"Product created: {record.name}")
    return records
```

| Element | Co robi |
|---|---|
| `@api.model_create_multi` | Deklaruje że metoda przyjmuje **listę** dictów (`vals_list`), nie jeden dict. Odoo automatycznie konwertuje wywołania z jednym dictem (`create({...})`) na listę jednoelementową, więc kod wewnątrz może bezpiecznie zakładać że dostaje listę. |
| `super().create(vals_list)` | **Kluczowa linia.** Wywołuje oryginalną implementację `create()` z `models.Model`, która faktycznie zapisuje dane do bazy. Bez tego rekordy nigdy by nie powstały — Twoja metoda tylko by "udawała" tworzenie. |
| `for record in records:` | `records` to recordset zwrócony przez `super().create()` — może zawierać wiele nowo utworzonych rekordów. |
| `return records` | Musi zwrócić to co dostał z `super()`, inaczej każdy kod wołający `create()` dostanie `None` zamiast rekordu. |

To jest wzorzec analogiczny do nadpisania `save()` w modelu Django — dopinasz się do **punktu w cyklu życia rekordu** (tworzenie/zapis/usunięcie), a Twój kod wykonuje się automatycznie przy każdym wywołaniu `create()`, niezależnie skąd przyszło (shell, UI, kontroler HTTP).

**Gdzie zobaczysz `print()`:**

| Skąd tworzysz rekord | Gdzie zobaczysz print |
|---|---|
| `odoo shell` | Bezpośrednio w terminalu shella (shell działa w tym samym procesie co Odoo) |
| UI w przeglądarce | `docker compose logs web` |
| Wywołanie kontrolera/API | `docker compose logs web` |

W kodzie produkcyjnym zamiast `print()` standardem jest `_logger.info(...)` z modułu `logging` — lepiej integruje się z systemem logowania Odoo (poziomy, filtrowanie).

### d) Dekoratory — kiedy który

| Dekorator | Kiedy używasz | Dlaczego |
|---|---|---|
| `@api.depends('pole')` | Na metodach liczących computed fields | Mówi Odoo kiedy przeliczyć wartość |
| `@api.model_create_multi` | Tylko przy nadpisywaniu `create()` | Deklaruje że metoda przyjmuje listę dictów, nie jeden dict |
| (brak dekoratora) | Własne metody biznesowe (`apply_discount` itp.) | Zawsze operują na `self` jako recordset — to domyślny, oczekiwany kontrakt każdej metody modelu, nie wymaga specjalnego traktowania przez framework |
| `@api.model` | Metody niezwiązane z konkretnymi rekordami | Rzadziej używane, głównie w starszym kodzie |

---

## 10. Relacje między modelami

### Many2one — "wiele do jednego"

Czytane z perspektywy modelu na którym pole definiujesz: "wiele [tego modelu] wskazuje na jeden [tamten model]".

```python
# models/category.py
from odoo import models, fields

class Category(models.Model):
    _name = 'hello.category'
    _description = 'Product Category'

    name = fields.Char(required=True)
```

```python
# models/product.py — dodaj pole
category_id = fields.Many2one('hello.category', string='Category')
```

| Element | Co robi |
|---|---|
| `'hello.category'` | Model do którego się odwołujesz (pierwszy argument). |
| `string='Category'` | Czysto kosmetyczna etykieta dla UI — nie ma związku z nazwą pola w Pythonie. |
| Kolumna w SQL | `category_id`, typu integer — klasyczny foreign key, przechowuje `id` powiązanego rekordu. |

**Konwencja nazewnictwa:** pola `Many2one` kończą się na `_id` (przechowują jeden ID), pola `One2many`/`Many2many` kończą się na `_ids` (przechowują wiele ID).

Nie zapomnij dodać importu w `models/__init__.py`:
```python
from . import product
from . import category
```

### Dostęp przez relację

```python
cat = env['hello.category'].create({'name': 'Elektronika'})
product = env['hello.product'].create({'name': 'Laptop', 'price': 2000, 'category_id': cat.id})

product.category_id          # zwraca recordset z hello.category, nie tylko liczbę
product.category_id.name     # 'Elektronika' — ORM automatycznie "dociąga" powiązany rekord
```

Korzyść: jeśli kategoria zmieni nazwę, wszystkie produkty z tą kategorią automatycznie pokazują nową wartość — bo w `hello_product` przechowywane jest tylko ID, nie kopia tekstu. To klasyczna normalizacja bazy danych wyrażona przez ORM.

### One2many — odwrotna strona relacji

```python
# w Category
product_ids = fields.One2many('hello.product', 'category_id', string='Products')
```

Czytane jako: "jedna kategoria ma wiele produktów". **Nie tworzy kolumny w bazie** — to wirtualne pole, ORM oblicza je w locie, odpytując `hello_product` po `category_id` równym ID tej kategorii. Drugi argument (`'category_id'`) to nazwa pola Many2one po stronie modelu `hello.product`, które łączy te dwa modele.

### Transakcje — błąd "InFailedSqlTransaction"

Jeśli w shellu zobaczysz:
```
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted
```
to znaczy że poprzednia komenda w tej sesji shella zawiodła, a PostgreSQL blokuje kolejne komendy do końca transakcji (standardowe zachowanie SQL). Napraw to:
```python
env.cr.rollback()
```
i spróbuj swojej komendy jeszcze raz.

---

## 12. UI — widoki, akcje, menu (XML)

Do tego momentu wszystko działało tylko przez shell. Żeby zobaczyć dane w przeglądarce, potrzebujesz czterech nowych elementów: **widoki** (jak wyświetlić dane), **akcję** (co otworzyć), **menu** (jak się tam dostać) i **uprawnienia** (kto może to zobaczyć).

### a) Czym jest XML w Odoo

XML to **kolejny sposób tworzenia rekordów** w bazie — równoległy do `create()` w shellu, tylko zapisany deklaratywnie w pliku, wczytywany podczas instalacji/upgrade modułu (nie podczas `docker compose restart` — restart przeładowuje tylko kod Pythona, nie dane z XML).

```xml
<record id="view_hello_product_list" model="ir.ui.view">
    <field name="name">hello.product.list</field>
</record>
```
To jest dosłownie odpowiednik:
```python
env['ir.ui.view'].create({'name': 'hello.product.list'})
```
`id="..."` w `<record>` to **external ID** — tekstowa etykieta którą wymyślasz, żeby móc odwołać się do tego rekordu z innego miejsca w XML, zanim jeszcze ma on prawdziwe ID liczbowe z bazy.

### b) Widok listy — `addons/hello/views/product_views.xml`

```xml
<odoo>
    <record id="view_hello_product_list" model="ir.ui.view">
        <field name="name">hello.product.list</field>
        <field name="model">hello.product</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="price"/>
                <field name="price_with_tax"/>
                <field name="category_id"/>
            </tree>
        </field>
    </record>
</odoo>
```

| Element | Co robi |
|---|---|
| `model="ir.ui.view"` | W którym modelu systemowym ma powstać ten rekord — model przechowujący definicje wyglądu |
| `<field name="name">` | Czysto opisowa nazwa widoku, widoczna w Technical → Views. Konwencja: `nazwa_modelu.typ_widoku` |
| `<field name="model">` | KTÓREGO modelu dotyczy ten widok — bez tego Odoo nie wie jakie pola są dostępne |
| `<field name="arch" type="xml">` | Pole którego WARTOŚCIĄ jest cały kawałek XML opisujący layout — XML zagnieżdżony w XML |
| `<tree>` | Mówi "to ma być widok tabelaryczny". ⚠️ W Odoo 17.0 musi być `<tree>`, nie `<list>` — nowsza dokumentacja Odoo (18+) używa `<list>`, ale w 17.0 to rzuca `ValueError: Wrong value for ir.ui.view.type: 'list'` |
| `<field name="name"/>` wewnątrz `<tree>` | Jedna kolumna w tabeli — odwołuje się do pola zdefiniowanego w `product.py`, **nie tworzy** nowego pola, tylko wyświetla istniejące |
| `<field name="category_id"/>` | Pole relacyjne (Many2one) — Odoo automatycznie wyświetli wartość pola `name` powiązanej kategorii, nie surowe ID |

**Skąd biorą się nagłówki kolumn:** jeśli pole w Pythonie nie ma `string=`, Odoo generuje nagłówek automatycznie z nazwy zmiennej (`price_with_tax` → "Price With Tax"). Możesz to nadpisać:
```python
price_with_tax = fields.Float(compute='...', store=True, string='Cena z VAT')
```

### c) Widok formularza — w tym samym pliku

```xml
<record id="view_hello_product_form" model="ir.ui.view">
    <field name="name">hello.product.form</field>
    <field name="model">hello.product</field>
    <field name="arch" type="xml">
        <form>
            <sheet>
                <field name="name"/>
                <field name="price"/>
                <field name="price_with_tax" readonly="1"/>
                <field name="category_id"/>
                <field name="active"/>
            </sheet>
        </form>
    </field>
</record>
```

| Element | Co robi |
|---|---|
| `<form>` | Widok **jednego** rekordu (nie tabela wielu) — używany identycznie przy tworzeniu nowego rekordu (przycisk "New") i przy edycji istniejącego (kliknięcie na wiersz z listy) — to **ten sam** widok w obu przypadkach, różni się tylko czy pola są puste czy wypełnione danymi |
| `<sheet>` | Czysto wizualny kontener ("biała karta") — bez logicznego znaczenia, tylko grupuje pola estetycznie |
| `readonly="1"` na `price_with_tax` | Blokuje ręczną edycję — logiczne, bo to pole jest WYLICZANE przez `@api.depends`, edycja ręczna i tak zostałaby nadpisana przy zmianie `price` |

**Automatyczny wybór widgetu na podstawie typu pola w Pythonie:**

| Typ pola w Pythonie | Domyślny widget w UI |
|---|---|
| `fields.Char` | pole tekstowe |
| `fields.Float` / `fields.Integer` | pole liczbowe |
| `fields.Boolean` | checkbox |
| `fields.Many2one` | dropdown/wyszukiwarka |
| `fields.Date` / `fields.Datetime` | kalendarz |
| `fields.Selection` | dropdown z ograniczoną listą |

Nie musisz nigdzie w XML wskazywać "to ma być checkbox" — Odoo sam to wie z definicji modelu. To samo dotyczy CSS/JS całej tabeli/formularza — **nie piszesz ani jednej linii frontendu**, silnik renderujący Odoo generuje to automatycznie na podstawie `arch` + typów pól.

### d) Action — łącznik między menu a modelem

```xml
<record id="action_hello_product" model="ir.actions.act_window">
    <field name="name">Products</field>
    <field name="res_model">hello.product</field>
    <field name="view_mode">tree,form</field>
</record>
```

| Element | Co robi |
|---|---|
| `model="ir.actions.act_window"` | "Akcja otwierająca okno" — bez tego rekordu żadne menu nie wie JAK otworzyć Twój model |
| `<field name="res_model">` | KTÓRY model ma zostać otwarty — to jest właściwy "cel" akcji |
| `<field name="view_mode">` | W jakiej kolejności udostępnić widoki: najpierw `tree` (lista), po kliknięciu na wiersz — `form` |

**Czym jest action, a czym nie jest** — to było źródłem zamieszania, więc dopowiedzenie:
- Action **nie wyświetla wszystkich modeli które masz** — działa dla **jednego konkretnego** modelu wskazanego w `res_model`. Inny model = potrzebujesz innej, osobnej akcji
- Action **nie decyduje ile rekordów** się pojawi — to jest zawsze dynamiczne, zależne od aktualnego stanu bazy w momencie kliknięcia (Odoo robi odpowiednik `search([])` automatycznie, w tle, niewidocznie w XML)
- Action **inicjuje** łańcuch (menu → action → dane z bazy → widok), ale sam nie pobiera danych i nie renderuje — to robią inne mechanizmy frameworka

Można ograniczyć widoczne rekordy przez `domain` na akcji (ten sam mechanizm domen co w `search()`):
```xml
<field name="domain">[('price', '>', 100)]</field>
```

**Skąd Odoo wie KTÓRY widok użyć**, jeśli `view_mode` podaje tylko typ (`tree`, `form`), nie konkretny `id`? Jeśli nie wskażesz explicite `view_id`, Odoo bierze **pierwszy** widok danego typu zarejestrowany dla tego modelu. Wystarcza to gdy masz jeden widok każdego typu — przy wielu widokach tego samego typu dla jednego modelu, trzeba wskazać `view_id` explicite.

### e) Menu

```xml
<menuitem id="menu_hello_root" name="Hello"/>
<menuitem id="menu_hello_product" name="Products" parent="menu_hello_root" action="action_hello_product"/>
```

| Element | Co robi |
|---|---|
| `<menuitem>` (pierwszy) | Główny punkt menu w pasku górnym (np. "Hello", analogicznie do "Sales", "Inventory"). Bez `action` — sam z siebie nic nie otwiera, to tylko kontener na podmenu. Skrócona składnia, pod spodem tworzy rekord w `ir.ui.menu` |
| `<menuitem>` (drugi) | Podmenu, widoczne po kliknięciu na "Hello". MA `action` — faktycznie coś robi po kliknięciu |
| `parent="menu_hello_root"` | Odwołanie do `id` pierwszego menuitem — umieszcza to podmenu WEWNĄTRZ niego |
| `action="action_hello_product"` | Odwołanie do `id` akcji — po kliknięciu wykonaj tę akcję |

**Bez action, menu i tak się pojawia w UI** (sam `menuitem` nie wymaga action), ale kliknięcie na niego nic nie robi — nie ma żadnej instrukcji co otworzyć.

### f) Mapa zależności — co jest zależne od czego

```
menu_hello_root  (menu "Hello" w górnym pasku, sam nic nie otwiera)
        │
        └── menu_hello_product  (podmenu "Products", ma action)
                │
                ▼
        action_hello_product  (mówi: model = hello.product, widoki = tree,form)
                │
                ▼ (Odoo automatycznie szuka widoków tego typu dla tego modelu —
                │  dopasowanie przez pole 'model', NIE przez explicit odwołanie do id)
                │
        ┌───────┴────────┐
        ▼                ▼
view_hello_product_list   view_hello_product_form
   (otwiera się PIERWSZY)   (otwiera się po kliknięciu na wiersz)
```

Kluczowy mechanizm: akcja **nigdy explicite nie mówi** "użyj widoku o id=X" — łączy widoki z akcją poprzez wspólne pole `model="hello.product"` obecne w każdym z nich.

### g) Rejestracja w manifeście

Pliki `.py` rejestrujesz przez import w `__init__.py`. Pliki **XML** (i CSV z security) rejestrujesz inaczej — w manifeście, liście `data`:

```python
'data': [
    'security/ir.model.access.csv',
    'views/product_views.xml',
],
```

To są dwa **zupełnie różne mechanizmy ładowania**: Python ładowany jest przez import przy starcie serwera, XML/CSV ładowany jest przez Odoo **tylko** podczas instalacji/upgrade modułu — sam `docker compose restart` nie wystarczy, trzeba zrobić upgrade:
```python
env['ir.module.module'].search([('name', '=', 'hello')]).button_immediate_upgrade()
```

---

## 13. Security — uprawnienia dostępu (`ir.model.access.csv`)

### Dlaczego to jest potrzebne

**Bez tego pliku, normalny zalogowany użytkownik nie ma prawa zobaczyć Twoich danych w przeglądarce** — Odoo chowa menu i blokuje dostęp do modelu, mimo że model i widoki istnieją w bazie. To jest niewidoczne podczas testów w shellu, bo shell działa jako superuser, który **ignoruje** reguły dostępu — problem wychodzi na jaw tylko przy testowaniu przez UI jako zwykły użytkownik.

Sygnał w logach że tego brakuje:
```
WARNING mydb odoo.modules.loading: The models ['hello.product'] have no access rules in module hello, consider adding some...
```

### Plik `addons/hello/security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_hello_product,access_hello_product,model_hello_product,base.group_user,1,1,1,1
access_hello_category,access_hello_category,model_hello_category,base.group_user,1,1,1,1
```

### Co znaczy każda kolumna

| Kolumna | Co znaczy |
|---|---|
| `id` | Zewnętrzny identyfikator tej reguły (jak `id` w `<record>` w XML) — wymyślasz sam |
| `name` | Czytelna nazwa reguły, widoczna w Technical → Access Rights. Zwyczajowo taka sama jak `id` |
| `model_id:id` | Którego modelu dotyczy reguła. Składnia: `model_` + nazwa modelu z podkreślnikami zamiast kropek — `hello.product` → `model_hello_product` |
| `group_id:id` | Której grupie użytkowników dotyczy reguła. `base.group_user` = standardowa grupa "zwykły zalogowany użytkownik" (Internal User) |
| `perm_read` | Czy grupa może **czytać** rekordy (1 = tak, 0 = nie) |
| `perm_write` | Czy może **edytować** istniejące rekordy |
| `perm_create` | Czy może **tworzyć** nowe rekordy |
| `perm_unlink` | Czy może **usuwać** rekordy |

### W skrócie, co ten plik robi

To lista zasad typu "kto może co robić z danym modelem":
```
hello.product   +  zwykli użytkownicy  →  mogą: czytać, edytować, tworzyć, usuwać
hello.category  +  zwykli użytkownicy  →  mogą: czytać, edytować, tworzyć, usuwać
```

### Dlaczego CSV, nie XML

Jedna z niekonsekwencji Odoo — większość konfiguracji idzie przez XML, ale `ir.model.access` ma osobny, zwarty format CSV, bo to tabela z dużą liczbą powtarzalnych wierszy (każdy moduł zwykle ma wiele takich reguł, jedna na model). Odpowiednik w XML wyglądałby tak (identyczny efekt, więcej pisania):
```xml
<record id="access_hello_product" model="ir.model.access">
    <field name="name">access_hello_product</field>
    <field name="model_id" ref="model_hello_product"/>
    <field name="group_id" ref="base.group_user"/>
    <field name="perm_read">1</field>
    <field name="perm_write">1</field>
    <field name="perm_create">1</field>
    <field name="perm_unlink">1</field>
</record>
```

### Praktyczna uwaga

W realnych modułach produkcyjnych rzadko daje się wszystkim `1,1,1,1` — zwykle różnicuje się uprawnienia (np. sprzedawcy czytają i tworzą, ale nie usuwają; menadżerowie mogą wszystko). To pierwsze miejsce gdzie projektuje się bezpieczeństwo dostępu do danych w module.

### Debugowanie — błąd "Access Error" w przeglądarce

Jeśli widzisz:
```
Access Error: You are not allowed to access [...] records.
```
mimo że dodałeś CSV, sprawdź w shellu czy reguła faktycznie odwołuje się do właściwej grupy:
```python
env['ir.model.access'].search([('name', '=', 'access_hello_product')]).group_id
env.user.groups_id.mapped('name')          # grupy Twojego zalogowanego użytkownika
env.ref('base.group_user').id               # ID grupy "Internal User"
```
Jeśli ID się zgadzają, a błąd nadal się pojawia — to zwykle **stara sesja w przeglądarce**. Hard refresh (`Cmd+Shift+R`) czasem nie wystarcza — wyloguj się i zaloguj ponownie, żeby wyczyścić sesję serwerową, nie tylko cache przeglądarki.

---

## 15. Przyciski akcji w formularzu

### Problem: przyciski wywołują metody bez argumentów

Przyciski w widoku (`<button type="object"/>`) mogą wywołać **tylko** metodę, która:
1. Nie przyjmuje żadnych argumentów poza `self`
2. Zwraca `None`, albo specjalny obiekt typu "akcja" (np. otwarcie innego okna)

Jeśli Twoja istniejąca metoda **wymaga** argumentu:
```python
def apply_discount(self, percent):
    for record in self:
        record.price = record.price * (1 - percent / 100)
```
nie możesz jej podłączyć wprost pod przycisk — XML nie ma mechanizmu na przekazanie `percent` z `<button>`.

### Rozwiązanie: metoda-wrapper

```python
# Wrapper for apply_discount — buttons in views (<button type="object"/>)
# can only call methods with no arguments besides self. Since apply_discount
# requires 'percent', this method hides that argument behind a hardcoded value.
def action_apply_discount_manually(self):
    for record in self:
        record.apply_discount(10)
```

**Konwencja nazewnictwa:** prefiks `action_` na metodach wywoływanych z przycisków w UI to standard w Odoo (nie wymóg techniczny, ale szeroko przyjęta konwencja) — odróżnia "metody do wywołania z przycisku" od metod wewnętrznych jak `apply_discount` czy `_compute_price_with_tax`.

**Alternatywne podejścia**, jeśli `percent` powinien być zmienny, nie zahardkodowany:
- **Wizard (TransientModel)** — przycisk otwiera okienko dialogowe, użytkownik wpisuje wartość, klika "Zastosuj". Częsty wzorzec w realnych modułach (np. "Zarejestruj płatność" na fakturach)
- **Dodatkowe pole na formularzu** — np. `discount_percent = fields.Float(default=10)`, a metoda czyta wartość z `record.discount_percent` zamiast hardkodować

### Dodanie przycisku w widoku formularza

```xml
<record id="view_hello_product_form" model="ir.ui.view">
    <field name="name">hello.product.form</field>
    <field name="model">hello.product</field>
    <field name="arch" type="xml">
        <form>
            <!-- Kontener na przyciski akcji, renderowany jako pasek NAD <sheet>.
                 Standardowe miejsce w Odoo na przyciski typu "Confirm", "Cancel",
                 "Apply Discount" — analogicznie do paska narzędzi -->
            <header>
                <button
                    name="action_apply_discount_manually"
                    string="Apply 10% Discount"
                    type="object"
                    class="btn-primary"/>
            </header>
            <sheet>
                <field name="name"/>
                <field name="price"/>
                <field name="price_with_tax" readonly="1"/>
                <field name="category_id"/>
                <field name="active"/>
            </sheet>
        </form>
    </field>
</record>
```

| Atrybut przycisku | Co robi |
|---|---|
| `name="action_apply_discount_manually"` | Nazwa metody Pythona do wywołania — **musi** dokładnie zgadzać się z nazwą metody w `product.py` |
| `string="Apply 10% Discount"` | Tekst widoczny na przycisku w UI |
| `type="object"` | Wywołaj metodę na obiekcie modelu — czyli na konkretnym rekordzie aktualnie otwartym w formularzu. Najczęstszy typ (istnieje też `type="action"` dla wywołania innej akcji) |
| `class="btn-primary"` | Standardowa klasa Bootstrapa (Odoo używa Bootstrapa pod spodem) — wyróżnia przycisk kolorem |

### Dlaczego przycisk w `<form>`, nie w `<tree>`

Przycisk **operuje na jednym, konkretnym rekordzie** — `self` wewnątrz wywołanej metody to ten jeden rekord aktualnie otwarty w formularzu. W widoku `<tree>` (lista) nie ma tego jednoznacznego kontekstu — patrzysz na wiele rekordów naraz, więc "kliknięcie przycisku" nie miałoby oczywistego znaczenia (który rekord ma dostać akcję?).

Zasada: **przycisk zawsze operuje na konkretnym rekordzie, nigdy na całej tabeli w sposób niejednoznaczny**. Odoo wspiera też przyciski w `<tree>` (renderowane jako kolumna, jeden przycisk per wiersz), ale koncepcyjnie to wciąż "jeden rekord", tylko inaczej osadzony wizualnie.

Po dodaniu przycisku — upgrade i test:
```python
env['ir.module.module'].search([('name', '=', 'hello')]).button_immediate_upgrade()
```
Otwórz formularz produktu w przeglądarce, kliknij przycisk, sprawdź czy `price` spadło o 10% i czy `price_with_tax` przeliczyło się automatycznie (dzięki `@api.depends`).

---

## 16. XML-RPC — dostęp do Odoo z zewnątrz

### Po co to istnieje

Do tego momentu pracowałeś z Odoo z **wewnątrz** — przez shell (gdzie `env` jest gotowe od razu) albo przez UI w przeglądarce. XML-RPC to **trzeci, zupełnie inny kanał**: pozwala napisać **osobny skrypt Pythona** (poza Dockerem, na swoim komputerze), który łączy się z Odoo przez sieć, tak jak zrobiłaby to inna, niezależna aplikacja.

Odoo **nie ma natywnego REST API** — XML-RPC (starszy protokół, ale wbudowany w każdą instalację Odoo) jest jedynym wbudowanym sposobem na programistyczny dostęp z zewnątrz, bez pisania własnych kontrolerów HTTP.

### Dwa rodzaje danych logowania — nie pomyl ich

| | PostgreSQL (kontener `db`) | Odoo (kontener `web`) |
|---|---|---|
| Skąd pochodzi | `POSTGRES_USER`/`POSTGRES_PASSWORD` z `docker-compose.yml` | Email/hasło, które **Ty** wpisałeś w formularzu przy tworzeniu bazy `mydb` na `localhost:8069` |
| Kto tego używa | Tylko Odoo, wewnętrznie, łącząc się z bazą — Ty tego nigdy nie wpisujesz osobiście | Ty — logując się w przeglądarce ALBO w skrypcie XML-RPC |
| Czy potrzebne do XML-RPC | Nie | **Tak — to jest `username`/`password` w skrypcie** |

Jeśli nie pamiętasz loginu/hasła do Odoo (nie do Postgresa!), sprawdź w shellu:
```python
env['res.users'].search([]).mapped('login')   # lista loginów (zwykle e-maile)
```
Hasła nie da się odczytać (zahaszowane), ale można je zresetować:
```python
user = env['res.users'].search([('login', '=', 'twoj_login_z_listy')])
user.write({'password': 'nowe_haslo_testowe'})
```

### Struktura skryptu

```python
import xmlrpc.client

url = 'http://localhost:8069'
db = 'mydb'                      # nazwa bazy — tej samej, którą widzisz w `odoo shell -d mydb`
username = 'twoj_email@example.com'
password = 'twoje_haslo'

# Krok 1: autoryzacja — osobny endpoint tylko do logowania
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

# Krok 2: operacje na modelach — przez endpoint 'object'
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

products = models.execute_kw(
    db, uid, password,
    'hello.product', 'search_read',
    [[]],
    {'fields': ['name', 'price']}
)
print(products)
```

### Rozbicie elementów

| Element | Co robi |
|---|---|
| `xmlrpc.client.ServerProxy(...)` | Standardowa klasa z biblioteki Pythona `xmlrpc.client` (nic do `pip install`) — "zdalny obiekt" wskazujący na endpoint serwera |
| `/xmlrpc/2/common` | Endpoint **tylko do autoryzacji** — `authenticate()` zwraca `uid`, numer Twojego użytkownika, potrzebny do każdego dalszego wywołania |
| `/xmlrpc/2/object` | Endpoint do **wszystkich operacji na modelach** |
| `execute_kw(db, uid, password, model, method, args, kwargs)` | Uniwersalna funkcja wywołująca dowolną metodę ORM: `search`, `create`, `write`, `unlink`, nawet Twoje własne metody jak `apply_discount` |

### Czemu to wygląda inaczej niż ogólna dokumentacja `xmlrpc.client`

Ogólna dokumentacja biblioteki Pythona pokazuje serwery, które rejestrują **dowolną, własną** metodę pod dowolną nazwą (`proxy.is_even(3)`, `proxy.today()`) — każdy serwer XML-RPC sam decyduje co udostępnia. Odoo poszło inną drogą: udostępnia tylko **dwie uniwersalne** metody (`authenticate`, `execute_kw`), gdzie `execute_kw` działa jako "dyspozytor" do całego ORM, zamiast mieć osobną zdaloną funkcję na `search`, osobną na `create` itd.

| Ogólny XML-RPC (dokumentacja Pythona) | Konkretna implementacja Odoo |
|---|---|
| `proxy.nazwa_wlasnej_metody(argumenty)` | `proxy.execute_kw(db, uid, password, model, orm_metoda, args)` |
| Serwer może zarejestrować cokolwiek | Odoo rejestruje tylko 2 generyczne metody |

Mechanizm `ServerProxy` jest identyczny w obu przypadkach — różni się tylko to, co konkretny serwer (tu: Odoo) zdecydował udostępnić pod tym protokołem.

### Porównanie z shellem — ten sam ORM, inny kanał dostępu

| Shell | XML-RPC |
|---|---|
| `env['hello.product'].search([])` | `models.execute_kw(db, uid, password, 'hello.product', 'search', [[]])` |
| `env['hello.product'].create({'name': 'X'})` | `models.execute_kw(db, uid, password, 'hello.product', 'create', [{'name': 'X'}])` |
| Wewnątrz kontenera, jako superuser (ignoruje uprawnienia) | Z dowolnego miejsca z dostępem sieciowym do portu 8069, jako zwykły zalogowany user (**uprawnienia z `ir.model.access.csv` mają zastosowanie**) |

### Wywołanie własnej metody przez XML-RPC

```python
models.execute_kw(
    db, uid, password,
    'hello.product', 'apply_discount',
    [[1], 15]   # [lista ID rekordów], argument metody (percent=15)
)
```
To wywołuje `apply_discount(15)` na rekordzie o `id=1` — ta sama metoda z `product.py`, wywołana z zewnątrz, bez dostępu do kontenera Docker.

### Praktyczny scenariusz użycia

```
Twoja aplikacja (np. FastAPI, osobny serwer)
        │
        │  XML-RPC (przez sieć, port 8069)
        ▼
   Odoo (baza klientów, faktur, produktów)
```
Typowy przypadek: klient robi zamówienie w Twojej aplikacji → ta aplikacja przez XML-RPC **tworzy** rekord w Odoo → inny zespół (np. księgowość) widzi to natychmiast w swoim interfejsie Odoo, bez ręcznego przepisywania danych między systemami.

---

## 17. Mentalny model całości

```
Twój komputer                          Kontener Odoo
─────────────────                      ──────────────
addons/hello/          ──(volume)──►   /mnt/extra-addons/hello/
config/odoo.conf       ──(volume)──►   /etc/odoo/odoo.conf

Ty piszesz kod .py  →  Odoo go importuje  →  rejestruje model w bazie  →  ORM daje
                                                                          create/search/write/unlink
```

Odoo to gotowa aplikacja (jak WordPress) — nie bibliotekę którą importujesz w swoim skrypcie. Dopisujesz do niej moduły, które Odoo samo integruje z bazą danych, HTTP i UI.

### Pełny łańcuch: od pliku na dysku do kliknięcia w przeglądarce

```
Python (models/*.py)              XML (views/*.xml)            CSV (security/*.csv)
       │                                  │                            │
       ▼                                  ▼                            ▼
  rejestruje model              rejestruje widoki              rejestruje uprawnienia
  w bazie (ir.model)             (ir.ui.view) i akcję           (ir.model.access)
       │                         (ir.actions.act_window)               │
       │                                  │                            │
       └──────────────┬───────────────────┴────────────────────────────┘
                       ▼
              wszystko ładowane przez __manifest__.py:
              - .py przez import w __init__.py (przy starcie/restart)
              - .xml/.csv przez listę 'data' (TYLKO przy install/upgrade)
                       │
                       ▼
        menuitem (klik użytkownika w pasku górnym)
                       │
                       ▼
        action (mówi: jaki model, jakie widoki, w jakiej kolejności)
                       │
                       ▼ (Odoo automatycznie dociąga dane — search() w tle)
                       │
              widok renderuje dane (tree = lista, form = jeden rekord)
                       │
                       ▼
              CSS/JS/HTML generowane automatycznie przez silnik Odoo —
              nigdy nie piszesz tego ręcznie dla podstawowego CRUD
```

Kluczowa zasada filozofii Odoo: **deklarujesz "co", framework sam decyduje "jak"**. To różni się od pisania własnego backendu (np. FastAPI + React), gdzie piszesz każdy krok explicite. W zamian za mniejszą kontrolę i przejrzystość, dostajesz kompletny, działający interfejs administracyjny (lista + formularz + uprawnienia) z minimalną ilością kodu.