"""GUVI callback utility for sending final results."""
import httpx
import logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intelligence_dict: Dict[str, Any],
    agent_notes: str
) -> bool:
    """
    Send final intelligence to GUVI evaluation endpoint.
    
    Args:
        session_id: Session identifier
        scam_detected: Whether scam was detected
        total_messages: Total messages exchanged
        intelligence_dict: Extracted intelligence dictionary
        agent_notes: Summary notes from agent
    
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intelligence_dict,
        "agentNotes": agent_notes
    }
    
    # LOG THE EXACT PAYLOAD BEING SENT
    import json
    logger.info(f"📤 Sending GUVI Callback to: {settings.guvi_callback_url}")
    logger.info(f"📤 Payload: {json.dumps(payload, indent=2)}")
    
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.guvi_callback_url,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"GUVI callback successful for session {session_id}")
                    return True
                else:
                    logger.warning(
                        f"GUVI callback failed (attempt {attempt + 1}/{max_retries}): "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
        
        except Exception as e:
            logger.error(
                f"GUVI callback error (attempt {attempt + 1}/{max_retries}): {e}"
            )
        
        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            import asyncio
            await asyncio.sleep(2 ** attempt)
    
    logger.error(f"GUVI callback failed after {max_retries} attempts for session {session_id}")
    return False
