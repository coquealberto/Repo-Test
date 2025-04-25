import os
import json
from openai import AzureOpenAI
from datetime import datetime, timedelta # Importar para lógica de fecha en dummy data

# --- Configuración ---
# Reemplaza con tus datos de configuración de Azure OpenAI o asegura variables de entorno
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "YOUR_AZURE_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "YOUR_AZURE_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# --- Cliente de Azure OpenAI ---
try:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    print("Azure OpenAI client initialized successfully.")
except Exception as e:
    print(f"Error initializing Azure OpenAI client: {e}")
    print("Please check your AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, and AZURE_OPENAI_API_VERSION configuration.")
    # exit() # Descomentar para salir si la configuración es crítica

# --- Definición de Items y sus reglas (completo para los 10 ítems en scope) ---
ITEM_RULES = {
    # Bloque 1: Inicio Llamada
    "1": { "name": "Saludo+Identificación (agente+empresa)", "complexity": "BAJO", "description": "...",
           "rules_detail": """
           Se valora que el saludo y la identificación del agente sean las establecidas por la empresa.
           - Llamadas Salientes: Agente debe presentarse con Nombre + 1 Apellido e indicar que llama de EOS Spain.
           - Llamadas Entrantes: Ajustarse a frase “EOS Spain buenos días/tardes le atiende nombre +er apellido, ¿en qué puedo ayudarle?”
           - Excepciones y otras consideraciones: Si agente solo indica su nombre, se acepta. Si frase en diferente orden, se acepta.
           - Relación con otros ítems: Sin relación directa.
           """},
    "2": { "name": "Informar posible grabación llamada + GDPR", "complexity": "BAJO", "description": "...",
           "rules_detail": """
           Informar siguiendo argumentario en TODAS llamadas salientes (incl. callback). RedSys: informar parar/reanudar grabación. Añadir persona: identificarse e informar grabación.
           - Excepciones: Cliente interrumpe, no se valora (Pass). Frase no exacta pero informa, correcto (Pass). Empresas autorizadas con NDA, no es necesario informar (Pass/N/A si aplica).
           - Relación con otros ítems: Sin relación directa.
           """},
    "3": { "name": "Identificación interlocutor (buscar confirmación)", "complexity": "BAJO", "description": "...",
           "rules_detail": """
           Agente debe buscar confirmación de que habla con la persona correcta (cliente).
           - Llamadas IN: Solicitar interlocutor facilite nombre y motivo. Si es cliente, pedir Nombre Completo, DNI, Fecha Nacimiento.
           - Llamadas OUT: Preguntar por interviniente con Nombre y Apellidos. Debe responder afirmativamente a "¿Es usted?". No basta con "Sí", "Dígame".
           - Excepciones: Interlocutor en llamada IN referencia su deuda ("llamo por mi tarjeta"), NO necesario el check "¿es usted?" (Pass). Llamada IN: agente pide datos ANTES de saber si es cliente, penaliza. Llamada IN: agente lee nombre SIN solicitar interlocutor lo facilite, penaliza. Penalizar solicitar 3 últimos dígitos DNI SIN negativa previa a confirmar completo (relacionado con Ítem 4, pero penaliza aquí).
           - Relación con otros ítems: Sin relación directa.
           """},
    "4": { "name": "Nombre completo Interviniente, DNI/NIF, Fecha nacimiento", "complexity": "MEDIO", "description": "...",
           "rules_detail": """
           Evalúa correcta identificación (Nombre Completo, DNI/NIE, Fecha Nacimiento) según tipo llamada.
           - Llamadas Salientes: Nombre completo Y DNI/NIE completo.
           - Llamadas Entrantes: Nombre completo + DNI/NIE completo + fecha nacimiento.
           - Excepciones: NO informar motivo antes identificar. Solo 3 últimos DNI si NEGATIVA previa. Si DOB no en sistema y valida por dirección, correcto. IN por SMS/perdida donde agente da nombre: Válido si sigue resto (pide DNI/DOB). Autorizados sin DNI/NIE: Válido si facilitan cedente/producto/ref.
           - Relación con Ítem 17: Si info contractual a NO interviniente (Ítem 4 Fail por persona incorrecta), fallo principal en Ítem 17.
           """},
    "5": { "name": "Motivo llamada-identificar expediente. Prescripción", "complexity": "MEDIO", "description": "...",
           "rules_detail": """
           Manejo correcto de información de prescripción o productos/cedente/importes.
           - Si aplica prescripción: fiel al texto facilitado y datos (fechas/importes) correctos.
           - Si NO procede prescripción (flag < 3 meses o no hay flag): informar productos, cedente, importes.
           - Si expediente NO tiene flag O flag > 3 meses Y hace prescripción: DEBE mencionar que registrará flag.
           - Penalizar datos erróneos (cedente, producto, importe, fecha formalización).
           - Si error corregido MÁS TARDE: NO penaliza (Pass).
           - Excepciones: Al hacer prescripción NO indica tipo interviniente ("usted tiene un préstamo") pero es cliente principal (ej. cliente dice "tengo una tarjeta" y es único): NO penaliza (Pass).
           - Relación con Ítem 14: Si datos erróneos en prescripción y error mantenido, penalización en Ítem 5, NO Ítem 14.
           """},
    "6": { "name": "Confirmar datos contacto (dirección, teléfono, email)", "complexity": "MEDIO", "description": "...",
           "rules_detail": """
           Valora si se confirman COMPLETOS todos los datos de contacto marcados "VALIDO" en K+.
           - Válido SÓLO si confirma COMPLETO TODOS los datos "VALIDO".
           - EXCEPCIONES (gestionadas en código, LLM no evalúa si aplica): NO valora llamadas < 4 minutos. NO valora si incidencias K+ reportadas.
           - Relación con Ítem 21: Confirmación incompleta de datos 'VALIDO' existentes cuando tocaba confirmar -> Fail en Ítem 6 y nota situación. Situaciones de Ítem 21 (conf. incompleta por operativa, no conf. por envío pero ya conf. último mes) penalizan en Ítem 21, no aquí.
           - Relación con Ítem 7: Solicitar datos adicionales DESPUÉS de confirmar datos sistema -> Ítem 7, NO Ítem 6.
           """},
    "7": { "name": "Solicitar datos contacto adicionales", "complexity": "BAJO", "description": "...",
           "rules_detail": """
           Evalúa si se solicitan datos de contacto adicionales (teléfono, mail) cuando corresponde.
           - Solicitar datos adicionales (telf fijo/móvil, email si no tenemos uno) en todas confirmaciones y/o actualizaciones.
           - SOLO se valora la SOLICITUD, no la correcta incorporación a BBDD (eso es Ítem 20).
           - Excepciones (N/A o Pass si aplica): NO valora si ya dispone de >1 teléfono Y >1 email. NO valora si NO corresponde confirmación/actualización datos. Operativa NO aplica para autorizados expresos.
           - Relación con Ítem 20: Correcta incorporación a BBDD -> Ítem 20. Este ítem es SOLO sobre la SOLICITUD.
           """},
    # Ítems Críticos Individuales
    "17": { "name": "Tratamiento de la información con 3os", "complexity": "ALTO", "description": "...",
            "rules_detail": """
            Protección de información personal/contractual, evitando facilitarla a personas NO autorizadas.
            - Penaliza facilitar info a NO autorizados.
            - EXCEPCIONES (N/A si aplica): Si interviniente ESTÁ presente en llamada a 3. Si abogados personados en K+, NO necesita autorización (Pass).
            - Relación con otros ítems: Sin relación directa relevante.
            """},
    "20": { "name": "Alta / Asignación datos (dirección teléfonos, etc.)", "complexity": "BAJO", "description": "...",
            "rules_detail": """
            Evalúa si el agente habla de dar de alta un dato nuevo necesario, o si discute un dato que NO debe darse de alta.
            - Penaliza cuando se habla de dar de alta dato nuevo necesario que NO SE HACE (según conv.) o se habla de dar de alta dato que POR OPERATIVA NO DEBE incorporarse (ej. Comisaría).
            - Si discute alta dato nuevo con error evidente en conv. (ej. CP erróneo), penaliza.
            - NOTA IMPORTANTE: Evaluación SOLO basada en conversación. NO puedes verificar correcta ejecución en sistema K+.
            - Relación con Ítem 21: Situaciones de alta con errores o datos no permitidos pueden valorarse en Ítem 21. En POC, si conversación muestra intento alta no permitido o alta con error evidente relacionado con dato *nuevo*, Fail Ítem 20.
            """},
    "26": { "name": "Ninguna amenaza o intimidación, ironía, frases inadecuadas. Sin provocaciones, sin juicios de valor", "complexity": "ALTO", "description": "...",
            "rules_detail": """
            Agente mantiene comportamiento respetuoso, profesional, SIN dañar imagen compañía.
            - Evitar: NINGUNA amenaza/intimidación, NINGUNA ironía, NINGUNA frase inadecuada, SIN provocaciones, SIN juicios de valor. Enfócate en violaciones CLARAS Y GRAVES que dañan la imagen.
            - Relación con Ítem 23 (Comunicación general): Mayoría problemas tono/comunicación penalizan Ítem 23. SOLO Ítem 26 si acción/lenguaje DAÑA CLARAMENTE IMAGEN o trato CRITICAMENTE INAPROPIADO/IRRESPECTUOSO según puntos listados.
            """},
}

