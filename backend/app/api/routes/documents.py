from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_project_service, get_rag_service
from app.api.schemas import ReferenceDocumentResponse, RetrievedChunkResponse
from app.services.project_service import ProjectService
from app.services.rag_service import RagService

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("", response_model=ReferenceDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference_document(
    project_id: str,
    file: UploadFile = File(...),
    project_service: ProjectService = Depends(get_project_service),
    rag_service: RagService = Depends(get_rag_service),
) -> ReferenceDocumentResponse:
    """Upload a reference document (.txt, .md, .pdf) for RAG grounding.
    Its content becomes retrievable context for the Planner and Architect
    agents on every future run in this project."""

    await project_service.get_project(project_id)
    raw_bytes = await file.read()
    document = await rag_service.ingest_reference_document(
        project_id, file.filename or "untitled", file.content_type or "text/plain", raw_bytes
    )
    return ReferenceDocumentResponse.from_domain(document)


@router.get("", response_model=list[ReferenceDocumentResponse])
async def list_reference_documents(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    rag_service: RagService = Depends(get_rag_service),
) -> list[ReferenceDocumentResponse]:
    await project_service.get_project(project_id)
    documents = await rag_service.list_documents(project_id)
    return [ReferenceDocumentResponse.from_domain(d) for d in documents]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_document(
    project_id: str,
    document_id: str,
    rag_service: RagService = Depends(get_rag_service),
) -> None:
    await rag_service.delete_document(project_id, document_id)


search_router = APIRouter(prefix="/projects/{project_id}", tags=["documents"])


@search_router.get("/search", response_model=list[RetrievedChunkResponse])
async def search_project_context(
    project_id: str,
    q: str,
    top_k: int = 5,
    project_service: ProjectService = Depends(get_project_service),
    rag_service: RagService = Depends(get_rag_service),
) -> list[RetrievedChunkResponse]:
    """Directly query the RAG index (reference docs + generated files) for
    this project -- the same retrieval agents use internally, exposed for
    inspection/demo purposes."""

    await project_service.get_project(project_id)
    chunks = await rag_service.retrieve(project_id, q, top_k=top_k)
    return [
        RetrievedChunkResponse(
            source_type=c.source_type, source_label=c.source_label, content=c.content, score=c.score
        )
        for c in chunks
    ]
