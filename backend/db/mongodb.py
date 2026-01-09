"""
MongoDB Database Connection

Provides async MongoDB connection for the RBAC system.
Uses motor for async operations with FastAPI.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB", "rakshakosh")

# =============================================================================
# DATABASE CLIENT
# =============================================================================

class Database:
    """MongoDB connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect(cls):
        """Initialize MongoDB connection."""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(MONGODB_URL)
            # Test connection
            await cls.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
    
    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            print("🔌 Disconnected from MongoDB")
    
    @classmethod
    def get_database(cls):
        """Get database instance."""
        if cls.client is None:
            raise RuntimeError("Database not connected. Call Database.connect() first.")
        return cls.client[DATABASE_NAME]
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a collection by name."""
        return cls.get_database()[collection_name]


# Convenience functions
def get_users_collection():
    """Get the users collection."""
    return Database.get_collection("users")


def get_documents_collection():
    """Get the documents metadata collection."""
    return Database.get_collection("documents")


# =============================================================================
# INDEXES (Run once on startup)
# =============================================================================

async def create_indexes():
    """Create necessary indexes for performance."""
    users = get_users_collection()
    docs = get_documents_collection()
    
    # Unique email index for users
    await users.create_index("email", unique=True)
    
    # Index for document lookups
    await docs.create_index("doc_id")
    await docs.create_index("owner_id")
    await docs.create_index("access_tier")
    
    print("📇 Database indexes created")
