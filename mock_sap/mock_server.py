import random
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel


# Criamos app FastAPI para simular servidor SAP
mock_sap_app = FastAPI(
    title="SAP Business One Service Layer (MOCK)",
    version="10.0 (FP 2208)",
    description=(
        "Emulador da Service Layer OData do SAP B1 para desenvolvimento e testes."
    ),
)

# Simulamos base de dados em memória
BANCO_SAP_MEMORIA = {
    # Tabela OCRD: Business Partners (Médicos Associados)
    "BusinessPartners": {
        "MED-RJ-123456": {
            "CardCode": "MED-RJ-123456",
            "CardName": "Dr. Roberto Kalil",
            "CardType": "cCustomer",
            "FederalTaxID": "12345678901",
            "EmailAddress": "kalil@cardiol.br",
            "U_CRM": "123456",
            "U_UF": "RJ",
            "U_StatusAnuidade": "EM_DIA",
        }
    },
    # Tabela ORDR: Sales Orders (Inscrições em Congressos / Eventos)
    "Orders": {},
    # Tabela OINV: Invoices (Faturas de Anuidades)
    "Invoices": {},
    # Sessões ativas de login
    "ActiveSessions": set(),
}


# SCHEMAS DE ENTRADA DO SAP B1
class SAPLoginRequest(BaseModel):
    CompanyDB: str
    UserName: Optional[str] = None
    Username: Optional[str] = None
    Password: str


class DocumentLineItem(BaseModel):
    ItemCode: str
    Quantity: float = 1.0
    UnitPrice: float


class SAPOrderCreate(BaseModel):
    CardCode: str
    Comments: Optional[str] = None
    DocDueDate: Optional[str] = None
    DocumentLines: List[DocumentLineItem]


# ENDPOINTS OFICIAIS DA SERVICE LAYER (ODATA)
@mock_sap_app.post("/b1s/v1/Login", summary="Autenticação na Service Layer")
def sap_login(creds: SAPLoginRequest, response: Response):
    """
    Simula o Login oficial da Service Layer do SAP B1.
    Retorna os cookies de sessão: B1SESSION e ROUTEID.
    """
    usuario = creds.UserName or creds.Username
    if usuario != "manager" or creds.Password != "password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": 100,
                    "message": "Credenciais inválidas para o banco SAP.",
                }
            },
        )

    # Gera um token único simulando a sessão do SAP
    session_id = str(uuid.uuid4())
    route_id = ".node1"
    BANCO_SAP_MEMORIA["ActiveSessions"].add(session_id)

    # Define os cookies de resposta no padrão exato da SAP
    response.set_cookie(key="B1SESSION", value=session_id, httponly=True)
    response.set_cookie(key="ROUTEID", value=route_id)

    return {
        "SessionId": session_id,
        "Version": "1000220",
        "SessionTimeout": 30,  # minutos
    }


def verificar_sessao_sap(request: Request):
    """Checa se o cookie B1SESSION foi enviado na requisição."""
    session_id = request.cookies.get("B1SESSION")
    if (
        not session_id
        or session_id not in BANCO_SAP_MEMORIA["ActiveSessions"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": 301,
                    "message": "Sessão inválida ou expirada na Service Layer.",
                }
            },
        )
    return session_id


@mock_sap_app.get(
    "/b1s/v1/BusinessPartners('{card_code}')",
    summary="Consultar Médico Associado (OCRD)",
)
def get_business_partner(card_code: str, request: Request):
    """Consulta os dados de um médico parceiro pelo CardCode na tabela OCRD."""
    verificar_sessao_sap(request)

    bp = BANCO_SAP_MEMORIA["BusinessPartners"].get(card_code)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": 404,
                    "message": f"Parceiro {card_code} não encontrado no SAP.",
                }
            },
        )
    return bp


@mock_sap_app.post(
    "/b1s/v1/BusinessPartners",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Parceiro (OCRD)",
)
def create_business_partner(payload: Dict[str, Any], request: Request):
    """Cria um novo médico associado na tabela OCRD."""
    verificar_sessao_sap(request)

    card_code = payload.get("CardCode")
    if not card_code:
        raise HTTPException(status_code=400, detail="CardCode é obrigatório.")

    BANCO_SAP_MEMORIA["BusinessPartners"][card_code] = payload
    return payload


@mock_sap_app.post(
    "/b1s/v1/Orders",
    status_code=status.HTTP_201_CREATED,
    summary="Criar Pedido de Venda (ORDR)",
)
def create_sales_order(order: SAPOrderCreate, request: Request):
    """
    Cria um pedido de venda no SAP B1 (tabela ORDR).
    Usado na SBC para registrar inscrições em congressos e eventos.
    """
    verificar_sessao_sap(request)

    # Verifica se o médico existe na OCRD
    if order.CardCode not in BANCO_SAP_MEMORIA["BusinessPartners"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"CardCode {order.CardCode} inexistente no SAP."
                }
            },
        )

    # Gera a chave primária oficial do SAP: DocEntry e DocNum
    doc_entry = random.randint(50000, 99999)
    doc_num = doc_entry

    total_pedido = sum(
        item.UnitPrice * item.Quantity for item in order.DocumentLines
    )

    registro_ordr = {
        "DocEntry": doc_entry,
        "DocNum": doc_num,
        "CardCode": order.CardCode,
        "DocTotal": total_pedido,
        "Comments": order.Comments,
        "DocumentStatus": "bost_Open",
        "DocumentLines": [
            line.model_dump() for line in order.DocumentLines
        ],
    }

    BANCO_SAP_MEMORIA["Orders"][doc_entry] = registro_ordr
    return registro_ordr
