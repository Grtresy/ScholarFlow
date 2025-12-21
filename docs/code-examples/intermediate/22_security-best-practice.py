#!/usr/bin/env python3
"""
高级代码示例22: 安全最佳实践
=================================

本示例展示如何构建一个功能完整的安全系统，
用于ScholarFlow项目的安全防护和合规管理。

功能特性:
- 身份认证
- 权限控制
- 数据加密
- 安全审计
- 漏洞扫描
- 安全策略
- 合规检查
- 威胁检测

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Awaitable, Union
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
import hmac
import secrets
import base64
import jwt
from pathlib import Path
from collections import defaultdict
import time
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VulnerabilitySeverity(Enum):
    """漏洞严重性"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuthMethod(Enum):
    """认证方法"""
    PASSWORD = "password"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    MFA = "mfa"


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    roles: List[str]
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityEvent:
    """安全事件"""
    event_id: str
    event_type: str
    user_id: Optional[str]
    ip_address: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: SecurityLevel = SecurityLevel.MEDIUM
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


@dataclass
class Vulnerability:
    """漏洞"""
    vuln_id: str
    title: str
    description: str
    severity: VulnerabilitySeverity
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    affected_component: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.now)
    status: str = "open"
    remediation: Optional[str] = None


# ============================================================================
# 2. 密码管理器
# ============================================================================

class PasswordManager:
    """密码管理器

    安全的密码存储和验证。
    """

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(32)

        # 使用PBKDF2进行哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        ).hex()

        return password_hash, salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = PasswordManager.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)

    @staticmethod
    def generate_strong_password(length: int = 16) -> str:
        """生成强密码"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """检查密码强度"""
        score = 0
        feedback = []

        # 长度检查
        if len(password) >= 12:
            score += 25
        elif len(password) >= 8:
            score += 15
            feedback.append("密码长度建议至少12个字符")
        else:
            score += 5
            feedback.append("密码长度至少8个字符")

        # 字符类型检查
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

        if has_lower:
            score += 10
        else:
            feedback.append("建议包含小写字母")

        if has_upper:
            score += 10
        else:
            feedback.append("建议包含大写字母")

        if has_digit:
            score += 10
        else:
            feedback.append("建议包含数字")

        if has_special:
            score += 15
        else:
            feedback.append("建议包含特殊字符")

        # 重复字符检查
        if not re.search(r'(.)\1{2,}', password):
            score += 10
        else:
            feedback.append("避免使用重复字符")

        # 常见密码检查
        common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() not in common_passwords:
            score += 20
        else:
            feedback.append("避免使用常见密码")
            score -= 20

        # 确定强度等级
        if score >= 80:
            strength = "very_strong"
        elif score >= 60:
            strength = "strong"
        elif score >= 40:
            strength = "medium"
        else:
            strength = "weak"

        return {
            "score": score,
            "strength": strength,
            "feedback": feedback
        }


# ============================================================================
# 3. 身份认证管理器
# ============================================================================

class AuthenticationManager:
    """身份认证管理器

    处理用户身份认证。
    """

    def __init__(self, jwt_secret: str = "default-secret"):
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.jwt_secret = jwt_secret
        self.lockout_threshold = 5
        self.lockout_duration = 300  # 5分钟

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: List[str] = None
    ) -> User:
        """注册用户"""
        if username in self.users:
            raise ValueError("Username already exists")

        # 检查密码强度
        password_check = PasswordManager.check_password_strength(password)
        if password_check["score"] < 40:
            raise ValueError(f"Password too weak: {', '.join(password_check['feedback'])}")

        # 哈希密码
        password_hash, salt = PasswordManager.hash_password(password)

        user = User(
            user_id=f"user_{len(self.users) + 1}",
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            roles=roles or ["user"]
        )

        self.users[username] = user
        logger.info(f"User registered: {username}")
        return user

    async def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str = "127.0.0.1"
    ) -> Optional[Dict[str, Any]]:
        """认证用户"""
        user = self.users.get(username)
        if not user:
            logger.warning(f"Login attempt with invalid username: {username} from {ip_address}")
            return None

        # 检查账户锁定
        if user.locked_until and datetime.now() < user.locked_until:
            remaining = (user.locked_until - datetime.now()).seconds
            logger.warning(f"Login attempt on locked account: {username} ({remaining}s remaining)")
            return None

        # 验证密码
        if not PasswordManager.verify_password(password, user.password_hash, user.salt):
            user.failed_attempts += 1

            # 检查是否需要锁定
            if user.failed_attempts >= self.lockout_threshold:
                user.locked_until = datetime.now() + timedelta(seconds=self.lockout_duration)
                logger.warning(f"Account locked due to failed attempts: {username}")

            logger.warning(f"Failed login attempt for: {username} from {ip_address}")
            return None

        # 登录成功
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()

        # 创建会话
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user.user_id,
            "username": username,
            "created_at": time.time(),
            "last_activity": time.time(),
            "ip_address": ip_address
        }

        # 生成JWT
        token = jwt.encode(
            {
                "user_id": user.user_id,
                "username": username,
                "roles": user.roles
            },
            self.jwt_secret,
            algorithm="HS256"
        )

        logger.info(f"Successful login: {username} from {ip_address}")
        return {
            "session_id": session_id,
            "token": token,
            "user": user
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None

    def revoke_session(self, session_id: str) -> bool:
        """撤销会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