# --- Estructura de Evaluación (Define grupos e ítems individuales) ---
EVALUATION_STRUCTURE = {
    "inicio_llamada_group": {
        "item_ids": ["1", "2", "3", "4", "5", "6", "7"],
        "prompt_template": """
        Eres un evaluador de calidad de llamadas experto para EOS Spain. Analiza la siguiente transcripción y los datos de la llamada para determinar si el agente cumplió con los siguientes ítems del bloque "Inicio Llamada": {item_ids}.

        **Datos de la Llamada:**
        Tipo de Llamada: {call_type}
        Duración (mins): {call_duration}
        Incidencia en K+ Reportada: {k_plus_incident}
        Datos de Contacto 'VALIDO' en K+: {k_plus_valid_contacts}
        ¿Tiene Flag Prescripción?: {has_prescription_flag}
        ¿Flag Prescripción Reciente (<3m)?: {is_prescription_flag_recent}
        Número Teléfonos en K+: {k_plus_phone_count}
        Número Emails en K+: {k_plus_email_count}
        ¿Corresponde Confirmación/Actualización de datos por operativa?: {corresponds_update}
        ¿Interviniente es Autorizado Expreso?: {is_authorised_express}
        Otros Datos K+ Relevantes (ej: DOB en sistema para Ítem 4): {k_plus_data}
        Transcripción: ```{transcript}```

        **Reglas de Evaluación para cada Ítem:**
        {all_items_rules_detail}

        Evalúa cada uno de los ítems listados ({item_ids}) estrictamente basándote en la transcripción, los datos de la llamada y las reglas proporcionadas para CADA ÍTEM. Para el Ítem 6, ten en cuenta las excepciones por duración o incidencia (aunque la lógica de N/A se aplicará después, detecta el cumplimiento si aplicara).

        Formato de Salida: Devuelve una lista de objetos JSON, uno por cada ítem evaluado en este grupo. CADA objeto JSON debe tener las claves "item_id", "result" ("Pass" | "Fail" | "N/A"), "reason" (explicación breve) y "transcript_segment" (fragmento relevante).

        ```json
        [
          {{
            "item_id": "1",
            "result": "Pass" | "Fail" | "N/A",
            "reason": "...",
            "transcript_segment": "..."
          }},
          {{
            "item_id": "2",
            "result": "Pass" | "Fail" | "N/A",
            "reason": "...",
            "transcript_segment": "..."
          }},
          // ... y así para todos los ítems del grupo (3, 4, 5, 6, 7)
        ]
        ```
        Asegúrate de que la salida sea una lista de objetos JSON válida.
        """,
    },
     "item_17_individual": { # Ítem Individual 17
        "item_ids": ["17"],
        "prompt_template": """
        Eres un evaluador de calidad de llamadas experto para EOS Spain. Analiza la siguiente transcripción y datos para evaluar el Ítem 17: Tratamiento de la Información con Terceros.

        **Datos de la Llamada:**
        Transcripción: ```{transcript}```
        ¿Está presente el interviniente en la llamada a 3?: {intervener_present_in_3way}
        ¿Está el abogado personado en K+?: {lawyer_personado}

        **Reglas de Evaluación (Ítem 17):**
        {all_items_rules_detail}

        Evalúa estrictamente basándote en la transcripción y los datos proporcionados. Enfócate en si se reveló información personal o contractual a alguien que no debía recibirla, considerando las excepciones.
        Formato de Salida (JSON):
        ```json
        {{
          "item_id": "17",
          "result": "Pass" | "Fail" | "N/A",
          "reason": "Breve explicación, indicando si se facilitó información a un tercero no autorizado o no, citando evidencia.",
          "transcript_segment": "Fragmento relevante (si aplica)"
        }}
        ```
        Asegúrate de que la salida sea JSON válido. Marca N/A si la regla de excepción (interviniente presente o abogado personado) aplica según los datos.
        """,
    },
    "item_20_individual": { # Ítem Individual 20
         "item_ids": ["20"],
         "prompt_template": """
        Eres un evaluador de calidad de llamadas experto para EOS Spain. Analiza la siguiente transcripción para determinar si el agente cumplió con el Ítem 20: Discusión/Intento de Alta/Asignación de Datos Nuevos.

        **Datos de la Llamada:**
        Transcripción: ```{transcript}```

        **Reglas de Evaluación (Ítem 20):**
        {all_items_rules_detail}

        Evalúa estrictamente basándote en la transcripción. Identifica si el agente discute o intenta dar de alta UN DATO *NUEVO* (dirección, teléfono, email, etc.) o si discute dar de alta un dato que POR OPERATIVA NO SE DEBE registrar (ej: teléfono de Comisaría).
        **NOTA IMPORTANTE:** Tu evaluación se basa SÓLO en la conversación en la transcripción. NO puedes verificar si el alta en el sistema se realizó correctamente o si el dato *realmente* era nuevo o erróneo en K+. Solo evalúa la acción o mención del agente en la llamada.

        Formato de Salida (JSON):
        ```json
        {{
          "item_id": "20",
          "result": "Pass" | "Fail" | "N/A",
          "reason": "Breve explicación. Indica si se discutió o intentó dar de alta un dato nuevo y si parecía correcto en la conversación, o si se discutió dar de alta un dato no permitido.",
          "transcript_segment": "Fragmento relevante (si aplica)"
        }}
        ```
        Asegúrate de que la salida sea JSON válido. Marca como N/A si no se discute ningún alta o modificación de datos nuevos en la llamada.
        """,
    },
    "item_26_individual": { # Ítem Individual 26
         "item_ids": ["26"],
         "prompt_template": """
        Eres un evaluador de calidad de llamadas experto para EOS Spain. Analiza la siguiente transcripción para determinar si el agente cumplió con el Ítem 26: Código Deontológico (Lenguaje y Comportamiento).

        **Datos de la Llamada:**
        Transcripción: ```{transcript}```

        **Reglas de Evaluación (Ítem 26):**
        {all_items_rules_detail}

        Evalúa estrictamente basándote en la transcripción. Busca evidencia de lenguaje o comportamiento del agente que sea una **violación clara y grave** del código deontológico. Enfócate en la presencia de:
        - Amenazas o intimidación
        - Ironía o sarcasmo (aunque difícil de detectar solo por texto, busca frases que claramente sugieran esto)
        - Frases inadecuadas o vulgares
        - Provocaciones
        - Juicios de valor sobre el interlocutor o su situación
        - Cualquier expresión que pueda dañar la imagen de la compañía o sea claramente irrespetuosa.

        Ignora aspectos de comunicación general como volumen, silencios o escucha activa, ya que esos se evalúan en otro ítem (Ítem 23, fuera de tu scope). Solo penaliza aquí si la violación es **grave** y afecta el trato o la imagen.

        Formato de Salida (JSON):
        ```json
        {{
          "item_id": "26",
          "result": "Pass" | "Fail" | "N/A",
          "reason": "Breve explicación, indicando el tipo de violación detectada (amenaza, ironía, etc.) y citando la evidencia.",
          "transcript_segment": "Fragmento relevante (si aplica)"
        }}
        ```
        Asegúrate de que la salida sea JSON válido. Marca como N/A si no hay evidencia de ninguna de estas violaciones graves.
        """,
    }
}

