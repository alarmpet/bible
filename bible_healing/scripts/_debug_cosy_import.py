import sys
import time
from pathlib import Path

log = Path(r"C:\Users\amd\module\bible_healing\runs\_cosy_import_debug.log")
log.parent.mkdir(parents=True, exist_ok=True)
log.write_text("", encoding="utf-8")


def p(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


p("start")
sys.path.insert(0, r"D:\Fun-CosyVoice3")
sys.path.insert(0, r"D:\Fun-CosyVoice3\third_party\Matcha-TTS")
p("path ok")
import torch
p(f"torch {torch.__version__}")
from modelscope import snapshot_download
p("modelscope")
from hyperpyyaml import load_hyperpyyaml
p("hyper")
from cosyvoice.utils.file_utils import logging
p("file_utils")
from cosyvoice.utils.class_utils import get_model_type
p("class_utils")
from cosyvoice.cli.frontend import CosyVoiceFrontEnd
p("frontend")
from cosyvoice.cli.model import CosyVoiceModel, CosyVoice2Model, CosyVoice3Model
p("model")
from cosyvoice.cli.cosyvoice import AutoModel
p("AutoModel ok")
