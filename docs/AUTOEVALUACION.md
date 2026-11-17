# Respuestas adaptadas a Bloques Arena

1. **Spot y entrenamiento:** una interrupción elimina el estado de una partida y desconecta jugadores. El entrenamiento puede continuar desde un checkpoint. Las partidas van en nodos bajo demanda.
2. **4300 jugadores:** con dos jugadores por partida son 2150 partidas. Buffer de 20% sobre ocupados: 2150 + 430 = 2580 servidores. En Agones, 20% del total Ready: techo(2150/0.8) = 2688. Si se mantiene el supuesto original de diez jugadores: 516 por suma o 538 en Agones. No se mezclan ambos porcentajes.
3. **HPA, FleetAutoscaler y nodos:** HPA cambia réplicas de servicios sin estado, FleetAutoscaler el tamaño de la flota y Cluster Autoscaler el número de nodos según pods no programables. Aquí la API usa escalado administrado Cloud Run y el asignador es un script, por lo que no hay un HPA de matchmaking desplegado.
4. **Costo de streaming:** lo domina el volumen entregado, producto de espectadores, bitrate y tiempo. ABR y codificación eficiente reducen bitrate. La CDN distribuye entrega y reduce tráfico de origen, pero su egress también cuesta.
5. **15000 espectadores a 4500 kbps, dos horas:** 15000 x 4500 x 7200 / 8000000 = 60750 GB = 60.75 TB decimales.
6. **Serverless:** registro de resultados, clasificación y recompensas al final de la partida encajan por ser solicitudes/eventos breves. El servidor de partida requiere estado y conexiones duraderas. Cloud Run admite WebSocket, pero sus timeouts y afinidad/persistencia requieren un diseño diferente; se usa Agones para esta práctica.
7. **Drift:** diferencia entre infraestructura real y estado declarado/versionado; se detecta al refrescar y ejecutar `terraform plan`. No basta revisar archivos Git.
8. **Capacidad máxima:** último escalón sostenido que cumple p95 <80 ms, tick p99 <25 ms y errores <0.5%, repetido en condiciones comparables. Para capacidad por nodo usa nodos activos de cada ventana y control de distribución, reservando recursos del sistema. La muestra local no mide capacidad por nodo GKE.

## Evidencias para cerrar la rúbrica

- IaC 20%: plan revisado, estado remoto, apply, segundo plan sin cambios, destroy y revisión de inventario.
- Orquestación 20%: imagen Docker ejecutada, métricas, servidores Ready/Allocated, llamadas SDK y recursos configurados.
- Escalado 20%: serie temporal Fleet/Ready/Allocated/Pending/nodos y demora de reacción. API Cloud Run bajo carga.
- Métricas 20%: CSV rampa/pico de 1000, prueba de 500 espectadores HLS, curva CCU/RTT y extrapolación de 20000 con supuestos.
- CI/CD y serverless 10%: ejecución GitHub verde, SHA desplegado, API accesible con identidad y prueba 80/20.
- Comunicación 10%: reporte de seis páginas, costo por jugador-hora y exposición de diez minutos con demo de escalado.

El paquete cubre implementación y pruebas locales. Estos puntos de nube necesitan ejecución real antes de presentar la actividad como laboratorio totalmente completado.
