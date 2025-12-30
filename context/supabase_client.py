import os
from supabase import create_client, Client
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class SupabaseConfig:
    """Configuration and client setup for Supabase database operations"""
    def __init__(self):
        self.supabase_url = os.getenv("BISON_SUPABASE_PROJECT_URL")
        self.supabase_key = os.getenv("BISON_SUPABASE_ANON_KEY")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not set in environment variables.")
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    def get_client(self) -> Client:
        return self.client

class BisonLeadDataHandler:
    """Handles upsert and fetch operations for bison_lead_data table"""
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "bison_lead_data"

    def upsert_leads(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upsert a list of leads into the bison_lead_data table.
        Uses 'id' as the unique key.
        """
        if not leads:
            return {"status": "success", "message": "No leads to upsert", "upserted_count": 0}
        try:
            result = self.client.table(self.table_name).upsert(leads, on_conflict="id").execute()
            return {
                "status": "success",
                "message": f"Upserted {len(leads)} leads.",
                "upserted_count": len(leads),
                "result": result.data if hasattr(result, 'data') else None
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "upserted_count": 0}

    def fetch_leads(self, workspace_id: Optional[int] = None, client_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch leads from bison_lead_data, optionally filtered by workspace_id and/or client_name.
        """
        query = self.client.table(self.table_name).select("*")
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        if client_name is not None:
            query = query.eq("client_name", client_name)
        result = query.execute()
        return result.data if hasattr(result, 'data') else []

class BisonRepliesDataHandler:
    """Handles upsert and fetch operations for bison_unibox_replies table"""
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "bison_unibox_replies"

    def upsert_replies(self, replies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upsert a list of replies into the bison_unibox_replies table.
        Uses 'uuid' as the unique key.
        """
        if not replies:
            return {"status": "success", "message": "No replies to upsert", "upserted_count": 0}
        try:
            result = self.client.table(self.table_name).upsert(replies, on_conflict="uuid").execute()
            return {
                "status": "success",
                "message": f"Upserted {len(replies)} replies.",
                "upserted_count": len(replies),
                "result": result.data if hasattr(result, 'data') else None
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "upserted_count": 0}

    def fetch_replies(self, workspace_id: Optional[int] = None, client_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch replies from bison_unibox_replies, optionally filtered by workspace_id and/or client_name.
        """
        query = self.client.table(self.table_name).select("*")
        if workspace_id is not None:
            query = query.eq("workspace_id", workspace_id)
        if client_name is not None:
            query = query.eq("client_name", client_name)
        result = query.execute()
        return result.data if hasattr(result, 'data') else []


class BisonClientDBHandler:
    """Handles database operations for the bison_client_db table."""
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "bison_client_db"

    def fetch_all_clients(self) -> List[Dict[str, Any]]:
        """Fetches all records from the bison_client_db table."""
        try:
            result = self.client.table(self.table_name).select("*").execute()
            return result.data if hasattr(result, 'data') else []
        except Exception as e:
            print(f"Error fetching clients from DB: {e}")
            return []

    def upsert_clients(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upserts a list of client records into the Supabase table."""
        if not records:
            return {"status": "success", "message": "No records to upsert", "upserted_count": 0}
        try:
            response = self.client.table(self.table_name).upsert(records, on_conflict='workspace_id').execute()
            upserted_count = len(response.data)
            return {
                "status": "success", 
                "message": f"Upserted {upserted_count} records.",
                "upserted_count": upserted_count
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "upserted_count": 0}

    def update_client_status(self, workspace_id: int, status: str) -> None:
        """Updates the status of a single client."""
        try:
            self.client.table(self.table_name).update({'client_status': status}).eq('workspace_id', workspace_id).execute()
        except Exception as e:
            print(f"Error updating status for workspace {workspace_id}: {e}")

class BisonScheduledEmailsDataHandler:
    """Handles database operations for Bison scheduled emails data."""
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.table_name = "bison_scheduled_emails"

    def upsert_scheduled_emails(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upserts a list of scheduled email records into the Supabase table.
        """
        if not records:
            return {"status": "success", "message": "No records to upsert", "upserted_count": 0}
        try:
            response = self.client.table(self.table_name).upsert(records, on_conflict='id').execute()
            upserted_count = len(response.data)
            return {
                "status": "success", 
                "message": f"Upserted {upserted_count} records.",
                "upserted_count": upserted_count
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "upserted_count": 0} 

if __name__ == "__main__":
    supabase_client = SupabaseConfig().get_client()
    bison_client_db_handler = BisonClientDBHandler(supabase_client)
    # print(bison_client_db_handler.fetch_all_clients())