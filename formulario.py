"""
Formulario de fatores de risco (epidermIA) -- versao revisada.

Questionario revisado pela dermatologista Dra. Natane Lopes (parecer tecnico de
28/08/2026 -- ver "PARECER TECNICO E VERSAO REVISADA.md" na raiz do projeto,
que e a fonte da verdade para todo texto, opcao e pontuacao abaixo). A revisao
se aplica exclusivamente a este questionario, NAO ao modelo de analise de
imagem (diagnostico.py), que nao foi objeto do parecer.

Independente da CNN: nao toca em diagnostico.py nem no calculo da
probabilidade da imagem. Este formulario apenas estima uma CONDUTA e um PRAZO
de encaminhamento a partir de fatores de risco -- nunca diz se a pessoa tem ou
nao cancer.

DESENHO GERAL (parecer, secao "Como combinar as pontuacoes"):

Os dois blocos medem coisas diferentes -- Bloco A mede o risco basal da
pessoa ao longo da vida, Bloco B mede a suspeicao da lesao fotografada agora
-- por isso NUNCA sao somados em um numero unico. Cada bloco e normalizado
como percentual do seu proprio maximo (respeitando os tetos de grupo do
parecer) e os dois viram eixos de uma matriz 3x3 (MATRIZ_CONDUTA) que devolve
a conduta e o prazo sugeridos.

Independentemente da matriz, uma REGRA DE SEGURANCA (12 situacoes especificas,
marcadas em QUESTOES via "regra_seguranca" nas opcoes) pode acionar
encaminhamento por conta propria. Quando isso acontece, a conduta da regra de
seguranca prevalece e o escore normalizado passa a ser exibido so como
informacao secundaria.

PONTOS EM ABERTO, respondidos nesta implementacao mas ainda nao confirmados
pela revisora -- ver conversa do projeto:

1. Teto de cada bloco (MAXIMO_BLOCO_A = 93, MAXIMO_BLOCO_B = 52): calculado
   aplicando os tetos de grupo que o parecer ja define explicitamente (A1-A4
   <= 5, A9-A10 <= 4, A17-A18 <= 4) e a regra do item 2 abaixo para as
   perguntas de multipla escolha. Note que MAXIMO_BLOCO_A subiu bastante (de
   61 para 93) ao marcar A15/A16/A20/A21 como multipla escolha -- ver
   ressalva no item 2.
2. Maximo de pergunta de multipla escolha: adotado "soma de todas as opcoes
   positivas" (nao so a de maior peso), por serem fatores/achados que podem
   coexistir na mesma pessoa. Perguntas "tipo": "multipla" -- por instrucao
   do autor -- sao A15, A16, A20, A21, A22 e B9 (alem de B10, que ja vinha
   marcada assim no parecer). Como consequencia, essas perguntas passam a
   pesar bem mais no bloco do que qualquer pergunta de escolha unica: A22=12,
   B10=13, A15=11, A16=9, A20=10, A21=19, B9=7 pontos possiveis cada.
   RESSALVA: em A15, A16 e A21 especificamente, algumas opcoes sao
   mutuamente excludentes na pratica clinica (ex.: A15 nao pode ter "um
   unico cancer nao melanoma" E "dois ou mais canceres nao melanoma" ao
   mesmo tempo; A21 reune sindromes geneticas raras dificilmente
   coexistentes) mesmo que o dado agora permita marcar as duas -- isso infla
   o maximo teorico do bloco (A21 sozinha: 5 -> 19) alem do que alguem
   atingiria na pratica. Registrado para confirmar com a revisora; nao
   resolvido nesta implementacao porque exigiria decidir QUAIS combinacoes
   proibir, o que nao esta no parecer.
3. Denominador de pergunta condicional: mantido FIXO (o maximo do bloco nao
   diminui quando A10 ou A12 ficam ocultas), porque nesses dois casos a
   resposta oculta e logicamente 0 (quem nunca queimou nao pode ter queimado
   antes dos 20 anos), e nao um dado desconhecido -- alem de manter os
   cortes da matriz comparaveis entre pessoas.
4. O parecer diz "quatro" perguntas condicionais no Bloco A, mas so A10
   (condicional a A9) e A12 (condicional a A11) estao explicitamente
   marcadas como tal no texto. Por instrucao do autor, tratadas como as
   UNICAS duas condicionais ate a revisora confirmar se ha mais alguma.
5. B15 (caroco/ingua perto da lesao) tem um comentario dizendo que, combinada
   com "qualquer sinal do Bloco B", deveria acionar encaminhamento
   prioritario -- mas nao e uma das 12 linhas da tabela formal de regra de
   seguranca, e o parecer nao especifica a combinacao. NAO implementada como
   regra de seguranca por falta de especificacao; tratada apenas como
   pergunta pontuada normalmente.
6. Prioridade entre regras de seguranca disparadas simultaneamente
   (PRIORIDADE_REGRA_SEGURANCA): escolha editorial deste arquivo, o parecer
   nao especifica como combinar disparos multiplos.
"""

