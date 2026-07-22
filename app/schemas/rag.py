from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    max_chunks: int = 8


class RetrievedChunkRead(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    document_type: str
    content: str
    rrf_score: float


class SearchResponse(BaseModel):
    results: list[RetrievedChunkRead]


class AskRequest(BaseModel):
    question: str
    max_chunks: int = 8


class CitationRead(BaseModel):
    document_id: int
    document_title: str
    document_type: str
    chunk_id: int


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationRead]
