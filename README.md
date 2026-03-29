# Tennis Partner Finder AI

Finální verze projektu s hezčím vzhledem a AI matchmakingem.

## Co umí
- formulář s poli:
  - přezdívka
  - město (`Praha`, `Brno`)
  - věk
  - úroveň (`začátečník`, `středně pokročilý`, `pokročilý`, `profesionál`)
  - termín přes kalendář a čas
  - e-mail
- ukládání do SQLite databáze
- hledání spoluhráče podle:
  - stejného města
  - stejné úrovně
  - času v rozmezí ± 60 minut
- AI odpověď:
  - zda byl nalezen spoluhráč
  - datum a hodina
  - úroveň
  - věk
  - email pro kontakt
- pokud nikoho nenajde, napíše že aktuálně nemá nikdo zájem o hru ve stejný čas

## Lokální spuštění
Vytvoř soubor `.env`:

```env
OPENAI_API_KEY=tvuj_token
OPENAI_BASE_URL=https://kurim.ithope.eu/v1
OPENAI_MODEL=gemma3:27b
```

Pak spusť:

```bash
docker compose up --build
```

Aplikace poběží na:
`http://localhost:8081`
