"""
HubSpot Company CSV Import Router

This module handles importing company data from HubSpot CSV exports.
Companies are the top-level entities in the property management hierarchy.

Expected CSV Fields:
- Company name (required): Company name
- Logo Website URL: Company website
- Mobile phone number: Company phone number
- Email: Primary contact email
- Hubspot Company ID: HubSpot tracking ID
- Contact first name, Contact last name: Contact information

Author: Development Team
Created: 2024
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import Company
import csv
import uuid
import io
from datetime import datetime, timezone
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class CompanyCSVProcessor:
    """Handles CSV processing and validation for company imports"""
    
    # Updated field mappings to match database schema
    FIELD_MAPPINGS = {
        'Company name': 'name',
        'Logo Website URL': 'logo_url',         # Fixed: maps to logo_url in database
        'Mobile phone number': 'contact_phone', # Fixed: maps to contact_phone in database
        'Email': 'contact_email',
        'Contact email': 'contact_email',
        'Hubspot Company ID': 'hubspot_company_id',
        'Contact first name': 'contact_first_name',
        'Contact last name': 'contact_last_name',
        'Contact ID': 'hubspot_contact_id',
        
        # Legacy field names
        'name': 'name',
        'domain': 'logo_url',           # Fixed
        'phone': 'contact_phone',       # Fixed
        'contact_email': 'contact_email',
        'hubspot_company_id': 'hubspot_company_id'
    }
    
    REQUIRED_FIELDS = ['name']
    
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
        """Process the CSV file and import companies"""
        
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is headers
            self.results['processed'] += 1
            
            try:
                # Map CSV fields to Company model fields correctly
                company_data = {
                    "name": row.get("Company name", "").strip(),
                    "contact_email": row.get("Email", "").strip(),
                    "contact_phone": row.get("Mobile phone number", "").strip(),
                    "logo_url": row.get("Logo Website URL", "").strip(),
                    "hubspot_company_id": row.get("Hubspot Company ID", "").strip()
                    # REMOVED: hubspot_contact_id - this field doesn't exist in Company model
                    # NOTE: "Contact ID" field is ignored for Company import
                }
                
                # Remove empty strings
                company_data = {k: v if v else None for k, v in company_data.items()}
                
                # Validate required fields
                await self._validate_company_data(company_data)
                
                # Check if company already exists
                existing_company = await self._find_existing_company(company_data)
                
                if existing_company:
                    # Update existing company
                    await self._update_company(existing_company, company_data)
                    self.results['updated'] += 1
                else:
                    # Create new company
                    await self._create_company(company_data)
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
    
    async def _transform_row_data(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Transform CSV row data to database format"""
        
        company_data = {}
        
        # Map CSV fields to database fields
        for csv_field, value in row.items():
            if csv_field in self.FIELD_MAPPINGS and value and value.strip():
                db_field = self.FIELD_MAPPINGS[csv_field]
                
                # Handle special transformations
                if db_field == 'logo_url' and value:
                    # Ensure website has proper protocol
                    if not value.startswith(('http://', 'https://')):
                        value = f"https://{value}"
                
                company_data[db_field] = value.strip()
        
        # Handle name field specially - it could be "Company name" or "name"
        if 'name' not in company_data:
            # Try alternative name mappings
            for field_name in ['Company name', 'company_name', 'Name']:
                if field_name in row and row[field_name] and row[field_name].strip():
                    company_data['name'] = row[field_name].strip()
                    break
        
        # Set defaults and system fields
        if 'id' not in company_data:
            company_data['id'] = uuid.uuid4()
        company_data['created_at'] = datetime.now(timezone.utc)
        company_data['updated_at'] = datetime.now(timezone.utc)
        
        return company_data
    
    async def _validate_company_data(self, company_data: Dict[str, Any]):
        """Validate required fields and data types"""
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in company_data or not company_data[field]:
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Validate company_size if present
        if 'company_size' in company_data and company_data['company_size']:
            try:
                company_data['company_size'] = int(company_data['company_size'])
            except ValueError:
                # If it's not a valid integer, remove it rather than fail
                del company_data['company_size']
    
    async def _find_existing_company(self, company_data: Dict[str, Any]) -> Company:
        """Find existing company by HubSpot ID or name"""
        
        # Try HubSpot ID first
        if company_data.get('hubspot_company_id'):
            result = await self.db.execute(
                select(Company).where(Company.hubspot_company_id == company_data['hubspot_company_id'])
            )
            company = result.scalar_one_or_none()
            if company:
                return company
        
        # Fall back to name
        result = await self.db.execute(
            select(Company).where(Company.name == company_data['name'])
        )
        return result.scalar_one_or_none()
    
    async def _create_company(self, company_data: Dict[str, Any]):
        """Create new company record"""
        company = Company(**company_data)
        self.db.add(company)
        await self.db.flush()
    
    async def _update_company(self, existing_company: Company, company_data: Dict[str, Any]):
        """Update existing company record"""
        for field, value in company_data.items():
            if field not in ['id', 'created_at']:  # Don't update these fields
                setattr(existing_company, field, value)
        existing_company.updated_at = datetime.now(timezone.utc)


@router.post("/companies/")
async def import_companies_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Import companies from HubSpot CSV export
    
    This endpoint processes a CSV file containing company data exported from HubSpot
    and imports it into the property management database.
    
    Supports both HubSpot export format and custom CSV formats.
    
    Args:
        file: CSV file containing company data
        db: Database session
    
    Returns:
        dict: Import results with statistics and error details
    """
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Process the CSV
        processor = CompanyCSVProcessor(db)
        results = await processor.process_csv_file(file_content)
        
        return {
            "message": "Company import completed",
            "filename": file.filename,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Company import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}") 