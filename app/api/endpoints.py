"""API endpoints for honeypot system."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime
from app.models import MessageRequest, MessageResponse, ResponseMessage, EngagementMetrics, ExtractedIntelligence
from app.middleware.auth import verify_api_key

# Use RL-enhanced session manager
from app.core.session_manager_enhanced import session_manager
from app.core.scam_detector import ScamDetector
from app.core.intelligence_extractor import IntelligenceExtractor
from app.core.agent_orchestrator import agent_orchestrator
from app.core.relevance_detector import relevance_detector
from app.utils import send_guvi_callback
from app.models.guvi_response import GUVISimpleResponse
from app.config import settings
from app.rl import RLAgent
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize core components
scam_detector = ScamDetector()


@router.post("/", response_model=GUVISimpleResponse)  # Root endpoint
@router.post("/api/message", response_model=GUVISimpleResponse)  # Compatibility alias
async def process_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
) -> GUVISimpleResponse:
    """
    Process incoming message and engage scammer if detected.
    
    This endpoint:
    1. Detects scam intent
    2. Activates appropriate AI agent
    3. Generates human-like response
    4. Extracts intelligence
    5. Sends GUVI callback when conversation completes
    """
    logger.info(f"Processing message for session: {request.sessionId}")
    logger.info(f"📥 Request body: {request.model_dump_json(indent=2)}")
    logger.info(f"Message text: {request.message.text}")
    logger.info(f"Conversation history length: {len(request.conversationHistory)}")
    
    try:
        # Get or create session
        session = session_manager.get_or_create_session(request.sessionId)
        
        # Add incoming message to session
        session.add_message(request.message)
        
        # CRITICAL FIX: Use session's conversation history, NOT client's request
        # This ensures proper turn counting and conversation progression
        history_dict = []
        for msg in session.conversation_history[:-1]:  # Exclude current message (just added)
            ts_str = ""
            if hasattr(msg.timestamp, "isoformat"):
                ts_str = msg.timestamp.isoformat()
            else:
                ts_str = str(msg.timestamp)
                
            history_dict.append({
                "sender": msg.sender,
                "text": msg.text,
                "timestamp": ts_str
            })
        
        # Stage 1: Scam Detection (only on first message)
        if session.total_messages == 1:
            logger.info("First message - performing scam detection")
            scam_result = await scam_detector.detect(
                message_text=request.message.text,
                conversation_history=history_dict
            )
            
            session.scam_detected = scam_result.is_scam
            session.scam_type = scam_result.scam_type
            
            # 🆕 DETECT SPECIFIC SCAM CATEGORY for persona adaptation
            from app.core.scam_type_detector import scam_detector as type_detector
            detected_category = type_detector.detect(request.message.text)
            session.scam_type = detected_category  # Override with specific category
            logger.info(f"🎯 Scam category detected: {detected_category}")
            
            if not scam_result.is_scam:
                logger.info("No scam detected - returning standard response")
                # Fix: Return GUVISimpleResponse instead of MessageResponse
                return GUVISimpleResponse(
                    status="success",
                    reply="I think you have the wrong number."
                )
            
            # Scam detected - activate agent
            logger.info(f"Scam detected: {scam_result.scam_type}, activating {scam_result.recommended_agent} agent")
            agent_orchestrator.get_agent(scam_result.recommended_agent, session)
        
        # Stage 2: Extract Intelligence from scammer's message
        logger.info(f"🔍 EXTRACTING INTELLIGENCE from scammer message: '{request.message.text}'")
        extractor = IntelligenceExtractor()
        extractor.intelligence = session.intelligence  # Use session's accumulated intelligence
        
        # Log BEFORE extraction
        logger.info(f"📊 Intelligence BEFORE extraction: {session.intelligence.count_items()} items")
        logger.info(f"   - Phones: {list(session.intelligence.phoneNumbers)}")
        logger.info(f"   - Accounts: {list(session.intelligence.bankAccounts)}")
        logger.info(f"   - UPI IDs: {list(session.intelligence.upiIds)}")
        
        extractor.extract_from_message(request.message.text)
        session.intelligence = extractor.get_intelligence()
        
        # Log AFTER extraction
        logger.info(f"📊 Intelligence AFTER extraction: {session.intelligence.count_items()} items")
        logger.info(f"   - Phones: {list(session.intelligence.phoneNumbers)}")
        logger.info(f"   - Accounts: {list(session.intelligence.bankAccounts)}")
        logger.info(f"   - UPI IDs: {list(session.intelligence.upiIds)}")
        
        # Stage 2.3: Relevance Check (TEMPORARILY DISABLED - too aggressive)
        # Causing false rejections for credit card & other valid scams
        # TODO: Re-enable with better scam-type awareness
        """
        if session.scam_detected and session.total_messages > 1:
            is_relevant, reason, confidence = relevance_detector.is_relevant(
                scammer_message=request.message.text,
                scam_type=session.scam_type,
                conversation_history=[msg for msg in session.conversation_history if msg.sender == "scammer"]
            )
            
            if not is_relevant:
                logger.info(f"🛑 Message irrelevant ({reason}, confidence={confidence:.2f}). Ending conversation gracefully.")
                
                # Get natural ending response
                from app.core.relevance_detector import RelevanceDetector
                graceful_ending = RelevanceDetector.get_graceful_ending(session.scam_type, reason)
                
                # Mark session as complete
                session.is_complete = True
                session_manager.save_session_to_db(session)
                session_manager.schedule_cleanup(session.session_id)
                
                # Return graceful ending
                return GUVISimpleResponse(
                    status="success",
                    reply=graceful_ending
                )
        """
        
        
        # Stage 2.5: RL Action Selection (NEW!)
        rl_action = None
        if session.scam_detected:
            previous_intel_count = session.intelligence.count_items()
            rl_action = session_manager.get_rl_action(session, request.message.text)
            logger.info(f"🧠 RL Agent selected strategy: {rl_action}")
        
        # Stage 3: Generate Agent Response (multi-agent pipeline)
        if session.scam_detected:
            agent_response, intel_log = await agent_orchestrator.generate_response(
                session=session,
                scammer_message=request.message.text,
                conversation_history=history_dict,
                rl_action=rl_action  # Pass RL action to agent
            )
            # Attach intelligence log to session for tracking
            if not hasattr(session, 'intelligence_logs'):
                session.intelligence_logs = []
            session.intelligence_logs.append(intel_log)
            logger.info(f"[INTELLIGENCE_LOG] Turn {session.total_messages}: {intel_log}")
        else:
            # scam_detected is False — check if this is a follow-up message
            # SAFETY NET: If GUVI sends multiple messages, force-engage from turn 2+
            # This prevents dropping GUVI sessions where scam detection had a false-negative on turn 1
            if session.total_messages >= 2:
                logger.warning(f"⚠️ Safety net activated: scam_detected=False but turn={session.total_messages}. Force-engaging uncle persona.")
                session.scam_detected = True
                session.scam_type = "unknown"
                agent_orchestrator.get_agent("uncle", session)
                agent_response, intel_log = await agent_orchestrator.generate_response(
                    session=session,
                    scammer_message=request.message.text,
                    conversation_history=history_dict,
                    rl_action=None
                )
                if not hasattr(session, 'intelligence_logs'):
                    session.intelligence_logs = []
                session.intelligence_logs.append(intel_log)
            else:
                agent_response = "I think you have the wrong number."
                intel_log = None
        
        # Create response message
        response_msg = ResponseMessage(
            sender="user",
            text=agent_response,
            timestamp=datetime.now()
        )
        
        # Add agent response to session
        from app.models.request import Message
        session.add_message(Message(
            sender="user",
            text=agent_response,
            timestamp=response_msg.timestamp
        ))
        
        # Stage 4: Check if conversation should complete
        should_complete = session.should_complete(
            max_turns=settings.max_conversation_turns,
            timeout_seconds=settings.session_timeout_seconds
        )
        
        # Check if we have enough intelligence
        # CRITICAL: Use count_valuable_items() to exclude keywords
        # Keywords alone don't prove extraction - we need phone/account/UPI
        current_intel_count = session.intelligence.count_valuable_items()
        has_enough_intelligence = current_intel_count >= settings.min_intelligence_items
        
        # VERBOSE LOGGING FOR DEBUGGING
        logger.info(f"📊 Intelligence Check: count={current_intel_count}, threshold={settings.min_intelligence_items}")
        logger.info(f"📊 Extracted: phones={len(session.intelligence.phoneNumbers)}, accounts={len(session.intelligence.bankAccounts)}, upi={len(session.intelligence.upiIds)}, emails={len(session.intelligence.emailAddresses)}")
        logger.info(f"📊 Should complete={should_complete}, Has enough intel={has_enough_intelligence}")
        
        # Stage 5: Send GUVI callback if conversation complete OR intelligence increased
        # CRITICAL: Send callback when intelligence increases, but DO NOT close session unless complete
        
        should_send_update = has_enough_intelligence or should_complete
        logger.info(f"📤 GUVI Callback Decision: should_send_update={should_send_update} (scam_detected={session.scam_detected})")
        
        if should_send_update and session.scam_detected:
            if should_complete:
                 logger.info(f"Session {request.sessionId} completing - sending FINAL GUVI callback")
            else:
                 logger.info(f"Session {request.sessionId} has {current_intel_count} items - sending INTERMEDIATE GUVI callback")
            
            agent_notes = agent_orchestrator.get_agent_notes(session)
            
            # Re-scan full conversation history to catch any missed intelligence
            history_extractor = IntelligenceExtractor()
            history_extractor.intelligence = session.intelligence  # Use same object
            history_dict_full = [{"text": m.text, "sender": m.sender} for m in session.conversation_history]
            history_extractor.extract_from_history(history_dict_full)
            logger.info(f"📊 After history re-scan: phones={len(session.intelligence.phoneNumbers)}, accounts={len(session.intelligence.bankAccounts)}, upi={len(session.intelligence.upiIds)}, emails={len(session.intelligence.emailAddresses)}, links={len(session.intelligence.phishingLinks)}") 
            
            # Add bank predictions to notes
            bank_predictions = session.intelligence.predict_bank_names()
            if bank_predictions:
                agent_notes += f" | Potential Banks: {', '.join(bank_predictions)}"
            
            # Append elicitation summary: GUVI scores 1.5pts per elicitation attempt (max 7pts)
            # List every category of intel actively elicited from the scammer
            elicited = []
            if session.intelligence.phoneNumbers:   elicited.append(f"phone numbers ({len(session.intelligence.phoneNumbers)}x)")
            if session.intelligence.upiIds:         elicited.append(f"UPI IDs ({len(session.intelligence.upiIds)}x)")
            if session.intelligence.bankAccounts:   elicited.append(f"bank accounts ({len(session.intelligence.bankAccounts)}x)")
            if session.intelligence.emailAddresses: elicited.append(f"email addresses ({len(session.intelligence.emailAddresses)}x)")
            if session.intelligence.phishingLinks:  elicited.append(f"phishing links ({len(session.intelligence.phishingLinks)}x)")
            if session.intelligence.caseIds:        elicited.append(f"case/reference IDs ({len(session.intelligence.caseIds)}x)")
            if session.intelligence.policyNumbers:  elicited.append(f"policy numbers ({len(session.intelligence.policyNumbers)}x)")
            if session.intelligence.orderNumbers:   elicited.append(f"order numbers ({len(session.intelligence.orderNumbers)}x)")
            if elicited:
                agent_notes += f" | ELICITED FROM SCAMMER: {', '.join(elicited)}"
            
            # Send callback NON-BLOCKING via background task:
            # API returns the reply immediately; GUVI's system waits up to 10s separately for finalOutput.
            # This keeps API response time well under 5s regardless of GUVI server latency.
            background_tasks.add_task(
                send_guvi_callback,
                session_id=request.sessionId,
                scam_detected=session.scam_detected,
                total_messages=session.total_messages,
                intelligence_dict=session.intelligence.to_dict(),
                agent_notes=agent_notes,
                engagement_duration_seconds=session.get_engagement_duration(),
                scam_type=getattr(session, "scam_type", "unknown") or "unknown",
                confidence_level=getattr(session, "confidence_level", 0.95) or 0.95,
            )
            logger.info(f"\ud83d\udce4 GUVI callback queued as background task for session {request.sessionId}")
            
            # Mark complete immediately if conversation is over (don't wait for callback)
            if should_complete:
                session_manager.mark_complete(request.sessionId)
                
            # If intermediate update, we continue conversation!
        
        
        # Stage 5: Update RL Agent with Reward (NON-BLOCKING!)
        # Run in background to avoid blocking response
        if session.scam_detected and rl_action:
            new_intel_count = session.intelligence.count_items()
            # We'll do this in background task below
            logger.info(f"🧠 RL Agent will be updated in background with count: {new_intel_count}")
        
        # Stage 6: Save Session to Database (NON-BLOCKING!)
        # Database save happens AFTER response is sent to GUVI
        # This reduces response time by 200-500ms!
        logger.info(f"💾 Session will be saved to database in background")
        
        
        # CRITICAL: Schedule RL and DB operations as background tasks
        # These run AFTER the response is sent, ensuring fast response to GUVI
        
        # Background task 1: Update RL
        if session.scam_detected and rl_action:
            new_intel_count = session.intelligence.count_items()
            background_tasks.add_task(
                session_manager.update_rl,
                session,
                new_intel_count,
                request.message.text
            )
        
        # Background task 2: Save to DB
        background_tasks.add_task(
            session_manager.save_session_to_db,
            session
        )
        
        # Build GUVI-compliant simple response
        return GUVISimpleResponse(
            status="success",
            reply=response_msg.text,
            intelligence_log=intel_log  # None when not updated → excluded by model_dump(exclude_none=True)
        )
    
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_active_session_count(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/honeypot", response_model=GUVISimpleResponse)
async def honeypot_endpoint(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
) -> GUVISimpleResponse:
    """Alias for root endpoint — matches GUVI submission format /honeypot."""
    return await process_message(request, background_tasks, api_key)
