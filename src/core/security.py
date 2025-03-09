import logging
import secrets
import hashlib
import base64
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum, auto
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, ValidationError, Field, validator

# Constants
AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "auth.db")
TOKEN_EXPIRY_DAYS = int(os.environ.get("TOKEN_EXPIRY_DAYS", "30"))
MASTER_KEY = os.environ.get("MASTER_KEY", "")  # Should be set via environment variable
DEFAULT_SALT = os.environ.get("DEFAULT_SALT", "HADES_SALT").encode()

class Role(Enum):
    """User roles with different permission levels."""
    ADMIN = auto()        # Full access to all features
    EDITOR = auto()       # Can modify data but not manage users
    ANALYST = auto()      # Can query and analyze but not modify
    READER = auto()       # Read-only access
    API = auto()          # Programmatic access with customizable permissions

class Permission(Enum):
    """Granular permissions for operations."""
    READ_ENTITIES = auto()
    WRITE_ENTITIES = auto()
    READ_RELATIONSHIPS = auto()
    WRITE_RELATIONSHIPS = auto()
    MANAGE_USERS = auto()
    MANAGE_ROLES = auto()
    EXECUTE_QUERIES = auto()
    MANAGE_VERSIONS = auto()
    ACCESS_HISTORY = auto()
    TRAIN_MODELS = auto()

# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.EDITOR: [
        Permission.READ_ENTITIES,
        Permission.WRITE_ENTITIES,
        Permission.READ_RELATIONSHIPS,
        Permission.WRITE_RELATIONSHIPS,
        Permission.EXECUTE_QUERIES,
        Permission.ACCESS_HISTORY,
    ],
    Role.ANALYST: [
        Permission.READ_ENTITIES,
        Permission.READ_RELATIONSHIPS,
        Permission.EXECUTE_QUERIES,
        Permission.ACCESS_HISTORY,
    ],
    Role.READER: [
        Permission.READ_ENTITIES,
        Permission.READ_RELATIONSHIPS,
        Permission.EXECUTE_QUERIES,
    ],
    Role.API: []  # Custom permissions set per API key
}

class User(BaseModel):
    """User model for authentication and authorization."""
    username: str
    password_hash: str
    salt: str
    role: Role
    permissions: List[Permission] = []
    rate_limit: int = 100  # Requests per minute
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True

class APIKey(BaseModel):
    """API key model for authentication and authorization."""
    key_id: str
    key_hash: str
    name: str
    owner: str
    role: Role
    permissions: List[Permission] = []
    rate_limit: int = 100  # Requests per minute
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

class AuditLog(BaseModel):
    """Audit log entry for tracking security events."""
    timestamp: datetime = Field(default_factory=datetime.now)
    user: str
    action: str
    resource: str
    status: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None

