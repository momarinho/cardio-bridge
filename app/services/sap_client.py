from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


class SAPServiceLayerClient:
    """
    Cliente oficial para consumo da Service Layer do SAP Business One (OData REST).
    Responsável pela gestão de sessão, cookies B1SESSION/ROUTEID e operações de
    negócio.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        company_db: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.SAP_SERVICE_LAYER_URL).rstrip("/")
        self.company_db = company_db or settings.SAP_COMPANY_DB
        self.username = username or settings.SAP_USERNAME
        self.password = password or settings.SAP_PASSWORD

        # Cliente HTTP que gerencia cookies automaticamente
        self.client = httpx.Client(
            timeout=getattr(settings, "SAP_TIMEOUT_SECONDS", 30.0),
            verify=False,
        )
        self.cookies: Dict[str, str] = {}

    def login(self) -> bool:
        """Executa autenticação na Service Layer do SAP B1."""
        url = f"{self.base_url}/Login"
        payload = {
            "CompanyDB": self.company_db,
            "Username": self.username,
            "Password": self.password,
        }

        try:
            response = self.client.post(url, json=payload)
            if response.status_code == 200:
                self.cookies = dict(response.cookies)
                return True

            raise ConnectionError(
                f"Falha de auth no SAP B1: {response.text}"
            )
        except httpx.RequestError as exc:
            raise ConnectionError(
                f"Não foi possível conectar ao servidor SAP B1: {exc}"
            ) from exc

    def _requisicao_com_retry(
        self,
        metodo: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Executa uma chamada HTTP com tratamento de expiração de sessão.
        Se receber 401 (Sessão Expirada), refaz o login e retenta uma vez.
        """
        if not self.cookies:
            self.login()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs["cookies"] = self.cookies

        response = self.client.request(metodo, url, **kwargs)

        # Se o token expirou (401), refaz o login transparente e tenta de novo
        if response.status_code == 401:
            self.login()
            kwargs["cookies"] = self.cookies
            response = self.client.request(metodo, url, **kwargs)

        return response

    def consultar_associado(
        self,
        card_code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta um médico associado na tabela OCRD (BusinessPartners).
        Retorna o JSON do parceiro ou None se não existir.
        """
        response = self._requisicao_com_retry(
            "GET",
            f"/BusinessPartners('{card_code}')",
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None

        raise RuntimeError(
            f"Erro ao consultar médico no SAP: {response.text}"
        )

    def cadastrar_associado(
        self,
        medico_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Cadastra um novo médico associado na tabela OCRD do SAP B1."""
        response = self._requisicao_com_retry(
            "POST",
            "/BusinessPartners",
            json=medico_data,
        )
        if response.status_code in (200, 201):
            return response.json()

        raise RuntimeError(
            f"Erro ao cadastrar parceiro no SAP: {response.text}"
        )

    def emitir_pedido_evento(
        self,
        card_code: str,
        item_code: str,
        valor: float,
        comentarios: str = "Inscrição em Congresso SBC",
    ) -> Dict[str, Any]:
        """
        Gera um Pedido de Venda oficial no SAP B1 (tabela ORDR).
        Retorna o DocEntry e o DocNum gerados pela SAP.
        """
        payload = {
            "CardCode": card_code,
            "Comments": comentarios,
            "DocumentLines": [
                {
                    "ItemCode": item_code,
                    "Quantity": 1.0,
                    "UnitPrice": valor,
                }
            ],
        }
        response = self._requisicao_com_retry(
            "POST",
            "/Orders",
            json=payload,
        )
        if response.status_code in (200, 201):
            return response.json()

        raise RuntimeError(
            f"Erro ao gerar pedido de venda no SAP: {response.text}"
        )

# Instância padrão para uso e injeção na aplicação
sap_client = SAPServiceLayerClient()

