from app.core.security import verify_api_key

# This file acts as a bridge. 
# we can add more dependencies here later, 
# such as get_db_session or get_current_user.

__all__ = ["verify_api_key"]