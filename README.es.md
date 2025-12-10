# Demo de Workflow Agéntico de Release Engineering

Este repositorio contiene un demo de un sistema de workflow agéntico que automatiza procesos de release engineering. El sistema integra workflows de n8n con un emulador de Microsoft Teams para demostrar workflows automatizados de aprobación de despliegues y ejecución de pipelines CI/CD.

## Resumen

El demo consiste en tres componentes principales:

1. **Workflow n8n (`re_agent.json`)**: Un workflow de agente impulsado por IA que:
   - Monitorea posts de Microsoft Teams para aprobación de despliegue
   - Verifica mensajes de aprobación del SCRUM Master
   - Dispara workflows de GitHub Actions cuando se otorga la aprobación
   - Monitorea el estado de ejecución del workflow

2. **Emulador de Teams (`app.py`)**: Un emulador de Microsoft Teams basado en FastAPI que:
   - Proporciona una API REST para posts y respuestas
   - Incluye una interfaz web para gestionar posts y respuestas
   - Simula canales de comunicación de Microsoft Teams

3. **Pipeline CI/CD (`lint.yml`)**: Un workflow de GitHub Actions que:
   - Ejecuta linting de código Python usando Black
   - Valida el formato del código
   - Sirve como pipeline de prueba para el workflow de release engineering

## Requisitos Previos

- Docker instalado y en ejecución
- Python 3.10+ (para ejecutar el emulador de Teams)
- Cuenta de n8n (o usar la configuración Docker proporcionada)
- Acceso de red a la API del emulador de Teams desde el contenedor n8n

## Instrucciones de Configuración

### Paso 1: Ejecutar n8n con Docker

Crea un volumen de Docker para la persistencia de datos de n8n y ejecuta el contenedor n8n:

```bash
docker volume create n8n_data && \
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -e GENERIC_TIMEZONE="America/Los_Angeles" \
  -e TZ="America/Los_Angeles" \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:1.121.3
```

Después de ejecutar este comando, n8n estará accesible en `http://localhost:5678`.

### Paso 2: Importar el Workflow de n8n

1. Abre n8n en tu navegador en `http://localhost:5678`
2. Navega a **Workflows** → **Import from File**
3. Selecciona el archivo: `src/n8n/re_agent.json`
4. El workflow se importará con todos los nodos y conexiones

### Paso 3: Ejecutar el Emulador de Teams

1. Navega al directorio del emulador de Teams:
   ```bash
   cd src/emulation/teams
   ```

2. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

3. Obtén la dirección IP de tu máquina (requerida para que n8n acceda a la API):
   ```bash
   # En macOS/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # En Windows:
   ipconfig
   ```
   Anota la dirección IP (ejemplo: `192.168.0.214`)

4. Ejecuta el servidor API del emulador de Teams:
   ```bash
   python app.py
   ```
   
   El servidor se iniciará en `http://0.0.0.0:8000` (accesible desde todas las interfaces de red).

5. Verifica que la API esté ejecutándose:
   - Abre `http://localhost:8000` en tu navegador para ver la interfaz del emulador de Teams
   - O prueba la API: `curl http://localhost:8000/api/posts`

### Paso 4: Configurar el Workflow de n8n con la IP del Emulador de Teams

1. En n8n, abre el workflow importado `re_agent.json`
2. Encuentra el primer nodo agente: **"TA-01 - Get Microsoft Teams post ID"**
3. Actualiza el parámetro URL para usar la dirección IP de tu máquina:
   - Cambia `http://192.168.0.214:8000/api/posts` a `http://<TU_IP>:8000/api/posts`
   - Reemplaza `<TU_IP>` con la dirección IP que obtuviste en el Paso 3.3

4. De manera similar, actualiza el nodo **"TA-01 - Get Microsoft Teams post replies"**:
   - La URL base debe ser: `http://<TU_IP>:8000/api/posts/<POST_ID>/replies`

### Paso 5: Ejecutar el Workflow

1. En n8n, activa el workflow (activa el interruptor en la esquina superior derecha)
2. Abre la interfaz de chat del workflow
3. Envía el siguiente mensaje JSON para iniciar el workflow:

```json
{
  "command": "start",
  "conversation_thread_title": "M190.0.0 Google Vertex AI Release"
}
```

4. El workflow:
   - Consultará el emulador de Teams para posts que coincidan con el título del hilo de conversación
   - Recuperará respuestas para verificar la aprobación del SCRUM Master
   - Si se encuentra aprobación, disparará el workflow de GitHub Actions
   - Monitoreará el estado de ejecución del workflow

