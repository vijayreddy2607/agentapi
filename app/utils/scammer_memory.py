"""Scammer memory system - Learn from past scammer tactics."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)


class ScammerMemory:
    """Store and retrieve learned scammer patterns."""
    
    def __init__(self, db_path: str = "honeypot.db"):
        self.db_path = db_path
        self._create_memory_table()
    
    def _create_memory_table(self):
        """Create scammer_memory table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scammer_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scam_type VARCHAR NOT NULL,
                scammer_keywords TEXT,
                scammer_tactics TEXT,
                successful_counter_tactics TEXT,
                phone_number VARCHAR,
                upi_id VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                times_seen INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Scammer memory table ready")
    
    def store_scammer_pattern(
        self,
        scam_type: str,
        keywords: List[str],
        tactics: List[str],
        counter_tactics: List[str],
        phone: Optional[str] = None,
        upi: Optional[str] = None
    ):
        """
        Store a new scammer pattern for future learning.
        
        Args:
            scam_type: Type of scam detected
            keywords: Suspicious keywords used by scammer
            tactics: Scammer's tactics (urgency, threats, promises)
            counter_tactics: What worked to delay/engage scammer
            phone: Phone number if extracted
            upi: UPI ID if extracted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we've seen similar pattern before
        if phone:
            cursor.execute("""
                SELECT id, times_seen FROM scammer_memory
                WHERE phone_number = ? AND scam_type = ?
            """, (phone, scam_type))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE scammer_memory
                    SET times_seen = times_seen + 1,
                        last_seen = CURRENT_TIMESTAMP,
                        scammer_keywords = ?,
                        scammer_tactics = ?,
                        successful_counter_tactics = ?
                    WHERE id = ?
                """, (
                    json.dumps(keywords),
                    json.dumps(tactics),
                    json.dumps(counter_tactics),
                    existing[0]
                ))
                logger.info(f"📚 Updated memory for {phone} (seen {existing[1] + 1} times)")
                conn.commit()
                conn.close()
                return
        
        # Insert new memory
        cursor.execute("""
            INSERT INTO scammer_memory (
                scam_type, scammer_keywords, scammer_tactics,
                successful_counter_tactics, phone_number, upi_id
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            scam_type,
            json.dumps(keywords),
            json.dumps(tactics),
            json.dumps(counter_tactics),
            phone,
            upi
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Stored new scammer memory: {scam_type}")
    
    def get_similar_patterns(self, scam_type: str, keywords: List[str] = None) -> List[Dict]:
        """
        Retrieve similar scammer patterns from memory.
        
        Args:
            scam_type: Type of scam to search for
            keywords: Optional keywords to match
        
        Returns:
            List of similar scammer patterns
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get patterns for this scam type from last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        
        cursor.execute("""
            SELECT * FROM scammer_memory
            WHERE scam_type = ?
              AND last_seen >= ?
            ORDER BY times_seen DESC, last_seen DESC
            LIMIT 5
        """, (scam_type, cutoff_date.isoformat()))
        
        patterns = []
        for row in cursor.fetchall():
            pattern = dict(row)
            # Parse JSON fields
            pattern['scammer_keywords'] = json.loads(pattern['scammer_keywords'])
            pattern['scammer_tactics'] = json.loads(pattern['scammer_tactics'])
            pattern['successful_counter_tactics'] = json.loads(pattern['successful_counter_tactics'])
            patterns.append(pattern)
        
        conn.close()
        
        if patterns:
            logger.info(f"🧠 Found {len(patterns)} similar patterns for {scam_type}")
        
        return patterns
    
    def check_repeat_scammer(self, phone: str = None, upi: str = None) -> Optional[Dict]:
        """
        Check if this phone/UPI has been seen before.
        
        Args:
            phone: Phone number to check
            upi: UPI ID to check
        
        Returns:
            Previous pattern if found, None otherwise
        """
        if not phone and not upi:
            return None
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if phone:
            cursor.execute("""
                SELECT * FROM scammer_memory
                WHERE phone_number = ?
                ORDER BY last_seen DESC
                LIMIT 1
            """, (phone,))
        else:
            cursor.execute("""
                SELECT * FROM scammer_memory
                WHERE upi_id = ?
                ORDER BY last_seen DESC
                LIMIT 1
            """, (upi,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            pattern = dict(row)
            pattern['scammer_keywords'] = json.loads(pattern['scammer_keywords'])
            pattern['scammer_tactics'] = json.loads(pattern['scammer_tactics'])
            pattern['successful_counter_tactics'] = json.loads(pattern['successful_counter_tactics'])
            logger.warning(f"🚨 REPEAT SCAMMER DETECTED! Seen {pattern['times_seen']} times before!")
            return pattern
        
        return None
    
    def get_best_counter_tactics(self, scam_type: str) -> List[str]:
        """
        Get the most successful counter-tactics for a scam type.
        
        Args:
            scam_type: Type of scam
        
        Returns:
            List of successful counter-tactics
        """
        patterns = self.get_similar_patterns(scam_type)
        
        # Aggregate all successful tactics
        all_tactics = set()
        for pattern in patterns:
            all_tactics.update(pattern['successful_counter_tactics'])
        
        tactics_list = list(all_tactics)
        
        if tactics_list:
            logger.info(f"💡 Found {len(tactics_list)} proven counter-tactics for {scam_type}")
        
        return tactics_list
    
    def generate_memory_context(self, scam_type: str, phone: str = None) -> str:
        """
        Generate context string for agent based on memory.
        
        Args:
            scam_type: Type of scam detected
            phone: Phone number if available
        
        Returns:
            Context string to add to agent prompt
        """
        context_parts = []
        
        # Check for repeat scammer
        if phone:
            repeat = self.check_repeat_scammer(phone=phone)
            if repeat:
                context_parts.append(
                    f"⚠️ MEMORY: This scammer has been seen {repeat['times_seen']} times before! "
                    f"They previously used tactics: {', '.join(repeat['scammer_tactics'][:3])}. "
                    f"Last successful counter: {repeat['successful_counter_tactics'][0] if repeat['successful_counter_tactics'] else 'stalling'}."
                )
        
        # Get similar patterns
        patterns = self.get_similar_patterns(scam_type)
        if patterns and not phone:  # Only if not a repeat scammer
            common_tactics = set()
            successful_counters = set()
            
            for p in patterns[:3]:  # Top 3 patterns
                common_tactics.update(p['scammer_tactics'][:2])
                successful_counters.update(p['successful_counter_tactics'][:2])
            
            if common_tactics:
                context_parts.append(
                    f"💡 MEMORY: Similar {scam_type} scammers often use: {', '.join(list(common_tactics)[:3])}. "
                    f"Effective responses: {', '.join(list(successful_counters)[:2])}."
                )
        
        return " ".join(context_parts) if context_parts else ""


# Global memory instance
scammer_memory = ScammerMemory()
