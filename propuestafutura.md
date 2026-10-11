Propuesta: resiliencia y recuperación para E2E-EKS-GitOps
Estado: propuesta de evolución; experimentos y objetivos pendientes de implementar y validar.
Objetivo
Demostrar que la plataforma puede detectar fallos, limitar su impacto y recuperar la inferencia y los procesos de entrenamiento de manera reproducible.
Aplicaremos ingeniería del caos: formular una hipótesis, introducir un fallo controlado, medir el resultado y mejorar el sistema. Incluiremos fallos de infraestructura, aplicaciones, datos y modelos.
1. Preparar una ejecución de referencia
Antes de introducir fallos, completar y registrar un recorrido funcional:
Datos versionados → validación → entrenamiento → evaluación → registro → despliegue → inferencia → monitoreo.
La evidencia debe identificar:
- Commit de Git, imagen por digest, versión del modelo y versión de datos.
- Configuración del entorno y dependencias.
- Métrica de calidad del modelo y conjunto de evaluación.
- Latencia p95, porcentaje de errores y volumen de solicitudes.
- Duración y costo medido del despliegue.
- Resultado de las pruebas y procedimiento de limpieza.
Usar tráfico sintético reproducible. Una ejecución de referencia fallida bloquea el experimento.
2. Experimentos propuestos
Prioridad	Fallo controlado	Hipótesis que queremos comprobar	Evidencia de éxito
P0	Terminar un pod de inferencia	Las réplicas restantes mantienen el servicio y Kubernetes repone capacidad	Errores, latencia y tiempo hasta recuperar réplicas
P0	Desplegar una imagen que no inicia	La versión defectuosa no recibe tráfico y puede revertirse	Readiness, eventos y recuperación de la versión anterior
P0	Promover un modelo con peor calidad	La evaluación bloquea la promoción aunque el servicio responda correctamente	Comparación con el modelo vigente y decisión registrada
P0	Enviar datos con columnas ausentes o tipos incorrectos	La validación detecta entradas inválidas antes del entrenamiento o inferencia	Rechazo explícito y ausencia de artefactos promovidos
P1	Introducir latencia o pérdida de acceso a una dependencia	Los tiempos de espera y reintentos limitados evitan una cascada de fallos	Latencia, errores y recuperación al restaurar acceso
P1	Interrumpir un entrenamiento	La ejecución queda marcada como fallida y puede repetirse sin registrar un modelo incompleto	Estado del trabajo, artefactos y reejecución
P1	Cambiar la distribución de los datos	El monitoreo detecta drift y abre una investigación	Alerta reproducible, características afectadas y comparación
P1	Drenar un nodo de pruebas	Las cargas se reubican si existe capacidad y las restricciones lo permiten	Pods pendientes, interrupción y tiempo de recuperación
P2	Reconstruir un entorno desechable	Infraestructura, aplicaciones y estado persistente pueden recuperarse mediante procedimientos documentados	Prueba funcional después de restauración y tiempo total


Distinciones importantes: detectar drift no demuestra pérdida de calidad; un modelo puede responder sin errores y producir malas predicciones. Cuando las etiquetas reales llegan tarde, la medición de calidad también tendrá retraso.
3. Recuperación de modelos y despliegues
Mantener una versión anterior conocida y evaluada del modelo, junto con su imagen, configuración y contrato de entrada.
Proponer este flujo:
1. Evaluar el candidato contra un conjunto de referencia y segmentos relevantes.
2. Bloquear candidatos que incumplan umbrales acordados.
3. Desplegar progresivamente, si la plataforma lo permite.
4. Comparar salud del servicio y calidad disponible.
5. Ante una regresión, restaurar la versión anterior.
6. Investigar y corregir antes de volver a promover.
En GitOps, la recuperación debe quedar reflejada en el estado deseado de Git. Un cambio manual aislado puede ser revertido por el reconciliador.
Definir qué recursos administra ArgoCD y cuáles Flux, evitando que ambos controlen el mismo objeto.
No reentrenar ni promover automáticamente solo porque aparezca drift. Primero distinguir problemas de datos, cambios legítimos y degradación real.
4. Métricas y criterios de aceptación
Medir por experimento:
- Tiempo de detección: desde la inyección hasta la alerta.
- Tiempo de recuperación: desde la inyección hasta volver al nivel de servicio definido.
- Solicitudes fallidas y latencia p95 durante el incidente.
- Pérdida de datos o artefactos, si la hubo.
- Intervenciones manuales necesarias.
- Costo de la ejecución.
Como objetivos iniciales de laboratorio, sujetos a la ejecución de referencia:
Experimento	Objetivo provisional
Pérdida de un pod	Recuperar capacidad en menos de 2 minutos
Versión defectuosa	Detectar y recuperar el servicio en menos de 5 minutos
Datos inválidos	Bloquear todos los casos definidos en la batería de pruebas
Modelo degradado	Bloquear candidatos que incumplan el umbral de evaluación
Reconstrucción del entorno	Medir primero; fijar después un objetivo realista


Estos valores son metas propuestas, no resultados alcanzados ni garantías.
5. Alcance y detención
Comenzar en un entorno aislado y desechable, con datos sintéticos, un fallo por ejecución y duración máxima definida.
Cada experimento debe declarar:
- Recursos afectados y alcance máximo.
- Condición de inicio.
- Umbral de detención.
- Procedimiento de recuperación.
- Presupuesto de ejecución y limpieza final.
Detener la inyección no equivale a reparar sus efectos. La recuperación debe verificarse por separado. AWS FIS permite condiciones de detención mediante alarmas de CloudWatch. Documentación de AWS FIS.
Para las sondas, separar arranque, disponibilidad para recibir tráfico y salud del proceso; una sonda HTTP correcta no valida la calidad del modelo. Sondas de Kubernetes.
6. Reconstrucción y persistencia
Separar dos ejercicios:
- Recrear cómputo y configuración: infraestructura y aplicaciones desde Terraform y GitOps.
- Restaurar estado: metadatos del registro, artefactos, datos y cualquier almacenamiento persistente necesario.
Recrear un clúster no recupera por sí solo modelos ni historiales. Conservar las copias y los artefactos de recuperación fuera del alcance del entorno destruido, y probar que pueden restaurarse.
7. Primera entrega recomendada
Construir una demostración pequeña y completa:
1. Una versión estable sirviendo predicciones.
2. Un generador de tráfico y un tablero con errores y latencia.
3. Pérdida controlada de un pod y recuperación observada.
4. Un candidato de modelo deliberadamente peor.
5. Bloqueo de su promoción por evaluación.
6. Una reversión de despliegue registrada en Git.
7. Un informe con resultados, costos y limitaciones.
Después ampliar a fallos de dependencias, drift, nodos y reconstrucción.
8. Plantilla de informe
Para cada experimento guardar:
- Nombre, fecha y commit.
- Hipótesis.
- Entorno, versiones y carga aplicada.
- Fallo introducido y duración.
- Estado previo y umbrales.
- Secuencia observada y métricas.
- Resultado: aprobado, fallido o inconcluso.
- Recuperación y limpieza verificadas.
- Hallazgos y próxima mejora.
Resultado buscado para el portafolio: poder demostrar qué falló, cómo se detectó, cuánto tardó la recuperación y qué decisión técnica mejoró el comportamiento, con evidencia reproducible.