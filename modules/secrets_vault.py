"""
===============================================================================
Drewgent Secrets Vault - Secure Reference System
===============================================================================
Location: modules/secrets_vault.py

Purpose:
    - Drew가 민감정보를 Vault에 등록
    - 실제 값은 Vault에만 저장 (암호화)
    - 에이전트/로깅에는 참조(ref)만 전달
    - 실행 시 system이 참조를 실제 값으로 치환

Security Model:
    - 에이전트는 Vault에 직접 접근 불가
    - 로깅에는 참조만 저장 (실제 값 유출 없음)
    - Drew만 Vault 조회/관리 가능

Usage:
    from secrets_vault import vault

    # Drew가 등록
    ref = vault.register("MINIMAX_API_KEY", "sk-xxx-actual-key")
    # → "vault_MjRkNWEx"

    # 에이전트가 참조 사용 (실제 값 모름)
    log_tool_call(..., parameters={"api_key": "vault_MjRkNWEx"})

    # 실행 시 system이 참조를 실제 값으로 치환
    actual_value = vault.resolve("vault_MjRkNWEx")
    # → "sk-xxx-actual-key"
===============================================================================
"""

import json
import os
import hashlib
import base64
import uuid
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# =============================================================================
# VAULT STORAGE
# =============================================================================


