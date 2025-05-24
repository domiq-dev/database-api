import asyncpg
import asyncio

async def test_connection():
    conn = await asyncpg.connect(
        user='postgres',
        password='n_i0UlVay|054Q3J$aCk)Ey0LY7Z',
        database='postgres',
        host='database-dev-5-22-25.ch4go0gi6pk8.us-east-2.rds.amazonaws.com',
        port=5432
    )
    print("Connected!")
    await conn.close()

asyncio.run(test_connection())
