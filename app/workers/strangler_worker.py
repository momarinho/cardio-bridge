import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.staging import LegacyStagingRecord
from app.services.sap_client import SAPServiceLayerClient

def processar_fila_legado_delphi(db: Session, sap_client: SAPServiceLayerClient) -> int:
    """
    Worker do Padrão Estrangulador (Strangler Fig Pattern).
    Lê registros 'PENDING' deixados pelo sistema legado (Delphi) na tabela de staging,
    converte para o contrato OData da Service Layer e sincroniza com o SAP B1.
    """
    pendentes = (
        db.query(LegacyStagingRecord)
        .filter(LegacyStagingRecord.status == "PENDING")
        .all()
    )

    sincronizados = 0
    for registro in pendentes:
        try:
            registro.status = "PROCESSING"
            db.commit()

            dados = json.loads(registro.raw_payload)
            uf = dados.get("UF", "RJ").upper()
            crm = str(dados.get("CRM", "")).strip()
            card_code = f"MED-{uf}-{crm}"

            # 1. Garante que o médico existe na tabela OCRD do SAP B1 via Service Layer
            parceiro = sap_client.consultar_associado(card_code)
            if not parceiro:
                sap_client.cadastrar_associado({
                    "CardCode": card_code,
                    "CardName": dados.get("NOME", "Médico Associado SBC"),
                    "CardType": "cCustomer",
                    "U_CRM": crm,
                    "U_UF": uf,
                })

            # 2. Emite o pedido/anuidade na tabela ORDR do SAP B1
            pedido = sap_client.emitir_pedido_evento(
                card_code=card_code,
                item_code=dados.get("ITEM", "ANUIDADE-SBC-2026"),
                valor=float(dados.get("VALOR", 650.00)),
                comentarios="Sincronizado via Strangler Worker (Origem: Legado Delphi)",
            )

            # 3. Atualiza status para SYNCED com o DocEntry oficial gerado pelo SAP
            registro.status = "SYNCED"
            registro.external_sap_docentry = pedido.get("DocEntry")
            registro.updated_at = datetime.utcnow()
            db.commit()
            sincronizados += 1

        except Exception as exc:
            db.rollback()
            registro.status = "ERROR"
            registro.retry_count += 1
            registro.error_message = str(exc)
            db.commit()

    return sincronizados
