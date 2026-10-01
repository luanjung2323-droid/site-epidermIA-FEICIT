"""
Logica de diagnostico da CNN (MobileNetV2 + Grad-CAM).

Extraido de prever_imagem.py: mesma classe de modelo, mesmo carregamento do
checkpoint (o mais recente em checkpoints/), mesmo pre-processamento (resize
224x224 + normalizacao ImageNet), mesmo corte sigmoid > 0.5 e mesmo Grad-CAM
(target_layers=[rede.features[-1]]). Nenhum valor foi alterado em relacao ao
script original -- a unica mudanca e a entrada: em vez de ler arquivos
minha_fotoN do disco, diagnosticar() recebe uma imagem ja em memoria.

ATENCAO: projeto academico (TCC), NAO e ferramenta de diagnostico medico.
"""

import base64
import io
from pathlib import Path

import torch
from torch import nn
from PIL import Image
from torchvision import transforms, models
import lightning as L
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import BinaryClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

BASE_DIR = Path(__file__).parent
IMG_SIZE = 224


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


def _carregar_modelo():
    ckpts = list((BASE_DIR / "checkpoints").glob("*.ckpt"))
    if not ckpts:
        raise SystemExit("Nenhum checkpoint encontrado em checkpoints/")
    ckpt = max(ckpts, key=lambda p: p.stat().st_mtime)
    print("Modelo carregado:", ckpt.name)
    return LesaoModel.load_from_checkpoint(ckpt).to(DEVICE).eval()


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODELO = _carregar_modelo()

_norm = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                              std=[0.229, 0.224, 0.225])
TF_MODELO = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)),
                                 transforms.ToTensor(), _norm])
TF_EXIBIR = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)),
                                 transforms.ToTensor()])

CAM = GradCAM(model=MODELO.rede, target_layers=[MODELO.rede.features[-1]])


def _array_para_base64_png(array_rgb_uint8):
    buffer = io.BytesIO()
    Image.fromarray(array_rgb_uint8).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def diagnosticar(imagem_pil):
    """
    Recebe uma imagem PIL e devolve a probabilidade do modelo (mesmo calculo
    de prever_imagem.py) e o Grad-CAM correspondente, para uma imagem por vez.
    """
    img = imagem_pil.convert("RGB")
    entrada = TF_MODELO(img).unsqueeze(0).to(DEVICE)
    rgb = TF_EXIBIR(img).permute(1, 2, 0).numpy()

    with torch.no_grad():
        prob = torch.sigmoid(MODELO.rede(entrada)).item()

    mapa = CAM(input_tensor=entrada, targets=[BinaryClassifierOutputTarget(1)])[0]
    sobreposto = show_cam_on_image(rgb, mapa, use_rgb=True)

    return {
        "prob": prob,
        "sugestivo": prob > 0.5,
        "grad_cam_base64": _array_para_base64_png(sobreposto),
    }