class SecretsVault:
    """
    Drewgent Secrets Vault

    Drew만 접근 가능. 에이전트는 참조(ref)만 사용.
    """

    def __init__(self, vault_path: Path = None, key_path: Path = None):
        self.vault_path = vault_path or Path.home() / ".drewgent" / "secrets_vault.json"
        self.key_path = key_path or Path.home() / ".drewgent" / ".vault_key"

        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

        # Vault 로드
        self._vault: Dict[str, Dict] = self._load_vault()

        # 암호화 키 초기화
        self._fernet = self._get_fernet()

        # 레지스트리 (ref → metadata 매핑)
        self._registry: Dict[str, Dict] = self._load_registry()

    # =========================================================================
    # Key Management
    # =========================================================================

    def _get_fernet(self) -> Fernet:
        """PBKDF2로 키 유도 + Fernet 대칭 암호화"""
        password = self._get_or_create_master_key()
        salt = self._get_or_create_salt()

        # 키 유도
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def _get_or_create_salt(self) -> bytes:
        """Vault별 고유 salt 생성/로드 (machine-specific entropy 포함)"""
        salt_path = self.key_path.parent / ".vault_salt"
        if salt_path.exists():
            salt_path.chmod(0o600)
            return salt_path.read_bytes()
        # 새 salt: os.random(32바이트) + machine entropy
        machine_entropy = f"{os.getuid()}-{os.getpid()}-{self.key_path}".encode()
        combined = secrets.token_bytes(32) + hashlib.sha256(machine_entropy).digest()
        salt = hashlib.sha256(combined).digest()
        salt_path.write_bytes(salt)
        salt_path.chmod(0o600)
        return salt

    def _get_or_create_master_key(self) -> str:
        """Master key 관리 (Drew만 접근 가능)"""
        if self.key_path.exists():
            # 기존 키는 Drew만 읽을 수 있음
            self.key_path.chmod(0o600)
            return self.key_path.read_text().strip()

        # 새 키 생성
        master_key = secrets.token_urlsafe(32)
        self.key_path.write_text(master_key)
        self.key_path.chmod(0o600)  # Drew만 읽기/쓰기
        return master_key

    # =========================================================================
    # Vault Operations
    # =========================================================================

    def _load_vault(self) -> Dict:
        """Vault 로드 (암호화된 값들)"""
        if self.vault_path.exists():
            try:
                with open(self.vault_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _load_registry(self) -> Dict:
        """레지스트리 로드 (ref → metadata)"""
        registry_path = self.vault_path.parent / "secrets_registry.json"
        if registry_path.exists():
            try:
                registry_path.chmod(0o600)
                with open(registry_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_vault(self):
        """Vault 저장 (암호화 상태)"""
        # 파일이 없으면 생성
        if not self.vault_path.exists():
            self.vault_path.touch()
        self.vault_path.chmod(0o600)
        with open(self.vault_path, "w") as f:
            json.dump(self._vault, f, indent=2)

    def _load_registry(self) -> Dict:
        """레지스트리 로드 (ref → metadata)"""
        registry_path = self.vault_path.parent / "secrets_registry.json"
        if registry_path.exists():
            registry_path.chmod(0o600)
            with open(registry_path, "r") as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        """레지스트리 저장"""
        registry_path = self.vault_path.parent / "secrets_registry.json"
        if not registry_path.exists():
            registry_path.touch()
        registry_path.chmod(0o600)
        with open(registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    # =========================================================================
    # Core Operations
    # =========================================================================

    def register(
        self,
        name: str,
        value: str,
        category: str = "secret",
        description: str = "",
        expires: str = None,
    ) -> str:
        """
        Drew가 민감정보를 Vault에 등록.

        Args:
            name: 키 이름 (예: "MINIMAX_API_KEY")
            value: 실제 민감정보 (예: "sk-xxx-actual-key")
            category: "api_key", "password", "url", "path", "token", "other"
            description: 설명 (선택)
            expires: 만료일 (선택, ISO format)

        Returns:
            참조 ref (예: "vault_MjRkNWEx")
        """
        # ref 생성 (고유한 짧은 ID)
        ref_id = self._generate_ref_id(name, value)

        # 암호화하여 vault에 저장
        encrypted = self._fernet.encrypt(value.encode()).decode()

        self._vault[ref_id] = {
            "name": name,
            "encrypted": encrypted,
            "category": category,
            "description": description,
            "created": datetime.now().isoformat(),
            "expires": expires,
        }

        # 레지스트리에 metadata 저장
        self._registry[ref_id] = {
            "name": name,
            "category": category,
            "created": datetime.now().isoformat(),
            "expires": expires,
        }

        self._save_vault()
        self._save_registry()

        print(f"[Vault] Registered: {name} → {ref_id}")
        return ref_id

    def _generate_ref_id(self, name: str, value: str) -> str:
        """고유한 ref ID 생성"""
        # 짧은 해시 (첫 8바이트)
        raw = f"{name}:{value}:{datetime.now().isoformat()}"
        hash_digest = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return f"vault_{hash_digest}"

    def resolve(self, ref: str) -> Optional[str]:
        """
        참조를 실제 값으로 치환 (system만 사용)

        Args:
            ref: 참조 ID (예: "vault_MjRkNWEx")

        Returns:
            실제 값 (복호화된)
        """
        if ref not in self._vault:
            return None

        entry = self._vault[ref]

        # 만료 체크
        if entry.get("expires"):
            exp = datetime.fromisoformat(entry["expires"])
            if datetime.now() > exp:
                return None  # 만료됨

        # 복호화
        try:
            return self._fernet.decrypt(entry["encrypted"].encode()).decode()
        except:
            return None

    def is_ref(self, value: str) -> bool:
        """값이 참조인지 확인"""
        return isinstance(value, str) and value.startswith("vault_")

    def resolve_if_ref(self, value: Any) -> Any:
        """값이 참조이면 실제 값으로 치환, 아니면 그대로 반환"""
        if self.is_ref(value):
            return self.resolve(value)
        return value

    def resolve_dict(self, params: dict) -> dict:
        """딕셔너리의 모든 참조를 치환"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and self.is_ref(value):
                resolved[key] = self.resolve(value) or value
            elif isinstance(value, dict):
                resolved[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve(v) if self.is_ref(v) else v for v in value
                ]
            else:
                resolved[key] = value
        return resolved

    # =========================================================================
    # Management (Drew Only)
    # =========================================================================

    def list(self, category: str = None) -> Dict[str, Dict]:
        """
        등록된 참조 목록 조회 (실제 값 없이 metadata만)
        """
        if category:
            return {
                ref: meta
                for ref, meta in self._registry.items()
                if meta.get("category") == category
            }
        return self._registry.copy()

    def get_metadata(self, ref: str) -> Optional[Dict]:
        """참조의 metadata 조회 (실제 값 없음)"""
        return self._registry.get(ref)

    def revoke(self, ref: str) -> bool:
        """참조 취소 (Vault에서 삭제)"""
        if ref in self._vault:
            del self._vault[ref]
            self._save_vault()

        if ref in self._registry:
            del self._registry[ref]
            self._save_registry()

        return True

    def rotate(self, ref: str, new_value: str) -> str:
        """
        값 순환 (새 값으로 교체, ref는 유지)
        """
        if ref not in self._vault:
            raise ValueError(f"Unknown ref: {ref}")

        entry = self._vault[ref]
        entry["encrypted"] = self._fernet.encrypt(new_value.encode()).decode()
        entry["rotated"] = datetime.now().isoformat()

        self._save_vault()
        print(f"[Vault] Rotated: {ref}")

        return ref

    def categories(self) -> list:
        """등록된 카테고리 목록"""
        cats = set()
        for meta in self._registry.values():
            cats.add(meta.get("category", "unknown"))
        return sorted(cats)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def register_from_env(self, prefix: str = "DREWGENT_") -> Dict[str, str]:
        """
        환경변수에서 민감정보 일괄 등록

        Args:
            prefix: 등록할 환경변수 prefix (기본: DREWGENT_)

        Returns:
            등록된 ref 매핑 {ENV_VAR_NAME: ref}
        """
        import os

        results = {}

        for key, value in os.environ.items():
            if key.startswith(prefix) and value:
                ref = self.register(
                    name=key,
                    value=value,
                    category=self._detect_category(key),
                    description=f"From environment variable: {key}",
                )
                results[key] = ref

        return results

    def _detect_category(self, name: str) -> str:
        """이름에서 카테고리 자동 감지"""
        name_lower = name.lower()

        if any(x in name_lower for x in ["key", "token", "secret", "auth"]):
            return "api_key"
        elif any(x in name_lower for x in ["password", "pwd", "pass"]):
            return "password"
        elif any(x in name_lower for x in ["url", "endpoint", "host"]):
            return "url"
        elif any(x in name_lower for x in ["path", "dir", "directory"]):
            return "path"
        else:
            return "other"


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

vault = SecretsVault()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def register(name: str, value: str, category: str = "secret", **kwargs) -> str:
    """Drew가 민감정보 등록"""
    return vault.register(name, value, category, **kwargs)


def resolve(ref: str) -> Optional[str]:
    """참조 → 실제 값 (system만 사용)"""
    return vault.resolve(ref)


def is_ref(value: str) -> bool:
    """값이 참조인지 확인"""
    return vault.is_ref(value)


def resolve_if_ref(value: Any) -> Any:
    """참조이면 실제 값으로"""
    return vault.resolve_if_ref(value)


def resolve_dict(params: dict) -> dict:
    """딕셔너리의 모든 참조 치환"""
    return vault.resolve_dict(params)


def list_secrets(category: str = None) -> Dict[str, Dict]:
    """참조 목록 조회 (Drew만)"""
    return vault.list(category)


def revoke(ref: str) -> bool:
    """참조 취소 (Drew만)"""
    return vault.revoke(ref)
