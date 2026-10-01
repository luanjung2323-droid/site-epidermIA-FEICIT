"""
epidermIA - interface web (Flask) do projeto de deteccao de lesoes de pele.

Este arquivo NAO contem logica de diagnostico. Toda a inferencia do modelo
(pre-processamento, threshold, Grad-CAM) fica em diagnostico.py, extraida de
prever_imagem.py sem nenhuma alteracao de valores.

ATENCAO: projeto academico (TCC), NAO e ferramenta de diagnostico medico.
"""

from flask import Flask, jsonify, render_template, request
from PIL import Image

from diagnostico import diagnosticar
from formulario import QUESTOES, calcular_resultado, obter_mensagem_combinacao

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB

_QUESTOES_POR_ID = {q["id"]: q for q in QUESTOES}


@app.route("/")
def index():
    return render_template("index.html", questoes=QUESTOES)


@app.route("/diagnosticar", methods=["POST"])
def rota_diagnosticar():
    arquivo = request.files.get("imagem")
    if arquivo is None or arquivo.filename == "":
        return jsonify({"erro": "Nenhuma imagem enviada."}), 400

    try:
        imagem = Image.open(arquivo.stream)
        imagem.load()
    except Exception:
        return jsonify({"erro": "Arquivo enviado nao e uma imagem valida."}), 400

    resultado = diagnosticar(imagem)
    rotulo = ("Sugestivo de câncer de pele maligno" if resultado["sugestivo"]
              else "Não sugestivo de câncer de pele maligno")

    return jsonify({
        "rotulo": rotulo,
        "sugestivo": resultado["sugestivo"],
        "probabilidade_percentual": round(resultado["prob"] * 100, 1),
        "grad_cam_base64": resultado["grad_cam_base64"],
    })


@app.route("/formulario/calcular", methods=["POST"])
def rota_calcular_formulario():
    dados = request.get_json(silent=True) or {}
    respostas_brutas = dados.get("respostas", {})

    # Mantem so pontuacoes que realmente existem como opcao da questao
    # correspondente (evita que uma resposta adulterada no client force
    # uma conduta indevida). Perguntas "tipo": "multipla" chegam como lista
    # de pontos -- cada valor e checado contra os pontos disponiveis na
    # questao, e o numero de vezes que um mesmo valor pode se repetir e
    # limitado a quantas opcoes daquela questao realmente valem esse tanto
    # (nao da pra selecionar a mesma opcao duas vezes).
    respostas = {}
    for qid, bruto in respostas_brutas.items():
        questao = _QUESTOES_POR_ID.get(qid)
        if questao is None:
            continue

        pontos_disponiveis = [op["pontos"] for op in questao["opcoes"]]

        if questao["tipo"] == "multipla":
            if not isinstance(bruto, list):
                continue
            restantes = pontos_disponiveis.copy()
            escolhidos = []
            for valor in bruto:
                if isinstance(valor, (int, float)) and valor in restantes:
                    restantes.remove(valor)
                    escolhidos.append(valor)
            if escolhidos:
                respostas[qid] = escolhidos
        else:
            if isinstance(bruto, (int, float)) and bruto in pontos_disponiveis:
                respostas[qid] = bruto

    resultado = calcular_resultado(respostas)

    sugestivo_imagem = dados.get("sugestivo_imagem")
    resultado["mensagem_combinacao"] = (
        obter_mensagem_combinacao(sugestivo_imagem, resultado)
        if isinstance(sugestivo_imagem, bool) else None
    )

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=True)
