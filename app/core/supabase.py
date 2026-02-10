from supabase import create_client, Client
from functools import lru_cache
from app.core.config import get_settings

settings = get_settings()


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@lru_cache()
def get_supabase_admin_client() -> Client:
    """Get cached Supabase admin client with service key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


class SupabaseService:
    """Service class for Supabase operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.admin_client = get_supabase_admin_client()
    
    # Storage operations
    def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str = None):
        """Upload a file to Supabase Storage."""
        return self.admin_client.storage.from_(bucket).upload(
            path,
            file_data,
            {"content-type": content_type} if content_type else {}
        )
    
    def download_file(self, bucket: str, path: str) -> bytes:
        """Download a file from Supabase Storage."""
        return self.admin_client.storage.from_(bucket).download(path)
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """Get public URL for a file."""
        return self.admin_client.storage.from_(bucket).get_public_url(path)
    
    def delete_file(self, bucket: str, path: str):
        """Delete a file from Supabase Storage."""
        return self.admin_client.storage.from_(bucket).remove([path])
    
    # Database operations
    async def insert(self, table: str, data: dict):
        """Insert a record into a table."""
        return self.admin_client.table(table).insert(data).execute()
    
    async def update(self, table: str, id: str, data: dict):
        """Update a record in a table."""
        return self.admin_client.table(table).update(data).eq("id", id).execute()
    
    async def select(self, table: str, columns: str = "*", filters: dict = None):
        """Select records from a table."""
        query = self.admin_client.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute()
    
    async def delete(self, table: str, id: str):
        """Delete a record from a table."""
        return self.admin_client.table(table).delete().eq("id", id).execute()
    
    # User verification
    async def verify_token(self, token: str):
        """Verify a JWT token and return user data."""
        try:
            response = self.client.auth.get_user(token)
            return response.user if response and response.user else None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None


def get_supabase_service() -> SupabaseService:
    """Get Supabase service instance."""
    return SupabaseService()
