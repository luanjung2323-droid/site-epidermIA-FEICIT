const secaoEntrada = document.getElementById("secao-entrada");
const btnEntradaFormulario = document.getElementById("btn-entrada-formulario");
const btnEntradaPular = document.getElementById("btn-entrada-pular");
const secaoUpload = document.getElementById("secao-upload");

const inputFoto = document.getElementById("input-foto");
const nomeArquivo = document.getElementById("nome-arquivo");
const areaRecorte = document.getElementById("area-recorte");
const imagemParaRecorte = document.getElementById("imagem-para-recorte");
const btnRecortarEnviar = document.getElementById("btn-recortar-enviar");
const btnEnviarOriginal = document.getElementById("btn-enviar-original");
const statusEnvio = document.getElementById("status-envio");
const secaoResultado = document.getElementById("secao-resultado");
const resultadoRotulo = document.getElementById("resultado-rotulo");
const resultadoBarraFill = document.getElementById("resultado-barra-fill");
const resultadoProb = document.getElementById("resultado-prob");
const resultadoImagemVisao = document.getElementById("resultado-imagem-visao");
const visaoIaTag = document.getElementById("visao-ia-tag");
const btnVisaoIa = document.getElementById("btn-visao-ia");
const btnNovaAnalise = document.getElementById("btn-nova-analise");

const secaoConviteFormulario = document.getElementById("secao-convite-formulario");
const btnAbrirFormulario = document.getElementById("btn-abrir-formulario");
const secaoFormulario = document.getElementById("secao-formulario");
const formularioProgressoTexto = document.getElementById("formulario-progresso-texto");
const formularioProgressoFill = document.getElementById("formulario-progresso-fill");
const formularioPerguntas = document.getElementById("formulario-perguntas");
const btnFormularioVoltar = document.getElementById("btn-formulario-voltar");
const btnFormularioAvancar = document.getElementById("btn-formulario-avancar");
const secaoResultadoCombinado = document.getElementById("secao-resultado-combinado");
const combRotuloImagem = document.getElementById("comb-rotulo-imagem");
const combProbImagem = document.getElementById("comb-prob-imagem");
const combConduta = document.getElementById("comb-conduta");
const combAvisoRegraSeguranca = document.getElementById("comb-aviso-regra-seguranca");
const combBlocoA = document.getElementById("comb-bloco-a");
const combBlocoB = document.getElementById("comb-bloco-b");
const combMensagemCombinacao = document.getElementById("comb-mensagem-combinacao");
const btnFormularioRefazer = document.getElementById("btn-formulario-refazer");
const btnNovaAnalise2 = document.getElementById("btn-nova-analise-2");
const formularioErro = document.getElementById("formulario-erro");

const blocoFatoresRiscoDesktop = document.getElementById("bloco-fatores-risco-desktop");
const combCondutaDesktop = document.getElementById("comb-conduta-desktop");
const combAvisoRegraSegurancaDesktop = document.getElementById("comb-aviso-regra-seguranca-desktop");
const combBlocoADesktop = document.getElementById("comb-bloco-a-desktop");
const combBlocoBDesktop = document.getElementById("comb-bloco-b-desktop");
const combMensagemCombinacaoDesktop = document.getElementById("comb-mensagem-combinacao-desktop");
const btnFormularioRefazerDesktop = document.getElementById("btn-formulario-refazer-desktop");
const btnNovaAnalise3 = document.getElementById("btn-nova-analise-3");
const mqDesktop = window.matchMedia("(min-width: 860px)");

let cropper = null;
let arquivoOriginal = null;
let ultimoResultadoImagem = null;
let ultimoResultadoFormulario = null;
let formularioConcluido = false;

