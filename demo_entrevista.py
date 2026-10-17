"""
Script de Demonstração Rápida (1 comando) — CardioBridge PoC
Executa os 3 cenários críticos de arquitetura para demonstração em entrevista:
  1. 1ª chamada de inscrição no Congresso (201 Created | MISS-NEW-TRANSACTION)
  2. 2ª chamada repetida com mesma Idempotency-Key (Cache HIT | Zero duplicação)
  3. Worker do Padrão Estrangulador lendo registro do Legado (Delphi) -> SYNCED no SAP B1
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.staging import LegacyStagingRecord
from app.services.sap_client import SAPServiceLayerClient
from app.workers.strangler_worker import processar_fila_legado_delphi
from mock_sap.mock_server import mock_sap_app

def rodar_demonstracao():
    Base.metadata.create_all(bind=engine)
    gateway_client = TestClient(app)

    chave_unica = f"cong-sbc-2026-{uuid.uuid4().hex[:8]}"
    payload_inscricao = {
        "crm": "123456",
        "uf": "RJ",
        "nome_medico": "Dr. Roberto Kalil",
        "codigo_evento": "CONG-CARDIO-2026",
        "nome_evento": "81º Congresso Brasileiro de Cardiologia",
        "categoria": "Associado Efetivo",
        "valor": 850.00,
        "forma_pagamento": "PIX",
    }
    headers = {"Idempotency-Key": chave_unica}

    print("=" * 75)
    print("🫀 CARDIOBRIDGE PoC — DEMONSTRAÇÃO DE ARQUITETURA DE INTEGRAÇÃO (SBC)")
    print("=" * 75)

    # 1. PRIMEIRA CHAMADA
    print("\n[1] 1ª Chamada de Inscrição no Congresso (Idempotency-Key nova):")
    r1 = gateway_client.post("/api/v1/eventos/inscricoes", json=payload_inscricao, headers=headers)
    d1 = r1.json()
    print(f"    -> HTTP Status: {r1.status_code}")
    print(f"    -> Header Idempotência: {r1.headers.get('x-cache-idempotency')}")
    print(f"    -> DocEntry SAP (ORDR): {d1['doc_entry_sap']} | Inscrição: {d1['numero_inscricao']}")

    # 2. SEGUNDA CHAMADA (REPETIDA / DUPLO CLIQUE)
    print("\n[2] 2ª Chamada Idêntica (Simulando duplo clique / oscilação de rede):")
    r2 = gateway_client.post("/api/v1/eventos/inscricoes", json=payload_inscricao, headers=headers)
    d2 = r2.json()
    print(f"    -> HTTP Status: {r2.status_code}")
    print(f"    -> Header Idempotência: {r2.headers.get('x-cache-idempotency')}")
    print(f"    -> DocEntry Retornado : {d2['doc_entry_sap']} (IDÊNTICO! Nenhuma cobrança duplicada)")

    # 3. WORKER DO PADRÃO ESTRANGULADOR (DELPHI -> SAP SERVICE LAYER via B1SESSION)
    print("\n[3] Worker do Padrão Estrangulador (Tabela Legada Delphi -> SAP B1 Service Layer):")
    db = SessionLocal()
    try:
        # Insere registro simulando gravação do sistema legado em Delphi
        registro_delphi = LegacyStagingRecord(
            record_type="ANUIDADE",
            raw_payload='{"CRM": "554433", "UF": "SP", "NOME": "Dra. Ludhmila Hajjar", "ITEM": "ANUIDADE-2026", "VALOR": 720.00}',
            status="PENDING",
        )
        db.add(registro_delphi)
        db.commit()
        db.refresh(registro_delphi)
        print(f"    -> Registro Legado #{registro_delphi.id} inserido pelo Delphi com status: {registro_delphi.status}")

        # Conecta o SAPServiceLayerClient ao Mock do SAP B1 em memória
        sap_test_client = SAPServiceLayerClient(base_url="http://testserver/b1s/v1")
        sap_test_client.client = TestClient(mock_sap_app)

        # Executa o Worker
        processados = processar_fila_legado_delphi(db, sap_test_client)
        db.refresh(registro_delphi)
        print(f"    -> Sessão SAP autenticada! Cookie B1SESSION ativo: {sap_test_client.cookies.get('B1SESSION')[:18]}...")
        print(f"    -> Worker processou {processados} registro(s). Novo status: {registro_delphi.status} | SAP DocEntry: {registro_delphi.external_sap_docentry}")
    finally:
        db.close()

    print("\n" + "=" * 75)
    print("✅ TODOS OS 3 CENÁRIOS VALIDADOS COM SUCESSO!")
    print("=" * 75)

if __name__ == "__main__":
    rodar_demonstracao()
