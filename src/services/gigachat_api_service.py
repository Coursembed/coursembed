from typing import List, Optional
from datetime import datetime
import requests
import uuid


class GigaChatAPIService:
    def __init__(self, authorization_key: str, certificate_path: str):
        super().__init__()
        self.authorization_key = authorization_key
        self.certificate_path = certificate_path
        self.access_token: Optional[str] = None
        self.expires_at: Optional[datetime] = None

    def _update_access_token(self) -> None:
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        unique_id = str(uuid.uuid4())

        payload = {"scope": "GIGACHAT_API_PERS"}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": unique_id,
            "Authorization": f"Basic {self.authorization_key}",
        }

        try:
            response = requests.post(
                url, headers=headers, data=payload, verify=self.certificate_path
            ).json()
            self.access_token = response["access_token"]
            self.expires_at = response["expires_at"]
        except requests.RequestException as e:
            raise e

    def _is_token_expired(self) -> bool:
        if not self.access_token or not self.expires_at:
            return True
        
        timestamp_seconds = self.expires_at / 1000 

        dt_given = datetime.fromtimestamp(timestamp_seconds)

        return datetime.now() >= dt_given

    def _ensure_valid_token(self) -> None:
        if self._is_token_expired():
            self._update_access_token()

    def _make_request(self, method: str, url: str, headers: Optional[dict] = None, payload: Optional[dict] = None) -> dict:
        try:
            response = requests.request(
                method, url, headers=headers, json=payload, verify=self.certificate_path
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise e

    def get_model_list(self) -> List[str]:
        self._ensure_valid_token()
        
        url = "https://gigachat.devices.sberbank.ru/api/v1/models"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        response = self._make_request("GET", url, headers, {})
        return [model["id"] for model in response.get("data", [])]

    def get_answer(self, query: str, system_prompt: str, model_name: str, top_p: float) -> str:
        self._ensure_valid_token()

        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "top_p": top_p,
            "stream": False,
            "max_tokens": 512,
            "repetition_penalty": 1.0,
            "update_interval": 0,
        }
        response = self._make_request("POST", url, headers, payload)
        return response["choices"][0]["message"]["content"]