## API del Emulador de Teams

El emulador de Teams proporciona los siguientes endpoints de API REST:

### Posts

- `GET /api/posts` - Obtener todos los posts (solo resumen)
- `GET /api/posts/full` - Obtener todos los posts con respuestas
- `GET /api/posts/{post_id}` - Obtener un post específico con respuestas
- `POST /api/posts` - Crear un nuevo post
- `PUT /api/posts/{post_id}` - Actualizar un post
- `DELETE /api/posts/{post_id}` - Eliminar un post

### Respuestas

- `GET /api/posts/{post_id}/replies` - Obtener todas las respuestas de un post
- `POST /api/posts/{post_id}/replies` - Crear una respuesta a un post
- `POST /api/replies` - Crear una respuesta (con post_id en el body)
- `PUT /api/replies/{reply_id}` - Actualizar una respuesta
- `DELETE /api/replies/{reply_id}` - Eliminar una respuesta

### Ejemplo: Crear una Respuesta

```bash
curl -X POST "http://localhost:8000/api/posts/<POST_ID>/replies" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "SCRUM Master",
    "role": "SCRUM Master",
    "message": "Aprobado. Por favor procede con el despliegue."
  }'
```

## Pipeline CI/CD

El repositorio incluye un workflow de GitHub Actions (`.github/workflows/lint.yml`) que:

- Se ejecuta con activación manual (`workflow_dispatch`)
- Configura Python 3.13
- Instala dependencias desde `src/emulation/teams/requirements.txt`
- Ejecuta el linter Black para verificar el formato del código
- Falla si se encuentran problemas de formato de código

### Ejecutar el Pipeline de Lint

El pipeline de lint puede ser activado manualmente desde la pestaña de GitHub Actions, o puede ser activado por el workflow de n8n cuando se aprueba un despliegue.

## Arquitectura del Workflow

El workflow de n8n consiste en múltiples agentes de IA:

1. **TA-01 (Agente de Teams)**: 
   - Recupera IDs de posts de Microsoft Teams
   - Obtiene respuestas a los posts
   - Determina si existe aprobación del SCRUM Master

2. **GAWA-01 (Agente de Workflow de GitHub Actions)**:
   - Dispara workflows de GitHub Actions
   - Monitorea el estado de ejecución del workflow
   - Recupera logs del workflow en caso de fallo

3. **Agente de Jira** (si está configurado):
   - Crea tickets de Jira
   - Monitorea el estado de los tickets

## Datos de Ejemplo

El emulador de Teams se inicializa con datos de ejemplo:

- **Post**: "M190.0.0 Google Vertex AI Release" por Cristina M. (Program Manager)
- **Respuesta**: Mensaje de aprobación de Alexa A. (SCRUM Master)

Estos datos de ejemplo te permiten probar el workflow inmediatamente después de la configuración.

## Solución de Problemas

### n8n no puede alcanzar el emulador de Teams

- Asegúrate de que el emulador de Teams esté ejecutándose en `0.0.0.0:8000` (no `127.0.0.1`)
- Verifica que la dirección IP en n8n coincida con la IP de tu máquina
- Verifica la configuración del firewall si se ejecutan en máquinas diferentes
- Prueba la conectividad: `curl http://<TU_IP>:8000/api/posts` desde el contenedor n8n

### El workflow no encuentra posts

- Verifica que el título del hilo de conversación coincida exactamente (sensible a mayúsculas)
- Revisa la interfaz del emulador de Teams en `http://localhost:8000` para ver los posts disponibles
- Asegúrate de que el post exista en la base de datos del emulador

### El workflow de GitHub Actions no se dispara

- Verifica que las credenciales de GitHub estén configuradas en n8n
- Verifica que el component_id coincida con un repositorio de GitHub válido
- Asegúrate de que el archivo de workflow exista en el repositorio objetivo

## Desarrollo

### Desarrollo del Emulador de Teams

El emulador de Teams está construido con:
- FastAPI para el servidor API
- Uvicorn como servidor ASGI
- Pydantic para validación de datos
- Jinja2 para plantillas

Para modificar el emulador:
1. Edita `src/emulation/teams/app.py`
2. Reinicia el servidor
3. Los cambios se reflejarán inmediatamente (reload habilitado)

### Agregar Nuevos Workflows

Para agregar nuevos workflows al agente de n8n:
1. Exporta el workflow desde n8n
2. Actualiza `src/n8n/re_agent.json`
3. Documenta el nuevo workflow en este README

## Licencia

[Agrega tu información de licencia aquí]

## Contribuir

[Agrega las guías de contribución aquí]

