import json
# Importar tiktoken para contar tokens
import tiktoken
# Importar config_manager para obtener config API
from src.config import config_manager
# Importar reglas y estructura de evaluación
from .item_rules import ITEM_RULES, EVALUATION_STRUCTURE
# Importar AzureOpenAI client
from openai import AzureOpenAI
#from azure.ai.inference import ChatCompletionsClient

# Configurar el cliente OpenAI aquí o importarlo si ya está configurado globalmente
# Esto asume que AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_KEY están en .env o variables de entorno
openai_client = AzureOpenAI(
    azure_endpoint=config_manager.config_manager.get_env("AZURE_OPENAI_ENDPOINT"),
    api_key=config_manager.config_manager.get_env("AZURE_OPENAI_API_KEY"),
    api_version=config_manager.config_manager.get("openai.api_version")
)

# Obtener el encoding para el modelo usado
# Esto debe coincidir con el modelo desplegado en Azure
# Para la mayoría de los modelos recientes de OpenAI, 'cl100k_base' es el encoding correcto.
# Verifica la documentación de Azure OpenAI para tu deployment específico si tienes dudas.
try:
    encoding = tiktoken.get_encoding("cl100k_base") # Usar el encoding común para gpt-4, gpt-3.5-turbo, etc.
    # Si tu deployment usa un modelo con un encoding diferente, ajusta aquí.
    # encoding = tiktoken.encoding_for_model("nombre-del-modelo-desplegado") # Alternativa si conoces el nombre exacto del modelo
except Exception as e:
    print(f"Error loading tiktoken encoding: {e}. Token counting may not be accurate.")
    encoding = None # Proceder sin conteo preciso si falla

def count_tokens(text: str) -> int:
    """Cuenta tokens usando el encoding configurado."""
    if encoding is None or not isinstance(text, str):
        return 0 # No contar si el encoding falló o la entrada no es string
    return len(encoding.encode(text))

