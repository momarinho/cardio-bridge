from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.schemas.associado import ESTADOS_BRASIL
import re

class InscricaoEventoSchema(BaseModel):
    crm: str = Field(..., description="CRM do médico participante")
    uf: str = Field(..., description="UF do CRM", min_length=2, max_length=2)
    nome_medico: str = Field(..., min_length=3, description="Nome do participante")
    codigo_evento: str = Field(default="CONG-CARDIO-2026", description="Código do evento no ERP")
    nome_evento: str = Field(default="81º Congresso Brasileiro de Cardiologia", description="Nome do evento")
    categoria: str = Field(default="Associado Efetivo", description="Categoria da inscrição")
    valor: float = Field(..., gt=0, description="Valor da inscrição em Reais (BRL)")
    forma_pagamento: str = Field(default="PIX", description="Forma de pagamento (PIX, BOLETO, CARTAO)")

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, v: str) -> str:
        uf_upper = v.strip().upper()
        if uf_upper not in ESTADOS_BRASIL:
            raise ValueError(f"UF inválida: {v}.")
        return uf_upper

    @field_validator("crm")
    @classmethod
    def validar_crm(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        if not digitos:
            raise ValueError("CRM inválido.")
        return digitos

class InscricaoResponseSchema(BaseModel):
    numero_inscricao: str = Field(..., description="Identificador único da inscrição no portal")
    doc_entry_sap: int = Field(..., description="Número DocEntry do Pedido de Venda no SAP B1 (ORDR)")
    card_code: str = Field(..., description="Código do Parceiro de Negócio (OCRD)")
    status: str = Field(..., description="Status do pedido (ex: CONFIRMADO, PENDENTE_PAGAMENTO)")
    valor: float = Field(..., description="Valor faturado")
    qr_code_pix: Optional[str] = Field(None, description="Payload PIX Copia-e-Cola")
    linha_digitavel_boleto: Optional[str] = Field(None, description="Linha digitável do boleto bancário")
    mensagem: str = Field(..., description="Mensagem de confirmação da transação")
