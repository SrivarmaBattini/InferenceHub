# crud/tag.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.tag import Tag
from models.user import User


async def add_tag_to_user(
    db: AsyncSession,
    user_id: int,
    tag_name: str,
):
    """Create tag if needed, add to user, return user with tags loaded."""
    # find or create tag
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag    = result.scalar_one_or_none()
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        await db.flush()   # get tag.id without committing

    # load user with existing tags
    result = await db.execute(
        select(User)
        .options(selectinload(User.tags))
        .where(User.id == user_id)
    )
    user = result.scalar_one()
    if tag not in user.tags:
        user.tags.append(tag)

    await db.commit()
    await db.refresh(user)
    return user