inputFoto.addEventListener("change", (evento) => {
  const arquivo = evento.target.files[0];
  if (!arquivo) return;

  arquivoOriginal = arquivo;
  nomeArquivo.textContent = arquivo.name;
  imagemParaRecorte.src = URL.createObjectURL(arquivo);
  areaRecorte.hidden = false;
  secaoResultado.hidden = true;

  if (cropper) cropper.destroy();
  cropper = new Cropper(imagemParaRecorte, {
    aspectRatio: 1,
    viewMode: 1,
    autoCropArea: 1,
  });
});

/* ---------- Barra de probabilidade em gradiente ---------- */
/* azul -> verde -> amarelo -> laranja -> vermelho, conforme a porcentagem */
const FAIXAS_COR_BARRA = [
  { p: 0, cor: [41, 121, 255] },
  { p: 25, cor: [67, 160, 71] },
  { p: 50, cor: [253, 216, 53] },
  { p: 75, cor: [251, 140, 0] },
  { p: 100, cor: [229, 57, 53] },
];

function corDaBarra(porcentagem) {
  const p = Math.max(0, Math.min(100, porcentagem));
  for (let i = 0; i < FAIXAS_COR_BARRA.length - 1; i++) {
    const atual = FAIXAS_COR_BARRA[i];
    const proxima = FAIXAS_COR_BARRA[i + 1];
    if (p >= atual.p && p <= proxima.p) {
      const t = (p - atual.p) / (proxima.p - atual.p);
      const [r1, g1, b1] = atual.cor;
      const [r2, g2, b2] = proxima.cor;
      const r = Math.round(r1 + t * (r2 - r1));
      const g = Math.round(g1 + t * (g2 - g1));
      const b = Math.round(b1 + t * (b2 - b1));
      return `rgb(${r}, ${g}, ${b})`;
    }
  }
  const ultima = FAIXAS_COR_BARRA[FAIXAS_COR_BARRA.length - 1].cor;
  return `rgb(${ultima.join(", ")})`;
}

/* ---------- Visao IA: alterna Grad-CAM <-> foto original ---------- */
let mostrandoGradcam = true;
let srcGradcam = "";
let srcFotoEnviada = "";

function atualizarVisaoIA() {
  resultadoImagemVisao.src = mostrandoGradcam ? srcGradcam : srcFotoEnviada;
  resultadoImagemVisao.alt = mostrandoGradcam ? "Mapa de calor Grad-CAM" : "Foto enviada";
  visaoIaTag.textContent = mostrandoGradcam ? "Grad-CAM" : "Foto original";
}

btnVisaoIa.addEventListener("click", () => {
  mostrandoGradcam = !mostrandoGradcam;
  atualizarVisaoIA();
});

async function enviarImagem(blob) {
  statusEnvio.textContent = "Analisando...";
  secaoResultado.hidden = true;
  secaoConviteFormulario.hidden = true;
  secaoFormulario.hidden = true;
  secaoResultadoCombinado.hidden = true;
  blocoFatoresRiscoDesktop.hidden = true;

  const formData = new FormData();
  formData.append("imagem", blob, "imagem.png");

  try {
    const resposta = await fetch("/diagnosticar", {
      method: "POST",
      body: formData,
    });

    if (!resposta.ok) {
      const erro = await resposta.json().catch(() => ({}));
      statusEnvio.textContent = "Erro: " + (erro.erro || resposta.statusText);
      return;
    }

    const dados = await resposta.json();
    statusEnvio.textContent = "";

    resultadoRotulo.textContent = dados.rotulo;
    resultadoRotulo.classList.toggle("alerta", dados.sugestivo);
    resultadoRotulo.classList.toggle("neutro", !dados.sugestivo);

    const corResultado = corDaBarra(dados.probabilidade_percentual);
    resultadoProb.textContent = dados.probabilidade_percentual + "%";
    resultadoProb.style.color = corResultado;
    resultadoBarraFill.style.width = dados.probabilidade_percentual + "%";
    resultadoBarraFill.style.background = corResultado;

    srcGradcam = "data:image/png;base64," + dados.grad_cam_base64;
    srcFotoEnviada = URL.createObjectURL(blob);
    mostrandoGradcam = true;
    atualizarVisaoIA();

    ultimoResultadoImagem = dados;
    secaoResultado.hidden = false;

    if (formularioConcluido) {
      // Caminho A: formulario ja foi respondido antes da foto -- agora que
      // sabemos "sugestivo", calcula e mostra os dois cartoes direto,
      // sem passar pelo convite.
      secaoConviteFormulario.hidden = true;
      await enviarFormulario();
    } else {
      secaoConviteFormulario.hidden = false;
    }
  } catch (erro) {
    statusEnvio.textContent = "Erro ao enviar imagem: " + erro.message;
  }
}

