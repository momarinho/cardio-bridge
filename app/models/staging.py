from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import Base

class LegacyStagingRecord(Base):
    """
    Tabela de Staging para o Padrão Estrangulador (Strangler Fig Pattern).
    Simula o ponto onde sistemas legados (desktop/Delphi) inserem dados brutos.
    O worker em Python monitora os registros com status 'PENDING' e os sincroniza
    com a Service Layer do SAP B1 de forma assíncrona e segura.
    """
    __tablename__ = "legacy_staging_records"

    id = Column(Integer, primary_key=True, index=True)
    record_type = Column(String(50), nullable=False, index=True)  # 'MEDICO', 'ANUIDADE', 'EVENTO'
    raw_payload = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING", index=True)  # 'PENDING', 'PROCESSING', 'SYNCED', 'ERROR'
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    external_sap_docentry = Column(Integer, nullable=True)  # Código DocEntry gerado no SAP B1
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
