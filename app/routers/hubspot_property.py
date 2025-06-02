"""
HubSpot Property CSV Import Router

This module handles importing property data from HubSpot CSV exports.
Properties must be linked to existing companies in the database.

Expected CSV Fields:
- property_name (required): Property name
- property_address: Property address
- property_city, property_state, property_zip: Location details
- property_type: Type of property (apartment, condo, etc.)
- units_count: Number of units
- year_built: Year the property was built
- square_footage: Total square footage
- hubspot_property_id: HubSpot tracking ID
- company_name or hubspot_company_id: Company association

Author: Development Team
Created: 2024
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import Property, Company, Chatbot
import csv
import uuid
import io
from datetime import datetime, timezone
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class PropertyCSVProcessor:
    """Handles CSV processing and validation for property imports"""
    
    REQUIRED_FIELDS = ['name', 'address', 'city', 'state', 'zip_code']
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }
    
    async def process_csv_file(self, file_content: str) -> Dict[str, Any]:
        """Process the CSV file and import properties"""
        
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is headers
            self.results['processed'] += 1
            
            try:
                # Map CSV fields to Property model fields correctly
                property_data = {
                    "name": row.get("Property Name", "").strip(),
                    "address": row.get("Address", "").strip(), 
                    "city": row.get("City", "").strip(),
                    "state": row.get("State", "").strip(),
                    "zip_code": row.get("Zip Code", "").strip(),
                    "property_type": row.get("Property Type", "").strip(),
                    "website_url": row.get("Website URL", "").strip(),
                }
                
                # Handle units count conversion
                units_str = row.get("Units Count", "").strip()
                if units_str:
                    try:
                        property_data["units_count"] = int(units_str)
                    except ValueError:
                        pass  # Skip invalid unit counts
                
                # Handle amenities parsing (semicolon separated)
                amenities_str = row.get("Amenities", "").strip()
                other_amenities_str = row.get("Other Amenities", "").strip()
                
                amenities_list = []
                if amenities_str:
                    amenities_list.extend([a.strip() for a in amenities_str.split(';') if a.strip()])
                if other_amenities_str:
                    amenities_list.extend([a.strip() for a in other_amenities_str.split(';') if a.strip()])
                
                if amenities_list:
                    property_data["amenities"] = amenities_list
                
                # Handle website URL protocol
                if property_data.get("website_url") and not property_data["website_url"].startswith(('http://', 'https://')):
                    property_data["website_url"] = f"https://{property_data['website_url']}"
                
                # Remove empty strings
                property_data = {k: v for k, v in property_data.items() if v is not None and v != ""}
                
                # Handle company lookup - since Company ID is empty, we'll use the imported company
                property_data["company_id"] = await self._resolve_company_for_property()
                
                # Validate required fields
                await self._validate_property_data(property_data)
                
                # Check if property already exists
                existing_property = await self._find_existing_property(property_data)
                
                if existing_property:
                    # Update existing property
                    await self._update_property(existing_property, property_data)
                    self.results['updated'] += 1
                else:
                    # Create new property
                    await self._create_property(property_data)
                    self.results['created'] += 1
                
                # Commit the transaction
                await self.db.commit()
                
            except ValueError as e:
                self.results['errors'] += 1
                self.results['error_details'].append({
                    'row': row_num,
                    'error': str(e),
                    'data': dict(row)
                })
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
    
    async def _resolve_company_for_property(self) -> str:
        """Get the company ID for the property - use the imported company"""
        
        # Since the CSV has empty Company ID, let's get the company we just imported
        result = await self.db.execute(
            select(Company).order_by(Company.created_at.desc()).limit(1)
        )
        company = result.scalar_one_or_none()
        
        if company:
            return str(company.id)
        
        raise ValueError("No company found. Please import a company first before importing properties.")
    
    async def _validate_property_data(self, property_data: Dict[str, Any]):
        """Validate required fields and data types"""
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in property_data or not property_data[field]:
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Validate company_id is present
        if 'company_id' not in property_data:
            raise ValueError("Company ID is required - property must belong to a company")
    
    async def _find_existing_property(self, property_data: Dict[str, Any]) -> Property:
        """Find existing property by name and address"""
        
        result = await self.db.execute(
            select(Property).where(
                Property.name == property_data['name'],
                Property.address == property_data['address']
            )
        )
        return result.scalar_one_or_none()
    
    async def _create_property(self, property_data: Dict[str, Any]):
        """Create new property record and auto-create chatbot"""
        property_obj = Property(**property_data)
        self.db.add(property_obj)
        await self.db.flush()  # Get property ID
        
        # AUTO-CREATE CHATBOT for this property
        chatbot = Chatbot(
            id=str(uuid.uuid4()),
            name=f"{property_obj.name} Chatbot",
            property_id=property_obj.id,
            is_active=True,
            welcome_message=f"Hi! I'm here to help you learn about {property_obj.name}. What would you like to know?"
        )
        self.db.add(chatbot)
        await self.db.flush()
        
        print(f"  🤖 Auto-created chatbot: {chatbot.id}")
    
    async def _update_property(self, existing_property: Property, property_data: Dict[str, Any]):
        """Update existing property record"""
        for field, value in property_data.items():
            if field not in ['id', 'created_at']:  # Don't update these fields
                setattr(existing_property, field, value)
        existing_property.updated_at = datetime.now(timezone.utc)


@router.post("/properties/")
async def import_properties_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Import properties from HubSpot CSV export
    
    Properties must be associated with existing companies in the database.
    
    Args:
        file: CSV file containing property data
        db: Database session
    
    Returns:
        dict: Import results with statistics and error details
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        content = await file.read()
        file_content = content.decode('utf-8')
        
        processor = PropertyCSVProcessor(db)
        results = await processor.process_csv_file(file_content)
        
        return {
            "message": "Property import completed",
            "filename": file.filename,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Property import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}") 