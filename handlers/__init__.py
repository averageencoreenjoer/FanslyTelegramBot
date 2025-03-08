from .common_handlers import router as common_router
from .admin_handlers import router as admin_router
from .worker_handlers import router as worker_router

__all__ = ["common_router", "admin_router", "worker_router"]