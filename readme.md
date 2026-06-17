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

## 11. Mentalny model całości

```
Twój komputer                          Kontener Odoo
─────────────────                      ──────────────
addons/hello/          ──(volume)──►   /mnt/extra-addons/hello/
config/odoo.conf       ──(volume)──►   /etc/odoo/odoo.conf

Ty piszesz kod .py  →  Odoo go importuje  →  rejestruje model w bazie  →  ORM daje
                                                                          create/search/write/unlink
```

Odoo to gotowa aplikacja (jak WordPress) — nie bibliotekę którą importujesz w swoim skrypcie. Dopisujesz do niej moduły, które Odoo samo integruje z bazą danych, HTTP i UI.