import os
import hashlib
import json
import time
from pathlib import Path

class UserMemoryManager:
    def __init__(self, base_directory="/home/hades/.hades"):
        self.base_directory = Path(base_directory)
        self.users_directory = self.base_directory / "users"
        self.system_directory = self.base_directory / "system"
        
        # Create base directories
        os.makedirs(self.users_directory, exist_ok=True)
        os.makedirs(self.system_directory, exist_ok=True)
        
        # Monitor system files
        self._setup_system_monitoring()
    
    def _hash_api_key(self, api_key):
        """Create a hash of API key for directory naming"""
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:16]
    
    def _setup_system_monitoring(self):
        """Set up monitoring for system files like /etc/passwd and /etc/group"""
        passwd_dir = self.system_directory / "passwd"
        group_dir = self.system_directory / "groups"
        
        # Create directories
        os.makedirs(passwd_dir / "raw", exist_ok=True)
        os.makedirs(group_dir / "raw", exist_ok=True)
        
        # Initial capture of system files
        self._capture_system_file("/etc/passwd", passwd_dir / "raw" / "etc_passwd.txt")
        self._capture_system_file("/etc/group", group_dir / "raw" / "etc_group.txt")
        
        # Create metadata file with permissions info
        self._create_permissions_metadata(passwd_dir)
        self._create_group_relationships(group_dir)
        
    def _capture_system_file(self, source_path, target_path):
        """Copy system file to monitored location"""
        try:
            with open(source_path, 'r') as source:
                with open(target_path, 'w') as target:
                    target.write(source.read())
            return True
        except Exception as e:
            print(f"Error capturing {source_path}: {e}")
            return False
    
    def _create_permissions_metadata(self, passwd_dir):
        """Create metadata about user permissions from passwd file"""
        metadata_path = passwd_dir / "metadata" / "permissions.json"
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        # Parse passwd file and extract user info
        passwd_info = {}
        try:
            with open(passwd_dir / "raw" / "etc_passwd.txt", 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split(':')
                        if len(parts) >= 7:
                            username, _, uid, gid, comment, home, shell = parts
                            passwd_info[username] = {
                                "uid": uid,
                                "gid": gid,
                                "comment": comment,
                                "home": home,
                                "shell": shell
                            }
            
            # Write metadata
            with open(metadata_path, 'w') as f:
                json.dump({"users": passwd_info, "timestamp": time.time()}, f, indent=2)
                
        except Exception as e:
            print(f"Error creating permissions metadata: {e}")
    
    def _create_group_relationships(self, group_dir):
        """Create metadata about group memberships"""
        metadata_path = group_dir / "metadata" / "relationships.json"
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        # Parse group file and extract relationships
        group_info = {}
        try:
            with open(group_dir / "raw" / "etc_group.txt", 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split(':')
                        if len(parts) >= 4:
                            groupname, _, gid, members = parts
                            member_list = members.split(',') if members else []
                            group_info[groupname] = {
                                "gid": gid,
                                "members": member_list
                            }
            
            # Write metadata
            with open(metadata_path, 'w') as f:
                json.dump({"groups": group_info, "timestamp": time.time()}, f, indent=2)
                
        except Exception as e:
            print(f"Error creating group relationships metadata: {e}")
    
    def get_user_directory(self, api_key):
        """Get the .hades directory for a specific user based on API key"""
        user_hash = self._hash_api_key(api_key)
        user_dir = self.users_directory / user_hash
        
        # Ensure user directory exists
        os.makedirs(user_dir, exist_ok=True)
        os.makedirs(user_dir / "observations", exist_ok=True)
        os.makedirs(user_dir / "conversations", exist_ok=True)
        
        return user_dir
    
    def add_user_observation(self, api_key, observation):
        """Add a new observation for a user"""
        user_dir = self.get_user_directory(api_key)
        observation_dir = user_dir / "observations"
        
        # Create observation file with timestamp
        timestamp = int(time.time())
        observation_file = observation_dir / f"obs_{timestamp}.txt"
        
        try:
            with open(observation_file, 'w') as f:
                f.write(observation)
            return True
        except Exception as e:
            print(f"Error adding observation: {e}")
            return False
    
    def create_conversation(self, api_key):
        """Create a new conversation for a user"""
        user_dir = self.get_user_directory(api_key)
        conversation_dir = user_dir / "conversations"
        
        # Create unique conversation ID
        conversation_id = f"conv_{int(time.time())}_{os.urandom(4).hex()}"
        conv_path = conversation_dir / conversation_id
        
        # Create conversation structure
        os.makedirs(conv_path / "raw", exist_ok=True)
        os.makedirs(conv_path / "metadata", exist_ok=True)
        
        # Initialize conversation with metadata
        with open(conv_path / "metadata" / "context.json", 'w') as f:
            json.dump({
                "created_at": time.time(),
                "last_updated": time.time(),
                "message_count": 0
            }, f, indent=2)
            
        # Initialize empty messages file
        with open(conv_path / "raw" / "messages.jsonl", 'w') as f:
            pass
            
        return conversation_id
    
    def add_message_to_conversation(self, api_key, conversation_id, role, content):
        """Add a message to an existing conversation"""
        user_dir = self.get_user_directory(api_key)
        conv_path = user_dir / "conversations" / conversation_id
        
        if not os.path.exists(conv_path):
            return False
            
        # Add message to JSONL file
        messages_file = conv_path / "raw" / "messages.jsonl"
        message = {
            "timestamp": time.time(),
            "role": role,
            "content": content
        }
        
        try:
            with open(messages_file, 'a') as f:
                f.write(json.dumps(message) + "\n")
                
            # Update metadata
            metadata_file = conv_path / "metadata" / "context.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                
            metadata["last_updated"] = time.time()
            metadata["message_count"] += 1
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False
