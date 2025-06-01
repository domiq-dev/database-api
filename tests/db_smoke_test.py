import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import init_db, close_db, execute_query, fetch_one, get_pool

async def test_connection():
    """Test database connection and basic operations"""
    print("\n🔍 Testing database connection...")
    
    try:
        # Initialize database connection
        await init_db()
        print("✅ Database connection pool initialized successfully")
        
        # Test basic query
        print("\n🔍 Testing basic query...")
        result = await execute_query("SELECT version();")
        print(f"✅ Database version: {result}")
        
        # Test transaction
        print("\n🔍 Testing transaction...")
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Test insert
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS test_table (
                            id SERIAL PRIMARY KEY,
                            test_column TEXT
                        );
                    """)
                    print("✅ Test table created")
                    
                    # Test insert
                    await conn.execute(
                        "INSERT INTO test_table (test_column) VALUES ($1)",
                        "test_value"
                    )
                    print("✅ Test insert successful")
                    
                    # Test select
                    row = await conn.fetchrow(
                        "SELECT * FROM test_table WHERE test_column = $1",
                        "test_value"
                    )
                    print(f"✅ Test select successful: {row}")
                    
                    # Test delete
                    await conn.execute(
                        "DELETE FROM test_table WHERE test_column = $1",
                        "test_value"
                    )
                    print("✅ Test delete successful")
                    
                    # Clean up
                    await conn.execute("DROP TABLE IF EXISTS test_table;")
                    print("✅ Test table cleaned up")
        
        except Exception as e:
            print(f"❌ Transaction test failed: {e}")
            raise
        
        print("\n✅ All database tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        raise
    finally:
        # Close database connection
        await close_db()
        print("\n✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_connection()) 