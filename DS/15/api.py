from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from guardrails import Answer


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    question: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=5)
    use_graph: bool = True


def create_app(guard):
    app = FastAPI(title='Lab15 bounded Energy GraphRAG')

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse(status_code=422, content={'detail': 'Invalid request'})

    @app.post('/ask', response_model=Answer)
    def ask(body: Request):
        return guard.ask(body.question.strip(), body.top_k, body.use_graph)

    @app.get('/health')
    def health():
        try:
            return guard.engine.health()
        except Exception:
            raise HTTPException(503, 'Backend unavailable')

    return app
