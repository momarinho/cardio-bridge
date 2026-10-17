import pytest
from app.core.database import Base, engine, SessionLocal
from app.models.audit import AuditLog
from app.models.idempotency import IdempotencyRecord
from app.models.staging import LegacyStagingRecord
from app.schemas.associado import MedicoCreateSchema
from app.schemas.evento import InscricaoEventoSchema
from datetime import datetime, timedelta

def setup_module():
    # Cria as tabelas para teste
    Base.metadata.create_all(bind=engine)

def test_database_models_creation():
    db = SessionLocal()
    try:
        # 1. Teste AuditLog
        audit = AuditLog(
            method="POST",
            endpoint="/api/v1/eventos/inscricoes",
            status_code=201,
            client_ip="127.0.0.1",
            request_payload='{"crm": "123456"}',
            response_body='{"doc_entry": 999}',
            execution_time_ms=45.2
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        assert audit.id is not None
        assert audit.status_code == 201

        # 2. Teste IdempotencyRecord
        idemp = IdempotencyRecord(
            idempotency_key="key-test-12345",
            method="POST",
            endpoint="/api/v1/eventos/inscricoes",
            request_hash="a1b2c3d4e5f6",
            response_status=201,
            response_body='{"doc_entry": 1001}',
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(idemp)
        db.commit()
        db.refresh(idemp)
        assert idemp.id is not None
        assert idemp.idempotency_key == "key-test-12345"

        # 3. Teste LegacyStagingRecord (Padrão Estrangulador)
        staging = LegacyStagingRecord(
            record_type="MEDICO",
            raw_payload='{"CRM": "98765", "NOME": "Dr. Carlos Silva", "UF": "RJ"}',
            status="PENDING"
        )
        db.add(staging)
        db.commit()
        db.refresh(staging)
        assert staging.id is not None
        assert staging.status == "PENDING"
    finally:
        db.close()

def test_medico_schema_validation_success():
    payload = {
        "crm": "123.456",  # Deve sanitizar pontuação
        "uf": "rj",        # Deve converter para maiúsculo
        "nome": "Dra. Ana Paula Souza",
        "cpf": "12345678901",
        "email": "ana.paula@cardiol.br",
        "especialidade_rqe": "RQE-14520"
    }
    schema = MedicoCreateSchema(**payload)
    assert schema.crm == "123456"
    assert schema.uf == "RJ"
    assert schema.cpf == "12345678901"

def test_medico_schema_validation_invalid_uf():
    payload = {
        "crm": "123456",
        "uf": "XX",  # UF inexistente
        "nome": "Dr. Invalido",
        "cpf": "12345678901",
        "email": "invalido@cardiol.br"
    }
    with pytest.raises(ValueError):
        MedicoCreateSchema(**payload)

def test_inscricao_evento_schema():
    payload = {
        "crm": "654321",
        "uf": "SP",
        "nome_medico": "Dr. Roberto Mendes",
        "codigo_evento": "CONG-CARDIO-2026",
        "valor": 850.00,
        "forma_pagamento": "PIX"
    }
    inscricao = InscricaoEventoSchema(**payload)
    assert inscricao.valor == 850.00
    assert inscricao.uf == "SP"
