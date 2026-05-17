"""CRUD for tool credentials stored in DB."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_owner
from app.db.database import AsyncSessionLocal
from app.db.models import ToolCredential

router = APIRouter(prefix="/api/credentials", dependencies=[Depends(require_owner)])


class CredentialIn(BaseModel):
    name: str
    type: str
    credentials: dict
    is_active: bool = True


class CredentialOut(BaseModel):
    id: int
    name: str
    type: str
    is_active: bool
    # credentials intentionally omitted from GET responses


async def _session() -> AsyncSession:
    async with AsyncSessionLocal() as s:
        yield s


@router.get("/", response_model=list[CredentialOut])
async def list_credentials(session: AsyncSession = Depends(_session)):
    result = await session.execute(select(ToolCredential))
    rows = result.scalars().all()
    return [CredentialOut(id=r.id, name=r.name, type=r.type, is_active=r.is_active) for r in rows]


@router.post("/", response_model=CredentialOut, status_code=201)
async def create_credential(body: CredentialIn, session: AsyncSession = Depends(_session)):
    cred = ToolCredential(
        name=body.name,
        type=body.type,
        credentials=body.credentials,
        is_active=body.is_active,
    )
    session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return CredentialOut(id=cred.id, name=cred.name, type=cred.type, is_active=cred.is_active)


@router.put("/{cred_id}", response_model=CredentialOut)
async def update_credential(
    cred_id: int, body: CredentialIn, session: AsyncSession = Depends(_session)
):
    result = await session.execute(select(ToolCredential).where(ToolCredential.id == cred_id))
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    cred.name = body.name
    cred.type = body.type
    cred.credentials = body.credentials
    cred.is_active = body.is_active
    await session.commit()
    return CredentialOut(id=cred.id, name=cred.name, type=cred.type, is_active=cred.is_active)


@router.delete("/{cred_id}", status_code=204)
async def delete_credential(cred_id: int, session: AsyncSession = Depends(_session)):
    await session.execute(delete(ToolCredential).where(ToolCredential.id == cred_id))
    await session.commit()
