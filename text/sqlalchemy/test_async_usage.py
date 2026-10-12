# itwwy/test/sqlalchemy/test_async_usage.py
# uv add aiosqlite

from __future__ import annotations

import asyncio
import datetime
from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import selectinload


class Base(AsyncAttrs, DeclarativeBase):
    pass

class B(Base):
    __tablename__ = "b"
    id: Mapped[int] = mapped_column(primary_key=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("a.id"))
    data: Mapped[str]

class A(Base):
    __tablename__ = "a"
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[str]
    create_date: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    bs: Mapped[List[B]] = relationship()

async def insert_objects(async_session: async_sessionmaker[AsyncSession]) -> None:
    async with async_session() as session:
        async with session.begin():
            session.add_all(
                [
                    A(bs=[B(data="b1"), B(data="b2")], data="a1"),
                    A(bs=[], data="a2"),
                    A(bs=[B(data="b3"), B(data="b4")], data="a3"),
                ]
            )

async def select_and_update_objects(
    async_session: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session() as session:
        stmt = select(A).order_by(A.id).options(selectinload(A.bs))
        result = await session.execute(stmt)
        for a in result.scalars():
            print(a, a.data)
            print(f"created at: {a.create_date}")
            for b in a.bs:
                print(b, b.data)
        result = await session.execute(select(A).order_by(A.id).limit(1))
        a1 = result.scalars().one()
        a1.data = "new data"
        await session.commit()
        # access attribute subsequent to commit; this is what
        # expire_on_commit=False allows
        print(a1.data)
        # alternatively, AsyncAttrs may be used to access any attribute
        # as an awaitable (new in 2.0.13)
        for b1 in await a1.awaitable_attrs.bs:
            print(b1, b1.data)

async def async_main() -> None:
    # 1. 创建引擎
    engine = create_async_engine("sqlite+aiosqlite:///async_mydb", echo=True)

    # 2. 创建异步session
    # async_sessionmaker: a factory for new AsyncSession objects.
    # expire_on_commit - don't expire objects after transaction commit
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # 3. 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 4. 插入数据
    await insert_objects(async_session)

    # 5. 查询和修改数据
    await select_and_update_objects(async_session)

    # 6. 关闭资源
    # for AsyncEngine created in function scope, close and
    # clean-up pooled connections
    await engine.dispose()


asyncio.run(async_main())