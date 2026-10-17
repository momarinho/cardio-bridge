from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.associado import MedicoCreateSchema, MedicoResponseSchema
from app.models.audit import AuditLog
import time

# O APIRouter funciona como um agrupador de rotas
# Todas as rotas aqui dentro terão a tag "Associados (Médicos)"

router = APIRouter(prefix="/associados", tags=["Associados (Médicos)"])


@router.post(
    "/sync",
    response_model=MedicoResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar ou Sincronizar Médico Associado"
)
def sincronizar_medico(
        medico_in: MedicoCreateSchema,
        db: Session = Depends(get_db),
):
    """
    Recebe os dados cadastrais de um cardiologista, valida CRM/UF
    e prepara o registro no formato exigido pela SBC e SAP B1
    """
    inicio = time.time()

    # 1. No SAP B1, todo Parceiro de Negócio (OCRD) tem um código único chamado CardCode.
    # Na SBC, a regra de negócio comum é: "MED-" + UF + "-" + CRM (ex: MED-RJ-123456).
    card_code_sap = f"MED-{medico_in.uf}-{medico_in.crm}"

    # 2. Montamos o objeto de resposta padrão do schema de saída
    resposta = MedicoResponseSchema(
        card_code=card_code_sap,
        crm=medico_in.crm,
        uf=medico_in.uf,
        nome=medico_in.nome,
        cpf=medico_in.cpf,
        email=medico_in.email,
        especialidade_rqe=medico_in.especialidade_rqe,
        telefone=medico_in.telefone,
        status_anuidade="EM_DIA",
        sap_synced=True
    )

    # 3. Auditoria: Todo endpoint corporativo sério registra o que aconteceu
    tempo_execucao = (time.time() - inicio) * 1000  # em milissegundos
    log = AuditLog(
        method="POST",
        endpoint="/api/v1/associados/sync",
        status_code=201,
        client_ip="127.0.0.1",
        request_payload=medico_in.model_dump_json(),
        response_body=resposta.model_dump_json(),
        execution_time_ms=tempo_execucao
    )

    db.add(log)
    db.commit()

    return resposta
