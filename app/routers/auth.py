"""
Authentication Router

Handles manager verification and authorization after OAuth login.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import PropertyManager, Property, Company, PropertyManagerAssignment
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class VerifyManagerRequest(BaseModel):
    email: EmailStr


class ManagerResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    role: str


class CompanyResponse(BaseModel):
    id: str
    name: str


class PropertyResponse(BaseModel):
    id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    units_count: int


class VerifyManagerResponse(BaseModel):
    authorized: bool
    manager: ManagerResponse = None
    company: CompanyResponse = None
    properties: List[PropertyResponse] = []
    error: str = None


@router.post("/auth/verify-manager", response_model=VerifyManagerResponse)
async def verify_manager(
    request: VerifyManagerRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify if an email belongs to a property manager and return their access permissions.
    
    This endpoint is called after frontend OAuth to check if the user is authorized
    to access the property management dashboard.
    
    Args:
        request: Email address from OAuth
        db: Database session
    
    Returns:
        Manager info, company info, and list of properties they can access
    """
    
    try:
        # 1. Check if email exists in PropertyManager table
        result = await db.execute(
            select(PropertyManager).where(PropertyManager.email == request.email)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            return VerifyManagerResponse(
                authorized=False,
                error="Email not found in property manager system"
            )
        
        # 2. Get company information
        result = await db.execute(
            select(Company).where(Company.id == manager.company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            logger.error(f"Manager {manager.email} has invalid company_id: {manager.company_id}")
            return VerifyManagerResponse(
                authorized=False,
                error="Manager company not found"
            )
        
        # 3. Get assigned properties
        result = await db.execute(
            select(Property, PropertyManagerAssignment)
            .join(PropertyManagerAssignment, Property.id == PropertyManagerAssignment.property_id)
            .where(
                PropertyManagerAssignment.property_manager_id == manager.id,
                PropertyManagerAssignment.end_date.is_(None)  # Active assignments only
            )
        )
        property_assignments = result.all()
        
        # 4. Build response
        properties = []
        for property_obj, assignment in property_assignments:
            properties.append(PropertyResponse(
                id=str(property_obj.id),
                name=property_obj.name,
                address=property_obj.address,
                city=property_obj.city,
                state=property_obj.state,
                zip_code=property_obj.zip_code,
                units_count=property_obj.units_count or 0
            ))
        
        return VerifyManagerResponse(
            authorized=True,
            manager=ManagerResponse(
                id=str(manager.id),
                first_name=manager.first_name,
                last_name=manager.last_name,
                email=manager.email,
                role=manager.role or "Property Manager"
            ),
            company=CompanyResponse(
                id=str(company.id),
                name=company.name
            ),
            properties=properties
        )
        
    except Exception as e:
        logger.error(f"Error verifying manager {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during verification")


@router.get("/auth/manager-properties/{manager_email}")
async def get_manager_properties(
    manager_email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get properties assigned to a specific manager (for API calls after verification).
    
    Args:
        manager_email: Manager's email address
        db: Database session
    
    Returns:
        List of property IDs this manager can access
    """
    
    try:
        # Get manager
        result = await db.execute(
            select(PropertyManager).where(PropertyManager.email == manager_email)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="Manager not found")
        
        # Get assigned property IDs
        result = await db.execute(
            select(PropertyManagerAssignment.property_id)
            .where(
                PropertyManagerAssignment.property_manager_id == manager.id,
                PropertyManagerAssignment.end_date.is_(None)
            )
        )
        property_ids = [str(row[0]) for row in result.all()]
        
        return {"property_ids": property_ids}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting properties for manager {manager_email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 