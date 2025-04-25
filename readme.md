Okay, aquí tienes la documentación propuesta para tu proyecto, estructurada en un formato README.md que es estándar para la documentación principal de un repositorio.
project_root/README.md
# Sistema de Evaluación Automatizada de Llamadas mediante IA (POC)

## Descripción del Proyecto

Este proyecto es una Prueba de Concepto (POC) para implementar un sistema automatizado de evaluación de calidad de llamadas realizadas por agentes de EOS Spain a deudores. Utiliza Speech Analytics (simulado inicialmente con transcripciones, con potencial integración de Whisper) e Inteligencia Artificial (LLM de Azure OpenAI) para evaluar las transcripciones de las llamadas contra un conjunto predefinido de criterios o "ítems".

La POC actual se centra en un subconjunto de ítems críticos y del bloque "Inicio Llamada", y está diseñada para ser ejecutada localmente utilizando archivos como fuente de datos inicial.

## Propósito

El objetivo principal de esta POC es validar la viabilidad y obtener una primera aproximación a la calidad de la evaluación automatizada utilizando LLMs y Prompt Engineering, gestionando la complejidad de las reglas de evaluación, excepciones y el uso de datos estructurados externos (Kollecto/K+). También busca establecer una estructura modular para el proyecto que facilite su crecimiento futuro.

## Características (POC Actual)

* **Estructura Modular:** Código organizado en módulos lógicos (configuración, datos, evaluación, resultados, workflow).
* **Evaluación basada en LLM:** Utiliza un modelo de lenguaje grande (Azure OpenAI) para analizar transcripciones y datos de K+.
* **Prompt Engineering:** La lógica de evaluación se define principalmente a través de instrucciones y reglas proporcionadas en los prompts al LLM.
* **Uso de Datos Estructurados:** Incorpora datos relevantes de Kollecto (K+) junto con la transcripción como entrada para el LLM, permitiendo validaciones cruzadas.
* **Estrategia de Agrupación de Ítems:** Los ítems del bloque "Inicio Llamada" se evalúan en un único prompt al LLM para optimizar costes y latencia. Otros ítems críticos se evalúan individualmente.
* **Post-Procesamiento Básico:** Lógica en Python para aplicar reglas de negocio o ajustar resultados después de la evaluación del LLM (ej. marcar ítems como N/A por metadatos de llamada).
* **Carga de Datos Local:** Lee transcripciones y datos de K+ desde archivos almacenados localmente.
* **Resultados Estructurados:** Genera archivos JSON con los resultados de la evaluación por ítem para cada llamada procesada.

## Estructura del Proyecto


project_root/
│
├── src/                  # Código fuente del proyecto
│   ├── config/           # Módulo para cargar la configuración (config_manager.py)
│   ├── data_acquisition/ # Módulo para descargar datos (PLACEHOLDER) (downloader.py)
│   ├── audio_processing/ # Módulo para procesar audio con Whisper (PLACEHOLDER) (whisper_processor.py)
│   ├── data_preparation/ # Módulo para cargar y preparar datos (data_loader.py)
│   ├── evaluation/       # Lógica central de evaluación (item_rules.py, evaluator.py, postprocessor.py)
│   ├── results/          # Módulo para guardar resultados (results_handler.py)
│   └── main_workflow.py    # Orquestador principal del pipeline
│
├── data/                 # Directorio para almacenar datos localmente
│   ├── raw_calls/          # Audios descargados (si se usa downloader)
│   ├── raw_transcripts/    # Transcripciones iniciales (si se usa downloader)
│   ├── whisper_transcripts/# Transcripciones generadas por Whisper (o dummy)
│   ├── k_plus_data/        # Archivos con datos estructurados de K+ por llamada (o dummy)
│   └── processed/          # (Opcional)
│
├── config/               # Archivos de configuración
│   └── settings.yaml       # Configuración general (rutas, API endpoints no sensibles)
│
├── results/              # Directorio para almacenar los resultados finales
│
├── scripts/              # Scripts de ayuda
│   └── run_pipeline.py     # Script simple para ejecutar main_workflow
│
├── .env                  # Variables de entorno (credenciales sensibles)
├── requirements.txt      # Dependencias del proyecto
└── README.md             # Documentación del proyecto (este archivo)

## Configuración

El proyecto utiliza dos fuentes de configuración: variables de entorno (cargadas desde `.env` por `python-dotenv`) y un archivo YAML (`config/settings.yaml`).

1.  **`.env`:** Almacena credenciales y claves sensibles. Crea este archivo en la raíz del proyecto y añade:
    ```dotenv
    AZURE_OPENAI_ENDPOINT="TU_AZURE_ENDPOINT"
    AZURE_OPENAI_KEY="TU_AZURE_KEY"
    # Otras claves API si son necesarias para descarga o Whisper real
    ```
    **¡Importante:** No compartas este archivo públicamente!

2.  **`config/settings.yaml`:** Contiene la configuración no sensible.
    ```yaml
    # Configuración general del proyecto

    # Configuración Azure OpenAI (no sensible, solo nombres/versiones)
    openai:
      deployment_name: "TU_GPT_DEPLOYMENT_NAME" # Ej: gpt-4o, gpt-4-turbo
      api_version: "2024-02-15-preview" # Versión API (verificar la compatible con tu deployment)

    # Rutas de directorios (relativas a project_root o absolutas)
    data_paths:
      base: "data/"
      raw_calls: "data/raw_calls/"
      raw_transcripts: "data/raw_transcripts/"
      whisper_transcripts: "data/whisper_transcripts/"
      k_plus_data: "data/k_plus_data/"
      results: "results/"

    # Configuración del pipeline
    pipeline:
      use_whisper: false # true para usar transcripciones Whisper, false para raw (dummy en POC)
      items_to_evaluate: # Lista de claves de EVALUATION_STRUCTURE a ejecutar (vacío=[] ejecuta todos)
        - "inicio_llamada_group"
        - "item_17_individual"
        - "item_20_individual"
        - "item_26_individual"

    # Configuración de la fuente de datos (PLACEHOLDER - para futura implementación real)
    data_source:
      api_endpoint: "http://your-call-system/api/"
      # ... otros parámetros de conexión
    ```
    Ajusta `deployment_name` y `api_version` según tu deployment en Azure. Las rutas de `data_paths` son relativas a la raíz del proyecto.

## Configuración Inicial (Setup)

1.  **Clonar el Repositorio:** (Si aplica)
    ```bash
    git clone <url_del_repositorio>
    cd <nombre_del_directorio>
    ```
2.  **Crear Entorno Virtual:** (Recomendado)
    ```bash
    python -m venv .venv
    source .venv/bin/activate # En Windows usar `.venv\Scripts\activate`
    ```
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Crear Archivos de Configuración:** Crea los archivos `.env` y `config/settings.yaml` como se describe en la sección anterior y rellénalos.
5.  **Crear Directorios de Datos y Resultados:**
    ```bash
    mkdir -p data/raw_calls data/raw_transcripts data/whisper_transcripts data/k_plus_data results
    ```
6.  **Preparar Datos Dummy para POC:** El `main_workflow.py` actual tiene lógica para crear archivos dummy básicos en `data/whisper_transcripts/` y `data/k_plus_data/` si no existen. Puedes modificar esta lógica en `main_workflow.py` para generar datos dummy más complejos que cubran diferentes escenarios de ítems. Alternativamente, puedes crear manualmente archivos `.txt` (transcripciones) y `.json` (datos K+) en los directorios `data/whisper_transcripts/` y `data/k_plus_data/` con los IDs de llamada que quieras probar.

## Cómo Funciona

El `main_workflow.py` orquesta el siguiente pipeline:

