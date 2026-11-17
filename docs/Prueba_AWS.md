# Bloques Arena · prueba de capacidad en AWS

EC2 t3.small, Linux, us-east-2. El generador y las salas de juego comparten una instancia.

| Objetivo | CCU inicial | CCU final | RTT p95 (ms) | Fallos de eco | Fallos de conexión |
|---:|---:|---:|---:|---:|---:|
| 2 | 2 | 2 | 65.6 | 0 | 0 |
| 10 | 10 | 10 | 65.56 | 0 | 0 |
| 25 | 25 | 25 | 151.08 | 0 | 0 |

Costo estimado: 0.026677 USD/h, con EC2 0.0208 USD/h, IPv4 0.005 USD/h y 8 GB gp3 a 0.08 USD/GB-mes (730 h). Tarifas de referencia antes de impuestos y créditos.

Mayor nivel aprobado: 10 jugadores, 65.56 ms p95, durante 3.78 s de medición. Costo de esa ventana: 0.00002804 USD. Exposición: 0.010511 horas-jugador. Costo: 0.00266767 USD por jugador-hora.

La prueba mide el mayor escalón ensayado que conservó sus conexiones, sin fallos y con RTT p95 menor a 80 ms. La duración es breve y el generador comparte CPU y red con el servidor. La prueba no mide escalado de EKS, tráfico público ni costos facturados. La medición de 29.78 s del reporte se obtuvo en el laboratorio local.

[EC2 T3](https://aws.amazon.com/ec2/instance-types/t3/) · [IPv4](https://aws.amazon.com/vpc/pricing/) · [EBS](https://aws.amazon.com/ebs/pricing/)
