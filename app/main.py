"""
Property Management Chatbot - Main Application

This is the main FastAPI application entry point for the property management
chatbot system. It configures the application, includes routers, and sets up
global middleware and exception handlers.

Application Architecture:
- FastAPI framework for high-performance async API
- Modular router structure for organized endpoints
- Automatic API documentation via OpenAPI/Swagger
- Environment-based configuration support

Current Features:
- Conversation management API
- HubSpot CSV import system
- Automatic API documentation at /docs
- Health check endpoint
- CORS support (can be added as needed)

Future Enhancements:
- Authentication and authorization middleware
- Rate limiting for API protection
- Logging and monitoring integration
- Additional routers for users, chatbots, etc.

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from fastapi import FastAPI
from app.routers import (
    conversation, 
    hubspot_company, 
    hubspot_property, 
    hubspot_property_manager,
    auth,
    leads  # Add the new leads router
)
from datetime import datetime, timezone

# Create FastAPI application instance with metadata
app = FastAPI(
    title="Property Management Chatbot API",
    description="REST API for managing chatbot conversations, lead qualification, and HubSpot data synchronization",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI documentation
    redoc_url="/redoc",    # ReDoc documentation
    openapi_url="/openapi.json"  # OpenAPI schema
)

# Include conversation router
# This provides all conversation-related endpoints under the /conversations path
app.include_router(
    conversation.router,
    prefix="",  # No prefix - endpoints are at root level
    tags=["conversations"]  # Groups endpoints in documentation
)

# Include HubSpot import routers
app.include_router(
    hubspot_company.router,
    prefix="/api/v1/hubspot/import",
    tags=["hubspot-company-import"]
)

app.include_router(
    hubspot_property.router,
    prefix="/api/v1/hubspot/import", 
    tags=["hubspot-property-import"]
)

app.include_router(
    hubspot_property_manager.router,
    prefix="/api/v1/hubspot/import",
    tags=["hubspot-manager-import"]
)

# Include authentication router
app.include_router(auth.router, prefix="/api", tags=["Authentication"])

# Add the new leads router
app.include_router(
    leads.router,
    prefix="/api",
    tags=["leads"]
)

# Future router inclusions (uncomment as needed):
# app.include_router(user.router, prefix="/api/v1", tags=["users"])
# app.include_router(chatbot.router, prefix="/api/v1", tags=["chatbots"])

# Root endpoint for API health check and basic information
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns the current status of the API and basic information.
    Used by monitoring systems and load balancers.
    """
    return {
        "status": "healthy",
        "docs_url": "/docs",
        "description": "REST API for managing chatbot conversations, lead qualification, and HubSpot data synchronization",
        "features": [
            "Conversation Management",
            "Lead Qualification", 
            "HubSpot CSV Import",
            "User Management",
            "Chatbot Configuration"
        ],
        "endpoints": {
            "conversations": "/conversations/",
            "hubspot_companies": "/api/v1/hubspot/import/companies/",
            "hubspot_properties": "/api/v1/hubspot/import/properties/",
            "hubspot_managers": "/api/v1/hubspot/import/property-managers/",
            "auth_verify": "/api/auth/verify-manager",
            "documentation": "/docs"
        }
    }

# Optional: Add startup and shutdown event handlers
@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler
    
    This function runs when the application starts up.
    Use it for initialization tasks like:
    - Database connection verification
    - Cache warming
    - External service health checks
    """
    print("🚀 Property Management Chatbot API starting up...")
    # Add startup logic here

@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler
    
    This function runs when the application shuts down.
    Use it for cleanup tasks like:
    - Closing database connections
    - Saving state
    - Cleanup of temporary resources
    """
    print("🛑 Property Management Chatbot API shutting down...")
    # Add shutdown logic here

# Optional: Add middleware (uncomment as needed)
# from fastapi.middleware.cors import CORSMiddleware
# 
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure for production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )