from fastapi import HTTPException, status, Response, Depends, APIRouter
from .. import schemas, models, oauth2
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from typing import List, Optional

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PostCreate)
async def create_post(post: schemas.PostCreate, db: Session = Depends(get_db),
                      user: schemas.User = Depends(oauth2.get_current_user)):
    print(user.id)
    new_post = models.Post(user_id=user.id, **post.dict())
    db.add(new_post)
    db.commit()

    return new_post


@router.get('/', response_model=List[schemas.PostOut])
async def get_posts(db: Session = Depends(get_db), limit: int = 10, query: Optional[str] = "", skip: int = 0,
                    user: schemas.User = Depends(oauth2.get_current_user)):
    print(user.id)
    posts = (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
        .group_by(models.Post.id)
        .order_by(func.count(models.Vote.post_id).desc())
        .filter(models.Post.title.contains(query))
        .limit(limit)
        .offset(skip)
        .all()
    )
    return posts


@router.get('/{id}', response_model=schemas.PostOut)
async def get_post(id: int, db: Session = Depends(get_db), user_id=Depends(oauth2.get_current_user)):
    post = db.query(models.Post, func.count(models.Vote.post_id).label("votes")).join(
        models.Vote, models.Vote.post_id == models.Post.id, isouter=True).group_by(models.Post.id).filter(
        models.Post.id == id).first()
    print(post)

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {id} not found")

    return post


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(id: int, db: Session = Depends(get_db), user=Depends(oauth2.get_current_user)):
    query = db.query(models.Post).filter(models.Post.id == id)
    post = query.first()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {id} not found")

    if post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not Allowed")

    query.delete()
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}", response_model=schemas.Post)
async def update_post(id: int, post: schemas.PostUpdate, db: Session = Depends(get_db),
                      user=Depends(oauth2.get_current_user)):
    query = db.query(models.Post).filter(models.Post.id == id)
    updated_post = query.first()

    if updated_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id {id} not found")

    if updated_post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not Allowed")

    query.update(post.dict(exclude_unset=True))
    db.commit()

    return updated_post