1.  **Carga de Configuración:** `config_manager.py` lee `.env` y `config/settings.yaml`.
2.  **Adquisición de Datos (Simulado):** `data_acquisition/downloader.py` (placeholder en POC) simula la descarga de audios y transcripciones iniciales a `data/raw_calls/` y `data/raw_transcripts/`.
3.  **Procesamiento de Audio (Simulado/Opcional):** `audio_processing/whisper_processor.py` (placeholder o integración real si `use_whisper` es true) simula o ejecuta la transcripción de audios (`data/raw_calls/`) a transcripciones de alta calidad (`data/whisper_transcripts/`) usando la API de Whisper.
4.  **Carga de Datos para Evaluación:** `data_preparation/data_loader.py` identifica las llamadas a evaluar (basado en archivos en `data/k_plus_data/`), lee la transcripción relevante (Whisper o raw según configuración) y el archivo JSON de datos de K+ para cada llamada, ensamblando el diccionario `call_data`. También realiza lógica de preparación de datos (ej. calcular si flag prescripción es reciente).
5.  **Evaluación con LLM:** `evaluation/evaluator.py`, utilizando las reglas e estructura de `evaluation/item_rules.py`, itera sobre los grupos/ítems definidos en `EVALUATION_STRUCTURE` (o la lista de `items_to_evaluate` en la configuración). Para cada grupo/ítem, construye un prompt al LLM de Azure OpenAI incluyendo la transcripción completa y el snapshot de datos de K+ (`call_data['call_metadata']['k_plus_data_snapshot']`), y parsea la respuesta (lista de resultados JSON para grupos, objeto JSON para ítems individuales).
6.  **Post-Procesamiento:** `evaluation/postprocessor.py` toma todos los resultados iniciales del LLM para la llamada y aplica lógica de negocio adicional o ajustes (ej. marcar Ítem 6 como N/A por duración/incidente, aunque el LLM lo haya evaluado).
7.  **Guardar Resultados:** `results/results_handler.py` toma los resultados finales de la llamada y los añade a una lista global. Al finalizar todas las llamadas, guarda esta lista plana en un archivo (ej. JSON) en el directorio `results/`.

## Lógica de Evaluación

* **`evaluation/item_rules.py`:** Contiene dos estructuras clave:
    * `ITEM_RULES`: Un diccionario donde cada clave es el ID de un ítem. Contiene los detalles (nombre, complejidad) y la **descripción detallada de la regla de evaluación (`rules_detail`)** para ese ítem. Es **fundamental** que `rules_detail` explique claramente al LLM cuándo y cómo usar la información de la transcripción y los datos de K+ (`k_plus_data_snapshot`).
    * `EVALUATION_STRUCTURE`: Un diccionario que define cómo se agrupan los ítems para las llamadas al LLM. Cada clave representa una llamada al LLM (ej. `"inicio_llamada_group"`, `"item_17_individual"`). El valor asociado indica qué `item_ids` se evalúan en esa llamada y proporciona el `prompt_template` específico.
* **Estrategia de Agrupación (POC):**
    * El bloque "Inicio Llamada" (Ítems 1-7) se agrupa y se evalúa en una sola llamada al LLM (clave `inicio_llamada_group`).
    * Los ítems críticos 17 (LOPD), 20 (Registro Datos), y 26 (Código Deontológico) se evalúan individualmente en llamadas separadas (`item_17_individual`, `item_20_individual`, `item_26_individual`).
    * Esta estrategia busca reducir el número total de llamadas al LLM manteniendo una complejidad manejable por prompt.

## Cómo Ejecutar el Pipeline

Desde el directorio raíz del proyecto (`project_root/`), ejecuta el script principal:

