from fastapi import APIRouter, HTTPException
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from backend.utils.logger import RakshaLogger

router = APIRouter()

LOG_FILE = "backend/logs/audit.jsonl"

@router.get("/analytics/stats", tags=["Analytics"])
async def get_analytics_stats():
    """
    ELITE Usage Analytics (USP 8.1): Aggregates real-time usage data from audit logs.
    """
    if not os.path.exists(LOG_FILE):
        return {
            "total_queries": 0,
            "avg_latency": 0, 
            "top_intents": [],
            "recent_activity": []
        }

    total_queries = 0
    total_latency = 0.0
    intent_counts = {}
    recent_activity = []

    try:
        # Read last 1000 lines efficiently for demo purposes
        # In prod, this would be a DB query
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines[-1000:]: # Analyze last 1000 events
            try:
                entry = json.loads(line)
                if entry.get("event_type") == "QUERY_GENERATED":
                    total_queries += 1
                    details = entry.get("details", {})
                    
                    # Latency
                    params = details.get("latency_sec", 0)
                    total_latency += float(params)
                    
                    # Intent
                    intent = details.get("intent", "unknown")
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
                    
                    # Activity Feed
                    if len(recent_activity) < 10:
                        recent_activity.insert(0, {
                            "time": entry["timestamp"],
                            "query": details.get("query"),
                            "intent": intent,
                            "latency": params
                        })
            except json.JSONDecodeError:
                continue
                
        avg_latency = round(total_latency / total_queries, 3) if total_queries > 0 else 0
        
        # Sort intents
        sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_queries": total_queries,
            "avg_latency": avg_latency,
            "top_intents": [{"name": k, "count": v} for k, v in sorted_intents],
            "recent_activity": recent_activity[:10]
        }
        
    except Exception as e:
        RakshaLogger.error("Analytics", f"Failed to aggregate stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Analytics aggregation failed")
