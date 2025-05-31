"""
Verify HubSpot Import Relationships
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text
from app.models import Company, Property, PropertyManager, PropertyManagerAssignment
import os
from dotenv import load_dotenv

async def verify_relationships():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    try:
        engine = create_async_engine(database_url)
        
        async with AsyncSession(engine) as db:
            print("🔍 Verifying HubSpot Import Relationships...\n")
            
            # 1. Check Companies
            result = await db.execute(select(Company))
            companies = result.scalars().all()
            
            print("📊 COMPANIES:")
            for company in companies:
                print(f"  • {company.name} (ID: {str(company.id)[:8]}...)")
                print(f"    Email: {company.contact_email}")
                print(f"    HubSpot ID: {company.hubspot_company_id}")
                print()
            
            # 2. Check Properties and their Company links
            result = await db.execute(select(Property))
            properties = result.scalars().all()
            
            print("🏢 PROPERTIES:")
            for prop in properties:
                # Get company name
                result = await db.execute(select(Company).where(Company.id == prop.company_id))
                company = result.scalar_one_or_none()
                company_name = company.name if company else "❌ NO COMPANY"
                
                print(f"  • {prop.name}")
                print(f"    Address: {prop.address}, {prop.city}, {prop.state} {prop.zip_code}")
                print(f"    Company: {company_name}")
                print(f"    Units: {prop.units_count}")
                print(f"    Amenities: {prop.amenities}")
                print()
            
            # 3. Check Property Managers and their Company links
            result = await db.execute(select(PropertyManager))
            managers = result.scalars().all()
            
            print("👥 PROPERTY MANAGERS:")
            for manager in managers:
                # Get company name
                result = await db.execute(select(Company).where(Company.id == manager.company_id))
                company = result.scalar_one_or_none()
                company_name = company.name if company else "❌ NO COMPANY"
                
                print(f"  • {manager.first_name} {manager.last_name}")
                print(f"    Email: {manager.email}")
                print(f"    Phone: {manager.phone}")
                print(f"    Role: {manager.role}")
                print(f"    Company: {company_name}")
                print()
            
            # 4. Check Property Manager Assignments
            result = await db.execute(
                select(PropertyManagerAssignment, Property, PropertyManager)
                .join(Property, PropertyManagerAssignment.property_id == Property.id)
                .join(PropertyManager, PropertyManagerAssignment.property_manager_id == PropertyManager.id)
            )
            assignments = result.all()
            
            print("🔗 PROPERTY MANAGER ASSIGNMENTS:")
            if assignments:
                for assignment, property_obj, manager in assignments:
                    print(f"  • {manager.first_name} {manager.last_name} → {property_obj.name}")
                    print(f"    Primary: {assignment.is_primary}")
                    print(f"    Start Date: {assignment.start_date}")
                    print(f"    End Date: {assignment.end_date or 'Active'}")
                    print()
            else:
                print("  ❌ No property manager assignments found")
                print()
            
            # 5. Relationship Summary
            print("📈 RELATIONSHIP SUMMARY:")
            print(f"  Companies: {len(companies)}")
            print(f"  Properties: {len(properties)}")
            print(f"  Property Managers: {len(managers)}")
            print(f"  Active Assignments: {len(assignments)}")
            
            # Check if all properties have companies
            unlinked_properties = [p for p in properties if not p.company_id]
            if unlinked_properties:
                print(f"  ❌ Properties without companies: {len(unlinked_properties)}")
            else:
                print(f"  ✅ All properties linked to companies")
            
            # Check if all managers have companies
            unlinked_managers = [m for m in managers if not m.company_id]
            if unlinked_managers:
                print(f"  ❌ Managers without companies: {len(unlinked_managers)}")
            else:
                print(f"  ✅ All managers linked to companies")
                
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_relationships()) 