def evaluate_with_llm(evaluation_key: str, transcript: str, call_metadata: dict) -> list[dict]:
    """
    Evalúa un grupo de ítems o un ítem individual utilizando el LLM.

    Args:
        evaluation_key (str): La clave del grupo o ítem individual en EVALUATION_STRUCTURE.
        transcript (str): La transcripción completa de la llamada.
        call_metadata (dict): Metadatos de la llamada.

    Returns:
        list[dict]: Lista de diccionarios con los resultados de evaluación para cada ítem(es) evaluado(s).
                    Retorna una lista vacía o con resultados de error si falla.
    """
    evaluation_config = EVALUATION_STRUCTURE.get(evaluation_key)
    if not evaluation_config:
        print(f"Error: Evaluation config not found for key {evaluation_key}.")
        return [{"item_id": "Error", "result": "Error", "reason": f"Configuración no encontrada para {evaluation_key}", "transcript_segment": ""}]

    item_ids = evaluation_config["item_ids"]
    prompt_template = evaluation_config["prompt_template"]

    # Compilar las reglas detalladas para los ítems de este grupo/individual
    all_items_rules_detail = ""
    for item_id in item_ids:
        if item_id in ITEM_RULES:
            all_items_rules_detail += f"\n--- Reglas Ítem {item_id}: {ITEM_RULES[item_id]['name']} ---\n"
            all_items_rules_detail += ITEM_RULES[item_id]['rules_detail'] + "\n"
        else:
            all_items_rules_detail += f"\n--- Reglas Ítem {item_id}: REGLAS NO DISPONIBLES ---\n"

    # Preparar datos específicos para el prompt (incluye todos los posibles metadatos que los templates puedan necesitar)
    prompt_data = {
        "item_ids": ", ".join(item_ids), # Lista de IDs para el prompt del grupo
        "transcript": transcript,
        "all_items_rules_detail": all_items_rules_detail,
        # Incluir todos los metadatos que cualquier prompt template pueda necesitar
        "call_type": call_metadata.get("call_type", "Desconocido"),
        "call_duration": call_metadata.get("duration", 0),
        "k_plus_incident": call_metadata.get("k_plus_incident", False),
        "intervener_present_in_3way": call_metadata.get("intervener_present_in_3way", False),
        "lawyer_personado": call_metadata.get("lawyer_personado", False),
        "k_plus_valid_contacts": call_metadata.get("k_plus_valid_contacts", []),
        "has_prescription_flag": call_metadata.get("has_prescription_flag", False),
        "prescription_flag_date": call_metadata.get("prescription_flag_date", "N/A"),
        "is_prescription_flag_recent": call_metadata.get("is_prescription_flag_recent", False), # Dato calculado en load_call_data
        "k_plus_phone_count": call_metadata.get("k_plus_phone_count", 0),
        "k_plus_email_count": call_metadata.get("k_plus_email_count", 0),
        "corresponds_update": call_metadata.get("corresponds_update", False),
        "is_authorised_express": call_metadata.get("is_authorised_express", False),
        "k_plus_data": call_metadata.get("k_plus_data", "No disponible")
    }

    # Formatear el prompt
    try:
        prompt = prompt_template.format(**prompt_data)
    except KeyError as e:
         print(f"Error formatting prompt for evaluation key {evaluation_key}: Missing key {e}")
         # Retorna un resultado de error para cada í