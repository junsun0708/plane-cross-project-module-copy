import os
import time
import requests
from typing import Any, Optional

def load_env_manual(file_path=".env"):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

class PlaneAPI:
    """Plane REST API v1 클라이언트 (Self-hosted 지원)"""

    def __init__(self, base_url: str, api_key: str, workspace_slug: str):
        self.base_url = base_url.rstrip("/")
        self.workspace_slug = workspace_slug
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/workspaces/{self.workspace_slug}/{path}"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = self._url(path)
        max_retries = 3
        retry_delay = 2
        
        for i in range(max_retries):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 429:
                wait = retry_delay * (i + 1)
                print(f"  ⚠ Rate limit (429) hit. Waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            
            try:
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                if resp.status_code == 400:
                    print(f"  ✗ Bad Request (400): {resp.text}")
                raise e
        
        resp.raise_for_status()

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict | None = None) -> Any:
        return self._request("POST", path, json=data or {})

    def _get_all_pages(self, path: str, per_page: int = 100) -> list[dict]:
        """커서 기반 페이지네이션으로 전체 결과 가져오기"""
        results = []
        cursor = None
        while True:
            params = {"per_page": per_page}
            if cursor:
                params["cursor"] = cursor
            data = self._get(path, params)
            if isinstance(data, list):
                results.extend(data)
                break
            results.extend(data.get("results", []))
            if not data.get("next_page_results"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return results

    # -- Projects --
    def list_projects(self) -> list[dict]:
        return self._get_all_pages("projects/")

    def find_project_by_name(self, name: str) -> dict | None:
        projects = self.list_projects()
        for p in projects:
            if p.get("name") == name or p.get("identifier") == name:
                return p
        return None

    # -- Modules --
    def list_modules(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/modules/")

    def get_module(self, project_id: str, module_id: str) -> dict:
        return self._get(f"projects/{project_id}/modules/{module_id}/")

    def find_module_by_name(self, project_id: str, name: str) -> dict | None:
        modules = self.list_modules(project_id)
        for m in modules:
            if m.get("name") == name:
                return m
        return None

    def create_module(self, project_id: str, data: dict) -> dict:
        return self._post(f"projects/{project_id}/modules/", data)

    def delete_module(self, project_id: str, module_id: str) -> None:
        url = self._url(f"projects/{project_id}/modules/{module_id}/")
        self.session.delete(url).raise_for_status()

    # -- Module Work Items --
    def list_module_work_items(self, project_id: str, module_id: str) -> list[dict]:
        return self._get_all_pages(
            f"projects/{project_id}/modules/{module_id}/module-issues/"
        )

    def add_work_items_to_module(self, project_id: str, module_id: str,
                                  work_item_ids: list[str]) -> Any:
        return self._post(
            f"projects/{project_id}/modules/{module_id}/module-issues/",
            {"issues": work_item_ids},
        )

    # -- Work Items --
    def list_work_items(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/work-items/")

    def get_work_item(self, project_id: str, work_item_id: str) -> dict:
        return self._get(f"projects/{project_id}/work-items/{work_item_id}/")

    def create_work_item(self, project_id: str, data: dict) -> dict:
        return self._post(f"projects/{project_id}/work-items/", data)

    # -- States --
    def list_states(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/states/")

    # -- Labels --
    def list_labels(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/labels/")

    # -- Estimate Points --
    def list_estimates(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/estimates/")

    def list_estimate_points(self, project_id: str, estimate_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/estimates/{estimate_id}/estimate-points/")

    # -- Workspace Members --
    def list_members(self) -> list[dict]:
        return self._get_all_pages("members/")

    # -- Cycles --
    def list_cycles(self, project_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/cycles/")

    # -- Comments --
    def list_comments(self, project_id: str, work_item_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/work-items/{work_item_id}/comments/")

    def create_comment(self, project_id: str, work_item_id: str, data: dict) -> dict:
        return self._post(f"projects/{project_id}/work-items/{work_item_id}/comments/", data)

    # -- Activity --
    def list_activities(self, project_id: str, work_item_id: str) -> list[dict]:
        return self._get_all_pages(f"projects/{project_id}/work-items/{work_item_id}/activities/")
