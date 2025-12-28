#!/usr/bin/env python3
"""
Database module for storing conversation leads and customer information.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class LeadsDatabase:
    """Manages SQLite database for conversation leads"""
    
    def __init__(self, db_path="leads.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                business_id TEXT DEFAULT 'rainbow_default',
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                customer_name TEXT,
                customer_phone TEXT,
                language TEXT,
                messages TEXT NOT NULL,
                summary TEXT,
                lead_classification TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Simple migration: try adding business_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN business_id TEXT DEFAULT 'rainbow_default'")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass
            
        self.conn.commit()
    
    def create_conversation(self, session_id: str, language: str = "English", business_id: str = "rainbow_default") -> int:
        """Create a new conversation record"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (session_id, business_id, started_at, language, messages)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, business_id, datetime.now().isoformat(), language, json.dumps([])))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def update_conversation(
        self,
        session_id: str,
        messages: List[Dict],
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        summary: Optional[str] = None,
        lead_classification: Optional[str] = None,
        ended: bool = False
    ):
        """Update conversation with new messages and extracted info"""
        cursor = self.conn.cursor()
        
        updates = ["messages = ?"]
        params = [json.dumps(messages)]
        
        if customer_name:
            updates.append("customer_name = ?")
            params.append(customer_name)
        
        if customer_phone:
            updates.append("customer_phone = ?")
            params.append(customer_phone)
        
        if summary:
            updates.append("summary = ?")
            params.append(summary)
        
        if lead_classification:
            updates.append("lead_classification = ?")
            params.append(lead_classification)
        
        if ended:
            updates.append("ended_at = ?")
            params.append(datetime.now().isoformat())
        
        params.append(session_id)
        
        query = f"UPDATE conversations SET {', '.join(updates)} WHERE session_id = ?"
        cursor.execute(query, params)
        self.conn.commit()
    
    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """Get conversation by session ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_all_conversations(self, limit: int = 100, business_id: Optional[str] = None) -> List[Dict]:
        """Get all conversations, filtered by business_id if provided"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM conversations"
        params = []
        
        if business_id:
            query += " WHERE business_id = ?"
            params.append(business_id)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_leads(self, limit: int = 100) -> List[Dict]:
        """Get conversations with captured lead information"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations 
            WHERE customer_name IS NOT NULL OR customer_phone IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Singleton instance
_db_instance = None

def get_db() -> LeadsDatabase:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = LeadsDatabase()
    return _db_instance
