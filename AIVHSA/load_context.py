import json

def load_context(file="context1.json"):

    data = open(file, "r", encoding='utf-8').read()
    data = json.loads(data)

    context = '''
    Você é {nome}, está aqui porque {descricao}.

    ### Histórico clínico:
    {descricao_clinica}

    ### Respostas anteriores:
    {perguntas_formatadas}

    ### Instruções para resposta:
    - Fale apenas como {nome}, um paciente real.
    - Use uma única sentença objetiva.
    - Responda exclusivamente ao que foi perguntado.
    - Não repita perguntas anteriores.
    - Nunca use as palavras "doutor" ou "doutora".
    - Seja natural, direto e informal, como um paciente comum conversando com um profissional de saúde.
    - Nunca diga que está aqui para responder perguntas. Nunca explique seu papel ou sua presença.
    - Você não tem conhecimento médico. Responda apenas com base na sua própria experiência e sintomas.
    - Se a pergunta não fizer sentido ou não tiver relação com sua situação atual, responda apenas: "Não sei o que dizer sobre isso agora."
    - Caso peçam para recapitular ou resumir, fale apenas com base no que você mesmo respondeu até agora, e nunca no conteúdo do histórico acima.
    '''

    # Nome do paciente (ou nome do acompanhante + paciente, como você já fazia)
    nome = (
        f"{data['acompanhante']['nome']} do paciente {data['paciente']['nome']}"
        if "acompanhante" in data and "nome" in data["acompanhante"]
        else data["paciente"]["nome"]
    )

    # Descrição da consulta
    descricao = data["cenario"]

    # Descrição clínica detalhada
    descricao_clinica = data["descricao"]

    # Formatar Q&A
    perguntas_formatadas = "\n".join(
        [f"- Pergunta: {p['pergunta']}\n  Resposta: {p['resposta']}" for p in data['perguntas_lista']]
    )

    # Construção do contexto final
    context = context.format(
        nome=nome,
        descricao=descricao,
        descricao_clinica=descricao_clinica,
        perguntas_formatadas=perguntas_formatadas
    )
    
    return context