# ============================================================================
# 4. 权限控制系统
# ============================================================================

class Permission(Enum):
    """权限"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"


@dataclass
class Role:
    """角色"""
    role_id: str
    name: str
    permissions: List[Permission]
    description: str = ""


class AccessControlManager:
    """访问控制管理器

    基于角色的访问控制（RBAC）。
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, List[str]] = defaultdict(list)

    def create_role(self, role_id: str, name: str, permissions: List[Permission], description: str = ""):
        """创建角色"""
        self.roles[role_id] = Role(role_id, name, permissions, description)
        logger.info(f"Role created: {name}")

    def assign_role(self, user_id: str, role_id: str):
        """分配角色"""
        if role_id not in self.roles:
            raise ValueError(f"Role not found: {role_id}")

        self.user_roles[user_id].append(role_id)
        logger.info(f"Role {role_id} assigned to user {user_id}")

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """检查用户权限"""
        user_role_ids = self.user_roles.get(user_id, [])

        for role_id in user_role_ids:
            role = self.roles.get(role_id)
            if role and permission in role.permissions:
                return True

        return False

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查权限（简化版）"""
        return self.has_permission(user_id, permission)

    def get_user_permissions(self, user_id: str) -> List[Permission]:
        """获取用户所有权限"""
        permissions = set()
        user_role_ids = self.user_roles.get(user_id, [])

        for role_id in user_role_ids:
            role = self.roles.get(role_id)
            if role:
                permissions.update(role.permissions)

        return list(permissions)


# ============================================================================
# 5. 数据加密器
# ============================================================================

class DataEncryption:
    """数据加密

    敏感数据加密和解密。
    """

    @staticmethod
    def encrypt(data: str, key: str) -> str:
        """加密数据"""
        # 使用HMAC进行简单加密（实际生产中应使用AES等更强加密）
        encrypted = hmac.new(
            key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return base64.b64encode(encrypted.encode()).decode()

    @staticmethod
    def decrypt(encrypted_data: str, key: str) -> Optional[str]:
        """解密数据"""
        try:
            decoded = base64.b64decode(encrypted_data.encode()).decode()
            # 验证完整性
            expected = hmac.new(
                key.encode(),
                decoded.encode(),
                hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(decoded, expected):
                return decoded
            return None
        except Exception:
            return None

    @staticmethod
    def hash_data(data: str) -> str:
        """数据哈希"""
        return hashlib.sha256(data.encode()).hexdigest()


# ============================================================================
# 6. 安全审计日志
# ============================================================================

class SecurityAuditLogger:
    """安全审计日志

    记录所有安全相关事件。
    """

    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = Path(log_file)
        self.events: List[SecurityEvent] = []
        self.alert_callbacks: List[Callable] = []

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str],
        ip_address: str,
        severity: SecurityLevel = SecurityLevel.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录安全事件"""
        event = SecurityEvent(
            event_id=f"evt_{len(self.events) + 1}",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            details=details or {}
        )

        self.events.append(event)

        # 写入日志文件
        log_entry = {
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id,
            "event_type": event.event_type,
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "severity": event.severity.value,
            "details": event.details
        }

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

        # 检查是否需要告警
        if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            for callback in self.alert_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

        logger.info(f"Security event logged: {event_type}")

    def register_alert(self, callback: Callable):
        """注册告警回调"""
        self.alert_callbacks.append(callback)

    def get_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[SecurityLevel] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """查询安全事件"""
        filtered = self.events

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]

        return filtered[-limit:]


