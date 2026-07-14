"""Remove duplicate categories: merge old 器械注册部 into new workflow modules."""
import asyncio, sys
sys.path.insert(0, '.')
from app.database import async_session_maker
from app.models.category import Category
from app.models.document import Document
from sqlalchemy import text, select, func

async def clean():
    async with async_session_maker() as db:
        r = await db.execute(text("SELECT name, id FROM categories"))
        cats = {row[0]: str(row[1]) for row in r.fetchall()}

        moves = [
            ('III类医疗器械注册', '注册资料'),
            ('I类医疗器械注册', '注册资料'),
            ('II类医疗器械注册', '注册资料'),
            ('检测代理', '3. 校验技术要求'),
            ('注册申报模板 & 案例库', '注册资料'),
            ('应急补发', '发补意见'),
            ('分类界定', '2. 分类目录'),
        ]

        for child, parent in moves:
            if child in cats and parent in cats:
                await db.execute(text(
                    "UPDATE categories SET parent_id = :pid WHERE name = :name"
                ), {'pid': cats[parent], 'name': child})
                print(f'  Moved {child} -> {parent}')

        old_dept = cats.get('器械注册部')
        if old_dept:
            r = await db.execute(select(Category).where(Category.parent_id == old_dept))
            remaining = [c.name for c in r.scalars().all()]
            if not remaining:
                await db.execute(text(
                    "UPDATE categories SET visible_departments = '[]'::json WHERE id = :id"
                ), {'id': old_dept})
                print('\nHidden old 器械注册部 (no children left)')
            else:
                print(f'\nSkipped 器械注册部: still has children: {remaining}')

        await db.commit()
        print('Done')

if __name__ == '__main__':
    asyncio.run(clean())
