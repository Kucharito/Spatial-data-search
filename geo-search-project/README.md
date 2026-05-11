# Geo Search Project – Spatial Database Object Finder

## 1. Strucny popis
Tento projekt demonstruje ukladanie a dotazovanie priestorovych dat v databazovom systeme PostgreSQL s rozsirenim PostGIS. Aplikacia obsahuje jednoduche REST API vo FastAPI, demo dataset vo formate CSV a jednoduchy frontend s mapou Leaflet na vizualizaciu vysledkov.

## 2. Preco projekt patri do temy "Ulozenie a dotazovanie priestorovych dat v DBS"
Projekt priamo pracuje s geografickymi objektmi reprezentovanymi ako body. V databaze su ulozene nazov, kategoria, adresa, zemepisna sirka, dlzka a priestorovy stlpec `geom` typu `GEOGRAPHY(Point, 4326)`. Projekt ukazuje:

- ulozenie priestorovych objektov v databaze,
- pouzitie PostGIS priestorovych typov,
- vytvorenie priestoroveho GiST indexu,
- import geografickych dat z CSV,
- priestorove dotazy `ST_DWithin`, `ST_Distance`, `ST_Intersects`,
- porovnanie vykonu dotazov s indexom a bez indexu,
- vysvetlenie vztahu medzi GiST indexom a R-tree principom v PostgreSQL,
- jednoduche API a mapove rozhranie na prezentaciu vysledkov.

## 3. Pouzite technologie
- PostgreSQL 16
- PostGIS 3.4
- Docker Compose
- Python 3.x
- FastAPI
- psycopg
- Leaflet
- HTML, CSS, JavaScript

## 4. Architektura projektu
Projekt ma tri hlavne casti:

1. Databaza v Dockeri
   Obsahuje PostgreSQL + PostGIS, tabulku `places` a SQL skripty na inicializaciu a pracu s indexami.
2. Backend vo FastAPI
   Poskytuje API endpointy pre import dat, hladanie najblizsich objektov, radius search, polygon search a benchmark.
3. Frontend v HTML/JS
   Zobrazuje mapu Ostravy, umoznuje kliknut bod na mape a volat API dotazy.

## 5. Struktura projektu
```text
geo-search-project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── schemas.py
│   │   ├── spatial_queries.py
│   │   └── importer.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── db/
│   ├── init.sql
│   ├── indexes.sql
│   ├── drop_indexes.sql
│   └── sample_queries.sql
├── data/
│   └── places.csv
├── docker-compose.yml
└── README.md
```

## 6. Spustenie projektu vo Windows

### 6.1 Spustenie databazy
V koreni projektu spustite:

```powershell
docker compose up -d
```

Databaza bude dostupna na:

- databaza: `geodb`
- pouzivatel: `postgres`
- heslo: `postgres`
- port: `5432`

### 6.2 Nastavenie Python backendu
Prejdite do backend priecinka:

```powershell
cd backend
python -m venv .venv
```

Aktivujte virtualne prostredie vo Windows:

```powershell
.venv\Scripts\activate
```

Nainstalujte zavislosti:

```powershell
pip install -r requirements.txt
```

Vytvorte `.env` subor, napr. skopirovanim z `.env.example`, a nastavte:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geodb
```

Spustite backend:

```powershell
uvicorn app.main:app --reload
```

Swagger dokumentacia bude dostupna na:

```text
http://localhost:8000/docs
```

### 6.3 Import dat
Po spusteni backendu otvorte Swagger UI a spustite endpoint:

```text
POST /import
```

Import nacita lokalny subor `data/places.csv`, vymaze povodny obsah tabulky a vlozi nove zaznamy. Importer je napisany vseobecne, takze mozete nahradit CSV subor inym suborom s rovnakymi stlpcami:

- `name`
- `category`
- `address`
- `latitude`
- `longitude`

### 6.4 Spustenie frontendu
V novom terminali prejdite do priecinka `frontend` a spustite jednoduchy lokalny server:

```powershell
cd frontend
python -m http.server 5500
```

Frontend otvorte na:

```text
http://localhost:5500
```

## 7. Docker setup pre databazu
Projekt pouziva obraz:

```text
postgis/postgis:16-3.4
```

Docker Compose:

- vystavuje port `5432`,
- nastavuje `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
- pouziva named volume `postgres_data`,
- pri prvom spusteni automaticky vykona `db/init.sql`.

