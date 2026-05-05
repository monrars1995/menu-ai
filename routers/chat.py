"""
Menu.AI — Router de Chat Conversacional
Gestão de sessões de chat e iterações de Human-in-the-Loop (HITL).
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import SessaoChat, MensagemChat, JobAgente, RoleMensagem
from database.schemas import (
    SessaoChatCreate,
    SessaoChatOut,
    SessaoChatDetalhada,
    NovaMensagemRequest,
    MensagemChatOut
)
from routers.auth_supabase import get_usuario_atual
from services.chat_llm import processar_mensagem_chat_bg

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/sessao", response_model=SessaoChatOut, status_code=status.HTTP_201_CREATED,
             summary="Criar sessão de chat")
def criar_sessao(
    body: SessaoChatCreate,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Cria uma nova sessão de chat, opcionalmente vinculada a um job_id."""
    
    # Valida job_id se fornecido
    if body.job_id:
        job = db.query(JobAgente).filter(JobAgente.job_id == body.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado.")
        if job.empresa_id != usuario.empresa_id and usuario.role != "super_admin":
            raise HTTPException(status_code=403, detail="Acesso negado ao Job.")

    nova_sessao = SessaoChat(
        id=str(uuid.uuid4()),
        usuario_id=usuario.id,
        job_id=body.job_id,
        titulo=body.titulo,
        status=body.status,
        contexto_json=body.contexto_json
    )
    db.add(nova_sessao)
    db.commit()
    db.refresh(nova_sessao)
    return SessaoChatOut.model_validate(nova_sessao)


@router.get("/sessao/{sessao_id}", response_model=SessaoChatDetalhada, summary="Obter sessão e mensagens")
def obter_sessao(
    sessao_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna uma sessão de chat e todo o seu histórico de mensagens."""
    sessao = db.query(SessaoChat).filter(SessaoChat.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    if sessao.usuario_id != usuario.id and usuario.role != "super_admin":
        raise HTTPException(status_code=403, detail="Acesso negado à sessão.")
        
    return SessaoChatDetalhada.model_validate(sessao)


@router.post("/{sessao_id}/refinar_analise", response_model=MensagemChatOut, summary="Hitl: Refinar Análise")
def refinar_analise(
    sessao_id: str,
    body: NovaMensagemRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """
    Adiciona uma mensagem de usuário à sessão para refinar a análise ou iteração atual.
    Este endpoint engatilha o LLM para processar a instrução via background tasks.
    """
    sessao = db.query(SessaoChat).filter(SessaoChat.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    if sessao.usuario_id != usuario.id and usuario.role != "super_admin":
        raise HTTPException(status_code=403, detail="Acesso negado à sessão.")
        
    # Salvar a mensagem do usuário
    nova_mensagem = MensagemChat(
        id=str(uuid.uuid4()),
        sessao_id=sessao_id,
        role=RoleMensagem.USER,
        content=body.content,
        metadata_json=body.metadata_json
    )
    db.add(nova_mensagem)
    db.commit()
    db.refresh(nova_mensagem)
    
    # Engatilhar processamento do LLM em background
    background_tasks.add_task(processar_mensagem_chat_bg, sessao_id)
    
    return MensagemChatOut.model_validate(nova_mensagem)