```bash
python scripts/run_pipeline.py

El script cargará la configuración, preparará los datos dummy (si no existen), cargará las llamadas, las evaluará usando Azure OpenAI y guardará los resultados en el directorio results/.
Extendiendo el Proyecto
 * Añadir Nuevos Ítems:
   * Actualiza evaluation/item_rules.py: Añade la definición completa del nuevo ítem al diccionario ITEM_RULES, prestando especial atención a su rules_detail.
   * Actualiza evaluation/item_rules.py: Decide si el nuevo ítem se agrupa con otros o se evalúa individualmente. Modifica una entrada existente en EVALUATION_STRUCTURE (si se agrupa) o añade una nueva entrada para el ítem individual, incluyendo su prompt_template.
   * Actualiza data_preparation/data_loader.py: Si el nuevo ítem requiere nuevos campos de K+, asegúrate de que load_call_data_for_evaluation los cargue y los incluya en call_metadata (y especialmente en k_plus_data_snapshot).
   * Actualiza apply_post_processing en evaluation/postprocessor.py: Si el nuevo ítem tiene reglas de post-procesamiento o dependencias complejas con otros ítems, implementa la lógica aquí.
 * Refinar Prompts: Modifica directamente el prompt_template en EVALUATION_STRUCTURE o el rules_detail en ITEM_RULES. La mejora continua de los prompts es clave para la calidad.
 * Integrar Fuentes de Datos Reales: Reemplaza la lógica dummy en data_acquisition/downloader.py y adapta data_preparation/data_loader.py para leer de tus sistemas reales (APIs, bases de datos) y no solo de archivos locales dummy. Asegúrate de que los datos de K+ cargados sigan la estructura esperada (k_plus_data_snapshot).
 * Integrar Whisper Real: Si pipeline.use_whisper es true, deberás implementar la lógica real de llamada a la API de Whisper en audio_processing/whisper_processor.py para procesar tus archivos de audio reales.
 * Añadir Más Bloques/Grupos: Define nuevas entradas en EVALUATION_STRUCTURE para los ítems de otros bloques (Negociación, Comportamiento, etc.) a medida que tengas sus reglas detalladas. Considera si agrupar ítems dentro de esos bloques tiene sentido en términos de complejidad y coste.
Limitaciones Conocidas de la POC
 * Evaluación de Tono/Paralenguaje: La evaluación del tono, sarcasmo u otros aspectos vocales (Ítem 26, relacionado con Ítem 23) se basa únicamente en la transcripción textual, lo cual tiene limitaciones inherentes. La futura integración de análisis de audio podría abordarlo.
 * Verificación Completa en K+: Aunque el LLM recibe un snapshot de datos de K+, la complejidad de verificar todos los matices de una correcta "Alta/Asignación" (Ítem 20) o "Actualización" (Ítem 21) basándose solo en texto y un snapshot puede ser limitada para el LLM sin lógica de negocio específica o una representación de datos muy detallada y estructurada. La revisión humana sigue siendo crucial.
 * Dependencia de Transcripciones: La calidad de la evaluación depende directamente de la calidad de las transcripciones (raw o Whisper). Errores en la transcripción llevarán a errores en la evaluación.
 * Alcance Limitado: La POC solo evalúa un subconjunto de los 29 ítems totales.
 * No Hay Bucle de Feedback Automático: Los resultados generados son para revisión humana. No hay un mecanismo automatizado para usar correcciones humanas para mejorar el modelo o las reglas (Fase 4/5).
Futuro Trabajo Potencial
 * Completar la definición de reglas y la implementación de evaluación para los 29 ítems.
 * Integrar la descarga y procesamiento de audio real (Whisper, detección de paralinguaje).
 * Implementar el bucle de Feedback y Calibración utilizando las revisiones humanas.
 * Explorar Fine-tuning de modelos LLM para la tarea específica si Prompt Engineering no es suficiente.
 * Optimizar rendimiento y coste para manejar grandes volúmenes de llamadas (procesamiento paralelo, modelos más pequeños si es posible).
 * Integración más profunda y en tiempo real con el sistema Kollecto.