## 8. Databazova schema
Tabulka `places`:

- `id SERIAL PRIMARY KEY`
- `name TEXT NOT NULL`
- `category TEXT NOT NULL`
- `address TEXT`
- `latitude DOUBLE PRECISION NOT NULL`
- `longitude DOUBLE PRECISION NOT NULL`
- `geom GEOGRAPHY(Point, 4326) NOT NULL`

Indexy:

- `idx_places_geom_gist` na stlpci `geom`
- `idx_places_category` na stlpci `category`

Typ `GEOGRAPHY(Point, 4326)` je pouzity preto, aby funkcie vzdialenosti vracali presne metre.

## 9. API endpointy

- `GET /` zakladne info o projekte
- `GET /health` kontrola spojenia s databazou
- `POST /import` import CSV dat do tabulky `places`
- `GET /places` zoznam vsetkych miest alebo filtrovanie podla `category`
- `GET /categories` zoznam kategorii
- `GET /places/nearest` najblizsie objekty k zadanemu bodu
- `GET /places/radius` objekty v zadanej vzdialenosti
- `POST /places/in-polygon` objekty vo vnutri polygonu
- `GET /benchmark/nearest` cas vykonania nearest query
- `GET /benchmark/radius` cas vykonania radius query
- `GET /explain/radius` plan dotazu `EXPLAIN ANALYZE`

## 10. Vysvetlenie priestorovych dotazov

### Nearest neighbor
Endpoint `GET /places/nearest` hlada najblizsich `k` objektov k zadanemu bodu. Vzdialenost sa pocita funkciou `ST_Distance`, pricom bod vznikne z dvojice `longitude, latitude` pomocou:

```sql
ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
```

### Radius search
Endpoint `GET /places/radius` vrati vsetky objekty v okruhu `radius_m` metrov od zadaneho bodu. Pouzita je funkcia:

```sql
ST_DWithin(...)
```

Tato funkcia je vhodna aj na demonstrovanie prinosu priestoroveho indexu.

### Polygon search
Endpoint `POST /places/in-polygon` prijme pole suradnic vo formate `[lon, lat]`. Backend polygon automaticky uzavrie, ak prvy a posledny bod nie su rovnake. Na test prieniku sa pouziva:

```sql
ST_Intersects(...)
```

Pripadne by bolo mozne pouzit aj `ST_Contains`.

### Pouzite PostGIS funkcie
- `ST_DWithin` testuje, ci je objekt do urcitej vzdialenosti
- `ST_Distance` vracia presnu vzdialenost v metroch
- `ST_Intersects` testuje, ci bod lezi v polygone alebo sa s nim pretina
- `ST_SetSRID` nastavi SRID 4326
- `ST_MakePoint` vytvori bod z longitude a latitude

### Priestorovy index
Na stlpci `geom` je vytvoreny GiST index:

```sql
CREATE INDEX idx_places_geom_gist ON places USING GIST (geom);
```

Tento index urychluje vyhladavanie kandidatov pri priestorovych dotazoch.

### GiST a R-tree v PostgreSQL
Pri prezentacii je dobre rozlisit dva pojmy:

- `R-tree` je koncept alebo typ stromovej priestorovej indexacnej struktury,
- `GiST` v PostgreSQL je vseobecna indexova metoda, cez ktoru PostGIS realizuje priestorove indexovanie.