# ---------------------------------------------------------------------------
# Tetos de grupo (perguntas que medem o mesmo fator e por isso tem soma
# maxima combinada menor que a soma dos maximos individuais).
# ---------------------------------------------------------------------------
TETOS_CONJUNTOS = {
    "A": [
        {"ids": ["A1", "A2", "A3", "A4"], "teto": 5},   # fenotipo pigmentar
        {"ids": ["A9", "A10"], "teto": 4},               # queimaduras solares
        {"ids": ["A17", "A18"], "teto": 4},              # nevos
    ],
    "B": [],
}

# Perguntas condicionais: só somam pontos (e só devem ser exibidas na
# interface) se a pergunta referenciada tiver sido respondida com pontos > 0.
# Ver ponto em aberto 4 no docstring.

QUESTOES = [
    # ================= Bloco A -- perfil de risco da pessoa =================
    {
        "id": "A1", "bloco": "A", "tipo": "unica",
        "texto": (
            "Fototipo cutâneo (classificação de Fitzpatrick). Pense em como "
            "sua pele reage à primeira exposição solar prolongada do verão "
            "(cerca de 30 minutos ao meio-dia, sem protetor)."
        ),
        "opcoes": [
            {"label": (
                "I — Pele muito clara. Sempre queima, nunca bronzeia. "
                "Frequentemente associada a cabelos ruivos ou loiros muito "
                "claros, olhos claros e sardas"
            ), "pontos": 3},
            {"label": "II — Pele clara. Queima com facilidade, bronzeia pouco e com dificuldade", "pontos": 2},
            {"label": "III — Pele morena clara. Queima moderadamente, bronzeia de forma gradual e uniforme", "pontos": 1},
            {"label": "IV — Pele morena moderada. Queima pouco, bronzeia com facilidade", "pontos": 0},
            {"label": "V — Pele morena escura. Raramente queima, bronzeia intensamente", "pontos": 0},
            {"label": "VI — Pele negra. Nunca queima, sempre intensamente pigmentada", "pontos": 0},
        ],
        # Fototipos V/VI valem 0 aqui, mas isso NAO reduz risco de melanoma
        # acral/ungueal -- o peso e recuperado no Bloco B (B12, B13).
    },
    {
        "id": "A2", "bloco": "A", "tipo": "unica",
        "texto": "Qual era a cor natural do seu cabelo aos 20 anos (antes de tinturas ou embranquecimento)?",
        "opcoes": [
            {"label": "Ruivo", "pontos": 2},
            {"label": "Loiro", "pontos": 1},
            {"label": "Castanho", "pontos": 0},
            {"label": "Preto", "pontos": 0},
        ],
    },
    {
        "id": "A3", "bloco": "A", "tipo": "unica",
        "texto": "Qual a cor dos seus olhos?",
        "opcoes": [
            {"label": "Azuis, verdes ou cinza", "pontos": 1},
            {"label": "Castanho-claros ou cor de mel", "pontos": 1},
            {"label": "Castanho-escuros ou pretos", "pontos": 0},
        ],
    },
    {
        "id": "A4", "bloco": "A", "tipo": "unica",
        "texto": (
            "Você tem sardas (efélides) no rosto, colo ou ombros — aquelas "
            "manchinhas claras e pequenas que escurecem no verão e clareiam "
            "no inverno?"
        ),
        "opcoes": [
            {"label": "Sim, muitas", "pontos": 2},
            {"label": "Sim, algumas", "pontos": 1},
            {"label": "Não tenho", "pontos": 0},
        ],
        # Separada de A17/A18 (pintas/nevos) no parecer: sarda mede
        # fotossensibilidade, nevo mede proliferacao melanocitica.
    },
    {
        "id": "A5", "bloco": "A", "tipo": "unica",
        "texto": (
            "Exposição solar crônica e ocupacional (dose acumulada ao longo "
            "da vida). Considere trabalho, deslocamento a pé, esportes ao ar "
            "livre e atividades rurais."
        ),
        "opcoes": [
            {"label": (
                "Trabalhei ou trabalho ao ar livre por 5 anos ou mais, "
                "várias horas por dia (lavoura, construção, pesca, "
                "entregas, segurança, esportes ao ar livre)"
            ), "pontos": 3},
            {"label": "Exposição diária moderada, de 1 a 3 horas por dia, na maior parte do ano", "pontos": 2},
            {"label": "Exposição eventual, 2 a 3 vezes por semana, por períodos curtos", "pontos": 1},
            {"label": "Praticamente não me exponho de forma prolongada", "pontos": 0},
        ],
    },
    {
        "id": "A6", "bloco": "A", "tipo": "unica",
        "texto": (
            "Exposição solar intermitente e recreacional — aquela "
            "concentrada em poucos dias, com pele desacostumada. Considere "
            "férias, veraneio, praia, piscina, rio e cachoeira."
        ),
        "opcoes": [
            {"label": (
                "Todos os anos, desde a infância ou adolescência, passei "
                "períodos de exposição intensa em férias escolares, "
                "veraneio ou praia"
            ), "pontos": 3},
            {"label": "Exposição intensa nos fins de semana, durante boa parte do ano", "pontos": 2},
            {"label": "Exposição intensa apenas eventual, algumas vezes ao ano", "pontos": 1},
            {"label": "Raramente ou nunca", "pontos": 0},
        ],
        # Padrao intermitente/de ferias -- distinto da exposicao cronica de
        # A5 -- e o mais associado a melanoma e carcinoma basocelular.
    },
    {
        "id": "A7", "bloco": "A", "tipo": "unica",
        "texto": "Em quais situações você aplica protetor solar com FPS 30 ou maior, de forma consistente?",
        "opcoes": [
            {"label": "Nunca ou quase nunca aplico", "pontos": 2},
            {"label": "Aplico somente quando vou à praia ou à piscina", "pontos": 1},
            {"label": "Aplico somente em atividades ao ar livre de fim de semana", "pontos": 1},
            {"label": "Aplico nas exposições eventuais, 2 a 3 vezes por semana", "pontos": 1},
            {"label": "Aplico diariamente, mas em dose única pela manhã, sem reaplicar", "pontos": 1},
            {"label": "Aplico diariamente e reaplico a cada 2 a 3 horas nas exposições prolongadas", "pontos": 0},
        ],
    },
    {
        "id": "A8", "bloco": "A", "tipo": "unica",
        "texto": (
            "Você usa medidas de fotoproteção física com regularidade "
            "(chapéu de aba larga, camisa de manga longa, roupa com "
            "proteção UV, óculos escuros, busca de sombra entre 10 h e "
            "16 h)?"
        ),
        "opcoes": [
            {"label": "Não, nenhuma dessas medidas", "pontos": 1},
            {"label": "Sim, pelo menos uma delas de forma habitual", "pontos": 0},
        ],
    },
    {
        "id": "A9", "bloco": "A", "tipo": "unica",
        "texto": (
            "Quantas vezes, ao longo de toda a vida, você teve queimadura "
            "solar forte — aquela com bolhas, ou com dor e descamação "
            "importante da pele?"
        ),
        "opcoes": [
            {"label": "6 ou mais vezes", "pontos": 3},
            {"label": "3 a 5 vezes", "pontos": 2},
            {"label": "1 a 2 vezes", "pontos": 1},
            {"label": "Nenhuma vez", "pontos": 0},
        ],
    },
    {
        "id": "A10", "bloco": "A", "tipo": "unica",
        "condicional_de": "A9",
        "texto": "Em que fase da vida essas queimaduras ocorreram?",
        "opcoes": [
            {"label": "Ocorreram antes dos 20 anos (infância ou adolescência)", "pontos": 2},
            {"label": "Ocorreram somente depois dos 20 anos", "pontos": 1},
            {"label": "Não tive queimaduras", "pontos": 0},
        ],
    },
    {
        "id": "A11", "bloco": "A", "tipo": "unica",
        "texto": "Você já usou câmara de bronzeamento artificial (solário)?",
        "opcoes": [
            {"label": "Sim, mais de 10 sessões ao longo da vida", "pontos": 3},
            {"label": "Sim, de 1 a 10 sessões", "pontos": 2},
            {"label": "Nunca usei", "pontos": 0},
        ],
    },
    {
        "id": "A12", "bloco": "A", "tipo": "unica",
        "condicional_de": "A11",
        "texto": "Com que idade você usou bronzeamento artificial pela primeira vez?",
        "opcoes": [
            {"label": "Antes dos 35 anos", "pontos": 1},
            {"label": "Aos 35 anos ou depois", "pontos": 0},
            {"label": "Nunca usei", "pontos": 0},
        ],
        # Bronzeamento artificial para fins esteticos e proibido no Brasil
        # (RDC ANVISA 56/2009); pergunta permanece relevante para quem usou
        # antes da proibicao ou no exterior.
    },
    {
        "id": "A13", "bloco": "A", "tipo": "unica",
        "texto": "Qual a sua idade?",
        "opcoes": [
            {"label": "70 anos ou mais", "pontos": 3},
            {"label": "50 a 69 anos", "pontos": 2},
            {"label": "40 a 49 anos", "pontos": 1},
            {"label": "18 a 39 anos", "pontos": 0},
        ],
        # Idade jovem NAO protege contra melanoma (uma das neoplasias mais
        # frequentes entre 20-39 anos); a idade pesa no risco basal, nunca
        # serve para descartar uma lesao suspeita.
    },
    {
        "id": "A14", "bloco": "A", "tipo": "unica",
        "texto": "Sexo biológico",
        "opcoes": [
            {"label": "Masculino", "pontos": 1},
            {"label": "Feminino", "pontos": 0},
        ],
    },
    {
        "id": "A15", "bloco": "A", "tipo": "multipla",
        "texto": "Você já teve algum câncer de pele ou lesão pré-cancerosa diagnosticada por médico?",
        "opcoes": [
            {"label": "Sim, melanoma", "pontos": 4, "regra_seguranca": "Seguimento dermatológico regular, qualquer lesão nova avaliada"},
            {"label": (
                "Sim, dois ou mais cânceres de pele não melanoma (carcinoma "
                "basocelular ou espinocelular)"
            ), "pontos": 3},
            {"label": "Sim, um único câncer de pele não melanoma", "pontos": 2},
            {"label": (
                "Sim, ceratose actínica, ou já fiz tratamento de campo "
                "(crioterapia, 5-fluorouracil, imiquimode, terapia "
                "fotodinâmica)"
            ), "pontos": 2},
            {"label": "Não / não sei", "pontos": 0},
        ],
    },
    {
        "id": "A16", "bloco": "A", "tipo": "multipla",
        "texto": "Algum parente de sangue já teve câncer de pele?",
        "opcoes": [
            {"label": (
                "Dois ou mais familiares com melanoma, ou melanoma em "
                "familiar antes dos 40 anos, ou melanoma associado a "
                "câncer de pâncreas na família"
            ), "pontos": 4},
            {"label": "Melanoma em parente de 1º grau (pai, mãe, irmão, filho)", "pontos": 3},
            {"label": "Melanoma apenas em parente de 2º grau (avós, tios, sobrinhos, meios-irmãos)", "pontos": 1},
            {"label": "Câncer de pele não melanoma em parente de 1º grau", "pontos": 1},
            {"label": "Não / não sei", "pontos": 0},
        ],
        # Primeira opcao sugere padrao de sindrome de melanoma familiar
        # (mutacao CDKN2A) -- justificaria encaminhamento para
        # aconselhamento genetico, independente da lesao fotografada.
    },
    {
        "id": "A17", "bloco": "A", "tipo": "unica",
        "texto": (
            "Contando apenas as pintas — manchas castanhas permanentes, que "
            "não mudam com as estações e são maiores que a cabeça de um "
            "alfinete — quantas você tem no corpo todo, incluindo costas e "
            "couro cabeludo?"
        ),
        "opcoes": [
            {"label": "Mais de 100", "pontos": 3},
            {"label": "De 50 a 100", "pontos": 2},
            {"label": "De 20 a 49", "pontos": 1},
            {"label": "Menos de 20", "pontos": 0},
        ],
    },
    {
        "id": "A18", "bloco": "A", "tipo": "unica",
        "texto": (
            "Alguma dessas pintas é maior que 5 mm, tem bordas irregulares, "
            "contorno mal definido ou mais de uma cor dentro dela?"
        ),
        "opcoes": [
            {"label": "Sim, três ou mais pintas assim", "pontos": 3},
            {"label": "Sim, uma ou duas", "pontos": 2},
            {"label": "Não / não sei", "pontos": 0},
        ],
    },
    {
        "id": "A19", "bloco": "A", "tipo": "unica",
        "texto": (
            "Você tem alguma mancha de nascença grande (nevo congênito), "
            "com mais de 20 mm na vida adulta, frequentemente com pelos?"
        ),
        "opcoes": [
            {"label": "Sim", "pontos": 2},
            {"label": "Não / não sei", "pontos": 0},
        ],
    },
    {
        "id": "A20", "bloco": "A", "tipo": "multipla",
        "texto": "Você tem alguma condição que reduz a imunidade ou faz tratamento que a reduz?",
        "opcoes": [
            {"label": "Transplante de órgão sólido, em uso de imunossupressores", "pontos": 4, "regra_seguranca": "Qualquer lesão nova avaliada em até 30 dias"},
            {"label": "Uso crônico (mais de 1 ano) de imunossupressores ou imunobiológicos para doença autoimune", "pontos": 2},
            {"label": "Leucemia linfocítica crônica, linfoma ou outra neoplasia hematológica", "pontos": 2},
            {"label": "HIV com imunidade comprometida", "pontos": 2},
            {"label": "Nenhuma dessas", "pontos": 0},
        ],
        # Transplantado de orgao solido e categoria a parte: risco de
        # carcinoma espinocelular ate 65-100x maior que a populacao geral.
    },
    {
        "id": "A21", "bloco": "A", "tipo": "multipla",
        "texto": "Você tem alguma destas condições genéticas ou de pele?",
        "opcoes": [
            {"label": "Xeroderma pigmentoso", "pontos": 5, "regra_seguranca": "Seguimento dermatológico especializado"},
            {"label": "Síndrome de Gorlin (síndrome do carcinoma basocelular nevoide)", "pontos": 4, "regra_seguranca": "Seguimento dermatológico especializado"},
            {"label": "Albinismo oculocutâneo", "pontos": 4, "regra_seguranca": "Seguimento dermatológico especializado"},
            {"label": "Síndrome do nevo displásico / síndrome do nevo atípico familiar", "pontos": 3},
            {"label": "Epidermólise bolhosa distrófica", "pontos": 3},
            {"label": "Vitiligo", "pontos": 0},
            {"label": "Nenhuma dessas", "pontos": 0},
        ],
        # Vitiligo NAO pontua (correcao do parecer): estudos de coorte
        # mostram incidencia REDUZIDA de melanoma em vitiligo, apesar da
        # pele queimar com facilidade -- oposto epidemiologico do albinismo.
    },
    {
        "id": "A22", "bloco": "A", "tipo": "multipla",
        "texto": "Você tem algum destes antecedentes? (pode marcar mais de um)",
        "opcoes": [
            {"label": "Radioterapia prévia na região onde está a lesão", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Cicatriz de queimadura, úlcera crônica ou fístula de longa data no local da lesão", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Contato ocupacional com arsênico, alcatrão, piche, breu ou óleos minerais", "pontos": 2},
            {"label": "Fototerapia com PUVA, mais de 100 sessões", "pontos": 2},
            {"label": "Uso prolongado de medicamentos fotossensibilizantes (hidroclorotiazida, voriconazol, tetraciclinas)", "pontos": 1},
            {"label": "Tabagismo atual ou passado", "pontos": 1},
            {"label": "Nenhum desses", "pontos": 0},
        ],
        # Lesao sobre cicatriz de queimadura / ulcera cronica corresponde a
        # ulcera de Marjolin -- entra na regra de seguranca.
    },

    # ============= Bloco B -- características da lesão fotografada =============
    {
        "id": "B1", "bloco": "B", "tipo": "unica",
        "texto": "Assimetria: se você traçasse uma linha dividindo a lesão ao meio, as duas metades ficariam diferentes uma da outra?",
        "opcoes": [
            {"label": "Sim", "pontos": 1},
            {"label": "Não", "pontos": 0},
        ],
    },
    {
        "id": "B2", "bloco": "B", "tipo": "unica",
        "texto": (
            "Bordas: as bordas da lesão são irregulares, recortadas, "
            "denteadas ou mal delimitadas — em vez de lisas e bem "
            "definidas?"
        ),
        "opcoes": [
            {"label": "Sim", "pontos": 1},
            {"label": "Não", "pontos": 0},
        ],
    },
    {
        "id": "B3", "bloco": "B", "tipo": "unica",
        "texto": (
            "Cores: quantas cores diferentes você consegue ver dentro da "
            "lesão (castanho-claro, castanho-escuro, preto, azul, branco, "
            "vermelho)?"
        ),
        "opcoes": [
            {"label": "Três ou mais cores, ou presença de azul, branco ou preto-acinzentado", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Duas cores", "pontos": 2},
            {"label": "Cor única e uniforme", "pontos": 0},
        ],
    },
    {
        "id": "B4", "bloco": "B", "tipo": "unica",
        "texto": "Diâmetro: qual o maior tamanho da lesão? (use como referência: a borracha da ponta de um lápis tem cerca de 6 mm)",
        "opcoes": [
            {"label": "Maior que 10 mm", "pontos": 2},
            {"label": "Entre 6 e 10 mm", "pontos": 1},
            {"label": "Menor que 6 mm", "pontos": 0},
        ],
    },
    {
        "id": "B5", "bloco": "B", "tipo": "unica",
        "texto": "Evolução: a lesão mudou nos últimos 6 a 12 meses — em tamanho, cor, formato, espessura ou relevo?",
        "opcoes": [
            {"label": "Sim", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Não / não sei", "pontos": 0},
        ],
    },
    {
        "id": "B6", "bloco": "B", "tipo": "unica",
        "texto": (
            "Sinal do patinho feio: comparando com as outras pintas do seu "
            "corpo, esta lesão chama a atenção por ser visivelmente "
            "diferente de todas as demais?"
        ),
        "opcoes": [
            {"label": "Sim", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Não", "pontos": 0},
            {"label": "Não tenho outras pintas para comparar", "pontos": 1},
        ],
    },
    {
        "id": "B7", "bloco": "B", "tipo": "unica",
        "texto": "Velocidade de crescimento: em quanto tempo você percebeu que a lesão cresceu?",
        "opcoes": [
            {"label": "Cresceu de forma perceptível em menos de 3 meses", "pontos": 3, "regra_seguranca": "Avaliação em até 15 dias"},
            {"label": "Cresceu ao longo de 3 a 12 meses", "pontos": 2},
            {"label": "Cresceu muito lentamente, ao longo de anos", "pontos": 1},
            {"label": "Não mudou de tamanho", "pontos": 0},
        ],
    },
    {
        "id": "B8", "bloco": "B", "tipo": "unica",
        "texto": (
            "É uma ferida que não cicatriza há 4 semanas ou mais, ou que "
            "cicatriza e volta a abrir sempre no mesmo lugar?"
        ),
        "opcoes": [
            {"label": "Sim", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Não / não se aplica", "pontos": 0},
        ],
    },
    {
        "id": "B9", "bloco": "B", "tipo": "multipla",
        "texto": "A lesão sangra?",
        "opcoes": [
            {"label": "Sangra sozinha, sem que eu tenha batido ou coçado", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Sangra com trauma mínimo (ao secar com a toalha, ao barbear, ao passar a roupa)", "pontos": 2},
            {"label": "Forma crostas que caem e voltam a se formar no mesmo lugar", "pontos": 2},
            {"label": "Não sangra", "pontos": 0},
        ],
    },
    {
        "id": "B10", "bloco": "B", "tipo": "multipla",
        "texto": "Qual destas descrições mais se parece com a superfície da lesão? (pode marcar mais de uma)",
        "opcoes": [
            {"label": "Elevada, firme, cor da pele ou rosada, de crescimento rápido", "pontos": 3},
            {"label": "Endurecida, com crosta espessa, aspereza intensa ou saliência córnea ('chifre')", "pontos": 3},
            {"label": "Brilhante, perolada ou translúcida, com vasinhos finos visíveis na superfície", "pontos": 3},
            {"label": "Avermelhada, áspera e descamativa, que não melhora com hidratante", "pontos": 2},
            {"label": "Placa esbranquiçada, endurecida, com aspecto de cicatriz, sem que tenha havido ferimento ali", "pontos": 2},
            {"label": "Nenhuma dessas", "pontos": 0},
        ],
        # Sem este bloco o questionario so rastreia lesao pigmentada e perde
        # o carcinoma basocelular, o cancer mais frequente no ser humano.
    },
    {
        "id": "B11", "bloco": "B", "tipo": "unica",
        "texto": "A lesão coça, dói, arde ou está sensível ao toque?",
        "opcoes": [
            {"label": "Sim, de forma persistente há mais de um mês", "pontos": 2},
            {"label": "Sim, mas apenas de vez em quando", "pontos": 1},
            {"label": "Não", "pontos": 0},
        ],
    },
    {
        "id": "B12", "bloco": "B", "tipo": "unica",
        "texto": "Onde está a lesão?",
        "opcoes": [
            {"label": "Palma das mãos, planta dos pés, unhas ou dentro da boca / região genital", "pontos": 3, "regra_seguranca": "Avaliação em até 30 dias"},
            {"label": "Rosto, nariz, pálpebra, orelha, lábio ou couro cabeludo", "pontos": 2},
            {"label": "Pescoço, colo, ombros, dorso das mãos, antebraços, costas ou pernas", "pontos": 1},
            {"label": "Área habitualmente coberta pela roupa", "pontos": 0},
        ],
        # Inclui explicitamente regiao acral/ungueal: melanoma acral nao se
        # relaciona a exposicao solar e e o que mais mata no Brasil por
        # atraso diagnostico -- contrapeso ao vies de fototipo/sol do
        # restante do questionario.
    },
    {
        "id": "B13", "bloco": "B", "tipo": "unica",
        "texto": (
            "Se a lesão está em uma unha: existe uma faixa escura no "
            "sentido do comprimento da unha que está alargando, ou o "
            "pigmento se estende para a pele ao redor da unha?"
        ),
        "opcoes": [
            {"label": "Sim", "pontos": 4, "regra_seguranca": "Avaliação em até 15 dias"},
            {"label": "Existe faixa escura, mas estável e sem alargamento", "pontos": 1},
            {"label": "Não / não se aplica", "pontos": 0},
        ],
        # "Sim" corresponde ao sinal de Hutchinson, altamente sugestivo de
        # melanoma subungueal.
    },
    {
        "id": "B14", "bloco": "B", "tipo": "unica",
        "texto": "Quando esta lesão surgiu?",
        "opcoes": [
            {"label": "É uma lesão pigmentada nova, que surgiu depois dos 40 anos", "pontos": 2},
            {"label": "Surgiu nos últimos 12 meses, em qualquer idade", "pontos": 1},
            {"label": "Está ali desde a infância ou adolescência e nunca mudou", "pontos": 0},
        ],
    },
    {
        "id": "B15", "bloco": "B", "tipo": "unica",
        "texto": "Você percebeu algum caroço ou íngua que apareceu perto da lesão (na virilha, axila ou pescoço)?",
        "opcoes": [
            {"label": "Sim", "pontos": 2},
            {"label": "Não / não sei", "pontos": 0},
        ],
        # Nao e uma das 12 linhas formais da regra de seguranca -- ver ponto
        # em aberto 5 no docstring.
    },
]

_QUESTOES_POR_ID = {q["id"]: q for q in QUESTOES}


# ---------------------------------------------------------------------------
# Prioridade entre regras de seguranca disparadas simultaneamente (menor
# numero = mais urgente = prevalece). Ver ponto em aberto 6 no docstring.
# ---------------------------------------------------------------------------
PRIORIDADE_REGRA_SEGURANCA = {
    "Avaliação em até 15 dias": 1,
    "Seguimento dermatológico especializado": 1,
    "Avaliação em até 30 dias": 2,
    "Qualquer lesão nova avaliada em até 30 dias": 2,
    "Seguimento dermatológico regular, qualquer lesão nova avaliada": 3,
}

# ---------------------------------------------------------------------------
# Matriz de conduta: eixo A (risco basal) x eixo B (suspeicao da lesao).
# Cortes (25%, 45%, 20%, 40%) PROVISORIOS E ARBITRARIOS -- nas palavras do
# parecer, "servem para o aplicativo funcionar, nao para serem defendidos
# como achado", a recalibrar quando houver amostra com desfecho conhecido.
# ---------------------------------------------------------------------------
MATRIZ_CONDUTA = {
    ("alto", "baixo"): "Consulta dermatológica de rotina e rastreio periódico",
    ("alto", "moderado"): "Avaliação em até 30 dias",
    ("alto", "alto"): "Avaliação prioritária, até 15 dias",
    ("moderado", "baixo"): "Orientação de fotoproteção e autoexame",
    ("moderado", "moderado"): "Avaliação em até 60 dias",
    ("moderado", "alto"): "Avaliação em até 30 dias",
    ("baixo", "baixo"): "Orientação de fotoproteção e autoexame",
    ("baixo", "moderado"): "Avaliação em até 90 dias",
    ("baixo", "alto"): "Avaliação em até 30 dias",
}


def _maximo_questao(questao):
    if questao["tipo"] == "multipla":
        return sum(op["pontos"] for op in questao["opcoes"])
    return max(op["pontos"] for op in questao["opcoes"])


def _somar_bloco(bloco, pontos_por_questao):
    """
    Soma os pontos de um bloco respeitando os tetos de grupo. Usada tanto
    para o escore real (pontos_por_questao = respostas efetivas) quanto para
    calcular o maximo teorico do bloco (pontos_por_questao = maximo de cada
    pergunta) -- garante que os dois usem exatamente a mesma regra.
    """
    ids_agrupados = set()
    total = 0

    for grupo in TETOS_CONJUNTOS.get(bloco, []):
        soma_grupo = sum(pontos_por_questao[qid] for qid in grupo["ids"])
        total += min(soma_grupo, grupo["teto"])
        ids_agrupados.update(grupo["ids"])

    for questao in QUESTOES:
        if questao["bloco"] != bloco or questao["id"] in ids_agrupados:
            continue
        total += pontos_por_questao[questao["id"]]

    return total


def _maximo_bloco(bloco):
    maximos = {q["id"]: _maximo_questao(q) for q in QUESTOES}
    return _somar_bloco(bloco, maximos)


MAXIMO_BLOCO_A = _maximo_bloco("A")  # 93
MAXIMO_BLOCO_B = _maximo_bloco("B")  # 52


def _faixa_bloco_a(percentual):
    if percentual > 45:
        return "alto"
    if percentual >= 25:
        return "moderado"
    return "baixo"


def _faixa_bloco_b(percentual):
    if percentual > 40:
        return "alto"
    if percentual >= 20:
        return "moderado"
    return "baixo"


def _contribuicao_e_gatilhos(questao, respostas):
    """
    Devolve (pontos_da_questao, lista_de_regras_de_seguranca_disparadas)
    para uma unica pergunta, ja aplicando a regra condicional (pergunta
    oculta contribui 0 pontos, mesmo que o cliente envie algo para ela).
    """
    condicao = questao.get("condicional_de")
    if condicao is not None and respostas.get(condicao, 0) <= 0:
        return 0, []

    pontos_disponiveis = {op["pontos"] for op in questao["opcoes"]}

    if questao["tipo"] == "multipla":
        brutos = respostas.get(questao["id"]) or []
        if not isinstance(brutos, list):
            brutos = [brutos]
        escolhidos = [p for p in brutos if p in pontos_disponiveis]
        total = sum(escolhidos)
        gatilhos = [
            op["regra_seguranca"] for op in questao["opcoes"]
            if op["pontos"] in escolhidos and op["pontos"] > 0 and "regra_seguranca" in op
        ]
        return total, gatilhos

    pontos = respostas.get(questao["id"], 0)
    if pontos not in pontos_disponiveis:
        return 0, []
    opcao = next(op for op in questao["opcoes"] if op["pontos"] == pontos)
    gatilhos = [opcao["regra_seguranca"]] if "regra_seguranca" in opcao else []
    return pontos, gatilhos


def calcular_resultado(respostas):
    """
    respostas: {id_da_questao: pontos (int), ou lista de pontos para
    perguntas "tipo": "multipla"}. Perguntas nao respondidas, ou ocultas por
    uma condicional nao satisfeita, contribuem 0 pontos.
    """
    pontos_por_questao = {}
    gatilhos = []  # (prioridade, texto_da_conduta, id_da_pergunta_gatilho)

    for questao in QUESTOES:
        pontos, disparos = _contribuicao_e_gatilhos(questao, respostas)
        pontos_por_questao[questao["id"]] = pontos
        for texto in disparos:
            gatilhos.append((PRIORIDADE_REGRA_SEGURANCA.get(texto, 99), texto, questao["id"]))

    pontuacao_a = _somar_bloco("A", pontos_por_questao)
    pontuacao_b = _somar_bloco("B", pontos_por_questao)

    percentual_a = round(100 * pontuacao_a / MAXIMO_BLOCO_A, 1)
    percentual_b = round(100 * pontuacao_b / MAXIMO_BLOCO_B, 1)

    faixa_a = _faixa_bloco_a(percentual_a)
    faixa_b = _faixa_bloco_b(percentual_b)

    resultado = {
        "pontuacao_bloco_a": pontuacao_a,
        "maximo_bloco_a": MAXIMO_BLOCO_A,
        "percentual_bloco_a": percentual_a,
        "faixa_bloco_a": faixa_a,
        "pontuacao_bloco_b": pontuacao_b,
        "maximo_bloco_b": MAXIMO_BLOCO_B,
        "percentual_bloco_b": percentual_b,
        "faixa_bloco_b": faixa_b,
        "regra_seguranca_disparada": False,
        "perguntas_gatilho": [],
        "escore_e_secundario": False,
    }

    if gatilhos:
        gatilhos.sort(key=lambda g: g[0])
        conduta_prioritaria = gatilhos[0][1]
        resultado["conduta"] = conduta_prioritaria
        resultado["regra_seguranca_disparada"] = True
        resultado["perguntas_gatilho"] = sorted({g[2] for g in gatilhos})
        resultado["escore_e_secundario"] = True
    else:
        resultado["conduta"] = MATRIZ_CONDUTA[(faixa_a, faixa_b)]

    return resultado


def obter_mensagem_combinacao(sugestivo_imagem, resultado_formulario):
    """
    Regra assimetrica (parecer, secao "Como combinar com o resultado da
    imagem"): o formulario so pode reforcar a cautela do resultado da
    imagem, nunca amenizar. Sem mensagem extra quando a imagem e sugestiva
    mas o questionario nao aponta suspeicao adicional -- a recomendacao da
    imagem se mantem integralmente.
    """
    if sugestivo_imagem is None:
        return None

    atencao_alta = (
        resultado_formulario["regra_seguranca_disparada"]
        or resultado_formulario["faixa_bloco_b"] == "alto"
    )

    if not atencao_alta:
        return None

    conduta = resultado_formulario["conduta"]

    if not sugestivo_imagem:
        return (
            "A análise da imagem não indicou sinais sugestivos, mas as "
            f"respostas sobre a lesão indicam: {conduta}. A ausência de "
            "sinais na imagem não descarta a necessidade de avaliação "
            "médica."
        )

    return (
        "A análise da imagem indicou sinais sugestivos e as respostas "
        f"sobre a lesão reforçam essa indicação: {conduta}. Procure um "
        "dermatologista para uma avaliação presencial."
    )
