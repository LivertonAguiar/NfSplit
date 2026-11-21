#!/usr/bin/env python3
"""
gui_moderno.py - NfSplit v1.0.0
Aplicativo Desktop Nativo, 100% Local, Sem Servidor HTTP.
Interface desenvolvida com CustomTkinter, caixas de diálogo integradas,
gestão de pastas persistente, suporte a Arraste e Solte (Drag & Drop) e OTA.
"""

import csv
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, ttk
from PIL import Image

# Suporte a Arraste e Solte (Drag & Drop) nativo do Windows
try:
    import windnd
    TEM_WINDND = True
except Exception:
    TEM_WINDND = False

# Importações do projeto
from separar_notas import processar_pdf
from updater import (
    AtualizadorOTA,
    VERSAO_ATUAL,
    REPOSITORIO_PADRAO,
    deve_verificar_atualizacao
)

# Configurações de diretório para execução direta e PyInstaller
if getattr(sys, "frozen", False):
    PASTA_BASE = Path(sys.executable).parent.resolve()
    PASTA_INTERNA = Path(sys._MEIPASS).resolve()
else:
    PASTA_BASE = Path(__file__).parent.resolve()
    PASTA_INTERNA = PASTA_BASE

CONFIG_DIR = Path.home() / ".separador_notas"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

CONFIG_FILE_LOCAL = PASTA_BASE / "config.json"
if CONFIG_FILE_LOCAL.exists():
    CONFIG_FILE = CONFIG_FILE_LOCAL

ICONE_ICO = PASTA_INTERNA / "app_icon.ico"
if not ICONE_ICO.exists():
    ICONE_ICO = PASTA_BASE / "app_icon.ico"

# Configuração Padrão inicial
CONFIG_PADRAO = {
    "juntar_boletos": True,
    "salvar_outros": True,
    "limpar_cnpj_nome": True,
    "pasta_saida_padrao": "",
    "formato_nome_nota": "NF {nf} - {nome}",
    "url_servidor_atualizacao": "",
    "verificar_atualizacoes_auto": True,
    "repositorio_github": REPOSITORIO_PADRAO,
    "ultima_verificacao_atualizacao": "",
}


def carregar_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**CONFIG_PADRAO, **cfg}
        except Exception:
            pass
    return CONFIG_PADRAO.copy()


def salvar_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# ----------------------------------------------------------------------------
# Caixas de Diálogo e Modais Nativas do Sistema (Sem usar caixas do Windows)
# ----------------------------------------------------------------------------

