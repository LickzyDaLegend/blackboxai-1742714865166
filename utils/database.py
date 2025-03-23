import motor.motor_asyncio
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from utils.logger import Logger

logger = Logger.get_logger()

class Database:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_collection(cls, collection_name: str):
        """Get a MongoDB collection"""
        if cls._db is None:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                client = motor.motor_asyncio.AsyncIOMotorClient(config['mongo_uri'])
                cls._db = client.discord_bot
                logger.info("Connected to MongoDB")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise

        return cls._db[collection_name]

class ModLogger:
    @staticmethod
    async def log_mod_action(guild_id: int, action: str, moderator_id: int, target_id: int, reason: Optional[str] = None) -> bool:
        """Log a moderation action to the database"""
        try:
            collection = await Database.get_collection('mod_logs')
            await collection.insert_one({
                'guild_id': guild_id,
                'action': action,
                'moderator_id': moderator_id,
                'target_id': target_id,
                'reason': reason,
                'timestamp': datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log moderation action: {e}")
            return False

    @staticmethod
    async def get_user_history(guild_id: int, user_id: int) -> List[Dict]:
        """Get moderation history for a user"""
        try:
            collection = await Database.get_collection('mod_logs')
            return await collection.find({
                'guild_id': guild_id,
                'target_id': user_id
            }).sort('timestamp', -1).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []

class WarningManager:
    @staticmethod
    async def add_warning(guild_id: int, user_id: int, reason: str, mod_id: int) -> bool:
        """Add a warning to a user"""
        try:
            collection = await Database.get_collection('warnings')
            await collection.insert_one({
                'guild_id': guild_id,
                'user_id': user_id,
                'reason': reason,
                'mod_id': mod_id,
                'timestamp': datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to add warning: {e}")
            return False

    @staticmethod
    async def get_warnings(guild_id: int, user_id: int) -> List[Dict]:
        """Get all warnings for a user"""
        try:
            collection = await Database.get_collection('warnings')
            return await collection.find({
                'guild_id': guild_id,
                'user_id': user_id
            }).sort('timestamp', -1).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get warnings: {e}")
            return []

    @staticmethod
    async def remove_warning(guild_id: int, user_id: int, warning_id: str) -> bool:
        """Remove a warning from a user"""
        try:
            collection = await Database.get_collection('warnings')
            result = await collection.delete_one({
                'guild_id': guild_id,
                'user_id': user_id,
                '_id': warning_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove warning: {e}")
            return False

class TicketManager:
    @staticmethod
    async def create_ticket(guild_id: int, channel_id: int, user_id: int, ticket_type: str) -> bool:
        """Create a new ticket"""
        try:
            collection = await Database.get_collection('tickets')
            await collection.insert_one({
                'guild_id': guild_id,
                'channel_id': channel_id,
                'user_id': user_id,
                'type': ticket_type,
                'status': 'open',
                'created_at': datetime.utcnow(),
                'closed_at': None
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return False

    @staticmethod
    async def close_ticket(guild_id: int, channel_id: int) -> bool:
        """Close a ticket"""
        try:
            collection = await Database.get_collection('tickets')
            result = await collection.update_one(
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id,
                    'status': 'open'
                },
                {
                    '$set': {
                        'status': 'closed',
                        'closed_at': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to close ticket: {e}")
            return False

class GiveawayManager:
    @staticmethod
    async def create_giveaway(guild_id: int, channel_id: int, message_id: int, prize: str, end_time: datetime, winners: int) -> bool:
        """Create a new giveaway"""
        try:
            collection = await Database.get_collection('giveaways')
            await collection.insert_one({
                'guild_id': guild_id,
                'channel_id': channel_id,
                'message_id': message_id,
                'prize': prize,
                'end_time': end_time,
                'winner_count': winners,
                'participants': [],
                'winners': [],
                'active': True
            })
            return True
        except Exception as e:
            logger.error(f"Failed to create giveaway: {e}")
            return False

    @staticmethod
    async def get_active_giveaways() -> List[Dict]:
        """Get all active giveaways"""
        try:
            collection = await Database.get_collection('giveaways')
            return await collection.find({'active': True}).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get active giveaways: {e}")
            return []

    @staticmethod
    async def end_giveaway(giveaway_id: str) -> bool:
        """End a giveaway"""
        try:
            collection = await Database.get_collection('giveaways')
            result = await collection.update_one(
                {'_id': giveaway_id},
                {'$set': {'active': False}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to end giveaway: {e}")
            return False

class SecurityManager:
    @staticmethod
    async def log_security_event(guild_id: int, event_type: str, user_id: int, details: str) -> bool:
        """Log a security event"""
        try:
            collection = await Database.get_collection('security_logs')
            await collection.insert_one({
                'guild_id': guild_id,
                'event_type': event_type,
                'user_id': user_id,
                'details': details,
                'timestamp': datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return False

    @staticmethod
    async def get_recent_events(guild_id: int, event_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent security events"""
        try:
            collection = await Database.get_collection('security_logs')
            query = {'guild_id': guild_id}
            if event_type:
                query['event_type'] = event_type
            return await collection.find(query).sort('timestamp', -1).limit(limit).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            return []

class BadgeManager:
    @staticmethod
    async def add_badge(user_id: int, badge_name: str, awarded_by: int) -> bool:
        """Add a badge to a user"""
        try:
            collection = await Database.get_collection('badges')
            await collection.insert_one({
                'user_id': user_id,
                'badge_name': badge_name,
                'awarded_by': awarded_by,
                'awarded_at': datetime.utcnow()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to add badge: {e}")
            return False

    @staticmethod
    async def remove_badge(user_id: int, badge_name: str) -> bool:
        """Remove a badge from a user"""
        try:
            collection = await Database.get_collection('badges')
            result = await collection.delete_one({
                'user_id': user_id,
                'badge_name': badge_name
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove badge: {e}")
            return False

    @staticmethod
    async def get_user_badges(user_id: int) -> List[Dict]:
        """Get all badges for a user"""
        try:
            collection = await Database.get_collection('badges')
            return await collection.find({'user_id': user_id}).to_list(None)
        except Exception as e:
            logger.error(f"Failed to get user badges: {e}")
            return []