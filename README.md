# Quiniela Mundial 2026 — Tablero público (auto-actualizable)

Página de **solo lectura** que muestra la clasificación de la porra y se **actualiza sola**:
un GitHub Action consulta los resultados reales del Mundial cada 2 horas, reescribe `results.json`,
y la página lo lee en cada carga. Cero mantenimiento una vez configurado.

## Qué hay aquí
- `index.html` — el tablero (predicciones de todos ya incluidas; lee `results.json`).
- `results.json` — resultados reales (lo actualiza el Action; ya viene con los jugados hasta ahora).
- `scripts/fetch_results.py` — baja los resultados de football-data.org y reescribe `results.json`.
- `scripts/fixtures.json` — mapa de partidos y nombres de equipos (no tocar).
- `.github/workflows/update.yml` — corre el fetch cada 2 horas.

## Configuración (una sola vez, ~15 min)
1. Crea una cuenta gratis en GitHub (si no tienes) y un repositorio **público** nuevo, p. ej. `quiniela-2026`.
2. Sube TODOS estos archivos respetando las carpetas (`scripts/…` y `.github/workflows/…`).
   La forma más fácil de conservar carpetas es con **GitHub Desktop** (arrastras la carpeta `quiniela-github` completa).
3. Consigue un token gratis de la API de resultados: regístrate en
   https://www.football-data.org/client/register (te llega por correo).
4. En el repo: **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `FOOTBALL_DATA_TOKEN`
   - Secret: (pega tu token)
5. Activa la web: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
   En ~1 min te da la URL pública: `https://TU-USUARIO.github.io/quiniela-2026/`
6. (Opcional) Corre el Action ya: pestaña **Actions → "Update results" → Run workflow**.

Comparte esa URL por WhatsApp. Funciona en celular y se actualiza sola.

## Notas
- Si el fetch llegara a fallar, la página muestra los últimos resultados guardados (no se rompe).
- Por ahora se auto-actualiza la **fase de grupos**. Las eliminatorias se pueden agregar después.
- Si algún equipo no empata por diferencia de nombre en la API, avísame y ajusto el mapa de alias.
