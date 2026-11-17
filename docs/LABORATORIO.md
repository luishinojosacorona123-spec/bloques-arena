# Prácticas 3.1 a 3.6 adaptadas

## 3.1 Cómputo para IA

La IA decide una colocación por pieza. El bot que funciona en el juego explora rotaciones y columnas, recompensa líneas y penaliza altura, huecos e irregularidad. Es una línea base heurística, sin entrenamiento. `ai/train.py` proporciona un entorno de bloques real para PPO con 40 acciones (4 rotaciones x 10 columnas), observación de tablero y piezas y límite de 1000 pasos por episodio. Este agente es experimental y no se sirve en el juego. Evalúa rendimiento y calidad antes de sustituir la heurística.

En un entorno separado o Colab, instala `ai/requirements.txt` y ejecuta:

```bash
python ai/train.py --device cpu --steps 100000
python ai/train.py --device cuda --steps 100000
```

CUDA requiere GPU/controlador/PyTorch compatibles. Guarda cada salida JSON, hardware, versión de PyTorch y consumo de GPU. Repite tres veces por dispositivo con el mismo presupuesto de pasos; compara media y dispersión y evalúa líneas por partida con semillas que no se usaron al entrenar. Una red pequeña puede entrenar más rápido en CPU. CPU basta para la heurística; GPU es una opción de entrenamiento PPO, TPU solo justificaría una migración a JAX/TensorFlow a mayor escala. Spot sirve para entrenamiento con checkpoints, mientras que las partidas deben usar nodos bajo demanda.

| Medida | CPU heurística | PPO CPU | PPO GPU |
|---|---|---|---|
| Tiempo de entrenamiento | No aplica | Pendiente | Pendiente |
| Latencia inferencia | Ver evidence/bot_local.json | Pendiente | Pendiente |
| Decisiones/s | Ver evidencia | Pendiente | Pendiente |
| Costo/h | Equipo local, no facturación cloud | Cotizar VM CPU | Cotizar VM GPU |

Dimensionamiento exigido: decisiones/s = 2000 x 10 = 20000. vCPU = techo(20000 / capacidad medida por núcleo x 1.30). La salida del benchmark calcula esta cifra como **extrapolación**. Medir un proceso en laptop no equivale a medir una vCPU GKE. El juego usa un bot cada 1.5 s (0.667 Hz), de modo que 10 Hz es un escenario didáctico más exigente. Evita inferir en todos los ticks si no hay pieza nueva.

## 3.3 Docker y Agones

```bash
docker build -t bloques-server:local server
docker run --rm -p 7654:7654 bloques-server:local
curl http://localhost:7654/health
curl http://localhost:7654/metrics
```

Docker necesita su motor activo. Para nube, prepara primero el proyecto y registro mediante 3.6. La flota usa un puerto TCP dinámico del host entre 7000 y 8000, dirigido al 7654 del contenedor. HTTP y WebSocket comparten ese puerto. Cada servidor aloja dos jugadores humanos o uno y un bot. El cliente está en `/`, el juego en `/ws` y métricas en `/metrics`.

Agones recibe `/ready`, `/health` y `/shutdown`; la asignación la hace `GameServerAllocation`, no el navegador. El servidor termina cuando todos los jugadores han salido durante tres segundos. Los espectadores no lo mantienen vivo. Una partida ya terminada conserva el estado hasta que salgan los jugadores. Borrar un pod Allocated o perder un nodo interrumpe la partida porque el estado solo está en memoria; el drenado protege despliegues normales, no fallos físicos. La recuperación persistente queda fuera del prototipo.

Después de aplicar flota y autoscaler:

```bash
kubectl get gameservers
kubectl create -f k8s/allocation.yaml -o yaml
kubectl get gameservers
```

Obtén `status.address` y `status.ports[name=game].port` de la asignación. Abre `http://DIRECCION:PUERTO` en dos navegadores para la misma partida. Es un endpoint de laboratorio HTTP sin TLS.

## 3.2 CI/CD

