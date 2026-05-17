"""
Menu.AI — Integração do Chat com LLM (LiteLLM) via Background Task
"""
import logging
import uuid
import json

from database.connection import SessionLocal
from database.models import SessaoChat, MensagemChat, RoleMensagem
from pipeline.model_router import ModelRouter

logger = logging.getLogger("menuai.chat_llm")

def processar_mensagem_chat_bg(sessao_id: str):
    """
    Função a ser executada em background.
    1. Carrega a sessão e suas mensagens.
    2. Envia para o LLM via ModelRouter.
    3. Salva a resposta do assistente no banco.
    """
    db = SessionLocal()
    try:
        sessao = db.query(SessaoChat).filter(SessaoChat.id == sessao_id).first()
        if not sessao:
            logger.warning(f"Sessão {sessao_id} não encontrada para processamento LLM.")
            return

        mensagens = db.query(MensagemChat).filter(MensagemChat.sessao_id == sessao_id).order_by(MensagemChat.created_at).all()
        
        llm_messages = []
        
        # Injetar o contexto do sistema
        system_content = "Você é o assistente inteligente do Menu.AI, ajudando o usuário a refinar a criação de cardápios e análises nutricionais."
        if sessao.contexto_json:
            try:
                ctx_str = json.dumps(sessao.contexto_json, ensure_ascii=False, indent=2)
                system_content += f"\n\nContexto Atual da Análise:\n{ctx_str}"
            except Exception:
                system_content += f"\n\nContexto Atual da Análise:\n{sessao.contexto_json}"
                
        llm_messages.append({"role": "system", "content": system_content})
        
        for msg in mensagens:
            if msg.role in [RoleMensagem.USER, RoleMensagem.ASSISTANT, RoleMensagem.SYSTEM, RoleMensagem.TOOL]:
                m = {"role": msg.role, "content": msg.content or ""}
                if msg.tool_calls:
                    m["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    m["tool_call_id"] = msg.tool_call_id
                llm_messages.append(m)

        # Enviar para o LLM
        empresa_id = sessao.usuario.empresa_id if sessao.usuario else None
        
        # Podemos ler o modelo do job (se houver) ou deixar o padrão multi-provider.
        model_id = None
        if sessao.job and sessao.job.parametros_json:
            params = sessao.job.parametros_json
            model_id = params.get("llm_model")

        router = ModelRouter(
            model_id=model_id,
            job_id=sessao.job_id,
            empresa_id=empresa_id,
            step_label="chat_refinamento"
        )
        
        logger.info(f"Chamando LLM para Sessão {sessao_id} (Mensagens: {len(llm_messages)})")
        result = router.call(messages=llm_messages)
        
        if result.success and result.response:
            choice = result.response.choices[0].message
            content = getattr(choice, "content", "")
            
            tool_calls_raw = getattr(choice, "tool_calls", None)
            tool_calls = []
            if tool_calls_raw:
                try:
                    tool_calls = [tc.model_dump() for tc in tool_calls_raw]
                except Exception:
                    tool_calls = tool_calls_raw

            nova_mensagem = MensagemChat(
                id=str(uuid.uuid4()),
                sessao_id=sessao_id,
                role=RoleMensagem.ASSISTANT,
                content=content or "",
                tool_calls=tool_calls if tool_calls else None,
            )
            db.add(nova_mensagem)
            db.commit()
            logger.info(f"Resposta salva para a Sessão {sessao_id}")
        else:
            logger.error(f"Erro ao processar LLM na Sessão {sessao_id}: {result.error}")
            
    except Exception as e:
        logger.error(f"Exceção ao processar chat em background: {e}", exc_info=True)
    finally:
        db.close()
