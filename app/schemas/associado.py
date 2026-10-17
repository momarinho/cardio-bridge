from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re

ESTADOS_BRASIL = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}

class MedicoBase(BaseModel):
    crm: str = Field(..., description="Número do CRM do médico (somente dígitos)")
    uf: str = Field(..., description="UF do CRM (ex: RJ, SP)", max_length=2, min_length=2)
    nome: str = Field(..., min_length=3, description="Nome completo do médico")
    cpf: str = Field(..., description="CPF (11 dígitos)")
    email: str = Field(..., description="E-mail de contato do associado")
    especialidade_rqe: Optional[str] = Field(None, description="Número de Registro de Especialidade (RQE)")
    telefone: Optional[str] = Field(None, description="Telefone com DDD")

    @field_validator("crm")
    @classmethod
    def validar_crm(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        if not digitos or len(digitos) < 4 or len(digitos) > 10:
            raise ValueError("CRM deve conter entre 4 e 10 dígitos numéricos.")
        return digitos

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, v: str) -> str:
        uf_upper = v.strip().upper()
        if uf_upper not in ESTADOS_BRASIL:
            raise ValueError(f"UF inválida: {v}. Deve ser uma sigla de estado válida.")
        return uf_upper

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return digitos

class MedicoCreateSchema(MedicoBase):
    pass

class MedicoResponseSchema(MedicoBase):
    card_code: str = Field(..., description="Código de Parceiro de Negócio gerado no SAP B1 (OCRD)")
    status_anuidade: str = Field(default="EM_DIA", description="Status financeiro da anuidade na SBC")
    sap_synced: bool = Field(default=True, description="Indicador de sincronização com a Service Layer")

    class Config:
        from_attributes = True
