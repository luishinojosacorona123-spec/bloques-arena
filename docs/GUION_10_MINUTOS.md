# Exposición de diez minutos

| Diapositiva | Tiempo | Explicación y demostración |
|---|---|---|
| 1. Bloques Arena | 0:00-0:40 | Presentar el objetivo: adaptar despliegue y escalado de un shooter a un duelo de bloques. |
| 2. Juego | 0:40-1:30 | Explicar tablero 10x20, siete piezas, eliminación de líneas y ataques. Dos jugadores por servidor. |
| 3. Arquitectura | 1:30-2:25 | Separar partida con estado en Agones de resultados en Cloud Run/Firestore. Explicar WebSocket y observabilidad. |
| 4. IA | 2:25-3:15 | Distinguir bot heurístico probado del PPO preparado. Mostrar benchmark y explicar cálculo de vCPU y frecuencia real de una decisión cada 1.5 s. |
| 5. Despliegue | 3:15-4:10 | Recorrer pruebas, imagen por SHA, registro y flota. Explicar drenado y rollback a plantilla anterior. |
| 6. Escalado | 4:10-5:05 | Calcular 500 partidas para 1000 jugadores y 625 servidores con buffer. Explicar flota, nodos y API. |
| 7. Mediciones | 5:05-6:00 | Mostrar curva local. Con 500 espectadores p95 cruza 80 ms. Aclarar que son espectadores de tableros, no HLS. |
| 8. Resultados | 6:00-6:45 | Mostrar nueve pruebas y límites de evidencia. La plataforma todavía requiere pruebas cloud de lanzamiento. |
| 9. Costos | 6:45-7:30 | Explicar escenario hipotético, costo por jugador-hora y peso del bitrate. No presentar una cotización como consumo real. |
| 10. Demo | 7:30-10:00 | Ejecutar el juego contra bot, mover/rotar y soltar piezas, abrir espectador y /metrics. Si ya desplegaste en nube, mostrar asignación y escalado en Grafana; si no, señalar la demo cloud pendiente. Cerrar explicando destroy y verificación de inventario. |

Antes de exponer: tener dos pestañas y terminal listas. No ejecutar Terraform ni cargas masivas por primera vez durante la exposición. La presentación contiene diez diapositivas editables. Los tiempos de esta tabla suman diez minutos y prevalecen sobre las notas orientativas de cada diapositiva.