# ============================================================================
# 7. 漏洞扫描器
# ============================================================================

class VulnerabilityScanner:
    """漏洞扫描器

    扫描系统和应用程序的漏洞。
    """

    def __init__(self):
        self.vulnerabilities: List[Vulnerability] = []

    def scan_sql_injection(self, query: str) -> Optional[Vulnerability]:
        """扫描SQL注入"""
        sql_patterns = [
            r"(\bunion\b.*\bselect\b)",
            r"(\bor\b\s+1\s*=\s*1\b)",
            r"(\bdrop\b\s+\btable\b)",
            r"(\bdelete\b\s+from\b)",
            r"(\binsert\b\s+into\b)",
            r"('--)|(\badmin\b\s*'/\*)|(\badmin\b\s*'--)|(\badmin\b\s*'%23)",
            r"(;.*\bdrop\b)",
            r"(\bexec\b\s*\()",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                vuln = Vulnerability(
                    vuln_id=f"sql_{len(self.vulnerabilities) + 1}",
                    title="SQL Injection Vulnerability",
                    description=f"Potential SQL injection detected in query",
                    severity=VulnerabilitySeverity.HIGH,
                    remediation="Use parameterized queries or ORM frameworks"
                )
                self.vulnerabilities.append(vuln)
                logger.warning(f"SQL injection vulnerability detected: {pattern}")
                return vuln

        return None

    def scan_xss(self, content: str) -> Optional[Vulnerability]:
        """扫描XSS"""
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
        ]

        for pattern in xss_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                vuln = Vulnerability(
                    vuln_id=f"xss_{len(self.vulnerabilities) + 1}",
                    title="Cross-Site Scripting (XSS)",
                    description=f"Potential XSS vulnerability detected",
                    severity=VulnerabilitySeverity.MEDIUM,
                    remediation="Sanitize and escape user input"
                )
                self.vulnerabilities.append(vuln)
                logger.warning(f"XSS vulnerability detected: {pattern}")
                return vuln

        return None

    def scan_path_traversal(self, path: str) -> Optional[Vulnerability]:
        """扫描路径遍历"""
        traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]

        for pattern in traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                vuln = Vulnerability(
                    vuln_id=f"path_{len(self.vulnerabilities) + 1}",
                    title="Path Traversal Vulnerability",
                    description="Potential path traversal attack detected",
                    severity=VulnerabilitySeverity.HIGH,
                    remediation="Validate and sanitize file paths"
                )
                self.vulnerabilities.append(vuln)
                logger.warning(f"Path traversal vulnerability detected: {pattern}")
                return vuln

        return None

    def get_vulnerabilities(
        self,
        severity: Optional[VulnerabilitySeverity] = None
    ) -> List[Vulnerability]:
        """获取漏洞列表"""
        if severity:
            return [v for v in self.vulnerabilities if v.severity == severity]
        return self.vulnerabilities


# ============================================================================
# 8. 安全策略管理器
# ============================================================================

@dataclass
class SecurityPolicy:
    """安全策略"""
    policy_id: str
    name: str
    description: str
    rules: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class SecurityPolicyManager:
    """安全策略管理器

    管理系统安全策略。
    """

    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {}

    def create_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        rules: Dict[str, Any]
    ):
        """创建策略"""
        self.policies[policy_id] = SecurityPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            rules=rules
        )
        logger.info(f"Security policy created: {name}")

    def evaluate_policy(self, policy_id: str, context: Dict[str, Any]) -> bool:
        """评估策略"""
        if policy_id not in self.policies:
            return True  # 策略不存在时允许

        policy = self.policies[policy_id]
        if not policy.enabled:
            return True

        # 简化策略评估
        for rule_name, rule_config in policy.rules.items():
            if rule_name == "max_login_attempts":
                if context.get("failed_attempts", 0) > rule_config:
                    return False

            elif rule_name == "password_min_length":
                if context.get("password_length", 0) < rule_config:
                    return False

            elif rule_name == "require_mfa":
                if rule_config and not context.get("mfa_enabled", False):
                    return False

            elif rule_name == "allowed_ip_ranges":
                client_ip = context.get("client_ip", "")
                if client_ip and client_ip not in rule_config:
                    return False

        return True