btnRecortarEnviar.addEventListener("click", () => {
  if (!cropper) return;
  cropper.getCroppedCanvas({ width: 224, height: 224 }).toBlob((blob) => {
    enviarImagem(blob);
  }, "image/png");
});

btnEnviarOriginal.addEventListener("click", () => {
  if (!arquivoOriginal) return;
  enviarImagem(arquivoOriginal);
});

function resetarParaNovaAnalise() {
  inputFoto.value = "";
  nomeArquivo.textContent = "Nenhuma foto selecionada";
  arquivoOriginal = null;
  ultimoResultadoImagem = null;
  ultimoResultadoFormulario = null;
  formularioConcluido = false;
  areaRecorte.hidden = true;
  secaoUpload.hidden = true;
  secaoResultado.hidden = true;
  secaoConviteFormulario.hidden = true;
  secaoFormulario.hidden = true;
  secaoResultadoCombinado.hidden = true;
  blocoFatoresRiscoDesktop.hidden = true;
  secaoEntrada.hidden = false;
  resultadoRotulo.classList.remove("alerta", "neutro");
  respostasFormulario = {};
  passoFormularioAtual = 0;
  formularioErro.hidden = true;
  if (cropper) {
    cropper.destroy();
    cropper = null;
  }
}

btnNovaAnalise.addEventListener("click", resetarParaNovaAnalise);
btnNovaAnalise2.addEventListener("click", resetarParaNovaAnalise);
btnNovaAnalise3.addEventListener("click", resetarParaNovaAnalise);

/* ---------- Formulario de fatores de risco ---------- */
const QUESTOES = JSON.parse(document.getElementById("dados-formulario").textContent);
const QUESTOES_POR_ID = Object.fromEntries(QUESTOES.map((q) => [q.id, q]));

function dividirEmGrupos(lista, tamanho) {
  const grupos = [];
  for (let i = 0; i < lista.length; i += tamanho) {
    grupos.push(lista.slice(i, i + tamanho));
  }
  return grupos;
}

const GRUPOS_FORMULARIO = dividirEmGrupos(QUESTOES, 5);
let respostasFormulario = {};
let passoFormularioAtual = 0;
let origemFormulario = "entrada";

// Perguntas "condicional_de" (ex.: A10 depende de A9) so contam como
// respondidas -- e so ficam visiveis -- se a pergunta referenciada tiver
// sido respondida com pontos > 0. Mesma regra aplicada no backend
// (formulario.py), aqui so controla o que aparece na tela.
function perguntaVisivel(questao) {
  if (!questao.condicional_de) return true;
  return (respostasFormulario[questao.condicional_de] || 0) > 0;
}

