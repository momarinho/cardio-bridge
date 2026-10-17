from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.endpoints import associados, eventos
import app.models  # Garante que todos os modelos sejam importados e registrados

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa as tabelas no banco de dados na inicialização
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## 🫀 CardioBridge: Enterprise ERP & Legacy Integration Gateway
    
    Gateway de integração corporativa projetado para a **Sociedade Brasileira de Cardiologia (SBC)**.
    
    ### Principais Recursos:
    * **Idempotência Transacional:** Impede cobranças e pedidos duplicados em congressos.
    * **Padrão Estrangulador (Strangler Fig):** Convivência e modernização suave de sistemas legados.
    * **Integração com SAP Business One:** Consumo nativo via Service Layer (OData / JSON).
    * **Auditoria Contínua:** Rastreamento ponta a ponta de todas as transações.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuração de CORS para permitir consumo por portais Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Status"])
def root():
    return {
        "sistema": settings.PROJECT_NAME,
        "versao": settings.VERSION,
        "status": "OPERATIONAL",
        "docs": "/docs",
        "erp_target": "SAP Business One (Service Layer OData)"
    }

@app.get("/health", tags=["Status"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "sap_service_layer": settings.SAP_SERVICE_LAYER_URL
    }

# Registro dos routers em /api/v1
app.include_router(associados.router, prefix="/api/v1")
app.include_router(eventos.router, prefix="/api/v1")