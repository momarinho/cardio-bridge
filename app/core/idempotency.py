import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.idempotency import IdempotencyRecord
from app.core.config import settings

def calcular_hash_payload(payload_str: str) -> str:
    """
    Gera um hash SHA-256 do corpo da requisição.
    Garante que duas requisições com a mesma chave tenham exatamente o mesmo conteúdo.
    """
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

class IdempotencyChecker:
    """
    Gerenciador de Idempotência Transacional.
    Evita que instabilidades de rede ou múltiplos cliques gerem
    faturas, boletos ou inscrições duplicadas no SAP Business One.
    """
    def __init__(
        self,
        db: Session = Depends(get_db),
        idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
    ):
        self.db = db
        self.key = idempotency_key

    def verificar_registro(self, endpoint: str, payload_str: str) -> Optional[IdempotencyRecord]:
        """
        Verifica se a chave já foi processada.
        Se existir e não tiver expirado, retorna o registro salvo para cache hit.
        Se a chave for repetida mas o payload for diferente, acusa inconsistência (409 Conflict).
        """
        if not self.key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O cabeçalho 'Idempotency-Key' é obrigatório para operações financeiras."
            )

        payload_hash = calcular_hash_payload(payload_str)

        registro = self.db.query(IdempotencyRecord).filter(
            IdempotencyRecord.idempotency_key == self.key
        ).first()

        if registro:
            # Se já expirou o TTL, remove o registro antigo
            if datetime.utcnow() > registro.expires_at:
                self.db.delete(registro)
                self.db.commit()
                return None

            # Proteção contra adulteração de payload com a mesma chave
            if registro.request_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A Idempotency-Key enviada já foi utilizada com um payload diferente."
                )

            return registro

        return None

    def salvar_resposta(self, endpoint: str, payload_str: str, status_code: int, response_body: str):
        """
        Grava a resposta final para interceptar chamadas duplicadas subsequentes.
        """
        payload_hash = calcular_hash_payload(payload_str)
        expira_em = datetime.utcnow() + timedelta(seconds=settings.IDEMPOTENCY_EXPIRE_SECONDS)

        novo_registro = IdempotencyRecord(
            idempotency_key=self.key,
            method="POST",
            endpoint=endpoint,
            request_hash=payload_hash,
            response_status=status_code,
            response_body=response_body,
            expires_at=expira_em
        )
        self.db.add(novo_registro)
        self.db.commit()
