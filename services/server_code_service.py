from typing import Optional
from services.supabase_client import supabase_client


class ServerCodeService:
    """Service for fetching server source code by record identifier."""

    @staticmethod
    def get_source_code_by_id(server_id: str) -> Optional[str]:
        """Return the source_code for a given server id if active; otherwise None."""
        print(f"[DEBUG] ServerCodeService.get_source_code_by_id called with server_id: '{server_id}'")
        if not server_id:
            return None

        query = """
            SELECT source_code
            FROM servers
            WHERE id = %s AND status = 'active'
            LIMIT 1
        """
        result = supabase_client.execute_query(query, (server_id,))
        if not result:
            return None

        row = dict(result[0])
        return row.get("source_code")