Pre prakticke ucely to znamena, ze v PostgreSQL sa pri PostGIS bezne nevytvara samostatny index s nazvom `R-tree`.
Namiesto toho sa vytvori `GiST` index, ktory sa pri priestorovych objektoch sprava ako `R-tree-like` struktura.

Preto je korektne porovnanie v tomto projekte:

- dotaz s GiST priestorovym indexom,
- ten isty dotaz bez priestoroveho indexu.

## 11. Benchmark a porovnanie s/bez indexu
Projekt obsahuje:

- `db/indexes.sql` na vytvorenie indexov
- `db/drop_indexes.sql` na odstranenie indexov
- endpointy `GET /benchmark/nearest` a `GET /benchmark/radius`
- endpoint `GET /explain/radius` pre plan vykonania

Toto benchmarkovanie mozes v texte prace opisat aj ako:

- porovnanie vykonu priestoroveho vyhladavania s GiST indexom,
- porovnanie vykonu bez priestoroveho indexu,
- diskusia, ze GiST v PostgreSQL predstavuje prakticku implementaciu R-tree-like indexovania pre PostGIS.

Odporucany postup testovania:

1. Importujte data a spustite benchmark s indexom.
2. Spustite `db/drop_indexes.sql`.
3. Znova spustite benchmark.
4. Porovnajte `execution_time_ms` a vystup `EXPLAIN ANALYZE`.
5. Nakoniec obnovte indexy pomocou `db/indexes.sql`.

Pri vyhodnoteni si vsimaj hlavne:

- ci planner pouzil index scan alebo bitmap/index-assisted scan,
- ci po odstraneni indexu presiel na sekvencny scan,
- rozdiel v `Execution Time`,
- rozdiel v pocte spracovanych riadkov a bufferov v `EXPLAIN ANALYZE`.

## 12. Demo dataset
Subor `data/places.csv` obsahuje pripraveny testovaci dataset s viac ako 40 zaznamami v okoli Ostravy. Ide o lokalny demo dataset vhodny na prezentaciu a testovanie bez internetoveho pripojenia.

V buducnosti je mozne dataset nahradit realnymi verejnymi datami, napr.:

- export z OpenStreetMap,
- GeoJSON subor,
- CSV z open data portalu,
- manualne pripraveny CSV subor so suradnicami.

Podmienkou je zachovanie stlpcov:

```text
name,category,address,latitude,longitude
```

## 13. Ukazkove SQL dotazy
Subor `db/sample_queries.sql` obsahuje:

1. vypis vsetkych objektov,
2. najblizsich 5 objektov,
3. objekty v okruhu 1000 m,
4. objekty v polygone,
5. `EXPLAIN ANALYZE` pre radius query,
6. poznamku k GiST a R-tree-like indexovaniu,
7. vytvorenie indexu,
8. zmazanie indexu,
9. odporucany benchmark postup.

## 14. Miesto pre screenshoty
Do odovzdania mozete doplnit:

- screenshot Swagger UI,
- screenshot frontend mapy,
- screenshot vysledkov benchmarku,
- screenshot `EXPLAIN ANALYZE`.

## 15. Mozne buduce rozsirenia
- podpora importu GeoJSON
- kreslenie polygonu priamo na mape
- viac datasetov a viac miest
- agregacne priestorove dotazy
- autentifikacia a ukladanie vlastnych vrstiev

## 16. Rychly test projektu

1. Spustite databazu:
   `docker compose up -d`
2. Spustite backend:
   `uvicorn app.main:app --reload`
3. Otvorte:
   `http://localhost:8000/docs`
4. Zavolajte:
   `POST /import`
5. Otestujte:
   `GET /places`
6. Otestujte:
   `GET /places/nearest?lat=49.8209&lon=18.2625&k=5`
7. Spustite frontend:
   `python -m http.server 5500`
8. Otvorte:
   `http://localhost:5500`
