"""
Database connection and operations for Supabase PostgreSQL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class Database:
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable not set")
        
    def get_connection(self):
        return psycopg2.connect(self.connection_string)
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oauth_tokens (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT,
                        token_expiry TIMESTAMP,
                        scope TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
    
    def get_or_create_user(self, session_id: str) -> Dict[str, Any]:
        """Get user by session_id or create new user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE session_id = %s",
                    (session_id,)
                )
                user = cur.fetchone()
                
                if not user:
                    cur.execute(
                        "INSERT INTO users (session_id) VALUES (%s) RETURNING *",
                        (session_id,)
                    )
                    user = cur.fetchone()
                    conn.commit()
                else:
                    cur.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                        (user['id'],)
                    )
                    conn.commit()
                
                return dict(user)
    
    def update_user_email(self, user_id: int, email: str):
        """Update user's email address"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET email = %s WHERE id = %s",
                    (email, user_id)
                )
                conn.commit()
    
    def save_oauth_tokens(self, user_id: int, credentials) -> bool:
        """Save or update OAuth tokens for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM oauth_tokens WHERE user_id = %s",
                        (user_id,)
                    )
                    
                    cur.execute("""
                        INSERT INTO oauth_tokens 
                        (user_id, access_token, refresh_token, token_expiry, scope)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        credentials.token,
                        credentials.refresh_token,
                        credentials.expiry,
                        ' '.join(credentials.scopes) if credentials.scopes else None
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error saving OAuth tokens: {e}")
            return False
    
    def get_oauth_tokens(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get OAuth tokens for a user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM oauth_tokens WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                tokens = cur.fetchone()
                return dict(tokens) if tokens else None
    
    def update_oauth_tokens(self, user_id: int, access_token: str, expiry: datetime) -> bool:
        """Update access token and expiry for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE oauth_tokens 
                        SET access_token = %s, token_expiry = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (access_token, expiry, user_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating OAuth tokens: {e}")
            return False
    
    def delete_oauth_tokens(self, user_id: int) -> bool:
        """Delete OAuth tokens for a user (logout)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM oauth_tokens WHERE user_id = %s",
                        (user_id,)
                    )
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error deleting OAuth tokens: {e}")
            return False