from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    """
    Tabela de auditoria para rastreamento de transações e integrações.
    Permite à controladoria/financeiro auditar todas as chamadas recebidas e feitas.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(255), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    client_ip = Column(String(50), nullable=True)
    request_payload = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=False)