function renderizarPassoFormulario() {
  const grupo = GRUPOS_FORMULARIO[passoFormularioAtual];

  formularioPerguntas.innerHTML = grupo.map((questao) => {
    const tipoInput = questao.tipo === "multipla" ? "checkbox" : "radio";
    const respostaAtual = respostasFormulario[questao.id];

    return `
    <div class="questao" data-id="${questao.id}" ${perguntaVisivel(questao) ? "" : "hidden"}>
      <p class="questao-texto">${questao.id}. ${questao.texto}</p>
      <div class="opcoes">
        ${questao.opcoes.map((opcao) => {
          const marcado = tipoInput === "checkbox"
            ? Array.isArray(respostaAtual) && respostaAtual.includes(opcao.pontos)
            : respostaAtual === opcao.pontos;
          return `
          <label class="opcao">
            <input type="${tipoInput}" name="${questao.id}" value="${opcao.pontos}"
              ${marcado ? "checked" : ""}>
            ${opcao.label}
          </label>
        `;
        }).join("")}
      </div>
    </div>
  `;
  }).join("");

  const totalPassos = GRUPOS_FORMULARIO.length;
  formularioProgressoTexto.textContent = `Passo ${passoFormularioAtual + 1} de ${totalPassos}`;
  formularioProgressoFill.style.width = `${((passoFormularioAtual + 1) / totalPassos) * 100}%`;
  formularioProgressoFill.style.background = "";

  btnFormularioVoltar.textContent = passoFormularioAtual === 0 ? "Sair" : "Voltar";
  btnFormularioAvancar.textContent = passoFormularioAtual === totalPassos - 1
    ? "Ver resultado do questionário"
    : "Próximo";
}

function atualizarVisibilidadeCondicionais() {
  GRUPOS_FORMULARIO[passoFormularioAtual].forEach((questao) => {
    if (!questao.condicional_de) return;
    const div = formularioPerguntas.querySelector(`.questao[data-id="${questao.id}"]`);
    if (div) div.hidden = !perguntaVisivel(questao);
  });
}

formularioPerguntas.addEventListener("change", (evento) => {
  const input = evento.target;
  if (input.type === "radio") {
    respostasFormulario[input.name] = Number(input.value);
  } else if (input.type === "checkbox") {
    const marcados = formularioPerguntas.querySelectorAll(`input[name="${input.name}"]:checked`);
    respostasFormulario[input.name] = Array.from(marcados).map((el) => Number(el.value));
  } else {
    return;
  }
  atualizarVisibilidadeCondicionais();
});

function abrirFormularioDoZero() {
  respostasFormulario = {};
  passoFormularioAtual = 0;
  formularioErro.hidden = true;
  renderizarPassoFormulario();
  secaoFormulario.hidden = false;
}

btnAbrirFormulario.addEventListener("click", () => {
  origemFormulario = "convite";
  secaoConviteFormulario.hidden = true;
  abrirFormularioDoZero();
});

btnEntradaFormulario.addEventListener("click", () => {
  origemFormulario = "entrada";
  secaoEntrada.hidden = true;
  abrirFormularioDoZero();
});

function sairDoFormulario() {
  secaoFormulario.hidden = true;
  if (origemFormulario === "convite") {
    secaoConviteFormulario.hidden = false;
  } else if (origemFormulario === "refazer") {
    atualizarLayoutResultadoCombinado();
  } else {
    secaoEntrada.hidden = false;
  }
}

btnEntradaPular.addEventListener("click", () => {
  secaoEntrada.hidden = true;
  secaoUpload.hidden = false;
});

function encontrarPerguntasFaltantes() {
  return QUESTOES.filter((questao) => {
    if (!perguntaVisivel(questao)) return false;
    const resposta = respostasFormulario[questao.id];
    if (questao.tipo === "multipla") return !Array.isArray(resposta) || resposta.length === 0;
    return !(questao.id in respostasFormulario);
  }).map((q) => q.id);
}

function indiceDoPassoComQuestao(idQuestao) {
  return GRUPOS_FORMULARIO.findIndex((grupo) => grupo.some((q) => q.id === idQuestao));
}

function formatarListaDeIds(ids) {
  if (ids.length === 1) return ids[0];
  return ids.slice(0, -1).join(", ") + " e " + ids[ids.length - 1];
}

btnFormularioVoltar.addEventListener("click", () => {
  if (passoFormularioAtual === 0) {
    sairDoFormulario();
    return;
  }
  passoFormularioAtual -= 1;
  renderizarPassoFormulario();
});

