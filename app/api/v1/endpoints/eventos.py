import json
import random
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.idempotency import IdempotencyChecker
from app.schemas.evento import InscricaoEventoSchema, InscricaoResponseSchema
from app.models.audit import AuditLog
import time

router = APIRouter(prefix="/eventos", tags=["Eventos & Congressos"])

@router.post(
    "/inscricoes",
    response_model=InscricaoResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrever Médico em Congresso (com Idempotência Transacional)"
)
def inscrever_congresso(
    inscricao_in: InscricaoEventoSchema,
    response: Response,
    idemp: IdempotencyChecker = Depends(),
    db: Session = Depends(get_db)
):
    """
    Realiza a inscrição de um médico cardiologista em congresso (ex: Congresso Brasileiro de Cardiologia).
    
    Protegido contra cliques múltiplos via **Idempotency-Key**:
    * 1ª requisição: Gera o pedido de venda no ERP e armazena o resultado.
    * Requisições repetidas: Retorna imediatamente a transação original via cache com header 'X-Cache-Idempotency: HIT'.
    """
    inicio = time.time()
    payload_str = inscricao_in.model_dump_json()

    # 1. Verifica se a requisição já foi processada anteriormente
    registro_existente = idemp.verificar_registro(
        endpoint="/api/v1/eventos/inscricoes",
        payload_str=payload_str
    )

    if registro_existente:
        # HIT DE IDEMPOTÊNCIA: Retorna a transação original sem chamar o ERP novamente!
        response.headers["X-Cache-Idempotency"] = "HIT-PREVIOUS-TRANSACTION"
        dados_salvos = json.loads(registro_existente.response_body)
        return dados_salvos

    # 2. Primeira vez que a chave chega: Processa a transação e simula geração do pedido SAP (ORDR)
    doc_entry_sap = random.randint(10000, 99999)
    numero_inscricao = f"CONG-2026-{inscricao_in.uf}-{doc_entry_sap}"
    card_code = f"MED-{inscricao_in.uf}-{inscricao_in.crm}"

    resposta = InscricaoResponseSchema(
        numero_inscricao=numero_inscricao,
        doc_entry_sap=doc_entry_sap,
        card_code=card_code,
        status="CONFIRMADO",
        valor=inscricao_in.valor,
        qr_code_pix="00020126580014br.gov.bcb.pix0136sbc-inscricoes-congresso-2026520400005303986540850.00",
        linha_digitavel_boleto="34191.79001 01043.510047 91020.150008 8 98760000085000",
        mensagem="Inscrição processada com sucesso no ERP SAP Business One."
    )

    # 3. Salva a resposta na tabela de idempotência
    idemp.salvar_resposta(
        endpoint="/api/v1/eventos/inscricoes",
        payload_str=payload_str,
        status_code=status.HTTP_201_CREATED,
        response_body=resposta.model_dump_json()
    )

    # 4. Registra log de auditoria
    tempo_execucao = (time.time() - inicio) * 1000
    log = AuditLog(
        method="POST",
        endpoint="/api/v1/eventos/inscricoes",
        status_code=201,
        client_ip="127.0.0.1",
        request_payload=payload_str,
        response_body=resposta.model_dump_json(),
        execution_time_ms=tempo_execucao
    )
    db.add(log)
    db.commit()

    response.headers["X-Cache-Idempotency"] = "MISS-NEW-TRANSACTION"
    return resposta
