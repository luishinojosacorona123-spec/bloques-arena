# Bloques Arena

Proyecto de Unidad 3: infraestructura y despliegue de un juego de bloques descendentes, inspirado en la mecánica de Tetris. Adaptación de Nebula Arena a duelos de **dos jugadores**, con bot, espectadores y servidor autoritativo.

## Inicio rápido

En Windows, extrae el ZIP y ejecuta **INICIAR_JUEGO.cmd**. Necesitas Python 3.11 o superior e Internet para instalar dependencias. El navegador abre http://localhost:7654. Si abre antes de que arranque el servidor, recarga la página.

En una terminal, desde esta carpeta:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r server\requirements.txt
cd server
..\.venv\Scripts\python server.py
```

Abre http://localhost:7654. Selecciona contra bot para jugar solo. Para un duelo, elige duelo en dos pestañas; para observar, usa una tercera pestaña en modo espectador. Cada proceso aloja una partida. Salgan ambos y esperen tres segundos para reiniciar en local. Las flechas mueven/rotan y Espacio deja caer. Los botones también permiten jugar con pantalla táctil. Al completar 2, 3 o 4 líneas se envían 1, 2 o 3 líneas de basura al rival. Termina cuando alguien llena el tablero. La puntuación por 1/2/3/4 líneas es 100/300/500/800 multiplicada por el nivel calculado después del borrado. No implementa hold, T-spins ni reglas SRS completas.

## Qué se entregó y qué evidencia falta

Consulta primero [la actualización de evidencias](docs/EVIDENCIAS_ACTUALIZADAS.md) para los
resultados posteriores de Docker, Terraform, carga, video y entrenamiento. La tabla siguiente
resume el estado del reporte técnico original.

| Solicitud del material | Implementación | Estado verificable |
|---|---|---|
| 3.1 IA y dimensionamiento | Bot heurístico ejecutable, entorno Gymnasium y entrenamiento PPO CPU/CUDA, benchmark | Heurística medida. PPO y GPU pendientes de ejecución |
| 3.2 CI/CD | GitHub Actions prueba, publica dos imágenes y cambia la plantilla de la flota | Workflow escrito; falta repositorio remoto, variables, WIF y ejecución verde |
| 3.3 Contenedores/Agones | Dockerfiles, Fleet, SDK Ready/Health/Shutdown, asignación | Servidor local probado; Docker y clúster pendientes |
| 3.4 Escalado/carga | FleetAutoscaler, autoescalado GKE, Locust, PodMonitor, Grafana | Muestra local 2 jugadores y hasta 500 espectadores de estado. Rampa/pico de 1000 y HLS pendientes |
| 3.5 Serverless | API privada Cloud Run + Firestore, SQLite local, resultados idempotentes | API local probada; URL y concurrencia Cloud Run pendientes |
| 3.6 IaC | Red, IAM, GKE, registro, Firestore, Cloud Run; Agones en segundo estado | Archivos preparados; validate/plan/apply/destroy reales pendientes |
| Reporte | PDF de seis páginas con arquitectura, mediciones y límites | Incluido |
| Exposición de diez minutos | Presentación y guion | Incluidos; demostración de escalado requiere nube |

**No hay capturas de nube, pipeline verde ni facturación inventados.** `evidence/` conserva pruebas y mediciones locales reales. Las plantillas necesitan tu proyecto, direcciones CIDR y SHA de imágenes. El prototipo no incluye un matchmaking público, autenticación de jugadores, TLS frontal ni persistencia/reconexión de partidas; la asignación la realiza el operador/Locust como en el laboratorio del material. En Internet, añade gateway TLS, tickets firmados y validación de identidad antes de habilitar acceso público. En local no envíes datos sensibles.

## Estructura

```text
server/        Juego, cliente web, métricas, pruebas, Dockerfile
ai/            Bot medido y entrenamiento PPO opcional
infra/         Terraform base y segundo estado Agones
k8s/           Fleet, asignación, autoescalador, PodMonitor
serverless/    API de clasificación y pruebas
loadtest/      Locust jugadores, espectadores, resultados y HLS
observability/ Dashboard Grafana y consultas
evidence/      Resultados locales y captura del juego
docs/          Laboratorio, autoevaluación y guion
.github/       Pipeline CI/CD
```

## Pruebas reproducibles

```powershell
.venv\Scripts\python -m pip install pytest flask
cd server
..\.venv\Scripts\python -m pytest -q
cd ..\serverless
..\.venv\Scripts\python -m pytest -q
cd ..
.venv\Scripts\python ai\benchmark.py
.venv\Scripts\python loadtest\local_probe.py
```

La validación realizada usó Python 3.12.14 en Windows 11. Registra las dependencias reales con `pip freeze` antes de comparar ejecuciones. El proyecto declara rangos compatibles, no un lockfile reproducible entre plataformas. Consulta `docs/LABORATORIO.md` para nube, entrenamiento, monitoreo, costos y limpieza.

## Fuentes

Material proporcionado: Unidad 3, Infraestructura y despliegue, octubre 2026, 49 páginas PDF. Secciones 3.1 a 3.6 y proyecto integrador, páginas físicas 45 a 47 para entregables/rúbrica/autoevaluación.

- Agones, SDK y flotas: https://agones.dev/site/docs/guides/client-sdks/ y https://agones.dev/site/docs/reference/fleet/
- Agones, buffer: https://agones.dev/site/docs/reference/fleetautoscaler/
- Cloud Run, identidad entre servicios: https://cloud.google.com/run/docs/authenticating/service-to-service
- Tarifas y calculadora: https://cloud.google.com/compute/all-pricing y https://cloud.google.com/products/calculator
- GKE: https://cloud.google.com/kubernetes-engine/pricing
- Cloud Run: https://cloud.google.com/run/pricing

Consulta técnica realizada el 9 de noviembre de 2026. Los costos del reporte son escenarios de cálculo con tarifas supuestas, no cotizaciones.