class SecurityManager:
    """
    Manager for security, authentication, and authorization.
    """
    
    def __init__(self, db_path: str = AUTH_DB_PATH):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.request_counts = {}  # For rate limiting
        
        # Setup encryption
        if not MASTER_KEY:
            self.logger.warning("No MASTER_KEY found in environment variables. Using a default key.")
            self._master_key = self._generate_master_key()
        else:
            self._master_key = MASTER_KEY.encode()
        
        self._encryption_key = self._derive_key(self._master_key, DEFAULT_SALT)
        self._cipher = Fernet(self._encryption_key)
        
        # Ensure database exists
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the authentication database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            permissions TEXT NOT NULL,
            rate_limit INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER NOT NULL
        )
        ''')
        
        # Create API keys table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id TEXT PRIMARY KEY,
            key_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            role TEXT NOT NULL,
            permissions TEXT NOT NULL,
            rate_limit INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            last_used TEXT,
            is_active INTEGER NOT NULL
        )
        ''')
        
        # Create tokens table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            is_revoked INTEGER NOT NULL
        )
        ''')
        
        # Create audit log table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            resource TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT NOT NULL,
            ip_address TEXT
        )
        ''')
        
        # Check if admin user exists, create if not
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = ?", (Role.ADMIN.name,))
        if cursor.fetchone()[0] == 0:
            # Create default admin user
            salt = secrets.token_hex(16)
            password_hash = self._hash_password("admin", salt)
            
            permissions = json.dumps([p.name for p in ROLE_PERMISSIONS[Role.ADMIN]])
            
            cursor.execute('''
            INSERT INTO users (
                username, password_hash, salt, role, permissions, 
                rate_limit, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                "admin", 
                password_hash, 
                salt, 
                Role.ADMIN.name, 
                permissions, 
                1000,  # Higher rate limit for admin
                datetime.now().isoformat(),
                1
            ))
            
            self.logger.warning("Created default admin user with password 'admin'. Please change it immediately.")
        
        conn.commit()
        conn.close()
    
    def register_user(self, username: str, password: str, role: Role, 
                    custom_permissions: Optional[List[Permission]] = None,
                    rate_limit: int = 100) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            username: Username
            password: Plain text password
            role: User role
            custom_permissions: Optional list of custom permissions (for API role)
            rate_limit: Request rate limit
            
        Returns:
            Result of registration
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            self.log_audit(
                user="system",
                action="register_user",
                resource=f"user/{username}",
                status="failed",
                details={"reason": "Username already exists"}
            )
            return {
                "status": "error",
                "message": f"Username '{username}' already exists"
            }
        
        # Generate salt and hash password
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        # Set permissions based on role or custom permissions
        if role == Role.API and custom_permissions:
            permissions = custom_permissions
        else:
            permissions = ROLE_PERMISSIONS.get(role, [])
        
        # Store user
        try:
            permissions_json = json.dumps([p.name for p in permissions])
            
            cursor.execute('''
            INSERT INTO users (
                username, password_hash, salt, role, permissions, 
                rate_limit, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, 
                password_hash, 
                salt, 
                role.name, 
                permissions_json, 
                rate_limit,
                datetime.now().isoformat(),
                1
            ))
            
            conn.commit()
            
            self.log_audit(
                user="system",
                action="register_user",
                resource=f"user/{username}",
                status="success"
            )
            
            return {
                "status": "success",
                "message": f"User '{username}' registered successfully",
                "username": username,
                "role": role.name
            }
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error registering user: {str(e)}")
            
            self.log_audit(
                user="system",
                action="register_user",
                resource=f"user/{username}",
                status="error",
                details={"error": str(e)}
            )
            
            return {
                "status": "error",
                "message": f"Error registering user: {str(e)}"
            }
            
        finally:
            conn.close()
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user and generate token.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Authentication result with token if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user
        cursor.execute('''
        SELECT username, password_hash, salt, role, is_active 
        FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        
        if not user or not user[4]:  # User not found or not active
            conn.close()
            
            self.log_audit(
                user=username,
                action="authenticate",
                resource=f"user/{username}",
                status="failed",
                details={"reason": "User not found or inactive"}
            )
            
            return {
                "status": "error",
                "message": "Invalid username or password"
            }
        
        # Verify password
        stored_hash = user[1]
        salt = user[2]
        
        if self._hash_password(password, salt) != stored_hash:
            conn.close()
            
            self.log_audit(
                user=username,
                action="authenticate",
                resource=f"user/{username}",
                status="failed",
                details={"reason": "Invalid password"}
            )
            
            return {
                "status": "error",
                "message": "Invalid username or password"
            }
        
        # Update last login
        cursor.execute('''
        UPDATE users SET last_login = ? WHERE username = ?
        ''', (datetime.now().isoformat(), username))
        
        # Generate token
        token = self._generate_token()
        token_hash = self._hash_token(token)
        expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRY_DAYS)
        
        # Store token
        cursor.execute('''
        INSERT INTO tokens (token_hash, user_id, expires_at, is_revoked)
        VALUES (?, ?, ?, ?)
        ''', (token_hash, username, expires_at.isoformat(), 0))
        
        conn.commit()
        conn.close()
        
        self.log_audit(
            user=username,
            action="authenticate",
            resource=f"user/{username}",
            status="success"
        )
        
        return {
            "status": "success",
            "message": "Authentication successful",
            "token": token,
            "expires_at": expires_at.isoformat(),
            "username": username,
            "role": user[3]
        }
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a token and get user information.
        
        Args:
            token: Authentication token
            
        Returns:
            Validation result with user information if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        token_hash = self._hash_token(token)
        
        # Get token
        cursor.execute('''
        SELECT user_id, expires_at, is_revoked 
        FROM tokens WHERE token_hash = ?
        ''', (token_hash,))
        
        token_data = cursor.fetchone()
        
        if not token_data:
            conn.close()
            return {
                "status": "error",
                "message": "Invalid token"
            }
        
        username, expires_at, is_revoked = token_data
        
        # Check if token is revoked
        if is_revoked:
            conn.close()
            
            self.log_audit(
                user=username,
                action="validate_token",
                resource=f"token/{token_hash[:8]}",
                status="failed",
                details={"reason": "Token revoked"}
            )
            
            return {
                "status": "error",
                "message": "Token has been revoked"
            }
        
        # Check if token is expired
        expiry = datetime.fromisoformat(expires_at)
        if datetime.now() > expiry:
            conn.close()
            
            self.log_audit(
                user=username,
                action="validate_token",
                resource=f"token/{token_hash[:8]}",
                status="failed",
                details={"reason": "Token expired"}
            )
            
            return {
                "status": "error",
                "message": "Token has expired"
            }
        
        # Get user information
        cursor.execute('''
        SELECT role, permissions, is_active, rate_limit 
        FROM users WHERE username = ?
        ''', (username,))
        
        user_data = cursor.fetchone()
        
        if not user_data or not user_data[2]:  # User not found or not active
            conn.close()
            
            self.log_audit(
                user=username,
                action="validate_token",
                resource=f"token/{token_hash[:8]}",
                status="failed",
                details={"reason": "User not found or inactive"}
            )
            
            return {
                "status": "error",
                "message": "User not found or inactive"
            }
        
        role, permissions_json, is_active, rate_limit = user_data
        
        if not is_active:
            conn.close()
            
            self.log_audit(
                user=username,
                action="validate_token",
                resource=f"token/{token_hash[:8]}",
                status="failed",
                details={"reason": "User inactive"}
            )
            
            return {
                "status": "error",
                "message": "User account is inactive"
            }
        
        # Convert permissions JSON to list
        permissions = json.loads(permissions_json)
        
        conn.close()
        
        self.log_audit(
            user=username,
            action="validate_token",
            resource=f"token/{token_hash[:8]}",
            status="success"
        )
        
        return {
            "status": "success",
            "message": "Token is valid",
            "username": username,
            "role": role,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "expires_at": expires_at
        }
    
    def revoke_token(self, token: str) -> Dict[str, Any]:
        """
        Revoke a token.
        
        Args:
            token: Authentication token
            
        Returns:
            Result of revocation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        token_hash = self._hash_token(token)
        
        # Get token user first for audit log
        cursor.execute('SELECT user_id FROM tokens WHERE token_hash = ?', (token_hash,))
        result = cursor.fetchone()
        username = result[0] if result else "unknown"
        
        # Revoke token
        cursor.execute('''
        UPDATE tokens SET is_revoked = 1 WHERE token_hash = ?
        ''', (token_hash,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            self.log_audit(
                user=username,
                action="revoke_token",
                resource=f"token/{token_hash[:8]}",
                status="success"
            )
            
            return {
                "status": "success",
                "message": "Token revoked successfully"
            }
        else:
            self.log_audit(
                user=username,
                action="revoke_token",
                resource=f"token/{token_hash[:8]}",
                status="failed",
                details={"reason": "Token not found"}
            )
            
            return {
                "status": "error",
                "message": "Token not found"
            }
    
    def create_api_key(self, name: str, owner: str, role: Role,
                     custom_permissions: Optional[List[Permission]] = None,
                     rate_limit: int = 100,
                     expiry_days: Optional[int] = 365) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            name: Name for the API key
            owner: Username of the key owner
            role: Role for the key
            custom_permissions: Optional custom permissions
            rate_limit: Request rate limit
            expiry_days: Days until key expires (None for no expiry)
            
        Returns:
            Created API key details
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if owner exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (owner,))
        if not cursor.fetchone():
            conn.close()
            
            self.log_audit(
                user="system",
                action="create_api_key",
                resource=f"api_key/{name}",
                status="failed",
                details={"reason": "Owner does not exist"}
            )
            
            return {
                "status": "error",
                "message": f"Owner '{owner}' does not exist"
            }
        
        # Generate API key
        key_id = f"hades_{secrets.token_hex(8)}"
        key_secret = secrets.token_hex(24)
        key_hash = self._hash_api_key(key_secret)
        
        # Set permissions based on role or custom permissions
        if role == Role.API and custom_permissions:
            permissions = custom_permissions
        else:
            permissions = ROLE_PERMISSIONS.get(role, [])
        
        # Set expiry
        expires_at = None
        if expiry_days is not None:
            expires_at = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        
        # Store API key
        try:
            permissions_json = json.dumps([p.name for p in permissions])
            
            cursor.execute('''
            INSERT INTO api_keys (
                key_id, key_hash, name, owner, role, permissions,
                rate_limit, created_at, expires_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                key_id,
                key_hash,
                name,
                owner,
                role.name,
                permissions_json,
                rate_limit,
                datetime.now().isoformat(),
                expires_at,
                1
            ))
            
            conn.commit()
            
            # Construct full API key
            api_key = f"{key_id}.{key_secret}"
            
            self.log_audit(
                user=owner,
                action="create_api_key",
                resource=f"api_key/{key_id}",
                status="success"
            )
            
            return {
                "status": "success",
                "message": "API key created successfully",
                "key_id": key_id,
                "api_key": api_key,  # Full key only shown once
                "name": name,
                "role": role.name,
                "permissions": [p.name for p in permissions],
                "expires_at": expires_at
            }
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error creating API key: {str(e)}")
            
            self.log_audit(
                user=owner,
                action="create_api_key",
                resource=f"api_key/{name}",
                status="error",
                details={"error": str(e)}
            )
            
            return {
                "status": "error",
                "message": f"Error creating API key: {str(e)}"
            }
            
        finally:
            conn.close()
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key and get associated permissions.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Validation result with permissions if successful
        """
        # Split key into ID and secret
        try:
            key_parts = api_key.split(".")
            if len(key_parts) != 2:
                self.log_audit(
                    user="unknown",
                    action="validate_api_key",
                    resource="api_key/unknown",
                    status="failed",
                    details={"reason": "Invalid key format"}
                )
                
                return {
                    "status": "error",
                    "message": "Invalid API key format"
                }
            
            key_id, key_secret = key_parts
            
        except Exception:
            self.log_audit(
                user="unknown",
                action="validate_api_key",
                resource="api_key/unknown",
                status="failed",
                details={"reason": "Invalid key format"}
            )
            
            return {
                "status": "error",
                "message": "Invalid API key format"
            }
        
        # Check rate limit first
        if not self._check_rate_limit(key_id):
            self.log_audit(
                user="unknown",
                action="validate_api_key",
                resource=f"api_key/{key_id}",
                status="failed",
                details={"reason": "Rate limit exceeded"}
            )
            
            return {
                "status": "error",
                "message": "Rate limit exceeded"
            }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate hash of the secret
        key_hash = self._hash_api_key(key_secret)
        
        # Get API key
        cursor.execute('''
        SELECT name, owner, role, permissions, rate_limit, expires_at, is_active, last_used 
        FROM api_keys WHERE key_id = ? AND key_hash = ?
        ''', (key_id, key_hash))
        
        key_data = cursor.fetchone()
        
        if not key_data:
            conn.close()
            
            self.log_audit(
                user="unknown",
                action="validate_api_key",
                resource=f"api_key/{key_id}",
                status="failed",
                details={"reason": "Invalid key"}
            )
            
            return {
                "status": "error",
                "message": "Invalid API key"
            }
        
        name, owner, role, permissions_json, rate_limit, expires_at, is_active, last_used = key_data
        
        # Check if key is active
        if not is_active:
            conn.close()
            
            self.log_audit(
                user=owner,
                action="validate_api_key",
                resource=f"api_key/{key_id}",
                status="failed",
                details={"reason": "Key inactive"}
            )
            
            return {
                "status": "error",
                "message": "API key is inactive"
            }
        
        # Check if key is expired
        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            if datetime.now() > expiry:
                conn.close()
                
                self.log_audit(
                    user=owner,
                    action="validate_api_key",
                    resource=f"api_key/{key_id}",
                    status="failed",
                    details={"reason": "Key expired"}
                )
                
                return {
                    "status": "error",
                    "message": "API key has expired"
                }
        
        # Update last used timestamp
        cursor.execute('''
        UPDATE api_keys SET last_used = ? WHERE key_id = ?
        ''', (datetime.now().isoformat(), key_id))
        
        conn.commit()
        conn.close()
        
        # Convert permissions JSON to list
        permissions = json.loads(permissions_json)
        
        self.log_audit(
            user=owner,
            action="validate_api_key",
            resource=f"api_key/{key_id}",
            status="success"
        )
        
        return {
            "status": "success",
            "message": "API key is valid",
            "key_id": key_id,
            "name": name,
            "owner": owner,
            "role": role,
            "permissions": permissions,
            "rate_limit": rate_limit
        }
    
    def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of the API key to revoke
            
        Returns:
            Result of revocation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get key owner first for audit log
        cursor.execute('SELECT owner FROM api_keys WHERE key_id = ?', (key_id,))
        result = cursor.fetchone()
        owner = result[0] if result else "unknown"
        
        # Revoke key
        cursor.execute('''
        UPDATE api_keys SET is_active = 0 WHERE key_id = ?
        ''', (key_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            self.log_audit(
                user=owner,
                action="revoke_api_key",
                resource=f"api_key/{key_id}",
                status="success"
            )
            
            return {
                "status": "success",
                "message": "API key revoked successfully"
            }
        else:
            self.log_audit(
                user="system",
                action="revoke_api_key",
                resource=f"api_key/{key_id}",
                status="failed",
                details={"reason": "Key not found"}
            )
            
            return {
                "status": "error",
                "message": "API key not found"
            }
    
    def has_permission(self, user_or_key: str, permission: Permission, 
                     is_api_key: bool = False) -> bool:
        """
        Check if a user or API key has a specific permission.
        
        Args:
            user_or_key: Username or API key ID
            permission: Permission to check
            is_api_key: Whether the identifier is an API key ID
            
        Returns:
            True if the user/key has the permission, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if is_api_key:
            cursor.execute('''
            SELECT permissions FROM api_keys WHERE key_id = ? AND is_active = 1
            ''', (user_or_key,))
        else:
            cursor.execute('''
            SELECT permissions FROM users WHERE username = ? AND is_active = 1
            ''', (user_or_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        permissions = json.loads(result[0])
        
        # Check if the permission is in the list
        return permission.name in permissions
    
    def get_permissions(self, user_or_key: str, is_api_key: bool = False) -> List[str]:
        """
        Get all permissions for a user or API key.
        
        Args:
            user_or_key: Username or API key ID
            is_api_key: Whether the identifier is an API key ID
            
        Returns:
            List of permission names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if is_api_key:
            cursor.execute('''
            SELECT permissions FROM api_keys WHERE key_id = ? AND is_active = 1
            ''', (user_or_key,))
        else:
            cursor.execute('''
            SELECT permissions FROM users WHERE username = ? AND is_active = 1
            ''', (user_or_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return []
        
        return json.loads(result[0])
    
    def log_audit(self, user: str, action: str, resource: str, status: str,
                details: Dict[str, Any] = None, ip_address: str = None) -> None:
        """
        Log an audit event.
        
        Args:
            user: Username or API key ID
            action: Action performed
            resource: Resource affected
            status: Status of the action (success, failed, error)
            details: Additional details
            ip_address: IP address of the request
        """
        if details is None:
            details = {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO audit_log (
            timestamp, user, action, resource, status, details, ip_address
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            user,
            action,
            resource,
            status,
            json.dumps(details),
            ip_address
        ))
        
        conn.commit()
        conn.close()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as a string
        """
        encrypted = self._cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Encrypted data as a string
            
        Returns:
            Decrypted data
        """
        try:
            decoded = base64.b64decode(encrypted_data)
            decrypted = self._cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Error decrypting data: {str(e)}")
            return ""
    
    def _generate_master_key(self) -> bytes:
        """Generate a secure master key."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32))
    
    def _derive_key(self, master_key: bytes, salt: bytes) -> bytes:
        """Derive an encryption key from the master key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key))
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash a password with a salt."""
        password_salt = (password + salt).encode()
        return hashlib.sha256(password_salt).hexdigest()
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _hash_api_key(self, key_secret: str) -> str:
        """Hash an API key secret for storage."""
        return hashlib.sha256(key_secret.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_hex(32)
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """
        Check if a user or API key has exceeded their rate limit.
        
        Args:
            identifier: Username or API key ID
            
        Returns:
            True if within rate limit, False otherwise
        """
        current_time = int(time.time())
        minute_window = current_time - (current_time % 60)
        
        # Initialize counter if not exists
        if identifier not in self.request_counts:
            self.request_counts[identifier] = {
                "count": 0,
                "window": minute_window
            }
        
        # Reset counter if in a new minute window
        if self.request_counts[identifier]["window"] != minute_window:
            self.request_counts[identifier] = {
                "count": 0,
                "window": minute_window
            }
        
        # Get rate limit from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try to find as API key first, then as user
        cursor.execute("SELECT rate_limit FROM api_keys WHERE key_id = ?", (identifier,))
        result = cursor.fetchone()
        
        if not result:
            cursor.execute("SELECT rate_limit FROM users WHERE username = ?", (identifier,))
            result = cursor.fetchone()
        
        conn.close()
        
        rate_limit = result[0] if result else 100  # Default rate limit
        
        # Increment counter
        self.request_counts[identifier]["count"] += 1
        
        # Check if exceeded
        return self.request_counts[identifier]["count"] <= rate_limit 