import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
import socketio
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.database import get_db
from app.core.security import decode_access_token
from app.chat import services as chat_services
from app.chat.schemas import MessageWithCrisisCreate
from app.chat.models import Message
from app.chat.models import Conversation

logger = logging.getLogger(__name__)

class SocketManager:
    def __init__(self):
        # Improved CORS configuration - only allow specific origins
        allowed_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            # Add production URLs here when deploying
        ]

        self.sio = socketio.AsyncServer(
            cors_allowed_origins=allowed_origins,
            async_mode='asgi',
            logger=True,
            engineio_logger=True
        )

        # Log all incoming events for debugging
        @self.sio.on('*')
        async def catch_all(event, sid, data):
            logger.info(f"🎯 CATCH-ALL: Received event '{event}' from {sid}")
            logger.info(f"   Data: {data}")

        # Room tracking
        self.conversation_rooms: Dict[int, Set[str]] = {}  # conversation_id -> set of session_ids
        self.monitor_rooms: Dict[str, Set[str]] = {}       # monitor_id -> set of session_ids
        # Improved structure: session_id -> {type, monitor_id?, conversations[], rooms[]}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

        self.setup_events()

    def setup_events(self):
        @self.sio.event
        async def connect(sid: str, environ: dict, auth: Optional[dict]):
            logger.info(f"🔌 Client connected: {sid}")
            logger.info(f"   Current monitor rooms: {list(self.monitor_rooms.keys())}")
            await self.sio.emit('connected', {'status': 'success'}, to=sid)

        @self.sio.event
        async def disconnect(sid: str):
            logger.info(f"Client disconnected: {sid}")

            # Mark user's conversation as disconnected if it was a user session
            if sid in self.user_sessions:
                session_info = self.user_sessions[sid]
                if session_info.get('type') == 'user':
                    # Handle new list-based structure
                    conversations = session_info.get('conversations', [])
                    # Also check old structure for backward compatibility
                    if not conversations:
                        old_conv_id = session_info.get('conversation_id')
                        if old_conv_id:
                            conversations = [old_conv_id]

                    # Mark all user conversations as disconnected
                    for conversation_id in conversations:
                        await self.mark_conversation_disconnected(conversation_id)

            await self.cleanup_user_session(sid)

        @self.sio.event
        async def join_conversation(sid: str, data: dict):
            conversation_id = data.get('conversation_id')
            user_type = data.get('user_type', 'user')  # 'user' or 'monitor'

            if not conversation_id:
                await self.sio.emit('error', {'message': 'conversation_id required'}, to=sid)
                return

            # Add to conversation room
            room_name = f"conversation_{conversation_id}"
            await self.sio.enter_room(sid, room_name)

            # Track in conversation rooms
            if conversation_id not in self.conversation_rooms:
                self.conversation_rooms[conversation_id] = set()
            self.conversation_rooms[conversation_id].add(sid)

            # ROBUST FIX: Merge session info with support for multiple rooms and conversations
            if sid in self.user_sessions:
                # Update existing session
                session = self.user_sessions[sid]

                # Add conversation to list if not already there
                if 'conversations' not in session:
                    session['conversations'] = []
                if conversation_id not in session['conversations']:
                    session['conversations'].append(conversation_id)

                # Add room to list if not already there
                if 'rooms' not in session:
                    session['rooms'] = []
                if room_name not in session['rooms']:
                    session['rooms'].append(room_name)

                logger.info(f"Updated session for {sid}: joined conversation {conversation_id}")
                logger.info(f"   Type: {session.get('type')}, Monitor ID: {session.get('monitor_id')}")
                logger.info(f"   Conversations: {session['conversations']}, Rooms: {session['rooms']}")
            else:
                # Create new session with list structure
                self.user_sessions[sid] = {
                    'type': user_type,
                    'conversations': [conversation_id],
                    'rooms': [room_name]
                }
                logger.info(f"Created new session for {sid}: {user_type} in conversation {conversation_id}")

            await self.sio.emit('joined_conversation', {
                'conversation_id': conversation_id
            }, to=sid)

        @self.sio.event
        async def join_monitor(sid: str, data: dict):
            logger.info(f"📩 RECEIVED join_monitor event from {sid}")
            logger.info(f"   Data: {data}")

            monitor_id = data.get('monitor_id')
            token = data.get('token')

            if not monitor_id:
                logger.error(f"❌ No monitor_id provided in data: {data}")
                await self.sio.emit('error', {'message': 'monitor_id required'}, to=sid)
                return

            # SECURITY: Validate JWT token for monitors
            if not token:
                logger.error(f"❌ No authentication token provided for monitor {monitor_id}")
                await self.sio.emit('error', {'message': 'Authentication required for monitors'}, to=sid)
                return

            try:
                # Decode and validate token
                payload = decode_access_token(token)
                username = payload.get('sub')

                if not username:
                    logger.error(f"❌ Invalid token: no username in payload")
                    await self.sio.emit('error', {'message': 'Invalid authentication token'}, to=sid)
                    return

                # Verify that the monitor_id matches the authenticated user
                if username != monitor_id:
                    logger.error(f"❌ Monitor ID mismatch: token={username}, monitor_id={monitor_id}")
                    await self.sio.emit('error', {'message': 'Monitor ID does not match authenticated user'}, to=sid)
                    return

                logger.info(f"✅ Monitor {monitor_id} authenticated successfully")

            except JWTError as e:
                logger.error(f"❌ JWT validation failed for monitor {monitor_id}: {e}")
                await self.sio.emit('error', {'message': 'Invalid or expired authentication token'}, to=sid)
                return
            except Exception as e:
                logger.error(f"❌ Unexpected error during authentication: {e}")
                await self.sio.emit('error', {'message': 'Authentication failed'}, to=sid)
                return

            # Add to monitor room
            room_name = f"monitor_{monitor_id}"
            await self.sio.enter_room(sid, room_name)

            # Track in monitor rooms
            if monitor_id not in self.monitor_rooms:
                self.monitor_rooms[monitor_id] = set()
            self.monitor_rooms[monitor_id].add(sid)

            # ROBUST FIX: Merge session info instead of overwriting
            if sid in self.user_sessions:
                # Update existing session
                session = self.user_sessions[sid]
                session['type'] = 'monitor'
                session['monitor_id'] = monitor_id

                # Add room to list if not already there
                if 'rooms' not in session:
                    session['rooms'] = []
                if room_name not in session['rooms']:
                    session['rooms'].append(room_name)

                logger.info(f"Updated session for {sid}: joined monitor room {monitor_id}")
                logger.info(f"   Conversations preserved: {session.get('conversations', [])}")
                logger.info(f"   All rooms: {session['rooms']}")
            else:
                # Create new session with list structure
                self.user_sessions[sid] = {
                    'type': 'monitor',
                    'monitor_id': monitor_id,
                    'conversations': [],
                    'rooms': [room_name]
                }
                logger.info(f"Created new session for monitor {monitor_id} ({sid})")

            logger.info(f"👨‍⚕️ Monitor {monitor_id} ({sid}) joined monitoring")
            logger.info(f"   Total monitors now: {len(self.monitor_rooms)}")
            logger.info(f"   All monitor IDs: {list(self.monitor_rooms.keys())}")

            await self.sio.emit('joined_monitor', {
                'monitor_id': monitor_id
            }, to=sid)

        @self.sio.event
        async def leave_conversation(sid: str, data: dict):
            conversation_id = data.get('conversation_id')
            if conversation_id and conversation_id in self.conversation_rooms:
                self.conversation_rooms[conversation_id].discard(sid)
                if not self.conversation_rooms[conversation_id]:
                    del self.conversation_rooms[conversation_id]

            room_name = f"conversation_{conversation_id}"
            await self.sio.leave_room(sid, room_name)

            logger.info(f"User {sid} left conversation {conversation_id}")

        @self.sio.event
        async def send_message(sid: str, data: dict):
            conversation_id = data.get('conversation_id')
            message_text = data.get('message')
            sender = data.get('sender', 'user')
            session_id = data.get('session_id')

            if not conversation_id or not message_text:
                await self.sio.emit('error', {
                    'message': 'conversation_id and message required'
                }, to=sid)
                return

            try:
                # Get database session
                db_gen = get_db()
                db = next(db_gen)

                room_name = f"conversation_{conversation_id}"

                # Process message through actual chat service
                if sender == 'monitor':
                    conv = db.query(Conversation).get(conversation_id)

                    if not conv or conv.mode != 'monitor':
                        await self.sio.emit('error', {
                            'message': 'Monitor must take control of conversation first'
                        }, to=sid)
                        db.close()
                        return

                    # Monitor messages: save and broadcast immediately
                    monitor_message = Message(
                        sender=sender,
                        text=message_text,
                        conversation_id=conversation_id,
                        session_id=session_id
                    )
                    db.add(monitor_message)
                    db.commit()
                    db.refresh(monitor_message)

                    message_obj = {
                        'id': monitor_message.id,
                        'sender': monitor_message.sender,
                        'text': monitor_message.text,
                        'created_at': monitor_message.created_at.isoformat(),
                        'conversation_id': conversation_id,
                        'session_id': session_id,
                        'flagged': False,
                        'risk_level': None
                    }

                    logger.info(f"📤 Broadcasting monitor message to room: {room_name}")
                    logger.info(f"   Message ID: {monitor_message.id}, Sender: monitor")
                    logger.info(f"   Users in conversation room {conversation_id}: {self.conversation_rooms.get(conversation_id, set())}")

                    await self.sio.emit('new_message', {
                        'conversation_id': conversation_id,
                        'message': message_obj
                    }, room=room_name)

                    # Broadcast para todos os monitors conectados
                    for monitor_id in self.monitor_rooms:
                        monitor_room = f"monitor_{monitor_id}"
                        await self.sio.emit('new_message', {
                            'conversation_id': conversation_id,
                            'message': message_obj
                        }, room=monitor_room)

                    logger.info(f"✅ Monitor message broadcasted successfully")

                else:
                    # User messages: save immediately and broadcast
                    # Update conversation activity
                    conv = db.query(Conversation).get(conversation_id)
                    if conv:
                        conv.user_connected = True
                        conv.last_activity = datetime.now()

                    user_message = Message(
                        sender=sender,
                        text=message_text,
                        conversation_id=conversation_id,
                        session_id=session_id,
                        flagged=False,
                        risk_level=None
                    )
                    db.add(user_message)
                    db.commit()
                    db.refresh(user_message)

                    # Broadcast user message immediately
                    message_obj = {
                        'id': user_message.id,
                        'sender': user_message.sender,
                        'text': user_message.text,
                        'created_at': user_message.created_at.isoformat(),
                        'conversation_id': conversation_id,
                        'session_id': user_message.session_id,
                        'flagged': False,
                        'risk_level': None
                    }

                    await self.sio.emit('new_message', {
                        'conversation_id': conversation_id,
                        'message': message_obj
                    }, room=room_name)

                    # Broadcast para todos os monitors conectados
                    for monitor_id in self.monitor_rooms:
                        monitor_room = f"monitor_{monitor_id}"
                        await self.sio.emit('new_message', {
                            'conversation_id': conversation_id,
                            'message': message_obj
                        }, room=monitor_room)

                    # Process AI response and crisis detection in background
                    self.sio.start_background_task(
                        self._process_ai_response,
                        conversation_id,
                        user_message.id,
                        room_name
                    )

                # Close database session
                db.close()

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self.sio.emit('error', {
                    'message': 'Failed to process message'
                }, to=sid)

        @self.sio.event
        async def typing(sid: str, data: dict):
            conversation_id = data.get('conversation_id')
            user_type = data.get('user', 'user')

            if conversation_id:
                room_name = f"conversation_{conversation_id}"
                await self.sio.emit('user_typing', {
                    'conversation_id': conversation_id,
                    'user': user_type
                }, room=room_name, skip_sid=sid)

        @self.sio.event
        async def heartbeat(sid: str, data: dict):
            """Handle heartbeat from user to keep conversation active"""
            conversation_id = data.get('conversation_id')

            if not conversation_id:
                return

            # Update last_activity timestamp
            db_gen = get_db()
            db = next(db_gen)

            try:
                conv = db.query(Conversation).get(conversation_id)
                if conv:
                    conv.user_connected = True
                    conv.last_activity = datetime.now()
                    db.commit()
                    logger.debug(f"💓 Heartbeat received for conversation {conversation_id}")
            finally:
                db.close()

    async def _process_ai_response(
        self,
        conversation_id: int,
        user_message_id: int,
        room_name: str
    ):
        """Process AI response and crisis detection in background."""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Run crisis detection and get AI response
            # Message already saved, just analyze and respond
            ai_response, crisis_analysis = await chat_services.analyze_and_respond(
                db, conversation_id, user_message_id
            )

            # Update user message if flagged
            if crisis_analysis and crisis_analysis.requires_human:
                await self.sio.emit('message_updated', {
                    'conversation_id': conversation_id,
                    'message_id': user_message_id,
                    'flagged': True,
                    'risk_level': crisis_analysis.risk_level
                }, room=room_name)

            # Broadcast AI response
            if ai_response:
                ai_message_obj = {
                    'id': ai_response.id,
                    'sender': 'ai',
                    'text': ai_response.text,
                    'created_at': ai_response.created_at.isoformat(),
                    'conversation_id': conversation_id,
                    'flagged': ai_response.flagged,
                    'risk_level': ai_response.risk_level
                }

                await self.sio.emit('new_message', {
                    'conversation_id': conversation_id,
                    'message': ai_message_obj
                }, room=room_name)

                # Broadcast para todos os monitors conectados
                for monitor_id in self.monitor_rooms:
                    monitor_room = f"monitor_{monitor_id}"
                    await self.sio.emit('new_message', {
                        'conversation_id': conversation_id,
                        'message': ai_message_obj
                    }, room=monitor_room)

            # Handle crisis detection
            if crisis_analysis and crisis_analysis.requires_human:
                logger.info(f"🔍 Crisis detected in conversation {conversation_id}")
                logger.info(f"   Risk level: {crisis_analysis.risk_level}")
                logger.info(f"   Requires human: {crisis_analysis.requires_human}")

                user_msg = db.query(Message).get(user_message_id)
                await self.broadcast_crisis_alert(
                    conversation_id,
                    crisis_analysis,
                    user_msg.text if user_msg else ""
                )
            else:
                logger.debug(f"No crisis detected for message {user_message_id} in conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error processing AI response: {e}")
        finally:
            db.close()

    async def cleanup_user_session(self, sid: str):
        """Clean up user session when they disconnect"""
        if sid in self.user_sessions:
            session_info = self.user_sessions[sid]

            if session_info['type'] == 'user':
                # Handle new list-based structure
                conversations = session_info.get('conversations', [])
                # Also check old structure for backward compatibility
                if not conversations:
                    old_conv_id = session_info.get('conversation_id')
                    if old_conv_id:
                        conversations = [old_conv_id]

                # Clean up all conversation rooms
                for conversation_id in conversations:
                    if conversation_id and conversation_id in self.conversation_rooms:
                        self.conversation_rooms[conversation_id].discard(sid)
                        if not self.conversation_rooms[conversation_id]:
                            del self.conversation_rooms[conversation_id]
                        logger.info(f"User {sid} disconnected from conversation {conversation_id}")

            elif session_info['type'] == 'monitor':
                monitor_id = session_info.get('monitor_id')
                if monitor_id and monitor_id in self.monitor_rooms:
                    self.monitor_rooms[monitor_id].discard(sid)
                    if not self.monitor_rooms[monitor_id]:
                        del self.monitor_rooms[monitor_id]
                        logger.warning(f"⚠️  Monitor {monitor_id} disconnected - No more monitors in room")
                    else:
                        logger.info(f"Monitor {monitor_id} session {sid} disconnected ({len(self.monitor_rooms[monitor_id])} sessions remaining)")
                logger.info(f"   Monitors still connected: {list(self.monitor_rooms.keys())}")

                # Clean up conversation rooms that this monitor was in
                conversations = session_info.get('conversations', [])
                for conversation_id in conversations:
                    if conversation_id and conversation_id in self.conversation_rooms:
                        self.conversation_rooms[conversation_id].discard(sid)
                        if not self.conversation_rooms[conversation_id]:
                            del self.conversation_rooms[conversation_id]

            del self.user_sessions[sid]

    async def broadcast_crisis_alert(self, conversation_id: int, crisis_analysis: Any, user_message: str):
        """Broadcast crisis alert to all monitors"""
        # Check if user is still connected before sending alert
        db_gen = get_db()
        db = next(db_gen)

        try:
            conv = db.query(Conversation).get(conversation_id)
            if not conv or not conv.user_connected:
                logger.warning(f"⚠️  USER DISCONNECTED - Skipping crisis alert for conversation {conversation_id}")
                logger.warning(f"   User is no longer active in this conversation")
                return
        finally:
            db.close()

        # Convert RiskLevel enum to string for JSON serialization
        risk_level_str = crisis_analysis.risk_level if isinstance(crisis_analysis.risk_level, str) else crisis_analysis.risk_level.value

        alert_data = {
            'conversation_id': conversation_id,
            'analysis': {
                'risk_level': risk_level_str,
                'confidence': crisis_analysis.confidence,
                'keywords_found': crisis_analysis.keywords_found,
                'requires_human': crisis_analysis.requires_human,
                'emergency_contact': crisis_analysis.emergency_contact,
                'analysis_details': crisis_analysis.analysis_details
            },
            'message': user_message,
            'timestamp': datetime.now().isoformat()
        }

        # Debug: Log current state of monitor rooms
        logger.info(f"🚨 BROADCASTING CRISIS ALERT for conversation {conversation_id}")
        logger.info(f"   Risk level: {crisis_analysis.risk_level}")
        logger.info(f"   Confidence: {crisis_analysis.confidence}")
        logger.info(f"   Emergency contact: {crisis_analysis.emergency_contact}")
        logger.info(f"   Total monitor rooms: {len(self.monitor_rooms)}")
        logger.info(f"   Monitor IDs: {list(self.monitor_rooms.keys())}")

        # Send to all monitor rooms
        alerts_sent = 0
        for monitor_id in self.monitor_rooms:
            room_name = f"monitor_{monitor_id}"
            session_count = len(self.monitor_rooms[monitor_id])
            logger.info(f"   Sending to monitor {monitor_id} (room: {room_name}, sessions: {session_count})")

            await self.sio.emit('crisis_alert', alert_data, room=room_name)
            alerts_sent += 1

        if alerts_sent > 0:
            logger.info(f"✅ Crisis alert sent to {alerts_sent} monitor(s) for conversation {conversation_id}")
        else:
            logger.warning(f"⚠️  NO MONITORS CONNECTED - Crisis alert NOT sent for conversation {conversation_id}")
            logger.warning(f"   Alert data: {alert_data}")
            # TODO: Save to database for later retrieval

    async def notify_monitor_joined(self, conversation_id: int, monitor_id: str):
        """Notify conversation participants that a monitor joined"""
        room_name = f"conversation_{conversation_id}"
        await self.sio.emit('monitor_joined', {
            'conversation_id': conversation_id,
            'monitor_id': monitor_id,
            'message': 'Um monitor entrou na conversa'
        }, room=room_name)

    async def broadcast_conversation_escalated(self, conversation_id: int, monitor_id: str, reason: str):
        """Broadcast that a conversation was escalated"""
        # Notify conversation participants
        room_name = f"conversation_{conversation_id}"
        await self.sio.emit('conversation_escalated', {
            'conversation_id': conversation_id,
            'monitor_id': monitor_id,
            'reason': reason,
            'message': 'Conversa escalada para monitor humano'
        }, room=room_name)

        # Notify all monitors
        for monitor_id_room in self.monitor_rooms:
            monitor_room = f"monitor_{monitor_id_room}"
            await self.sio.emit('conversation_escalated', {
                'conversation_id': conversation_id,
                'monitor_id': monitor_id,
                'reason': reason
            }, room=monitor_room)

    async def mark_conversation_disconnected(self, conversation_id: int):
        """Mark conversation as disconnected when user leaves."""
        db_gen = get_db()
        db = next(db_gen)

        try:
            conv = db.query(Conversation).get(conversation_id)
            if conv:
                conv.user_connected = False
                conv.last_activity = datetime.now()
                db.commit()

                logger.info(f"🔌 User disconnected from conversation {conversation_id}")
                logger.info(f"   Conversation marked as inactive - alerts will be disabled")

                # Notify monitors that user disconnected
                for monitor_id in self.monitor_rooms:
                    room_name = f"monitor_{monitor_id}"
                    await self.sio.emit('user_disconnected', {
                        'conversation_id': conversation_id,
                        'timestamp': datetime.now().isoformat()
                    }, room=room_name)
        finally:
            db.close()

# Global instance
socket_manager = SocketManager()