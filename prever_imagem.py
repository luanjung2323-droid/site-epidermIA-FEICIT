"""
Testa o modelo em VARIAS imagens de uma vez.
Procura automaticamente os arquivos: minha_foto1, minha_foto2, minha_foto3, ...
(aceita .jpg, .jpeg, .png) e processa todos os que encontrar.
Gera a previsao de cada uma + um painel Grad-CAM com todas.

ATENCAO: projeto academico (TCC), NAO e ferramenta de diagnostico.

Roda no PC, na pasta do projeto (junto da pasta checkpoints/).
Precisa: pip install grad-cam
"""

from pathlib import Path
BASE_DIR = Path(__file__).parent

import numpy as np
import torch
from torch import nn
from PIL import Image
from torchvision import transforms, models
import matplotlib.pyplot as plt
import lightning as L
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import BinaryClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

# ======================================================================
# As imagens devem se chamar: minha_foto1, minha_foto2, minha_foto3, ...
# e estar na MESMA pasta deste script. Aceita .jpg, .jpeg e .png.
# ======================================================================
PREFIXO = "minha_foto"
EXTENSOES = [".jpg", ".jpeg", ".png"]
IMG_SIZE = 224

# ----------------------------------------------------------------------
# Procura as imagens em sequencia (1, 2, 3, ...) ate nao achar mais
# ----------------------------------------------------------------------
def acha_imagens():
    encontradas = []
    i = 1
    while True:
        achou = None
        for ext in EXTENSOES:
            caminho = BASE_DIR / f"{PREFIXO}{i}{ext}"
            if caminho.exists():
                achou = caminho
                break
        if achou is None:
            break              # parou de achar a sequencia -> termina
        encontradas.append(achou)
        i += 1
    return encontradas

imagens = acha_imagens()
if not imagens:
    raise SystemExit(f"Nenhuma imagem '{PREFIXO}1' encontrada na pasta {BASE_DIR}")
print(f"{len(imagens)} imagem(ns) encontrada(s).")

# ----------------------------------------------------------------------
# Classe do modelo (para carregar o checkpoint)
# ----------------------------------------------------------------------
class LesaoModel(L.LightningModule):
    def __init__(self, peso_pos=1.0, fine_tuning=False, lr=1e-3):
        super().__init__()
        self.save_hyperparameters()
        self.rede = models.mobilenet_v2(weights=None)
        n_feat = self.rede.classifier[1].in_features
        self.rede.classifier[1] = nn.Linear(n_feat, 1)
        self.loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([peso_pos]))

    def forward(self, x):
        return self.rede(x).squeeze(1)

# ----------------------------------------------------------------------
# Carrega o melhor checkpoint
# ----------------------------------------------------------------------
ckpts = list((BASE_DIR / "checkpoints").glob("*.ckpt"))
if not ckpts:
    raise SystemExit("Nenhum checkpoint encontrado em checkpoints/")
ckpt = max(ckpts, key=lambda p: p.stat().st_mtime)
print("Modelo:", ckpt.name)

device = "cuda" if torch.cuda.is_available() else "cpu"
modelo = LesaoModel.load_from_checkpoint(ckpt).to(device).eval()

norm = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                            std= [0.229, 0.224, 0.225])
tf_modelo = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)),
                                transforms.ToTensor(), norm])
tf_exibir = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)),
                                transforms.ToTensor()])

cam = GradCAM(model=modelo.rede, target_layers=[modelo.rede.features[-1]])

# ----------------------------------------------------------------------
# Processa cada imagem; monta um painel com todas (2 colunas por imagem)
# ----------------------------------------------------------------------
n = len(imagens)
fig, axes = plt.subplots(n, 2, figsize=(8, 4 * n))
if n == 1:
    axes = [axes]   # garante que da para indexar axes[i] quando ha 1 imagem

for i, caminho in enumerate(imagens):
    img = Image.open(caminho).convert("RGB")
    entrada = tf_modelo(img).unsqueeze(0).to(device)
    rgb = tf_exibir(img).permute(1, 2, 0).numpy()

    with torch.no_grad():
        prob = torch.sigmoid(modelo.rede(entrada)).item()
    pred = "MALIGNO" if prob > 0.5 else "BENIGNO"
    confianca = prob if prob > 0.5 else 1 - prob

    print(f"\n[{caminho.name}]")
    print(f"  Previsao: {pred} | prob maligno: {prob:.3f} | confianca: {confianca:.1%}")

    mapa = cam(input_tensor=entrada, targets=[BinaryClassifierOutputTarget(1)])[0]
    sobreposto = show_cam_on_image(rgb, mapa, use_rgb=True)

    axes[i][0].imshow(rgb)
    axes[i][0].set_title(f"{caminho.name}")
    axes[i][0].axis("off")
    axes[i][1].imshow(sobreposto)
    axes[i][1].set_title(f"Grad-CAM\n{pred} ({prob:.2f})")
    axes[i][1].axis("off")

plt.tight_layout()
saida = BASE_DIR / "teste_imagens.png"
plt.savefig(saida, dpi=150)
print(f"\nPainel salvo em: {saida}")
print("Lembrete: projeto academico, NAO e diagnostico medico.")