Sube el contenido de este directorio a la raíz de un repositorio GitHub. Configura Workload Identity Federation para GitHub con restricciones por repositorio/rama. Cuenta CI: `roles/artifactregistry.writer`. Cuenta de despliegue: permisos GKE de acceso y RBAC en namespace default para get/list/watch/create/update/patch de Fleets, FleetAutoscalers y ServiceAccounts. Para cambiar Cloud Run, agrega `roles/run.developer` y `roles/iam.serviceAccountUser` sobre su cuenta de servicio. No uses llaves JSON.

Variables del repositorio: `WIF_PROVIDER`, `CI_SERVICE_ACCOUNT`, `DEPLOY_SERVICE_ACCOUNT`, `GCP_PROJECT`, `LEADERBOARD_URL`. Configura un runner Linux propio con etiquetas `self-hosted, linux, bloques-deploy`, kubectl y plugin GKE, dentro de `admin_cidrs`. Configura aprobación en el entorno GitHub `production`. La primera publicación puede hacerse con producción pendiente; aplica Terraform y Agones antes de aprobar el despliegue.

El workflow prueba servidor y API, publica imágenes por SHA y actualiza la Fleet. Agones drena servidores asignados durante el rolling update. El control de disponibilidad de la flota requiere inspección de `kubectl get fleet,gameservers` y métricas. El workflow aún no implementa promoción canary ni puerta automática por latencia. Para producción: staging, smoke de 200 usuarios con flota suficiente, canary a 10% de nuevas asignaciones, 30 min de observación y promoción si p95 <80 ms y errores <0.5%. Para rollback, reaplica el SHA anterior en la plantilla; las partidas actuales terminan con su versión. Conserva evidencia de cada etapa.

## 3.4 Métricas y carga

