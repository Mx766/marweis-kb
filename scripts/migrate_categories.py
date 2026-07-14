"""Fast migration: move existing categories under new workflow modules using direct SQL."""
import asyncio, sys
sys.path.insert(0, '.')
from app.database import async_session_maker
from sqlalchemy import text

async def migrate():
    async with async_session_maker() as db:
        r = await db.execute(text("SELECT name, id FROM categories"))
        name_to_id = {row[0]: str(row[1]) for row in r.fetchall()}

        def cid(name):
            return name_to_id.get(name)

        moves = [
            ('NMPA 法规库', '通用法规（国内）'),
            ('FDA 法规库', '通用法规（国外）'),
            ('CE MDR 法规库', '通用法规（国外）'),
            ('IVD指导原则', '指导原则'),
            ('医疗器械指导原则', '指导原则'),
            ('体外诊断试剂审评报告', '审评论坛'),
            ('医疗器械审评报告', '审评论坛'),
            ('分类目录', '2. 分类目录'),
            ('创新申报', '注册资料'),
        ]

        count = 0
        for child_name, parent_name in moves:
            child_id = cid(child_name)
            parent_id = cid(parent_name)
            if child_id and parent_id:
                await db.execute(text(
                    "UPDATE categories SET parent_id = :pid WHERE id = :cid"
                ), {'pid': parent_id, 'cid': child_id})
                count += 1
                print(f'  OK  {child_name} -> {parent_name}')

        await db.commit()
        print(f'\nMoved {count} categories. Done.')

if __name__ == '__main__':
    asyncio.run(migrate())