class DialogoModerno(ctk.CTkToplevel):
    """Caixa de diálogo modal customizada com cantos arredondados e estética nativa."""

    def __init__(
        self,
        parent,
        titulo: str,
        mensagem: str,
        tipo: str = "info",
        detalhes: str = "",
        callback_abrir_pasta: Optional[callable] = None
    ):
        super().__init__(parent)
        self.parent = parent
        self.resposta = False
        self.callback_abrir_pasta = callback_abrir_pasta

        self.title(titulo)
        self.geometry("490x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")

        paletas = {
            "sucesso": {"bg_icon": "#059669", "icon": "✔", "titulo": "#065F46"},
            "aviso": {"bg_icon": "#D97706", "icon": "⚠", "titulo": "#92400E"},
            "erro": {"bg_icon": "#DC2626", "icon": "✖", "titulo": "#991B1B"},
            "info": {"bg_icon": "#4F46E5", "icon": "ℹ", "titulo": "#3730A3"},
            "pergunta": {"bg_icon": "#4F46E5", "icon": "❓", "titulo": "#1E1B4B"},
        }
        self.cores = paletas.get(tipo, paletas["info"])
        self.tipo = tipo
        self.titulo_txt = titulo
        self.mensagem_txt = mensagem
        self.detalhes_txt = detalhes

        self._centralizar()
        self._construir_ui()

    def _centralizar(self):
        try:
            self.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w, h = 490, 320
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _construir_ui(self):
        card = ctk.CTkFrame(
            self, fg_color="#FFFFFF", corner_radius=18,
            border_width=1, border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))

        icone_lbl = ctk.CTkLabel(
            top, text=self.cores["icon"],
            width=46, height=46, corner_radius=14,
            fg_color=self.cores["bg_icon"], text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        icone_lbl.pack(side="left")

        lbl_tit = ctk.CTkLabel(
            top, text=self.titulo_txt,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0F172A", anchor="w"
        )
        lbl_tit.pack(side="left", padx=14, fill="x", expand=True)

        lbl_msg = ctk.CTkLabel(
            card, text=self.mensagem_txt,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#334155", justify="left", wraplength=410, anchor="w"
        )
        lbl_msg.pack(fill="x", padx=22, pady=(4, 8))

        if self.detalhes_txt:
            box_det = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=10, border_width=1, border_color="#E2E8F0")
            box_det.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            lbl_det = ctk.CTkLabel(
                box_det, text=self.detalhes_txt,
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color="#475569", justify="left", padx=10, pady=8
            )
            lbl_det.pack(fill="both", expand=True)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=(0, 16))

        if self.tipo == "pergunta":
            btn_sim = ctk.CTkButton(
                footer, text="Confirmar", command=self._confirmar,
                width=110, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_sim.pack(side="right", padx=(8, 0))

            btn_nao = ctk.CTkButton(
                footer, text="Cancelar", command=self._cancelar,
                width=90, height=36, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
                text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            btn_nao.pack(side="right")

        elif self.tipo == "sucesso" and self.callback_abrir_pasta:
            btn_fechar = ctk.CTkButton(
                footer, text="Concluído", command=self._confirmar,
                width=100, height=36, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
                text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            btn_fechar.pack(side="right")

            btn_abrir = ctk.CTkButton(
                footer, text="📂 Abrir Pasta Gerada", command=self._abrir_pasta,
                width=165, height=36, corner_radius=10, fg_color="#059669", hover_color="#047857",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_abrir.pack(side="right", padx=(0, 8))
        else:
            btn_ok = ctk.CTkButton(
                footer, text="OK", command=self._confirmar,
                width=100, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            btn_ok.pack(side="right")

    def _confirmar(self):
        self.resposta = True
        self.destroy()

    def _cancelar(self):
        self.resposta = False
        self.destroy()

    def _abrir_pasta(self):
        if self.callback_abrir_pasta:
            self.callback_abrir_pasta()
        self.destroy()


def mostrar_aviso(parent, titulo: str, mensagem: str):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="aviso")
    parent.wait_window(dlg)


def mostrar_erro(parent, titulo: str, mensagem: str, detalhes: str = ""):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="erro", detalhes=detalhes)
    parent.wait_window(dlg)


def mostrar_sucesso(parent, titulo: str, mensagem: str, detalhes: str = "", callback_abrir_pasta=None):
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="sucesso", detalhes=detalhes, callback_abrir_pasta=callback_abrir_pasta)
    parent.wait_window(dlg)


def mostrar_confirmacao(parent, titulo: str, mensagem: str) -> bool:
    dlg = DialogoModerno(parent, titulo, mensagem, tipo="pergunta")
    parent.wait_window(dlg)
    return dlg.resposta


# ----------------------------------------------------------------------------
# Diálogo Especial: Solicitação de Pasta de Salvamento na Primeira Execução
# ----------------------------------------------------------------------------

class DialogoPrimeiraPasta(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pasta_escolhida = ""

        self.title("Definir Local de Salvamento")
        self.geometry("520x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self._construir_ui()

    def _construir_ui(self):
        card = ctk.CTkFrame(
            self, fg_color="#FFFFFF", corner_radius=18,
            border_width=1, border_color="#E2E8F0"
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))

        icone = ctk.CTkLabel(
            top, text="📁", width=46, height=46, corner_radius=14,
            fg_color="#EEF2FF", text_color="#4F46E5",
            font=ctk.CTkFont(family="Segoe UI", size=22)
        )
        icone.pack(side="left")

        lbl_tit = ctk.CTkLabel(
            top, text="Onde deseja salvar os arquivos?",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0F172A"
        )
        lbl_tit.pack(side="left", padx=14)

        lbl_desc = ctk.CTkLabel(
            card,
            text="Para manter suas notas e boletos organizados, escolha uma pasta no seu computador onde os PDFs separados serão guardados.\n\nEssa pasta ficará salva automaticamente como padrão para os próximos usos.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", justify="left", wraplength=440
        )
        lbl_desc.pack(fill="x", padx=20, pady=(4, 12))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 16))

        sugestao = str(Path.home() / "Desktop" / "Notas_Separadas")
        self.var_caminho = ctk.StringVar(value=sugestao)

        self.entry = ctk.CTkEntry(
            row, textvariable=self.var_caminho, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Button-1>", lambda e: self._procurar())
        if hasattr(self.entry, "_entry"):
            self.entry._entry.configure(cursor="hand2")
            self.entry._entry.bind("<Button-1>", lambda e: self._procurar())
        if hasattr(self.entry, "_canvas"):
            self.entry._canvas.configure(cursor="hand2")

        btn_proc = ctk.CTkButton(
            row, text="Escolher...", command=self._procurar,
            width=90, height=34, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_proc.pack(side="left")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=(0, 16))

        btn_confirmar = ctk.CTkButton(
            footer, text="✔  Salvar Pasta e Continuar", command=self._confirmar,
            width=190, height=38, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_confirmar.pack(side="right", padx=(8, 0))

        btn_cancelar = ctk.CTkButton(
            footer, text="Cancelar", command=self.destroy,
            width=90, height=38, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#334155", font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_cancelar.pack(side="right")

    def _procurar(self):
        p = filedialog.askdirectory(title="Selecione onde salvar as notas separadas")
        if p:
            self.var_caminho.set(p)

    def _confirmar(self):
        caminho = self.var_caminho.get().strip()
        if not caminho:
            mostrar_aviso(self, "Atenção", "Por favor, selecione uma pasta válida para continuar.")
            return
        self.pasta_escolhida = caminho
        self.destroy()


# ----------------------------------------------------------------------------
# Janelas Modais: Notificação de Nova Versão e Progresso de Download OTA
# ----------------------------------------------------------------------------

class DialogoNovaVersao(ctk.CTkToplevel):
    def __init__(self, parent, info_versao: dict):
        super().__init__(parent)
        self.parent = parent
        self.info = info_versao
        self.title("🚀 Atualização Disponível • NfSplit")
        self.geometry("540x540")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self._construir_ui()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_inner = ctk.CTkFrame(header, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=20)

        lbl_tit = ctk.CTkLabel(
            top_inner, text="🚀  Nova Versão Disponível!",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_tit.pack(side="left", pady=12)

        badge_nova = ctk.CTkLabel(
            top_inner, text=f"Versão {self.info.get('tag', '')}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#059669", text_color="#FFFFFF", corner_radius=8, padx=8, pady=3
        )
        badge_nova.pack(side="right", pady=18)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        card_comp = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#E2E8F0")
        card_comp.pack(fill="x", pady=(0, 12), ipady=4)

        row_comp = ctk.CTkFrame(card_comp, fg_color="transparent")
        row_comp.pack(fill="x", padx=16, pady=10)

        lbl_inst = ctk.CTkLabel(
            row_comp, text=f"Versão Instalada: v{VERSAO_ATUAL}",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#64748B"
        )
        lbl_inst.pack(side="left")

        tamanho_mb = self.info.get("tamanho_bytes", 0) / 1024 / 1024
        tam_str = f" • {tamanho_mb:.1f} MB" if tamanho_mb > 0 else ""
        lbl_disp = ctk.CTkLabel(
            row_comp, text=f"Nova no GitHub: {self.info.get('tag', '')}{tam_str}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#059669"
        )
        lbl_disp.pack(side="right")

        lbl_c_tit = ctk.CTkLabel(
            body, text="📋 Novidades e Melhorias desta Versão:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_c_tit.pack(anchor="w", pady=(0, 6))

        txt_box = ctk.CTkTextbox(
            body, height=220, corner_radius=10,
            border_width=1, border_color="#CBD5E1", fg_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#1E293B"
        )
        txt_box.pack(fill="x", pady=(0, 10))
        txt_box.insert("1.0", self.info.get("changelog", "Melhorias de desempenho e correções gerais."))
        txt_box.configure(state="disabled")

        lbl_aviso = ctk.CTkLabel(
            body,
            text="💡 Suas configurações, preferências e pasta padrão serão preservadas automaticamente.",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#64748B"
        )
        lbl_aviso.pack(anchor="w", pady=(0, 12))

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        btn_atualizar = ctk.CTkButton(
            footer, text="⚡  Baixar e Atualizar Agora", command=self._iniciar_atualizacao,
            width=210, height=38, corner_radius=10, fg_color="#059669", hover_color="#047857",
            text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_atualizar.pack(side="left")

        btn_depois = ctk.CTkButton(
            footer, text="Lembrar Mais Tarde", command=self.destroy,
            width=140, height=38, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_depois.pack(side="right")

    def _iniciar_atualizacao(self):
        self.destroy()
        DialogoProgressoDownload(self.parent, self.info)


class DialogoProgressoDownload(ctk.CTkToplevel):
    def __init__(self, parent, info_versao: dict):
        super().__init__(parent)
        self.parent = parent
        self.info = info_versao
        self.title("Baixando Atualização • NfSplit")
        self.geometry("480x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self._construir_ui()
        self.after(300, self._iniciar_download)

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=58)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl_tit = ctk.CTkLabel(
            header, text=f"📥  Baixando NfSplit {self.info.get('tag', '')}...",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_tit.pack(side="left", padx=20, pady=14)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=24, pady=18)

        self.lbl_detalhe = ctk.CTkLabel(
            body, text="Conectando aos servidores do GitHub...",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#475569"
        )
        self.lbl_detalhe.pack(anchor="w", pady=(4, 8))

        self.progress_bar = ctk.CTkProgressBar(
            body, height=12, corner_radius=6,
            fg_color="#E2E8F0", progress_color="#4F46E5", mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)

        self.lbl_stats = ctk.CTkLabel(
            body, text="0.0 MB / 0.0 MB (0%)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#0F172A"
        )
        self.lbl_stats.pack(anchor="w")

        self.lbl_msg_final = ctk.CTkLabel(
            body, text="Por favor, aguarde. O aplicativo será reiniciado automaticamente após o download.",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#64748B"
        )
        self.lbl_msg_final.pack(anchor="w", pady=(10, 0))

    def _iniciar_download(self):
        def _worker():
            url = self.info.get("url_download")
            atualizador = AtualizadorOTA(versao_atual=VERSAO_ATUAL)

            def _callback(baixados, total):
                if total > 0:
                    pct = baixados / total
                    pct_int = int(pct * 100)
                    mb_baixados = baixados / 1024 / 1024
                    mb_total = total / 1024 / 1024
                    self.after(0, lambda: self._atualizar_progresso(pct, mb_baixados, mb_total, pct_int))

            sucesso, msg, temp_exe = atualizador.baixar_atualizacao(url, callback_progresso=_callback)

            if sucesso and temp_exe:
                self.after(0, lambda: self._finalizar_instalacao(temp_exe))
            else:
                self.after(0, lambda: self._falha_download(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _atualizar_progresso(self, pct, mb_baixados, mb_total, pct_int):
        try:
            self.progress_bar.set(pct)
            self.lbl_stats.configure(text=f"{mb_baixados:.1f} MB de {mb_total:.1f} MB ({pct_int}%)")
            self.lbl_detalhe.configure(text="Transferindo nova versão a partir do GitHub Releases...")
        except Exception:
            pass

    def _finalizar_instalacao(self, temp_exe: Path):
        self.lbl_detalhe.configure(text="✔ Download concluído com sucesso!")
        self.lbl_stats.configure(text="100% Concluído")
        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#059669")
        self.lbl_msg_final.configure(
            text="Aplicando nova versão e reiniciando o NfSplit... Aguarde.",
            text_color="#059669"
        )
        self.update()

        def _aplicar():
            time.sleep(1)
            sucesso, msg = AtualizadorOTA.aplicar_atualizacao_ota(temp_exe)
            if not sucesso:
                self.after(0, lambda: mostrar_erro(self, "Falha na Atualização", msg))
            else:
                try:
                    self.parent.destroy()
                except Exception:
                    pass
                sys.exit(0)

        threading.Thread(target=_aplicar, daemon=True).start()

    def _falha_download(self, erro_msg: str):
        mostrar_erro(
            self,
            "Erro no Download",
            f"Não foi possível concluir o download da nova versão:\n{erro_msg}\n\nPor favor, tente novamente mais tarde."
        )
        self.destroy()


# ----------------------------------------------------------------------------
# Janela Modal: Sobre, Versões, Changelog e Atualizador OTA
# ----------------------------------------------------------------------------

class JanelaSobre(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Sobre o NfSplit • Versões & Atualizações")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.configure(fg_color="#F8FAFC")
        self.cfg = carregar_config()
        self._construir_ui()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        top_inner = ctk.CTkFrame(header, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=20)

        lbl_tit = ctk.CTkLabel(
            top_inner, text=f"NfSplit v{VERSAO_ATUAL}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_tit.pack(side="left", pady=12)

        badge = ctk.CTkLabel(
            top_inner, text="Release Oficial",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#312E81", text_color="#38BDF8", corner_radius=10, padx=10, pady=4
        )
        badge.pack(side="left", padx=10, pady=18)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Card Novidades
        card_nov = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_nov.pack(fill="x", pady=(0, 12), padx=2, ipady=4)

        lbl_nov_tit = ctk.CTkLabel(
            card_nov, text="📋 Novidades da Versão 1.0.0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_nov_tit.pack(anchor="w", padx=16, pady=(10, 6))

        novidades = (
            "• Suporte completo a Arraste e Solte (Drag & Drop) de arquivos PDF.\n"
            "• Executável nativo único (.exe) autônomo, 100% local e sem servidor.\n"
            "• Caixas de diálogo nativas personalizadas integradas à interface.\n"
            "• Solicitação e gravação persistente da pasta de destino na primeira execução.\n"
            "• Extração de DANFEs por Chave de Acesso (44 dígitos) e agregação multi-página.\n"
            "• Leitor universal de boletos FEBRABAN com valores em centavos e vencimentos.\n"
            "• Geração de relatório de faturamento compatível com Microsoft Excel (CSV UTF-8 BOM)."
        )
        lbl_nov_txt = ctk.CTkLabel(
            card_nov, text=novidades,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569", justify="left", wraplength=480
        )
        lbl_nov_txt.pack(anchor="w", padx=16, pady=(0, 10))

        # Card OTA
        card_ota = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_ota.pack(fill="x", pady=(0, 14), padx=2, ipady=6)

        top_ota = ctk.CTkFrame(card_ota, fg_color="transparent")
        top_ota.pack(fill="x", padx=16, pady=(10, 6))

        lbl_ota_t = ctk.CTkLabel(
            top_ota, text="🔄 Atualizações de Software (GitHub Releases)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ota_t.pack(side="left")

        lbl_ota_st = ctk.CTkLabel(
            top_ota, text="🟢 Conectado ao GitHub",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#059669"
        )
        lbl_ota_st.pack(side="right")

        lbl_ota_desc = ctk.CTkLabel(
            card_ota,
            text="O NfSplit busca novas versões diretamente no GitHub Releases oficial. Ele realiza verificação semanal automática e você pode buscar manualmente a qualquer momento. Ao confirmar, o download ocorre em segundo plano com substituição automática do executável, preservando todas as suas configurações.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B", justify="left", wraplength=480
        )
        lbl_ota_desc.pack(anchor="w", padx=16, pady=(0, 10))

        self.btn_verificar = ctk.CTkButton(
            card_ota, text="🔍  Verificar Atualizações Agora", command=self._verificar_atualizacoes,
            width=220, height=34, corner_radius=10, fg_color="#E2E8F0", hover_color="#CBD5E1",
            text_color="#1E293B", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.btn_verificar.pack(anchor="w", padx=16, pady=(0, 10))

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        btn_fechar = ctk.CTkButton(
            footer, text="Fechar", command=self.destroy,
            width=100, height=36, corner_radius=10, fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_fechar.pack(side="right")

    def _verificar_atualizacoes(self):
        self.btn_verificar.configure(state="disabled", text="⏳  Verificando no GitHub...")

        def _worker():
            url_custom = self.cfg.get("url_servidor_atualizacao", "").strip()
            repo = self.cfg.get("repositorio_github", REPOSITORIO_PADRAO)
            atualizador = AtualizadorOTA(versao_atual=VERSAO_ATUAL, repo=repo, url_custom=url_custom)
            sucesso, msg, dados = atualizador.verificar_atualizacao()

            self.cfg["ultima_verificacao_atualizacao"] = datetime.now().isoformat()
            salvar_config(self.cfg)

            def _concluir():
                try:
                    self.btn_verificar.configure(state="normal", text="🔍  Verificar Atualizações Agora")
                except Exception:
                    pass

                if sucesso and dados:
                    DialogoNovaVersao(self.parent, dados)
                elif dados and not sucesso and ("mais recente" in msg or "já está" in msg):
                    mostrar_sucesso(
                        self,
                        "Sistema Atualizado!",
                        f"Parabéns! Você já está utilizando a versão mais recente do NfSplit (v{VERSAO_ATUAL})."
                    )
                else:
                    mostrar_aviso(self, "Verificação OTA", msg)

            self.after(0, _concluir)

        threading.Thread(target=_worker, daemon=True).start()


# ----------------------------------------------------------------------------
# Janela Modal de Configurações
# ----------------------------------------------------------------------------

class JanelaConfiguracoes(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configurações do NfSplit")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.cfg = carregar_config()
        self.configure(fg_color="#F8FAFC")
        self._construir_ui()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl = ctk.CTkLabel(
            header, text="⚙  Preferências e Padrões do Sistema",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl.pack(side="left", padx=24, pady=18)

        body = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        body.pack(fill="both", expand=True, padx=22, pady=16)

        # Card Opções
        card_opts = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_opts.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        lbl_sec = ctk.CTkLabel(
            card_opts, text="Comportamento Padrão de Processamento",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_sec.pack(anchor="w", padx=16, pady=(10, 8))

        self.var_juntar = ctk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        c1 = ctk.CTkCheckBox(
            card_opts, text="Sempre juntar Nota + Boleto em PDF único",
            variable=self.var_juntar, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c1.pack(anchor="w", padx=16, pady=4)

        self.var_outros = ctk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        c2 = ctk.CTkCheckBox(
            card_opts, text="Sempre salvar Mapas e Acertos de Carga por padrão",
            variable=self.var_outros, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c2.pack(anchor="w", padx=16, pady=4)

        self.var_limpar_cnpj = ctk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        c3 = ctk.CTkCheckBox(
            card_opts, text="Sempre limpar CNPJ do início da Razão Social",
            variable=self.var_limpar_cnpj, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        c3.pack(anchor="w", padx=16, pady=(4, 10))

        # Card Pasta Padrão
        card_pasta = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_pasta.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        lbl_pasta = ctk.CTkLabel(
            card_pasta, text="Pasta de Saída Padrão (Gravada)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_pasta.pack(anchor="w", padx=16, pady=(10, 6))

        row_pasta = ctk.CTkFrame(card_pasta, fg_color="transparent")
        row_pasta.pack(fill="x", padx=16, pady=(0, 10))

        self.var_pasta = ctk.StringVar(value=self.cfg.get("pasta_saida_padrao", ""))
        e_pasta = ctk.CTkEntry(
            row_pasta, textvariable=self.var_pasta, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou em Procurar para definir a pasta...",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        e_pasta.pack(side="left", fill="x", expand=True, padx=(0, 8))
        e_pasta.bind("<Button-1>", lambda e: self._procurar_pasta())
        if hasattr(e_pasta, "_entry"):
            e_pasta._entry.configure(cursor="hand2")
            e_pasta._entry.bind("<Button-1>", lambda e: self._procurar_pasta())
        if hasattr(e_pasta, "_canvas"):
            e_pasta._canvas.configure(cursor="hand2")

        btn_procurar = ctk.CTkButton(
            row_pasta, text="Procurar...", command=self._procurar_pasta,
            width=90, height=34, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_procurar.pack(side="left")

        # Card Servidor OTA e GitHub
        card_ota = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=14, border_width=1, border_color="#E2E8F0")
        card_ota.pack(fill="x", pady=(0, 16), padx=2, ipady=6)

        lbl_ota = ctk.CTkLabel(
            card_ota, text="Atualizações de Software (GitHub Releases & OTA)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ota.pack(anchor="w", padx=16, pady=(8, 4))

        self.var_auto_update = ctk.BooleanVar(value=self.cfg.get("verificar_atualizacoes_auto", True))
        chk_auto = ctk.CTkCheckBox(
            card_ota, text="Verificar novas versões automaticamente toda semana",
            variable=self.var_auto_update, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#1E293B"
        )
        chk_auto.pack(anchor="w", padx=16, pady=(2, 6))

        row_repo = ctk.CTkFrame(card_ota, fg_color="transparent")
        row_repo.pack(fill="x", padx=16, pady=(0, 6))

        lbl_repo = ctk.CTkLabel(
            row_repo, text="Repositório GitHub:", width=130, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#475569"
        )
        lbl_repo.pack(side="left")

        self.var_repo = ctk.StringVar(value=self.cfg.get("repositorio_github", REPOSITORIO_PADRAO))
        e_repo = ctk.CTkEntry(
            row_repo, textvariable=self.var_repo, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="LivertonAguiar/NfSplit",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        e_repo.pack(side="left", fill="x", expand=True)

        self.var_ota_url = ctk.StringVar(value=self.cfg.get("url_servidor_atualizacao", ""))
        e_ota = ctk.CTkEntry(
            card_ota, textvariable=self.var_ota_url, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Servidor customizado (opcional, deixe vazio para usar GitHub oficial)",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        e_ota.pack(fill="x", padx=16, pady=(4, 10))

        # Rodapé
        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        btn_salvar = ctk.CTkButton(
            footer, text="✔  Salvar Padrões", command=self._salvar,
            width=140, height=38, corner_radius=10, fg_color="#4F46E5",
            hover_color="#4338CA", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_salvar.pack(side="right", padx=(8, 0))

        btn_cancelar = ctk.CTkButton(
            footer, text="Cancelar", command=self.destroy,
            width=90, height=38, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_cancelar.pack(side="right")

        btn_reset = ctk.CTkButton(
            footer, text="Restaurar Padrões", command=self._restaurar_padrao,
            width=130, height=34, corner_radius=8, fg_color="#F1F5F9",
            hover_color="#E2E8F0", text_color="#64748B",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        btn_reset.pack(side="left")

    def _procurar_pasta(self):
        p = filedialog.askdirectory(title="Selecione a Pasta de Saída Padrão")
        if p:
            self.var_pasta.set(p)

    def _restaurar_padrao(self):
        if mostrar_confirmacao(self, "Restaurar Padrões", "Deseja restaurar todas as configurações para o padrão original de fábrica?"):
            self.var_juntar.set(CONFIG_PADRAO["juntar_boletos"])
            self.var_outros.set(CONFIG_PADRAO["salvar_outros"])
            self.var_limpar_cnpj.set(CONFIG_PADRAO["limpar_cnpj_nome"])
            self.var_pasta.set(CONFIG_PADRAO["pasta_saida_padrao"])
            self.var_auto_update.set(CONFIG_PADRAO["verificar_atualizacoes_auto"])
            self.var_repo.set(CONFIG_PADRAO["repositorio_github"])
            self.var_ota_url.set(CONFIG_PADRAO["url_servidor_atualizacao"])

    def _salvar(self):
        nova_cfg = {
            "juntar_boletos": self.var_juntar.get(),
            "salvar_outros": self.var_outros.get(),
            "limpar_cnpj_nome": self.var_limpar_cnpj.get(),
            "pasta_saida_padrao": self.var_pasta.get().strip(),
            "formato_nome_nota": self.cfg.get("formato_nome_nota", "NF {nf} - {nome}"),
            "url_servidor_atualizacao": self.var_ota_url.get().strip(),
            "verificar_atualizacoes_auto": self.var_auto_update.get(),
            "repositorio_github": self.var_repo.get().strip() or REPOSITORIO_PADRAO,
            "ultima_verificacao_atualizacao": self.cfg.get("ultima_verificacao_atualizacao", ""),
        }
        salvar_config(nova_cfg)

        self.parent.var_juntar.set(nova_cfg["juntar_boletos"])
        self.parent.var_outros.set(nova_cfg["salvar_outros"])
        self.parent.var_limpar_cnpj.set(nova_cfg["limpar_cnpj_nome"])
        self.parent.var_saida.set(nova_cfg["pasta_saida_padrao"])
        self.parent.cfg = nova_cfg

        mostrar_sucesso(self, "Preferências Salvas", "As configurações foram atualizadas e salvas com sucesso!")
        self.destroy()


# ----------------------------------------------------------------------------
# Janela Principal do Aplicativo NfSplit v1.0.0
# ----------------------------------------------------------------------------

class AppSeparador(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NfSplit • Separador de Notas & Boletos")
        self.geometry("1060x780")
        self.minsize(940, 680)

        if ICONE_ICO.exists():
            try:
                self.iconbitmap(str(ICONE_ICO))
            except Exception:
                pass

        self.cfg = carregar_config()
        self.configure(fg_color="#F8FAFC")

        self._construir_interface()

        # Ativa o suporte a Arraste e Solte (Drag & Drop) nativo
        if TEM_WINDND:
            try:
                windnd.hook_dropfiles(self, func=self._on_arquivos_soltos)
            except Exception:
                pass

        # Checagem semanal automática de atualizações em segundo plano
        self.after(2500, self._checar_atualizacoes_background)

    def _construir_interface(self):
        # --------------------------------------------------------------------
        # 1. Header Superior Moderno
        # --------------------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color="#1E1B4B", corner_radius=0, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=24)

        lbl_box = ctk.CTkFrame(header_content, fg_color="transparent")
        lbl_box.pack(side="left", pady=12)

        lbl_titulo = ctk.CTkLabel(
            lbl_box, text="📄  NfSplit",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            lbl_box, text=f"v{VERSAO_ATUAL} • Classificação de DANFEs e Boletos • 100% Offline • Sem Servidor",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#C7D2FE"
        )
        lbl_sub.pack(anchor="w")

        # Botões do Header
        btn_box = ctk.CTkFrame(header_content, fg_color="transparent")
        btn_box.pack(side="right", pady=16)

        btn_sobre = ctk.CTkButton(
            btn_box, text="ℹ  Sobre & OTA", command=self._abrir_sobre,
            width=120, height=36, corner_radius=12, fg_color="#312E81",
            hover_color="#4338CA", text_color="#38BDF8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_sobre.pack(side="left", padx=(0, 8))

        btn_config = ctk.CTkButton(
            btn_box, text="⚙  Configurações", command=self._abrir_configuracoes,
            width=135, height=36, corner_radius=12, fg_color="#312E81",
            hover_color="#4338CA", text_color="#E0E7FF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_config.pack(side="left", padx=(0, 10))

        badge = ctk.CTkLabel(
            btn_box, text="● 100% Local",
            corner_radius=12, fg_color="#312E81", text_color="#34D399",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12, pady=6
        )
        badge.pack(side="left")

        # --------------------------------------------------------------------
        # Container Central
        # --------------------------------------------------------------------
        content = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # --------------------------------------------------------------------
        # 2. Card de Arquivos com Zona de Arraste e Solte (Dropzone)
        # --------------------------------------------------------------------
        card_sel = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        card_sel.pack(fill="x", pady=(0, 12), ipady=4)

        pad_sel = ctk.CTkFrame(card_sel, fg_color="transparent")
        pad_sel.pack(fill="x", padx=20, pady=14)

        # Zona Visual de Arraste e Solte (Drag & Drop)
        self.drop_zone = ctk.CTkFrame(
            pad_sel, fg_color="#F8FAFC", corner_radius=12,
            border_width=2, border_color="#C7D2FE", cursor="hand2"
        )
        self.drop_zone.pack(fill="x", pady=(0, 12), ipady=6)
        self.drop_zone.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_icon = ctk.CTkLabel(
            self.drop_zone, text="📥",
            font=ctk.CTkFont(size=24), text_color="#4F46E5"
        )
        self.lbl_drop_icon.pack(pady=(6, 2))
        self.lbl_drop_icon.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_title = ctk.CTkLabel(
            self.drop_zone, text="Arraste e solte o arquivo PDF da carga aqui",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1E1B4B"
        )
        self.lbl_drop_title.pack(pady=(0, 2))
        self.lbl_drop_title.bind("<Button-1>", lambda e: self._selecionar_pdf())

        self.lbl_drop_sub = ctk.CTkLabel(
            self.drop_zone, text="ou utilize os botões abaixo para selecionar o arquivo / pasta",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B"
        )
        self.lbl_drop_sub.pack(pady=(0, 6))
        self.lbl_drop_sub.bind("<Button-1>", lambda e: self._selecionar_pdf())

        # Linha Entrada
        row_in = ctk.CTkFrame(pad_sel, fg_color="transparent")
        row_in.pack(fill="x", pady=(0, 10))

        lbl_ent = ctk.CTkLabel(
            row_in, text="Arquivo da Carga:", width=130, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_ent.pack(side="left")

        self.var_entrada = ctk.StringVar()
        self.entry_entrada = ctk.CTkEntry(
            row_in, textvariable=self.var_entrada, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou arraste o PDF para carregar...",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_entrada.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_entrada.bind("<Button-1>", lambda e: self._selecionar_pdf())
        if hasattr(self.entry_entrada, "_entry"):
            self.entry_entrada._entry.configure(cursor="hand2")
            self.entry_entrada._entry.bind("<Button-1>", lambda e: self._selecionar_pdf())
        if hasattr(self.entry_entrada, "_canvas"):
            self.entry_entrada._canvas.configure(cursor="hand2")

        btn_pdf = ctk.CTkButton(
            row_in, text="📂 Selecionar PDF", command=self._selecionar_pdf,
            width=135, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        btn_pdf.pack(side="left", padx=3)

        btn_pasta = ctk.CTkButton(
            row_in, text="📁 Pasta Inteira", command=self._selecionar_pasta_origem,
            width=115, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_pasta.pack(side="left", padx=3)

        # Linha Saída
        row_out = ctk.CTkFrame(pad_sel, fg_color="transparent")
        row_out.pack(fill="x")

        lbl_sai = ctk.CTkLabel(
            row_out, text="Salvar Arquivos em:", width=130, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_sai.pack(side="left")

        self.var_saida = ctk.StringVar(value=self.cfg.get("pasta_saida_padrao", ""))
        self.entry_saida = ctk.CTkEntry(
            row_out, textvariable=self.var_saida, corner_radius=10,
            border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#0F172A",
            placeholder_text="Clique aqui ou no botão para escolher a pasta...",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_saida.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_saida.bind("<Button-1>", lambda e: self._selecionar_pasta_saida())
        if hasattr(self.entry_saida, "_entry"):
            self.entry_saida._entry.configure(cursor="hand2")
            self.entry_saida._entry.bind("<Button-1>", lambda e: self._selecionar_pasta_saida())
        if hasattr(self.entry_saida, "_canvas"):
            self.entry_saida._canvas.configure(cursor="hand2")

        btn_dest = ctk.CTkButton(
            row_out, text="Alterar Pasta", command=self._selecionar_pasta_saida,
            width=115, height=36, corner_radius=10, fg_color="#E2E8F0",
            hover_color="#CBD5E1", text_color="#1E293B",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        btn_dest.pack(side="left", padx=3)

        # --------------------------------------------------------------------
        # 3. Card de Opções
        # --------------------------------------------------------------------
        card_opts = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        card_opts.pack(fill="x", pady=(0, 12), ipady=4)

        pad_opts = ctk.CTkFrame(card_opts, fg_color="transparent")
        pad_opts.pack(fill="x", padx=20, pady=12)

        header_opts = ctk.CTkFrame(pad_opts, fg_color="transparent")
        header_opts.pack(fill="x", pady=(0, 8))

        lbl_opts_t = ctk.CTkLabel(
            header_opts, text="Opções da Execução:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#0F172A"
        )
        lbl_opts_t.pack(side="left")

        lbl_opts_sub = ctk.CTkLabel(
            header_opts, text="(Padrões configurados)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B"
        )
        lbl_opts_sub.pack(side="left", padx=6)

        opts_row = ctk.CTkFrame(pad_opts, fg_color="transparent")
        opts_row.pack(fill="x")

        self.var_juntar = ctk.BooleanVar(value=self.cfg.get("juntar_boletos", True))
        chk1 = ctk.CTkCheckBox(
            opts_row, text="Juntar Nota + Boleto em PDF único",
            variable=self.var_juntar, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk1.pack(side="left", padx=(0, 24))

        self.var_outros = ctk.BooleanVar(value=self.cfg.get("salvar_outros", True))
        chk2 = ctk.CTkCheckBox(
            opts_row, text="Salvar Mapas de Entrega e Acertos de Carga",
            variable=self.var_outros, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk2.pack(side="left", padx=(0, 24))

        self.var_limpar_cnpj = ctk.BooleanVar(value=self.cfg.get("limpar_cnpj_nome", True))
        chk3 = ctk.CTkCheckBox(
            opts_row, text="Limpar CNPJ da Razão Social",
            variable=self.var_limpar_cnpj, corner_radius=6, border_color="#CBD5E1",
            fg_color="#4F46E5", hover_color="#4338CA",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#1E293B"
        )
        chk3.pack(side="left")

        # --------------------------------------------------------------------
        # 4. Barra de Ações
        # --------------------------------------------------------------------
        actions_bar = ctk.CTkFrame(content, fg_color="transparent")
        actions_bar.pack(fill="x", pady=(0, 8))

        self.btn_iniciar = ctk.CTkButton(
            actions_bar, text="⚡  PROCESSAR E SEPARAR ARQUIVOS", command=self._iniciar_processamento,
            width=260, height=44, corner_radius=12, fg_color="#4F46E5",
            hover_color="#4338CA", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.btn_iniciar.pack(side="left")

        self.btn_abrir_pasta = ctk.CTkButton(
            actions_bar, text="📂 Abrir Pasta Gerada", command=self._abrir_pasta_saida,
            width=175, height=44, corner_radius=12, fg_color="#059669",
            hover_color="#047857", text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            state="disabled"
        )
        self.btn_abrir_pasta.pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(
            actions_bar, text="Pronto para processar.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748B"
        )
        self.lbl_status.pack(side="right", pady=8)

        self.progress_bar = ctk.CTkProgressBar(
            content, height=8, corner_radius=8,
            fg_color="#E2E8F0", progress_color="#4F46E5", mode="indeterminate"
        )

        # --------------------------------------------------------------------
        # 5. Tabela de Resultados Moderna
        # --------------------------------------------------------------------
        self.table_card = ctk.CTkFrame(
            content, fg_color="#FFFFFF", corner_radius=16,
            border_width=1, border_color="#E2E8F0"
        )
        self.table_card.pack(fill="both", expand=True)

        top_table = ctk.CTkFrame(self.table_card, fg_color="transparent", height=36)
        top_table.pack(fill="x", padx=16, pady=(12, 6))

        lbl_table_tit = ctk.CTkLabel(
            top_table, text="📋  Documentos Processados",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0F172A"
        )
        lbl_table_tit.pack(side="left")

        self.lbl_badge_count = ctk.CTkLabel(
            top_table, text="0 itens",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#F1F5F9", text_color="#475569",
            corner_radius=8, padx=10, pady=3
        )
        self.lbl_badge_count.pack(side="right")

        self.colunas_tabela = [
            ("Tipo", 100, "center"),
            ("Nº NF", 80, "center"),
            ("Destinatário / Pagador", 0, "w"),
            ("CNPJ / CPF", 145, "center"),
            ("Valor Total", 115, "e"),
            ("Forma Pgto", 100, "center"),
            ("Pág.", 60, "center"),
            ("Ação", 65, "center")
        ]

        self.header_frame = ctk.CTkFrame(
            self.table_card, fg_color="#F8FAFC", corner_radius=8,
            height=36, border_width=1, border_color="#E2E8F0"
        )
        self.header_frame.pack(fill="x", padx=(16, 28), pady=(0, 4))
        self.header_frame.pack_propagate(False)

        for i, (col_name, col_width, col_anchor) in enumerate(self.colunas_tabela):
            if col_width == 0:
                self.header_frame.grid_columnconfigure(i, weight=1)
            else:
                self.header_frame.grid_columnconfigure(i, minsize=col_width, weight=0)
            lbl = ctk.CTkLabel(
                self.header_frame, text=col_name,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#475569"
            )
            sticky = "ew" if col_width == 0 else ("w" if col_anchor == "w" else ("e" if col_anchor == "e" else ""))
            lbl.grid(row=0, column=i, sticky=sticky, padx=8, pady=6)

        self.scroll_tabela = ctk.CTkScrollableFrame(
            self.table_card, fg_color="#FFFFFF", corner_radius=10,
            scrollbar_button_color="#CBD5E1", scrollbar_button_hover_color="#94A3B8"
        )
        self.scroll_tabela.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._mostrar_empty_state()

    # ------------------------------------------------------------------------
    # Métodos e Ações de Arraste e Solte
    # ------------------------------------------------------------------------

    def _on_arquivos_soltos(self, arquivos):
        """Manipula os arquivos arrastados e soltos sobre a janela do aplicativo."""
        if not arquivos:
            return

        caminho = arquivos[0]
        if isinstance(caminho, bytes):
            try:
                caminho = caminho.decode("mbcs")
            except Exception:
                caminho = caminho.decode("utf-8", errors="replace")

        p = Path(caminho)
        if p.is_dir() or p.suffix.lower() == ".pdf":
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)
            self.lbl_status.configure(text=f"Carregado via Arraste: {p.name}")
        else:
            mostrar_aviso(
                self,
                "Formato Não Suportado",
                f"O arquivo solto ({p.name}) não é um PDF válido.\nPor favor, arraste um arquivo com extensão .pdf ou uma pasta."
            )

    def _atualizar_visual_dropzone(self, p: Path):
        """Atualiza a caixa visual de arraste com informações do arquivo carregado."""
        self.drop_zone.configure(fg_color="#F0FDF4", border_color="#86EFAC")
        self.lbl_drop_icon.configure(text="✔", text_color="#059669")
        self.lbl_drop_title.configure(text=f"Arquivo Carregado: {p.name}", text_color="#065F46")
        self.lbl_drop_sub.configure(
            text="Pronto para processar! Clique em PROCESSAR E SEPARAR ou arraste outro para trocar.",
            text_color="#047857"
        )

    # ------------------------------------------------------------------------
    # Métodos e Ações
    # ------------------------------------------------------------------------

    def _abrir_configuracoes(self):
        JanelaConfiguracoes(self)

    def _abrir_sobre(self):
        JanelaSobre(self)

    def _checar_atualizacoes_background(self):
        """Verifica silenciosamente em segundo plano se existe nova versão no GitHub."""
        if not deve_verificar_atualizacao(self.cfg, dias_intervalo=7):
            return

        def _worker():
            url_custom = self.cfg.get("url_servidor_atualizacao", "").strip()
            repo = self.cfg.get("repositorio_github", REPOSITORIO_PADRAO)
            atualizador = AtualizadorOTA(versao_atual=VERSAO_ATUAL, repo=repo, url_custom=url_custom)
            sucesso, msg, dados = atualizador.verificar_atualizacao()

            self.cfg["ultima_verificacao_atualizacao"] = datetime.now().isoformat()
            salvar_config(self.cfg)

            if sucesso and dados:
                self.after(0, lambda: DialogoNovaVersao(self, dados))

        threading.Thread(target=_worker, daemon=True).start()

    def _selecionar_pdf(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo PDF da carga",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os Arquivos", "*.*")]
        )
        if caminho:
            p = Path(caminho)
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)

    def _selecionar_pasta_origem(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta com vários PDFs")
        if caminho:
            p = Path(caminho)
            self.var_entrada.set(str(p.resolve()))
            self._atualizar_visual_dropzone(p)

    def _selecionar_pasta_saida(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta de saída")
        if caminho:
            self.var_saida.set(caminho)
            self.cfg["pasta_saida_padrao"] = caminho
            salvar_config(self.cfg)

    def _abrir_pasta_saida(self):
        pasta = self.var_saida.get().strip()
        if Path(pasta).exists():
            if sys.platform == "win32":
                os.startfile(pasta)
            else:
                subprocess.run(["xdg-open", pasta])

    def _iniciar_processamento(self):
        entrada_str = self.var_entrada.get().strip()
        saida_str = self.var_saida.get().strip()

        # 1. Validação de Entrada
        if not entrada_str:
            mostrar_aviso(self, "Atenção", "Por favor, arraste ou selecione um arquivo PDF / pasta de entrada primeiro.")
            return

        p_ent = Path(entrada_str)
        if not p_ent.exists():
            mostrar_erro(self, "Arquivo Não Encontrado", "O arquivo ou pasta selecionada não existe mais no computador.")
            return

        # 2. Verificação de Pasta de Destino (Solicita se não configurada)
        if not saida_str:
            dlg_pasta = DialogoPrimeiraPasta(self)
            self.wait_window(dlg_pasta)
            if not dlg_pasta.pasta_escolhida:
                return
            saida_str = dlg_pasta.pasta_escolhida
            self.var_saida.set(saida_str)
            self.cfg["pasta_saida_padrao"] = saida_str
            salvar_config(self.cfg)

        arquivos = []
        if p_ent.is_dir():
            arquivos = sorted(p_ent.glob("*.pdf"))
        elif p_ent.suffix.lower() == ".pdf":
            arquivos = [p_ent]

        if not arquivos:
            mostrar_aviso(self, "Atenção", "Nenhum arquivo PDF encontrado no local selecionado.")
            return

        self.btn_iniciar.configure(state="disabled")
        self.btn_abrir_pasta.configure(state="disabled")
        self.lbl_status.configure(text=f"Processando {len(arquivos)} arquivo(s)... Aguarde.")
        self.progress_bar.pack(fill="x", pady=(0, 8), before=self.table_card)
        self.progress_bar.start()

        self._limpar_tabela()

        threading.Thread(
            target=self._executar_worker,
            args=(arquivos, Path(saida_str)),
            daemon=True
        ).start()

    def _mostrar_empty_state(self):
        self._limpar_tabela()
        empty_box = ctk.CTkFrame(self.scroll_tabela, fg_color="transparent")
        empty_box.pack(fill="both", expand=True, pady=45)

        lbl_icon = ctk.CTkLabel(
            empty_box, text="📄✨",
            font=ctk.CTkFont(size=36), text_color="#6366F1"
        )
        lbl_icon.pack(pady=(0, 6))

        lbl_tit = ctk.CTkLabel(
            empty_box, text="Nenhum documento processado ainda",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_tit.pack(pady=(0, 4))

        lbl_sub = ctk.CTkLabel(
            empty_box,
            text="Arraste o arquivo PDF da carga para a caixa acima ou selecione-o e clique em\n'PROCESSAR E SEPARAR ARQUIVOS' para visualizar notas e boletos classificados.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B", justify="center"
        )
        lbl_sub.pack()

    def _limpar_tabela(self):
        for w in self.scroll_tabela.winfo_children():
            w.destroy()
        self.lbl_badge_count.configure(text="0 itens")

    def _adicionar_linha_tabela(self, item: dict, indice: int, saida: Path):
        bg_base = "#FFFFFF" if indice % 2 == 0 else "#F8FAFC"
        row = ctk.CTkFrame(
            self.scroll_tabela, fg_color=bg_base, corner_radius=8,
            height=38, border_width=1, border_color="#F1F5F9"
        )
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        for i, (col_name, col_width, col_anchor) in enumerate(self.colunas_tabela):
            if col_width == 0:
                row.grid_columnconfigure(i, weight=1)
            else:
                row.grid_columnconfigure(i, minsize=col_width, weight=0)

        # 1. Badge de Tipo
        tipo = (item.get("tipo") or "").lower()
        if "nota" in tipo:
            badge_txt = "📄 DANFE"
            b_fg = "#EEF2FF"
            b_tc = "#4338CA"
        elif "boleto" in tipo:
            badge_txt = "💳 BOLETO"
            b_fg = "#ECFDF5"
            b_tc = "#047857"
        elif "mapa" in tipo:
            badge_txt = "🗺 MAPA"
            b_fg = "#FFFBEB"
            b_tc = "#B45309"
        elif "acerto" in tipo:
            badge_txt = "📋 ACERTO"
            b_fg = "#FEF3C7"
            b_tc = "#92400E"
        else:
            badge_txt = f"⚠ {tipo.upper()}"
            b_fg = "#FEF2F2"
            b_tc = "#B91C1C"

        badge = ctk.CTkLabel(
            row, text=badge_txt,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=b_fg, text_color=b_tc, corner_radius=6, padx=8, pady=3
        )
        badge.grid(row=0, column=0, padx=6, pady=4)

        # 2. Nº NF
        nf_txt = str(item.get("nf") or "-")
        lbl_nf = ctk.CTkLabel(
            row, text=nf_txt,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#0F172A"
        )
        lbl_nf.grid(row=0, column=1, padx=6, pady=4)

        # 3. Nome
        nome_txt = str(item.get("nome") or "-")
        lbl_nome = ctk.CTkLabel(
            row, text=nome_txt,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#1E293B", anchor="w"
        )
        lbl_nome.grid(row=0, column=2, sticky="w", padx=8, pady=4)

        # 4. CNPJ / CPF
        cnpj_txt = str(item.get("cnpj_cpf") or "-")
        lbl_cnpj = ctk.CTkLabel(
            row, text=cnpj_txt,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748B"
        )
        lbl_cnpj.grid(row=0, column=3, padx=6, pady=4)

        # 5. Valor Total
        val = item.get("valor_nf") or item.get("valor_boleto") or "-"
        val_txt = f"R$ {val}" if val != "-" else "-"
        lbl_val = ctk.CTkLabel(
            row, text=val_txt,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#059669" if val != "-" else "#94A3B8", anchor="e"
        )
        lbl_val.grid(row=0, column=4, sticky="e", padx=8, pady=4)

        # 6. Forma Pgto
        pgto_txt = str(item.get("forma_pgto") or "-")
        lbl_pgto = ctk.CTkLabel(
            row, text=pgto_txt,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#475569"
        )
        lbl_pgto.grid(row=0, column=5, padx=6, pady=4)

        # 7. Páginas
        pags_txt = str(item.get("paginas") or "-")
        lbl_pags = ctk.CTkLabel(
            row, text=pags_txt,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748B"
        )
        lbl_pags.grid(row=0, column=6, padx=6, pady=4)

        # Ação Abrir Arquivo
        arq_rel = item.get("arquivo")
        def _abrir_doc(e=None):
            if arq_rel:
                arq_completo = saida / arq_rel
                if arq_completo.exists():
                    if sys.platform == "win32":
                        os.startfile(arq_completo)
                    else:
                        subprocess.run(["xdg-open", str(arq_completo)])
                    return
            if saida.exists():
                if sys.platform == "win32":
                    os.startfile(saida)
                else:
                    subprocess.run(["xdg-open", str(saida)])

        # 8. Botão Abrir
        btn_acao = ctk.CTkButton(
            row, text="Abrir ↗", width=54, height=24,
            corner_radius=6, fg_color="#F1F5F9", hover_color="#E0E7FF",
            text_color="#4F46E5", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            command=_abrir_doc
        )
        btn_acao.grid(row=0, column=7, padx=6, pady=4)

        # Hover e Duplo Clique
        def _on_enter(e):
            row.configure(fg_color="#EEF2FF", border_color="#C7D2FE")
        def _on_leave(e):
            row.configure(fg_color=bg_base, border_color="#F1F5F9")

        for widget in (row, lbl_nf, lbl_nome, lbl_cnpj, lbl_val, lbl_pgto, lbl_pags):
            widget.bind("<Enter>", _on_enter)
            widget.bind("<Leave>", _on_leave)
            widget.bind("<Double-Button-1>", _abrir_doc)

    def _executar_worker(self, arquivos: list[Path], saida: Path):
        t0 = time.time()
        saida.mkdir(parents=True, exist_ok=True)
        relatorio = []
        totais = {"notas": 0, "boletos": 0, "paginas": 0}

        juntar = self.var_juntar.get()
        salvar_outros = self.var_outros.get()
        limpar_cnpj = self.var_limpar_cnpj.get()

        for pdf in arquivos:
            stats = processar_pdf(
                pdf_path=pdf,
                saida=saida,
                relatorio=relatorio,
                juntar_boletos=juntar,
                salvar_outros=salvar_outros,
                limpar_cnpj_nome=limpar_cnpj
            )
            totais["notas"] += stats["notas"]
            totais["boletos"] += stats["boletos"]
            totais["paginas"] += stats["total_paginas"]

        caminho_csv = saida / "relatorio.csv"
        campos = [
            "origem", "tipo", "nf", "parcela", "nome", "cnpj_cpf",
            "valor_nf", "valor_boleto", "vencimento", "forma_pgto",
            "banco", "paginas", "arquivo", "obs"
        ]
        with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=campos, delimiter=";")
            writer.writeheader()
            writer.writerows(relatorio)

        t_gasto = time.time() - t0
        tempo_str = f"{t_gasto:.1f}s"

        self.after(0, self._finalizar_processamento, totais, relatorio, tempo_str, saida)

    def _finalizar_processamento(self, totais: dict, relatorio: list, tempo_str: str, saida: Path):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_iniciar.configure(state="normal")
        self.btn_abrir_pasta.configure(state="normal")

        self.lbl_status.configure(
            text=f"✅ Concluído em {tempo_str}! {totais['notas']} NFs | {totais['boletos']} Boleto(s)."
        )

        self._limpar_tabela()
        self.lbl_badge_count.configure(text=f"{len(relatorio)} documentos")

        for i, item in enumerate(relatorio):
            self._adicionar_linha_tabela(item, i, saida)

        resumo_det = (
            f"⏱ Tempo: {tempo_str}\n"
            f"📄 Notas Fiscais: {totais['notas']}\n"
            f"💳 Boletos: {totais['boletos']}\n"
            f"📑 Total de Páginas: {totais['paginas']}\n\n"
            f"Destino: {saida}"
        )
        mostrar_sucesso(
            self,
            "Processamento Concluído!",
            "Os arquivos foram classificados, organizados e salvos com sucesso!",
            detalhes=resumo_det,
            callback_abrir_pasta=self._abrir_pasta_saida
        )


if __name__ == "__main__":
    app = AppSeparador()
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        p = Path(sys.argv[1]).resolve()
        app.var_entrada.set(str(p))
        app._atualizar_visual_dropzone(p)
    app.mainloop()
