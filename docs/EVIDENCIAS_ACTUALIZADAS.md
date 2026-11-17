# Bloques Arena · actualización de evidencias

11 de noviembre de 2026. Resultados de laboratorio posteriores al reporte técnico original.

Docker ejecutó las imágenes del juego y la API. Ambos endpoints de salud respondieron. Terraform 1.13.5 validó ambos módulos con los proveedores instalados. Las salidas están en `evidence/docker_local.txt` y `evidence/terraform_validate.txt`.

Agones 1.62 asignó el servidor `bloques-fleet-zf5qx-7cq6c`. El manifiesto de la flota se corrigió para usar maxUnavailable=1, el mínimo que acepta esta versión.

Agones en kind pasó de 3 a 4 servidores. Tiempo observado tras el lote de asignaciones hasta un servidor Ready: 29.78 s. La prueba usó un nodo local. El autoescalado de nodos de GKE sigue pendiente.

La partida asignada recibió dos conexiones, una acción de caída y un ping. El endpoint de métricas registró dos jugadores. Se verificó el tablero Bloques Arena con siete paneles en Grafana y la métrica de estados de Agones en Prometheus. Para la demostración local, el nodo del laboratorio puede arrancarse con `docker start bloques-eval-control-plane` y el kubeconfig existente en `work/bloques.kubeconfig`.

## Jugadores por WebSocket

El generador y las 500 salas compartieron un proceso. Cada nivel midió cuatro tandas de eco por jugador. El RTT incluye colas del generador y servidor. CCU es la cantidad activa al final de la ventana.

| Escenario | Jugadores objetivo | CCU observado | RTT p95 (ms) | Fallos de eco | Fallos al conectar |
|---|---:|---:|---:|---:|---:|
| rampa | 100 | 100 | 587.98 | 0 | 0 |
| rampa | 300 | 300 | 1599.46 | 0 | 0 |
| rampa | 600 | 600 | 3514.47 | 0 | 0 |
| rampa | 1000 | 294 | 1752.1 | 2824 | 0 |
| pico | 100 | 100 | 596.46 | 0 | 0 |
| pico | 1000 | 612 | 4280.72 | 1552 | 0 |

El ensayo local no cumple el objetivo de RTT p95 menor a 80 ms. La capacidad de una flota distribuida queda por medir.

La gráfica de esta prueba está en `evidence/ccu_rtt_local.png`.

## Espectadores y clasificación

Los 500 clientes HLS realizaron 500 solicitudes de lista y 1500 de segmentos, con 0 errores. El p95 de segmentos fue 3512.83 ms. Se sirvió un clip sintético de seis segundos en memoria. El generador utilizó hasta 100 conexiones HTTP y no mide tiempos de un reproductor real.

A 20,000 espectadores, el bitrate medido del clip extrapola 9,175.15 GB/h. A 6 Mbps, el escenario del reporte da 54,000 GB/h. Ambas cifras son proyecciones de tráfico.

La API Docker con SQLite atendió 2500 solicitudes de 500 usuarios virtuales, 80% GET y 20% POST. Hubo 2 errores y un p99 de 26229.69 ms. La prueba detectó bloqueos de SQLite. Se corrigieron la inicialización del esquema y el cierre de las conexiones y se activó WAL. Aún falta repetir el escenario con Cloud Run y Firestore.

## Entrenamiento PPO

Entrenamiento CPU: 686.19 s. Inferencia media: 1.4553 ms, 687.1 decisiones/s. La medición usa 1,000 predicciones en CPU. El juego conserva el bot heurístico. El equipo tiene una Radeon 660M y no dispone de CUDA para el ensayo GPU.

## Evidencias que requieren acceso externo

- Google Cloud con facturación y permisos para GKE, Artifact Registry, Cloud Run y Firestore. Aplicar y destruir Terraform en ese proyecto, registrar costos y medir escalado de nodos y concurrencia de Cloud Run.
- Repositorio GitHub con sesión iniciada, Workload Identity Federation y runner autorizado. Publicar el código y obtener una ejecución verde del pipeline con despliegue.
- Repetir rampa, pico y HLS contra la infraestructura desplegada y mostrar su escalado durante la exposición.
- Ejecutar el entrenamiento con CUDA para la comparación CPU/GPU de la práctica 3.1.

Fuentes de instalación: [kind](https://kind.sigs.k8s.io/docs/user/quick-start/), [Agones](https://agones.dev/site/docs/installation/install-agones/yaml/) y [Terraform](https://developer.hashicorp.com/terraform/install).
