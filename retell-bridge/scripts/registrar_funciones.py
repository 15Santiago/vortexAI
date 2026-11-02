"""Register the Vortex catalog and screen-navigation tools in a Retell agent."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv, set_key
from retell import Retell

BRIDGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRIDGE_ROOT))

load_dotenv(BRIDGE_ROOT / ".env")

PROMPT_MARKER = "## Control de pantalla de VortexAI"
SCREEN_PROMPT = f"""{PROMPT_MARKER}
El usuario ve la tienda VortexAI en su pantalla y tú puedes controlarla con tus funciones.

- Cuando uses buscar_productos o mejores_ofertas, los resultados se muestran automáticamente en el catálogo. Dile "Te los estoy mostrando en pantalla" y menciona solo los 2 o 3 mejores.
- Cuando uses detalle_producto, la página de ese producto se abre automáticamente.
- Si el usuario pide ir a inicio, catálogo, métricas o perfil, o abrir un producto que ya mencionaste, usa navegar. Para un producto, envía seccion="producto" y producto_id con el id devuelto por la búsqueda o el detalle.
- Después de cada herramienta, responde en voz alta con el resultado y sigue la conversación: no te quedes callado, no llames end_call y mantén la llamada abierta para escuchar la siguiente petición.
- Solo usa end_call si el usuario pide terminar o se despide claramente. Después de mostrar resultados, pregunta brevemente si quiere otro producto o más detalles y continúa escuchando.
- Nunca digas que no puedes mover la pantalla.
"""

TOOL_SCHEMAS: tuple[dict[str, Any], ...] = (
    {
        "name": "buscar_productos",
        "path": "/retell/buscar-productos",
        "description": "Busca productos del catálogo con palabras clave y filtros de precio, calificación, descuento y orden.",
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Producto o palabras clave buscadas, en español o inglés."},
                "precio_max": {"type": "number", "description": "Precio máximo en dólares."},
                "calificacion_min": {"type": "number", "description": "Calificación mínima de 0 a 5."},
                "solo_descuento": {"type": "boolean", "description": "Limitar a productos con descuento."},
                "orden": {
                    "type": "string",
                    "enum": ["relevancia", "precio_menor", "calificacion", "descuento", "mas_resenas"],
                },
                "categoria": {"type": "string", "description": "Categoría, si el usuario la especifica."},
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "detalle_producto",
        "path": "/retell/detalle-producto",
        "description": "Obtiene el detalle de un producto usando el id devuelto por una búsqueda.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "integer", "description": "Id interno del producto."}},
            "required": ["id"],
        },
    },
    {
        "name": "mejores_ofertas",
        "path": "/retell/mejores-ofertas",
        "description": "Encuentra productos con descuentos destacados, opcionalmente por tipo y precio máximo.",
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Tipo de producto buscado."},
                "categoria": {"type": "string", "description": "Categoría, si el usuario la especifica."},
                "precio_max": {"type": "number", "description": "Precio máximo en dólares."},
            },
        },
    },
    {
        "name": "navegar",
        "path": "/retell/navegar",
        "description": "Abre una sección de la tienda o un producto mencionado previamente.",
        "parameters": {
            "type": "object",
            "properties": {
                "seccion": {
                    "type": "string",
                    "enum": ["inicio", "catalogo", "metricas", "perfil", "producto"],
                },
                "producto_id": {
                    "type": "integer",
                    "description": "Id interno del producto; obligatorio si seccion es producto.",
                },
            },
            "required": ["seccion"],
        },
    },
)

LLM_CREATE_FIELDS = frozenset(
    {
        "backup_model",
        "begin_after_user_silence_ms",
        "begin_message",
        "default_dynamic_variables",
        "general_prompt",
        "general_tools",
        "is_transfer_llm",
        "kb_config",
        "knowledge_base_ids",
        "mcps",
        "model",
        "model_config",
        "model_high_priority",
        "model_temperature",
        "model_ultrafast",
        "s2s_model",
        "start_speaker",
        "starting_state",
        "states",
        "tool_call_strict_mode",
    }
)
AGENT_CREATE_FIELDS = frozenset(
    {
        "agent_name",
        "allow_user_dtmf",
        "contact_memory_config",
        "data_storage_setting",
        "enable_expressive_mode",
        "end_call_after_silence_ms",
        "fallback_voice_ids",
        "handbook_config",
        "interruption_sensitivity",
        "language",
        "max_call_duration_ms",
        "opt_in_signed_url",
        "pii_config",
        "post_call_analysis_model",
        "response_engine",
        "timezone",
        "user_dtmf_options",
        "version_description",
        "voice_id",
        "voice_speed",
        "voice_temperature",
        "voicemail_option",
        "volume",
    }
)


def _tool_payload(schema: dict[str, Any], base_url: str) -> dict[str, Any]:
    return {
        "type": "custom",
        "name": schema["name"],
        "description": schema["description"],
        "url": f"{base_url}{schema['path']}",
        "method": "POST",
        "parameters": schema["parameters"],
        "args_at_root": False,
        "speak_during_execution": True,
        "speak_after_execution": True,
    }


def _prompt_with_screen_instructions(current: str | None) -> str:
    prompt = (current or "").rstrip()
    if PROMPT_MARKER in prompt:
        prompt = prompt.split(PROMPT_MARKER, 1)[0].rstrip()
    return f"{prompt}\n\n{SCREEN_PROMPT}".strip()


def _llm_create_payload(
    current: dict[str, Any],
    tools: list[dict[str, Any]],
    prompt: str,
) -> dict[str, Any]:
    payload = {key: value for key, value in current.items() if key in LLM_CREATE_FIELDS}
    payload["general_tools"] = tools
    payload["general_prompt"] = prompt
    return payload


def _agent_create_payload(
    current: dict[str, Any],
    response_engine: dict[str, Any],
) -> dict[str, Any]:
    payload = {key: value for key, value in current.items() if key in AGENT_CREATE_FIELDS}
    payload["response_engine"] = response_engine
    payload["version_description"] = "VortexAI voice assistant with catalog continuity"
    return payload


def _find_matching_replacement_llm(
    client: Any,
    current: dict[str, Any],
    tools: list[dict[str, Any]],
    prompt: str,
) -> Any | None:
    expected = _llm_create_payload(current, tools, prompt)
    page = client.llm.list(limit=100)
    while True:
        for item in page.items:
            data = item.model_dump(mode="json", exclude_none=True, by_alias=True)
            if data.get("is_published") is False and all(
                data.get(key) == value for key, value in expected.items()
            ):
                return item
        if not page.has_more or not page.pagination_key:
            return None
        page = client.llm.list(limit=100, pagination_key=page.pagination_key)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Public HTTPS base URL for retell-bridge.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect the agent and print proposed tools without changing Retell.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    parsed_url = urlparse(args.url)
    if parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.path not in ("", "/"):
        print("ERROR: --url must be a public HTTPS base URL without a path.")
        return 2

    api_key = os.getenv("RETELL_API_KEY", "").strip()
    agent_id = os.getenv("RETELL_AGENT_ID", "").strip()
    if not api_key or not agent_id:
        print("ERROR: RETELL_API_KEY and RETELL_AGENT_ID must be configured in retell-bridge/.env.")
        return 2

    base_url = args.url.rstrip("/")
    stage = "initializing Retell client"
    try:
        client = Retell(api_key=api_key)
        stage = "retrieving agent"
        agent = client.agent.retrieve(agent_id=agent_id)
        engine = agent.response_engine
        if engine.type != "retell-llm":
            print("ERROR: The configured Retell agent does not use a Retell LLM response engine.")
            return 2

        stage = "retrieving LLM"
        llm = client.llm.retrieve(llm_id=engine.llm_id)
        llm_data = llm.model_dump(mode="json", exclude_none=True)
        existing_tools = llm_data.get("general_tools", [])
        replacement_names = {schema["name"] for schema in TOOL_SCHEMAS}
        preserved_tools = [
            tool for tool in existing_tools
            if not (isinstance(tool, dict) and tool.get("name") in replacement_names)
        ]
        proposed_tools = preserved_tools + [
            _tool_payload(schema, base_url) for schema in TOOL_SCHEMAS
        ]
        proposed_prompt = _prompt_with_screen_instructions(llm_data.get("general_prompt", ""))

        print(f"Agent: {agent.agent_name}")
        print(f"Mode: {'DRY RUN — no Retell changes will be made' if args.dry_run else 'LIVE REGISTRATION'}")
        print(f"{'Tool':24} {'Method':8} Endpoint")
        for schema in TOOL_SCHEMAS:
            print(f"{schema['name']:24} {'POST':8} {base_url}{schema['path']}")
        preserved_names = [
            tool.get("name", "existing tool")
            for tool in preserved_tools
            if isinstance(tool, dict)
        ]
        if preserved_names:
            print("Preserved existing tools: " + ", ".join(preserved_names))
        print(
            "Screen instructions: "
            + (
                "already current"
                if proposed_prompt == llm_data.get("general_prompt", "")
                else "will be updated"
                if PROMPT_MARKER in (llm_data.get("general_prompt") or "")
                else "will be appended"
            )
        )
        if (
            proposed_prompt == llm_data.get("general_prompt", "")
            and proposed_tools == existing_tools
        ):
            print("Tools and prompt are already current; no Retell changes are needed.")
            return 0
        if llm_data.get("is_published"):
            print("Published LLM: a replacement will be created to preserve the published version.")
        if agent.is_published:
            print("Published agent: a replacement will be created and the bridge config updated.")

        if args.dry_run:
            return 0

        if llm_data.get("is_published"):
            stage = "finding or creating replacement LLM"
            updated_llm = _find_matching_replacement_llm(
                client,
                llm_data,
                proposed_tools,
                proposed_prompt,
            )
            if updated_llm is None:
                updated_llm = client.llm.create(
                    **_llm_create_payload(llm_data, proposed_tools, proposed_prompt)
                )
        else:
            stage = "updating LLM"
            updated_llm = client.llm.update(
                llm_id=engine.llm_id,
                general_tools=proposed_tools,
                general_prompt=proposed_prompt,
            )
        response_engine = {
            "type": "retell-llm",
            "llm_id": updated_llm.llm_id,
            "version": updated_llm.version,
        }
        if agent.is_published:
            stage = "creating replacement agent"
            updated_agent = client.agent.create(
                **_agent_create_payload(
                    agent.model_dump(mode="json", exclude_none=True, by_alias=True),
                    response_engine,
                )
            )
        else:
            stage = "updating agent"
            updated_agent = client.agent.update(
                agent_id=agent_id,
                response_engine=response_engine,
                version_description="Register VortexAI catalog and screen actions",
            )
        stage = "publishing agent"
        client.agent.publish(agent_id=updated_agent.agent_id, version=updated_agent.version)
        if agent.is_published:
            stage = "updating bridge agent configuration"
            set_key(str(BRIDGE_ROOT / ".env"), "RETELL_AGENT_ID", updated_agent.agent_id)
        print("Registration and agent publication completed.")
        print("Registered tools: end_call + " + " + ".join(schema["name"] for schema in TOOL_SCHEMAS))
        if agent.is_published:
            print("Bridge config updated. Restart retell-bridge to use the replacement agent.")
        return 0
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        suffix = f" (HTTP {status_code})" if isinstance(status_code, int) else ""
        print(f"ERROR: Retell registration failed while {stage}: {type(exc).__name__}{suffix}.")
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            detail = body.get("message") or body.get("detail")
            if isinstance(detail, str):
                print(f"Retell detail: {detail[:300]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