btnFormularioAvancar.addEventListener("click", () => {
  if (passoFormularioAtual < GRUPOS_FORMULARIO.length - 1) {
    passoFormularioAtual += 1;
    formularioErro.hidden = true;
    renderizarPassoFormulario();
    return;
  }

  const faltantes = encontrarPerguntasFaltantes();
  if (faltantes.length > 0) {
    const verbo = faltantes.length === 1 ? "Faltou responder a questão" : "Faltaram responder as questões";
    formularioErro.textContent = `${verbo} ${formatarListaDeIds(faltantes)}.`;
    formularioErro.hidden = false;
    passoFormularioAtual = indiceDoPassoComQuestao(faltantes[0]);
    renderizarPassoFormulario();
    return;
  }

  formularioErro.hidden = true;
  formularioConcluido = true;

  if (ultimoResultadoImagem) {
    // Caminho B: formulario respondido depois da foto (via convite) --
    // ja temos os dois lados, calcula e mostra os cartoes direto.
    enviarFormulario();
  } else {
    // Caminho A: formulario respondido antes da foto -- segue pro envio
    // da imagem, o calculo acontece quando a foto for analisada.
    secaoFormulario.hidden = true;
    secaoUpload.hidden = false;
  }
});

function refazerFormulario() {
  origemFormulario = "refazer";
  secaoResultadoCombinado.hidden = true;
  blocoFatoresRiscoDesktop.hidden = true;
  abrirFormularioDoZero();
}

btnFormularioRefazer.addEventListener("click", refazerFormulario);
btnFormularioRefazerDesktop.addEventListener("click", refazerFormulario);

const ROTULOS_FAIXA = { alto: "Alto", moderado: "Moderado", baixo: "Baixo" };

function descreverFaixa(rotulo, faixa, percentual) {
  return `${rotulo}: ${ROTULOS_FAIXA[faixa] || faixa} (${percentual}%)`;
}

function preencherBlocoFatoresRisco(elementos, dados) {
  elementos.conduta.textContent = dados.conduta;

  const atencaoAlta = dados.regra_seguranca_disparada
    || dados.faixa_bloco_a === "alto"
    || dados.faixa_bloco_b === "alto";
  elementos.conduta.classList.toggle("alerta", atencaoAlta);
  elementos.conduta.classList.toggle("neutro", !atencaoAlta);

  elementos.avisoRegraSeguranca.hidden = !dados.regra_seguranca_disparada;
  if (dados.regra_seguranca_disparada) {
    elementos.listaGatilhos.innerHTML = dados.perguntas_gatilho.map((id) => {
      const questao = QUESTOES_POR_ID[id];
      return `<li>${questao ? `${questao.id}. ${questao.texto}` : id}</li>`;
    }).join("");
  }

  elementos.blocoA.textContent = descreverFaixa(
    "Risco basal (perfil da pessoa)", dados.faixa_bloco_a, dados.percentual_bloco_a
  );
  elementos.blocoB.textContent = descreverFaixa(
    "Suspeição da lesão fotografada", dados.faixa_bloco_b, dados.percentual_bloco_b
  );

  if (dados.mensagem_combinacao) {
    elementos.mensagem.textContent = dados.mensagem_combinacao;
    elementos.mensagem.hidden = false;
  } else {
    elementos.mensagem.hidden = true;
  }
}

const elementosFatoresRiscoMobile = {
  conduta: combConduta,
  avisoRegraSeguranca: combAvisoRegraSeguranca,
  listaGatilhos: document.getElementById("comb-lista-gatilhos"),
  blocoA: combBlocoA,
  blocoB: combBlocoB,
  mensagem: combMensagemCombinacao,
};

const elementosFatoresRiscoDesktop = {
  conduta: combCondutaDesktop,
  avisoRegraSeguranca: combAvisoRegraSegurancaDesktop,
  listaGatilhos: document.getElementById("comb-lista-gatilhos-desktop"),
  blocoA: combBlocoADesktop,
  blocoB: combBlocoBDesktop,
  mensagem: combMensagemCombinacaoDesktop,
};

