import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class SupabaseClient:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)
    
    def save_candidate(self, candidate_data):
        """Save candidate to Supabase with fallback to JSON"""
        try:
            # Format data for Supabase
            supabase_data = {
                "name": candidate_data.get("name"),
                "email": candidate_data.get("email"),
                "phone": candidate_data.get("phone"),
                "experience": candidate_data.get("experience"),
                "position": candidate_data.get("position"),
                "location": candidate_data.get("location"),
                "programming_languages": candidate_data.get("programming_languages", []),
                "frameworks": candidate_data.get("frameworks", []),
                "databases": candidate_data.get("databases", []),
                "tools": candidate_data.get("tools", []),
                "cloud_platforms": candidate_data.get("cloud_platforms", []),
                "other_skills": candidate_data.get("other_skills"),
                "generated_questions": candidate_data.get("generated_questions"),
                "loom_video_url": candidate_data.get("loom_video_url"),
                "status": "submitted"
            }
            
            result = self.supabase.table("candidates").insert(supabase_data).execute()
            return {"success": True, "data": result.data[0]}
            
        except Exception as e:
            # Fallback to JSON storage
            return self.save_to_json(candidate_data, str(e))
    
    def save_to_json(self, candidate_data, error_msg):
        """Fallback JSON storage"""
        try:
            if os.path.exists("data/candidates.json"):
                with open("data/candidates.json", 'r') as f:
                    candidates = json.load(f)
            else:
                candidates = []
            
            candidate_data['timestamp'] = datetime.now().isoformat()
            candidate_data['supabase_error'] = error_msg
            candidates.append(candidate_data)
            
            with open("data/candidates.json", 'w') as f:
                json.dump(candidates, f, indent=2)
            
            return {"success": True, "fallback": "json", "error": error_msg}
        except Exception as json_error:
            return {"success": False, "error": str(json_error)}
    
    def get_candidates(self):
        """Fetch candidates from Supabase"""
        try:
            result = self.supabase.table("candidates").select("*").execute()
            return result.data
        except Exception as e:
            return [] 