def evaluate_with_llm(evaluation_key: str, transcript: str, call_metadata: dict) -> list[dict]:
    """
    Evalúa un grupo de ítems o un ítem individual utilizando el LLM.

    Args:
        evaluation_key (str): La clave del grupo o ítem individual en EVALUATION_STRUCTURE.
        transcript (str): La transcripción completa de la llamada.
        call_metadata (dict): Metadatos de la llamada (incluyendo k_plus_data_snapshot).

    Returns:
        tuple[list[dict], int, int]: Una tupla conteniendo:
        - list[dict]: Lista de diccionarios con los resultados de evaluación.
        - int: Tokens de entrada (prompt).
        - int: Tokens de salida (respuesta).
        Retorna una lista vacía y (0, 0) si falla la llamada al API o parsing.
    """
    evaluation_config = EVALUATION_STRUCTURE.get(evaluation_key)
    if not evaluation_config:
        print(f"Error: Evaluation config not found for key {evaluation_key}.")
        return [{"item_id": "Error", "result": "Error", "reason": f"Configuración no encontrada para {evaluation_key}", "transcript_segment": ""}], 0, 0

    item_ids = evaluation_config["item_ids"]
    prompt_template = evaluation_config["prompt_template"]

    # Compilar las reglas detalladas para los ítems de este grupo/individual
    all_items_rules_detail = ""
    for item_id in item_ids:
        if item_id in ITEM_RULES:
            # Usar la descripción y reglas detalladas de ITEM_RULES
            all_items_rules_detail += f"\n--- Ítem {item_id}: {ITEM_RULES[item_id]['name']} ---\n"
            # all_items_rules_detail += f"Descripción: {ITEM_RULES[item_id]['description']}\n" # Opcional, si es útil para el LLM
            all_items_rules_detail += ITEM_RULES[item_id]['rules_detail'] + "\n"
        else:
            all_items_rules_detail += f"\n--- Ítem {item_id}: Reglas NO DISPONIBLES ---\n"

    # Preparar datos para el prompt. Asegurarse de incluir k_plus_data_snapshot.
    prompt_data = {
        "item_ids": ", ".join(item_ids),
        "transcript": transcript,
        "all_items_rules_detail": all_items_rules_detail,
        # Incluir TODOS los metadatos y el snapshot de K+ que los templates o reglas puedan necesitar
        "call_type": call_metadata.get("call_type", "Desconocido"),
        "call_duration": call_metadata.get("'duration_minutes'", 0),
        "k_plus_incident": call_metadata.get("k_plus_incident", False),
        "intervener_present_in_3way": call_metadata.get("intervener_present_in_3way", False),
        "lawyer_personado": call_metadata.get("lawyer_personado", False),
        "k_plus_valid_contacts": call_metadata.get("k_plus_data_snapshot", {}).get("telefonos_validos", []) + call_metadata.get("k_plus_data_snapshot", {}).get("emails_validos", []) + ([call_metadata.get("k_plus_data_snapshot", {}).get("direccion_valido")] if call_metadata.get("k_plus_data_snapshot", {}).get("direccion_valido") else []), # Combinar validos para prompt 6 si es necesario
        "has_prescription_flag": call_metadata.get("k_plus_data_snapshot", {}).get("tiene_flag_argumentario_prescripcion", False),
        "prescription_flag_date": call_metadata.get("k_plus_data_snapshot", {}).get("fecha_flag_argumentario_prescripcion", "N/A"),
        # Usar el dato calculado en data_loader para la lógica de Item 5
        "is_prescription_flag_recent": call_metadata.get("is_prescription_flag_recent", False),
        "k_plus_phone_count": call_metadata.get("k_plus_data_snapshot", {}).get("numero_telefonos_total_en_k", 0), # Usar total counts para Item 7
        "k_plus_email_count": call_metadata.get("k_plus_data_snapshot", {}).get("numero_emails_total_en_k", 0), # Usar total counts para Item 7
        # Estos dos simulan si por operativa tocaba confirmar/actualizar. Vienen de metadata, no K+ snapshot directo.
        "corresponds_update": call_metadata.get("corresponds_update", False), # Dato a nivel de llamada/metadata
        "is_authorised_express": call_metadata.get("is_authorised_express", False), # Dato a nivel de llamada/metadata
        # Pasar el snapshot completo de K+
        "k_plus_data_snapshot": json.dumps(call_metadata.get("k_plus_data_snapshot", {}), ensure_ascii=False) # Convertir a string JSON para el prompt

        # NOTA: La preparación de prompt_data debe ser robusta. Asegurarse
        # de que todas las claves que usa CUALQUIER prompt_template
        # estén presentes, quizás con valores por defecto si no están en call_metadata.
    }


    # Formatear el prompt
    try:
        prompt = prompt_template.format(**prompt_data)
    except KeyError as e:
        print(f"Error formatting prompt for evaluation key {evaluation_key}: Missing key {e}")
        # Retorna un resultado de error para cada ítem en el grupo/individual
        error_results = [{"item_id": item_id, "result": "Error", "reason": f"Error formatting prompt: Missing data {e}", "transcript_segment": ""} for item_id in item_ids]
        return error_results, 0, 0

    # Construir los mensajes para la API
    system_message = "You are an AI assistant specialized in analyzing call center transcripts for quality assurance based on predefined criteria for EOS Spain. Your task is to evaluate the specified compliance items based *strictly* on the provided transcript, call metadata, and evaluation rules. Use the K+ data snapshot provided to verify system state when rules require it. Respond ONLY with the requested JSON object or list of JSON objects."
    user_message = prompt

    messages = [
        {"role": "system", "content": "You are an AI assistant specialized in analyzing call center transcripts for quality assurance based on predefined criteria for EOS Spain. Your task is to evaluate the specified compliance items based *strictly* on the provided transcript, call metadata, and evaluation rules. Use the K+ data snapshot provided to verify system state when rules require it. Respond ONLY with the requested JSON object or list of JSON objects."},
        {"role": "user", "content": prompt}
    ]

    # --- Contabilizar tokens de entrada ---
    # Contar tokens en los mensajes que se enviarán
    # La función count_tokens de tiktoken para mensajes de chat es más compleja que simple conteo de texto.
    # Incluye tokens especiales por rol, etc.
    # Una aproximación simple es sumar los tokens de los contenidos:
    input_tokens = count_tokens(system_message) + count_tokens(user_message)
    # Una aproximación más precisa con tiktoken (requiere la librería instalada y el nombre exacto del modelo):
    # try:
    #     input_tokens = len(tiktoken.encoding_for_model(config_manager.get("openai.deployment_name")).encode_messages(messages))
    # except Exception as e:
    #     print(f"Warning: Could not use tiktoken.encoding_for_model for input token counting: {e}. Falling back to simple content sum.")
    #     input_tokens = count_tokens(system_message) + count_tokens(user_message)

    try:
        # print(f"Sending prompt for {evaluation_key} ({item_ids})...") # Debugging print
        # print(f"Prompt:\n{prompt}\n---\n") # Debugging print full prompt

        response = openai_client.chat.completions.create(
            model=config_manager.config_manager.get("openai.deployment_name"),
            messages=messages,
            temperature=0, # Usar temperatura baja para resultados más deterministas
            # max_tokens=... # Considerar ajustar si las transcripciones o prompts combinados son muy largos
        )
        llm_output_string = response.choices[0].message.content.strip()

        # --- Contabilizar tokens de salida ---
        output_tokens = count_tokens(llm_output_string)
        # O usando la info de uso de la respuesta (más precisa si la API lo proporciona):
        # if response.usage:
        #      input_tokens_api = response.usage.prompt_tokens
        #      output_tokens_api = response.usage.completion_tokens
        #      # Usar estos si están disponibles, son más precisos que el conteo manual
        #      # Puedes loguear o retornar ambos para comparación/verificación
        #      # Para simplicidad ahora, retornamos el conteo manual, pero ten en cuenta response.usage

        # Limpiar posibles marcadores de código JSON
        if llm_output_string.startswith("```json"):
            llm_output_string = llm_output_string[len("```json"):].strip()
            if llm_output_string.endswith("```"):
                llm_output_string = llm_output_string[:-len("```")].strip()

        # Intentar parsear la respuesta.
        try:
            parsed_output = json.loads(llm_output_string)
        except json.JSONDecodeError:
             print(f"Error decoding JSON from LLM output for {evaluation_key}:\n{llm_output_string}")
             # Retorna resultados de error si falla el parsing
             error_results = [{"item_id": item_id, "result": "Error", "reason": f"JSON decoding error: {llm_output_string[:150]}...", "transcript_segment": llm_output_string} for item_id in item_ids]
             return error_results, input_tokens, output_tokens # Retorna tokens contados incluso en error

        # Validar y estandarizar la salida
        results = []
        if evaluation_key.endswith("_group"): # Esperamos una lista para grupos
            if isinstance(parsed_output, list):
                for item_result in parsed_output:
                    # Validación básica de cada objeto en la lista
                    if isinstance(item_result, dict) and item_result.get('item_id') in item_ids and 'result' in item_result and 'reason' in item_result:
                        if 'transcript_segment' not in item_result: item_result['transcript_segment'] = ""
                        results.append(item_result)
                    else:
                        print(f"Warning: Malformed item result in list for {evaluation_key}: {json.dumps(item_result)[:100]}...")
                        # Añadir un resultado de error para el ítem malformado si se puede identificar el item_id
                        item_id_from_output = item_result.get('item_id', 'Unknown')
                        if item_id_from_output not in item_ids: item_id_from_output = "Unknown"
                        results.append({"item_id": item_id_from_output, "result": "Error", "reason": f"Malformed item output from LLM: {json.dumps(item_result)[:100]}...", "transcript_segment": ""})

                # Verificar si faltan ítems en la respuesta del LLM para el grupo
                returned_item_ids = {res.get('item_id') for res in results if isinstance(res, dict)}
                missing_item_ids = set(item_ids) - returned_item_ids
                for missing_id in missing_item_ids:
                    print(f"Warning: LLM did not return result for item {missing_id} in group {evaluation_key}. Adding error result.")
                    results.append({"item_id": missing_id, "result": "Error", "reason": "LLM did not return result for this item in the group.", "transcript_segment": ""})
            else:
                print(f"Warning: LLM output for group {evaluation_key} is not a list:\n{llm_output_string}")
                # Retorna resultados de error para todos los ítems esperados si la salida es del tipo incorrecto
                results = [{"item_id": item_id, "result": "Error", "reason": f"LLM output for group not list: {llm_output_string[:150]}...", "transcript_segment": llm_output_string} for item_id in item_ids]

        else: # Esperamos un diccionario para ítems individuales
             if isinstance(parsed_output, dict) and parsed_output.get('item_id') == item_ids[0] and 'result' in parsed_output and 'reason' in parsed_output:
                if 'transcript_segment' not in parsed_output: parsed_output['transcript_segment'] = ""
                results.append(parsed_output)
             else:
                print(f"Warning: LLM output for individual item {evaluation_key} is not in expected format:\n{llm_output_string}")
                # Añadir un resultado de error para el ítem esperado
                results.append({"item_id": item_ids[0], "result": "Error", "reason": f"LLM output format error for individual item: {llm_output_string[:150]}...", "transcript_segment": llm_output_string})

        return results, input_tokens, output_tokens # Retorna resultados Y conteos de tokens

    except Exception as e:
        print(f"Error calling Azure OpenAI API for {evaluation_key}: {e}")
        # Retornar resultados de error para todos los ítems esperados si falla la API
        return [{"item_id": item_id, "result": "Error", "reason": f"API error: {e}", "transcript_segment": ""} for item_id in item_ids], input_tokens, 0 # Retorna input_tokens contados, output_tokens es 0 si API falla