Instala kube-prometheus-stack para Prometheus, Grafana y kube-state-metrics:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install observability prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f k8s/prometheus-values.yaml
kubectl apply -f k8s/podmonitor.yaml
kubectl -n monitoring port-forward svc/observability-grafana 3000:80
```

Obtén la contraseña del Secret creado por Helm e importa `observability/grafana.json`. Selecciona tu datasource Prometheus. Para estados Agones, habilita y scrapea métricas de su controlador con ServiceMonitor según la versión instalada; el panel de estados muestra No data hasta ese paso. Verifica `/metrics` del controlador y las etiquetas antes de interpretar los estados. No confundas número de pods con GameServers Ready/Allocated.

Tres capas: FleetAutoscaler conserva servidores Ready, Cluster Autoscaler agrega nodos si los pods no caben y Cloud Run escala instancias de la API. No se incluye HPA de matchmaking porque no hay un Deployment de matchmaking. Si se añade, su HPA ajustaría réplicas por CPU/cola y necesitaría estado de cola externo. En este laboratorio el script asignador cumple esa función operativa.

**1000 jugadores** implican 500 partidas y techo(500/0.8) = 625 GameServers con buffer Agones de 20% del total. El límite de la plantilla es 650; el clúster permite hasta 20 nodos y debe disponer de cuota y capacidad medidos. Los requests son iniciales, no una garantía de densidad. `allocate.py` falla si no encuentra un servidor Ready; reserva lotes y espera el escalado, o incrementa temporalmente el mínimo antes del ensayo. Al preasignar todo, la rampa mide conexiones pero no asignaciones bajo demanda: para medir el escalado, lanza lotes crecientes durante la prueba y registra ambos tiempos por separado. No uses el modo bot para simular usuarios humanos.

```bash
pip install -r loadtest/requirements.txt
python loadtest/allocate.py --matches 500 --output endpoints.json
# PowerShell: $env:ENDPOINTS='endpoints.json'; $env:SCENARIO='ramp'
# Bash: export ENDPOINTS=endpoints.json SCENARIO=ramp
locust -f loadtest/locustfile.py --headless --csv evidence/ramp
```

Repite con `SCENARIO=spike`, reseteando la flota y endpoints entre escenarios (se pueden eliminar servidores de la prueba solo cuando no hay jugadores). Para 500 espectadores de estado usa `SCENARIO=spectators` y un endpoint con una partida activa. Para la API usa `SCENARIO=scores`, un ID token con audiencia correcta en `TOKEN` y `--host URL_CLOUD_RUN`. No distribuyas un mismo archivo de endpoints entre workers: particiónalo, dos plazas por partida.

Para video HLS usa `video_locust.py` con un origen/CDN propio que sirva una media playlist de segmentos de 2 s a 1 Mbps. Genera un video sintético autorizado con FFmpeg (`testsrc2`, H.264, `-b:v 1M -g 60`, HLS tiempo 2) y publícalo en tu almacenamiento/CDN. No se incluye un origen HLS ni su infraestructura en este paquete. Ejecuta 500 usuarios solo tras revisar costo/ancho de banda. Los espectadores WebSocket de la prueba local reciben tableros, no video; no validan startup, rebuffering ni glass-to-glass.

```bash
locust -f loadtest/video_locust.py --headless -u 500 -r 10 -t 5m --host https://TU_CDN --csv evidence/hls
```

Registra CCU, RTT p50/p95/p99, tick p99, lag del bucle, errores, CCV, Ready/Allocated, pods y nodos. Para tick p99 usa `histogram_quantile(0.99,sum by(le)(rate(bloques_tick_seconds_bucket[5m])))`. El tiempo de trabajo del tick no incluye todo el retraso de planificación: mide también `bloques_loop_lag_seconds`. Criterios: RTT p95 <80 ms, tick p99 <25 ms para 20 Hz y sesiones fallidas <0.5%. Genera CSV por escenario; guarda hardware y configuración del generador.

Tiempo de reacción = timestamp del primer nuevo servidor Ready menos timestamp en que cayó el buffer. Añade tiempo hasta nodo Ready cuando hubo pods Pending. Capacidad máxima: último escalón de carga sostenida que cumple todos los SLO, con repeticiones, no el mayor número de sockets que abrió el cliente. Con cuatro niveles y 30 RTT por nivel, la muestra local solo identifica un límite preliminar del fanout.

Video extrapolado: GB/h = CCV x kbps x 3600 / 8,000,000. A 500 espectadores y 1000 kbps son 225 GB/h y 18.75 GB en 5 min. A 20000 y 6000 kbps, 54000 GB/h = 54 TB/h decimales. La extrapolación estima transferencia, no prueba que el sistema soporte esa carga.

## 3.5 Tabla de líderes

```bash
pip install flask
python serverless/main.py
```

En otra terminal: POST `http://127.0.0.1:8080/score` con `{"match":"demo1","player":"ana","score":1200}` y GET `/top`. El POST valida tipos/rangos y deduplica por (partida,jugador); `/top` clasifica los diez mejores resultados individuales. La API local usa SQLite y se limita a loopback. Cloud Run usa Firestore y no tiene binding `allUsers`; necesita identidad de servicio e ID token. La cuenta del servidor obtiene `run.invoker` vía Workload Identity. Tras acabar la partida, el servidor envía puntos calculados por él, usando su ID efímero de jugador; no implementa perfiles persistentes. `LEADERBOARD_URL` habilita ese envío. El cliente web aún no presenta la clasificación.

Los reintentos en la misma instancia no duplican resultados. La cola está en memoria; un fallo del pod puede perder resultados no enviados. Para producción se requiere un outbox durable. La métrica de concurrencia de Cloud Run y p99 deben medirse en nube con 80% GET y 20% POST, incluyendo un arranque desde cero.

## 3.6 Terraform y limpieza

Necesitas proyecto facturable, permisos, cuotas GKE/Compute, Terraform >=1.6, gcloud autenticado, kubectl y Helm. Reserva CIDR sin solapamientos y verifica la versión Agones 1.62.0 contra GKE antes de aplicar. La infraestructura usa dos estados para instalar Agones después de existir GKE.