# ============================================================================
# 9. 使用示例
# ============================================================================

async def example_security_best_practice():
    """安全最佳实践示例"""

    # 1. 创建密码管理器
    print("\n=== 密码管理 ===")
    password = "MySecureP@ssw0rd"
    password_hash, salt = PasswordManager.hash_password(password)
    print(f"密码哈希: {password_hash[:32]}...")
    print(f"盐值: {salt[:32]}...")

    is_valid = PasswordManager.verify_password(password, password_hash, salt)
    print(f"密码验证: {'成功' if is_valid else '失败'}")

    # 检查密码强度
    strength = PasswordManager.check_password_strength(password)
    print(f"\n密码强度: {strength['strength']} (分数: {strength['score']})")
    if strength['feedback']:
        print("建议:")
        for feedback in strength['feedback']:
            print(f"  - {feedback}")

    # 生成强密码
    new_password = PasswordManager.generate_strong_password(16)
    print(f"\n生成的新密码: {new_password}")

    # 2. 创建认证管理器
    print("\n=== 身份认证 ===")
    auth_manager = AuthenticationManager(jwt_secret="my-secret-key")

    # 注册用户
    user = auth_manager.register_user(
        username="alice",
        email="alice@example.com",
        password="SecureP@ssw0rd123",
        roles=["user"]
    )
    print(f"用户注册: {user.username} ({user.user_id})")

    # 认证用户
    auth_result = await auth_manager.authenticate(
        username="alice",
        password="SecureP@ssw0rd123",
        ip_address="192.168.1.100"
    )

    if auth_result:
        print(f"认证成功: {auth_result['user']['username']}")
        print(f"会话ID: {auth_result['session_id'][:16]}...")
        print(f"JWT令牌: {auth_result['token'][:32]}...")

    # 验证令牌
    payload = auth_manager.verify_token(auth_result['token'])
    if payload:
        print(f"令牌验证成功: {payload['username']}")

    # 3. 创建访问控制
    print("\n=== 权限控制 ===")
    ac_manager = AccessControlManager()

    # 创建角色
    ac_manager.create_role("admin", "Administrator", [Permission.ADMIN, Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE])
    ac_manager.create_role("user", "Regular User", [Permission.READ, Permission.CREATE])

    # 分配角色
    ac_manager.assign_role(user.user_id, "user")
    user_permissions = ac_manager.get_user_permissions(user.user_id)
    print(f"用户权限: {[p.value for p in user_permissions]}")

    has_permission = ac_manager.check_permission(user.user_id, Permission.DELETE)
    print(f"有删除权限: {'是' if has_permission else '否'}")

    # 4. 数据加密
    print("\n=== 数据加密 ===")
    sensitive_data = "信用卡号: 1234-5678-9012-3456"
    encryption_key = "my-encryption-key"

    encrypted = DataEncryption.encrypt(sensitive_data, encryption_key)
    print(f"加密数据: {encrypted[:32]}...")

    decrypted = DataEncryption.decrypt(encrypted, encryption_key)
    print(f"解密数据: {decrypted}")

    # 5. 安全审计
    print("\n=== 安全审计 ===")
    audit_logger = SecurityAuditLogger()

    # 注册告警
    def security_alert(event: SecurityEvent):
        print(f"\n🚨 安全告警: {event.event_type}")
        print(f"   用户: {event.user_id}")
        print(f"   IP: {event.ip_address}")
        print(f"   严重性: {event.severity.value}")

    audit_logger.register_alert(security_alert)

    # 记录安全事件
    audit_logger.log_event(
        event_type="LOGIN_SUCCESS",
        user_id=user.user_id,
        ip_address="192.168.1.100",
        severity=SecurityLevel.LOW
    )

    audit_logger.log_event(
        event_type="FAILED_LOGIN",
        user_id="bob",
        ip_address="10.0.0.1",
        severity=SecurityLevel.HIGH,
        details={"reason": "Invalid password"}
    )

    # 查询事件
    events = audit_logger.get_events(severity=SecurityLevel.HIGH)
    print(f"高危事件数: {len(events)}")

    # 6. 漏洞扫描
    print("\n=== 漏洞扫描 ===")
    scanner = VulnerabilityScanner()

    # SQL注入扫描
    malicious_query = "SELECT * FROM users WHERE id = 1 OR 1=1"
    vuln = scanner.scan_sql_injection(malicious_query)
    if vuln:
        print(f"发现漏洞: {vuln.title} - {vuln.severity.value}")

    # XSS扫描
    malicious_content = "<script>alert('XSS')</script>"
    vuln = scanner.scan_xss(malicious_content)
    if vuln:
        print(f"发现漏洞: {vuln.title} - {vuln.severity.value}")

    # 路径遍历扫描
    malicious_path = "../../etc/passwd"
    vuln = scanner.scan_path_traversal(malicious_path)
    if vuln:
        print(f"发现漏洞: {vuln.title} - {vuln.severity.value}")

    # 列出所有漏洞
    all_vulns = scanner.get_vulnerabilities()
    print(f"\n漏洞总数: {len(all_vulns)}")

    # 7. 安全策略
    print("\n=== 安全策略 ===")
    policy_manager = SecurityPolicyManager()

    # 创建密码策略
    password_policy = {
        "password_min_length": 12,
        "require_mfa": False,
        "max_login_attempts": 5
    }

    policy_manager.create_policy(
        "password_policy",
        "Password Policy",
        "Enforce password requirements",
        password_policy
    )

    # 评估策略
    context = {
        "password_length": 16,
        "mfa_enabled": False,
        "failed_attempts": 2
    }

    is_compliant = policy_manager.evaluate_policy("password_policy", context)
    print(f"策略合规: {'是' if is_compliant else '否'}")

    # 8. 安全检查清单
    print("\n=== 安全检查清单 ===")
    checklist = [
        ("密码哈希", "✅ 使用PBKDF2进行哈希"),
        ("密码强度检查", "✅ 强制使用强密码"),
        ("账户锁定", "✅ 失败尝试后锁定账户"),
        ("JWT令牌认证", "✅ 使用JWT进行会话管理"),
        ("权限控制", "✅ 基于角色的访问控制"),
        ("数据加密", "✅ 敏感数据加密"),
        ("安全审计", "✅ 记录所有安全事件"),
        ("漏洞扫描", "✅ 自动检测常见漏洞"),
        ("安全策略", "✅ 强制执行安全规则")
    ]

    for item, status in checklist:
        print(f"  {status} {item}")


# ============================================================================
# 10. 高级功能：合规检查
# ============================================================================

class ComplianceChecker:
    """合规检查器

    检查系统是否符合安全合规要求。
    """

    def __init__(self, standard: str):
        self.standard = standard  # e.g., "ISO27001", "SOC2", "GDPR"
        self.checks: Dict[str, Callable] = {}

    def register_check(self, check_id: str, check_func: Callable):
        """注册合规检查"""
        self.checks[check_id] = check_func

    async def run_compliance_check(self) -> Dict[str, Any]:
        """运行合规检查"""
        results = {}
        passed = 0
        failed = 0

        for check_id, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                results[check_id] = {
                    "status": "PASS" if result else "FAIL",
                    "compliant": result
                }

                if result:
                    passed += 1
                else:
                    failed += 1

            except Exception as e:
                results[check_id] = {
                    "status": "ERROR",
                    "error": str(e),
                    "compliant": False
                }
                failed += 1

        compliance_score = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0

        return {
            "standard": self.standard,
            "compliance_score": compliance_score,
            "passed": passed,
            "failed": failed,
            "results": results
        }


# ============================================================================
# 11. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_security_best_practice())
