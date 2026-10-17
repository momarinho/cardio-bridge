from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import Base

class IdempotencyRecord(Base):
    """
    Tabela de Idempotência.
    Garante que requisições repetidas (ex: duplo clique em inscrição de congresso)
    não gerem faturas ou pedidos duplicados no SAP B1.
    """
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)  # SHA-256 do payload para checar integridade
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
