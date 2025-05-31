"""
HubSpot Property Manager CSV Import Router

This module handles importing property manager data from HubSpot CSV exports.
Property managers must be linked to existing companies in the database.

Expected CSV Fields:
- first_name (required): Manager's first name
- last_name (required): Manager's last name
- email (required): Manager's email address
- phone: Manager's phone number
- title: Job title
- department: Department
- is_active: Whether manager is active (true/false)
- hubspot_contact_id: HubSpot tracking ID
- company_name or hubspot_company_id: Company association

Author: Development Team
Created: 2024
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import PropertyManager, Company, Property, PropertyManagerAssignment
import csv
import uuid
import io
from datetime import datetime, timezone, date
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class PropertyManagerCSVProcessor:
    """Handles CSV processing and validation for property manager imports"""
    
    FIELD_MAPPINGS = {
        'First name': 'first_name',
        'Last name': 'last_name', 
        'Email': 'email',
        'Phone': 'phone',
        'Role': 'role'
    }
    
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email', 'phone']
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'assignments_created': 0,
            'error_details': []
        }
    
    async def process_csv_file(self, file_content: str) -> Dict[str, Any]:
        """Process the CSV file and import property managers"""
        
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        for row_num, row in enumerate(csv_reader, start=2):
            self.results['processed'] += 1
            
            try:
                # Map CSV fields to PropertyManager model fields
                manager_data = {
                    "first_name": row.get("First name", "").strip(),
                    "last_name": row.get("Last name", "").strip(),
                    "email": row.get("Email", "").strip(),
                    "phone": row.get("Phone", "").strip(),
                    "role": row.get("Role", "").strip(),
                }
                
                # Remove empty strings
                manager_data = {k: v for k, v in manager_data.items() if v}
                
                # Get company ID - use the imported company since Company ID is empty
                manager_data["company_id"] = await self._resolve_company_for_manager()
                
                # Validate required fields
                await self._validate_manager_data(manager_data)
                
                # Check if manager already exists
                existing_manager = await self._find_existing_manager(manager_data)
                
                if existing_manager:
                    # Update existing manager
                    await self._update_manager(existing_manager, manager_data)
                    self.results['updated'] += 1
                    manager = existing_manager
                else:
                    # Create new manager
                    manager = await self._create_manager(manager_data)
                    self.results['created'] += 1
                
                # Handle property assignments
                properties_managed = row.get("Properties Managed", "").strip()
                if properties_managed:
                    await self._handle_property_assignments(manager, properties_managed)
                
                # Commit the transaction
                await self.db.commit()
                
            except ValueError as e:
                self.results['errors'] += 1
                self.results['error_details'].append({
                    'row': row_num,
                    'error': str(e),
                    'data': dict(row)
                })
                await self.db.rollback()
                continue
            except Exception as e:
                self.results['errors'] += 1
                self.results['error_details'].append({
                    'row': row_num,
                    'error': f"Unexpected error: {str(e)}",
                    'data': dict(row)
                })
                await self.db.rollback()
                continue
        
        return self.results

    async def _resolve_company_for_manager(self) -> str:
        """Get the company ID for the manager - use the imported company"""
        
        # Get the most recently imported company
        result = await self.db.execute(
            select(Company).order_by(Company.created_at.desc()).limit(1)
        )
        company = result.scalar_one_or_none()
        
        if company:
            return str(company.id)
        
        raise ValueError("No company found. Please import a company first before importing property managers.")

    async def _validate_manager_data(self, manager_data: Dict[str, Any]):
        """Validate required fields"""
        
        for field in self.REQUIRED_FIELDS:
            if field not in manager_data or not manager_data[field]:
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        if 'company_id' not in manager_data:
            raise ValueError("Company ID is required - manager must belong to a company")

    async def _find_existing_manager(self, manager_data: Dict[str, Any]) -> PropertyManager:
        """Find existing manager by email"""
        
        result = await self.db.execute(
            select(PropertyManager).where(PropertyManager.email == manager_data['email'])
        )
        return result.scalar_one_or_none()

    async def _create_manager(self, manager_data: Dict[str, Any]) -> PropertyManager:
        """Create new property manager record"""
        manager = PropertyManager(**manager_data)
        self.db.add(manager)
        await self.db.flush()
        return manager

    async def _handle_property_assignments(self, manager: PropertyManager, properties_managed: str):
        """Handle property assignments for the manager"""
        
        # Parse comma-separated property names
        property_names = [name.strip() for name in properties_managed.split(',') if name.strip()]
        
        for property_name in property_names:
            try:
                # Find property by name
                result = await self.db.execute(
                    select(Property).where(Property.name == property_name)
                )
                property_obj = result.scalar_one_or_none()
                
                if not property_obj:
                    logger.warning(f"Property '{property_name}' not found for manager assignment")
                    continue
                
                # Check if assignment already exists
                result = await self.db.execute(
                    select(PropertyManagerAssignment).where(
                        PropertyManagerAssignment.property_manager_id == manager.id,
                        PropertyManagerAssignment.property_id == property_obj.id,
                        PropertyManagerAssignment.end_date.is_(None)  # Active assignment
                    )
                )
                existing_assignment = result.scalar_one_or_none()
                
                if not existing_assignment:
                    # Create new assignment
                    assignment = PropertyManagerAssignment(
                        property_id=property_obj.id,
                        property_manager_id=manager.id,
                        is_primary=True,  # Assume primary for now
                        start_date=date.today()
                    )
                    self.db.add(assignment)
                    self.results['assignments_created'] += 1
                    
            except Exception as e:
                logger.error(f"Error creating assignment for property '{property_name}': {str(e)}")
                continue

    async def _update_manager(self, existing_manager: PropertyManager, manager_data: Dict[str, Any]):
        """Update existing property manager record"""
        for field, value in manager_data.items():
            if field not in ['id', 'created_at']:
                setattr(existing_manager, field, value)
        existing_manager.updated_at = datetime.now(timezone.utc)


@router.post("/property-managers/")
async def import_property_managers_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Import property managers from HubSpot CSV export
    
    Property managers must be associated with existing companies in the database.
    
    Args:
        file: CSV file containing property manager data
        db: Database session
    
    Returns:
        dict: Import results with statistics and error details
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        content = await file.read()
        file_content = content.decode('utf-8')
        
        processor = PropertyManagerCSVProcessor(db)
        results = await processor.process_csv_file(file_content)
        
        return {
            "message": "Property manager import completed",
            "filename": file.filename,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Property manager import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}") 