1. Crea un bucket GCS de estado con nombre único, control uniforme, versionado y bloqueo por Terraform. Es un recurso bootstrap fuera del estado. Crea una alerta de presupuesto según tu límite.
2. Copia `infra/terraform.tfvars.example` a `infra/terraform.tfvars`. Cambia proyecto, CIDR de pruebas/admin e imagen. No publiques credenciales, tfvars ni estado.
3. Ejecuta `terraform -chdir=infra init -backend-config="bucket=TU_BUCKET" -backend-config="prefix=dev/base"`.
4. Ejecuta fmt y validate. Para romper la dependencia inicial del registro y la imagen, crea solo `google_artifact_registry_repository.images` y sus APIs con un plan bootstrap dirigido: `terraform -chdir=infra plan -target=google_artifact_registry_repository.images -out=bootstrap.tfplan`, revísalo y aplica ese plan. Es una excepción inicial; las siguientes aplicaciones deben usar el plan completo.
5. Construye/publica ambas imágenes en `us-central1-docker.pkg.dev/PROYECTO/bloques/server:SHA` y `.../leaderboard:SHA`. Actualiza la variable de la imagen serverless.
6. `terraform -chdir=infra fmt -recursive`, `terraform -chdir=infra validate`, `terraform -chdir=infra plan -out=plan.tfplan`, revisión por PR y `terraform -chdir=infra apply plan.tfplan`.
7. `gcloud container clusters get-credentials bloques-dev --zone us-central1-a --project PROYECTO`.
8. Inicializa `infra/agones` con el mismo bucket y `prefix=dev/agones`, planifica/aplica con `-var project=PROYECTO`.
9. Reemplaza `REPLACE_PROJECT` y `REPLACE_SHA` en `k8s/fleet.yaml` y `k8s/serviceaccount.yaml`. Si usas otro entorno, ajusta también el nombre de cuenta. Añade `LEADERBOARD_URL` con la salida Terraform en los env de la Fleet. Aplica la cuenta de servicio y `k8s/sdk-rbac.yaml` después de instalar Agones para que su SDK pueda actualizar GameServers. Aplica después la flota y el autoscaler. Instala observabilidad y aplica PodMonitor y ServiceMonitor después de sus CRD.
10. Guarda salida de plan, apply, estados GameServer, métricas y pruebas. Una segunda ejecución de plan sin cambios debe confirmar ausencia de drift.

Para limpiar, confirma que no hay usuarios y elimina FleetAutoscaler, Fleet, PodMonitor y cuenta Kubernetes. Desinstala el stack de monitoreo y sus PVC antes de destruir GKE. Ejecuta **primero** destroy en `infra/agones`, luego en `infra`, revisando planes de destrucción. Vacía/elimina versiones del registro y datos solo si son de este laboratorio y los quieres descartar. El bucket bootstrap de estado, sus versiones, imágenes, logs retenidos y recursos manuales no deben darse por eliminados automáticamente. Revisa inventario y facturación y guarda evidencia de limpieza; conserva el estado remoto hasta confirmar la destrucción. Si ya existe Firestore default o el registro, impórtalos solo si pertenecen a este proyecto de laboratorio, no los borres para resolver conflictos.

## Costos y capacidad

Todos los números monetarios del reporte son **supuestos de ejercicio**, no tarifas verificadas. Cotiza región, moneda y fecha en la calculadora oficial. Costo/h = nodos x tarifa_VM + gestión_GKE + discos + balanceo + logs + API + Firestore + CDN/egress. Costo por jugador-hora = costo_total / CCU medio, con la misma ventana y todos los componentes. Usa CCU medio, no pico, en la división.

Ejemplo aritmético: VM 0.134 USD/h, gestión 0.10 USD/h, otros 0.02 USD/h, tres nodos: 0.522 USD/h sin video. Con 1000 CCU medios, 0.000522 USD por jugador-hora **si esa infraestructura soportara la carga**, lo cual aún no se ha demostrado. A veinte nodos, 2.80 USD/h y 0.00280 por jugador-hora bajo el mismo supuesto. A 0.12 USD/GB supuesto, 54 TB/h de video agregarían 6480 USD/h; CDN no elimina los bytes ni su costo de entrega, aunque reduce carga del origen.

Serverless vs VM, ejemplo supuesto: API con 0.5 vCPU-s y 0.125 GiB-s por solicitud a 10000 solicitudes/mes, tarifas supuestas 0.000024 USD/vCPU-s y 0.0000025 USD/GiB-s, costo de cómputo 0.123125 USD/mes más solicitudes, Firestore y red, sin aplicar créditos. VM de 0.02 USD/h x 730 h = 14.60 USD/mes más disco/red. No compares estos importes como precio final: medir duración y concurrencia cambia el resultado. Cloud Run min=0 reduce inactividad, mientras que min>0 reduce cold starts con costo base.
