# Importa as bibliotecas utilizadas
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set

import requests
from dotenv import load_dotenv
from requests import Response, Session
from requests.exceptions import RequestException
from supabase import Client, create_client


# Configuração de ambiente e logging
# Python-dotenv que carrega as variáveis
load_dotenv()

#Registra os loggins
logging.basicConfig(
    filename="logging.log",
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(filename)s | %(lineno)d | %(message)s"
)
logger = logging.getLogger(__name__)


def get_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


#Autenticação do [Supabase]
SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_KEY")


#Autenticação do [Z-api]
ZAPI_INSTANCE_ID = get_env("ZAPI_INSTANCE_ID")
ZAPI_INSTANCE_TOKEN = get_env("ZAPI_INSTANCE_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN", "").strip()


#Mensagem a ser enviada
MESSAGE_TEMPLATE = get_env(
    "MESSAGE_TEMPLATE",
    required=False,
    default="Olá, <nome_contato> tudo bem com você?"
)

MAX_CONTACTS = int(get_env("MAX_CONTACTS", required=False, default="3"))


# Clientes do banco de dados [Supabase]
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Configuração do Z-api
# ------------------------------------------------------------------------------
def sanitize_phone(phone: str) -> str:
    """Mantém apenas dígitos. A Z-API exige telefone com DDI+DDD+número."""
    return re.sub(r"\D", "", phone or "")


def build_message(template: str, nome_contato: str) -> str:
    nome = (nome_contato or "").strip() or "cliente"
    return template.replace("<nome_contato>", nome)


def build_zapi_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json"
    }
    if ZAPI_CLIENT_TOKEN:
        headers["Client-Token"] = ZAPI_CLIENT_TOKEN
    return headers


def build_zapi_base_url() -> str:
    return f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}"


# Supabase: busca os contatos
def fetch_contacts(limit: int) -> List:
    """
    Busca contatos ativos na tabela 'contatos', remove números duplicados
    e retorna até 'limit' contatos válidos.
    """
    supabase = get_supabase_client()

    logger.info("Buscando contatos no Supabase...")
    response = (
        supabase
        .table("contatos")
        .select("id, nome, telefone, ativo") 
        .eq("ativo", True)
        .execute()
    )

    rows = response.data or []

    seen: Set[str] = set()
    selected: List[Dict] = []

    for row in rows:
        raw_phone = row.get("telefone", "")
        phone = sanitize_phone(raw_phone)

        if not phone:
            logger.warning("Contato sem telefone válido ignorado: %s", row)
            continue

        if phone in seen:
            logger.info("Telefone duplicado ignorado: %s", phone)
            continue

        seen.add(phone)
        selected.append(
            {
                "id": row.get("id"),
                "nome": row.get("nome", ""),
                "telefone": phone,
            }
        )

        if len(selected) >= limit:
            break

    logger.info("Total de contatos selecionados: %s", len(selected))
    return selected


# Z-API: Verifica o status da instância
def check_zapi_status(session: Session) -> bool:
    """
    Verifica se a instância Z-API está conectada a uma conta do WhatsApp.
    """
    url = f"{build_zapi_base_url()}/status"
    headers = build_zapi_headers()

    logger.info("Verificando status da instância Z-API...")
    try:
        response = session.get(url, headers=headers, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()

        connected = data.get("connected", False)
        smartphone_connected = data.get("smartphoneConnected", False)
        status_message = data.get("error", "")

        logger.info(
            "Z-API status | connected=%s | smartphoneConnected=%s | detail=%s",
            connected,
            smartphone_connected,
            status_message
        )

        return bool(connected)
    except RequestException as exc:
        logger.error("Falha ao consultar status da Z-API: %s", exc)
        return False
    except ValueError:
        logger.error("Resposta inválida ao consultar status da Z-API.")
        return False


# Z-API: Envia a mensagem de texto
def send_text_message(session: Session, phone: str, message: str) -> Dict:
    """
    Envia mensagem de texto para um telefone usando Z-API.
    """
    url = f"{build_zapi_base_url()}/send-text"
    headers = build_zapi_headers()
    payload = {
        "phone": phone,
        "message": message
    }

    try:
        response: Response = session.post(
            url,
            json=payload,
            headers=headers,
            timeout=(5, 20)
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            data = {"raw_response": response.text}

        return {
            "success": True,
            "status_code": response.status_code,
            "data": data
        }

    except RequestException as exc:
        raw_response = ""
        if hasattr(exc, "response") and exc.response is not None:
            raw_response = exc.response.text

        return {
            "success": False,
            "error": str(exc),
            "raw_response": raw_response
        }


# Orquestração principal
def main() -> int:
    logger.info("Iniciando rotina de envio...")

    try:
        contacts = fetch_contacts(MAX_CONTACTS)
    except Exception as exc:
        logger.exception("Erro ao buscar contatos no Supabase: %s", exc)
        return 1

    if not contacts:
        logger.warning("Nenhum contato disponível para envio.")
        return 0

    with requests.Session() as session:
        if not check_zapi_status(session):
            logger.error("A instância Z-API não está conectada. Conecte o WhatsApp e tente novamente.")
            return 1

        sent_count = 0

        for contact in contacts:
            nome = contact["nome"]
            phone = contact["telefone"]
            message = build_message(MESSAGE_TEMPLATE, nome)

            logger.info("Enviando mensagem para %s (%s)...", nome, phone)
            result = send_text_message(session, phone, message)

            if result["success"]:
                sent_count += 1
                logger.info("Envio OK para %s | resposta=%s", phone, result["data"])
            else:
                logger.error(
                    "Falha no envio para %s | erro=%s | resposta=%s",
                    phone,
                    result.get("error"),
                    result.get("raw_response")
                )

        logger.info("Processo finalizado. Total enviado com sucesso: %s", sent_count)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("Execução interrompida pelo usuário.")
        sys.exit(130)