function atualizarLayoutResultadoCombinado() {
  if (!ultimoResultadoFormulario) return;

  preencherBlocoFatoresRisco(elementosFatoresRiscoMobile, ultimoResultadoFormulario);
  preencherBlocoFatoresRisco(elementosFatoresRiscoDesktop, ultimoResultadoFormulario);

  if (mqDesktop.matches) {
    // Desktop: o card da imagem ja aparece em secao-resultado, entao so
    // mostra os fatores de risco no espaco vago -- sem repetir a imagem.
    secaoResultadoCombinado.hidden = true;
    blocoFatoresRiscoDesktop.hidden = false;
  } else {
    // Mobile: mantem o resumo com os 2 cartoes como ja era, sem mudanca.
    secaoResultadoCombinado.hidden = false;
    blocoFatoresRiscoDesktop.hidden = true;
  }
}

mqDesktop.addEventListener("change", atualizarLayoutResultadoCombinado);

async function enviarFormulario() {
  const corpo = {
    respostas: respostasFormulario,
    sugestivo_imagem: ultimoResultadoImagem ? ultimoResultadoImagem.sugestivo : null,
  };

  const resposta = await fetch("/formulario/calcular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  ultimoResultadoFormulario = await resposta.json();

  if (ultimoResultadoImagem) {
    combRotuloImagem.textContent = ultimoResultadoImagem.rotulo;
    combRotuloImagem.classList.toggle("alerta", ultimoResultadoImagem.sugestivo);
    combRotuloImagem.classList.toggle("neutro", !ultimoResultadoImagem.sugestivo);
    combProbImagem.textContent = ultimoResultadoImagem.probabilidade_percentual + "%";
    combProbImagem.style.color = corDaBarra(ultimoResultadoImagem.probabilidade_percentual);
  }

  secaoFormulario.hidden = true;
  atualizarLayoutResultadoCombinado();
}

/* ---------- Menu hamburguer ---------- */
const btnMenu = document.getElementById("btn-menu");
const menuDrawer = document.getElementById("menu-drawer");
const menuOverlay = document.getElementById("menu-overlay");
const btnLogoHome = document.getElementById("btn-logo-home");
const itensMenu = document.querySelectorAll(".menu-item");
const abas = document.querySelectorAll(".aba");

function abrirMenu() {
  menuDrawer.hidden = false;
  menuOverlay.hidden = false;
  btnMenu.setAttribute("aria-expanded", "true");
}

function fecharMenu() {
  menuDrawer.hidden = true;
  menuOverlay.hidden = true;
  btnMenu.setAttribute("aria-expanded", "false");
}

btnMenu.addEventListener("click", () => {
  if (menuDrawer.hidden) {
    abrirMenu();
  } else {
    fecharMenu();
  }
});

menuOverlay.addEventListener("click", fecharMenu);

/* Troca a aba visivel. Recebe o nome curto usado no data-aba
   ("diagnostico", "o-que-e", "sinais-alerta", "sobre"). */
function mostrarAba(nomeAba) {
  const alvo = "aba-" + nomeAba;

  abas.forEach((aba) => {
    aba.hidden = aba.id !== alvo;
  });
  itensMenu.forEach((i) => i.classList.toggle("ativa", i.dataset.aba === nomeAba));
  fecharMenu();
  window.scrollTo({ top: 0, behavior: "auto" });
}

itensMenu.forEach((item) => {
  item.addEventListener("click", () => mostrarAba(item.dataset.aba));
});

/* Clicar na logo sempre volta para a pagina inicial (enviar foto). */
if (btnLogoHome) {
  btnLogoHome.addEventListener("click", () => mostrarAba("diagnostico"));
}

/* Botoes dentro do conteudo que levam para outra aba
   (ex.: "Ver sinais de alerta ->" na aba Sobre o cancer de pele). */
document.querySelectorAll("[data-ir-para]").forEach((botao) => {
  botao.addEventListener("click", () => mostrarAba(botao.dataset.irPara));
});
